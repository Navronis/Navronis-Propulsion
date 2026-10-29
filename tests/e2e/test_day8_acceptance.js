const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

(async () => {
  const browser = await chromium.launch({
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: true,
    args: ['--no-sandbox', '--disable-web-security']
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 950 } });

  const consoleLogs = [];
  const uncaughtErrors = [];
  page.on('console', msg => consoleLogs.push(msg.text()));
  page.on('pageerror', err => uncaughtErrors.push(err.message));

  await page.route('**/*', route => {
    const url = route.request().url();
    if (url.startsWith('http:') || url.startsWith('https:')) {
      route.abort();
    } else {
      route.continue();
    }
  });

  const indexPath = 'file:///' + path.resolve(__dirname, '../../docs/index.html').replace(/\\/g, '/');
  await page.goto(indexPath, { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(1000);

  const outDir = path.resolve(__dirname, '../../evidence_screenshots');
  if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
  }

  console.log('--- 1. INJECTOR TOPOLOGY PROGRAMMATIC INSPECTION ---');
  const injectors = ['coaxial', 'pintle', 'swirl', 'impinging'];
  const topologyReport = {};

  // Switch to cutaway view to inspect inner injector array clearly
  await page.click('#btn-cut-180');
  await page.waitForTimeout(400);

  for (const inj of injectors) {
    await page.selectOption('#inp-inj', inj);
    await page.waitForTimeout(500);

    const topo = await page.evaluate(() => window.inspectCurrentCadTopology());
    topologyReport[inj] = topo;
    console.log(`[${inj.toUpperCase()}] Meshes: ${topo.meshCount}, Vertices: ${topo.vertexCount}, Faces: ${topo.faceCount}, Hash: ${topo.geometryHash}`);
    console.log(`   Bounding Box: ${topo.bboxMm.dimensionsMm.join(' x ')} mm`);

    const canvas = await page.locator('#view-3d-wrapper');
    await canvas.screenshot({ path: path.join(outDir, `topology_injector_${inj}.png`) });
  }

  console.log('\n--- 2. TRUE SCALE COMPARISON (FIXED CAMERA 3.6m & 100mm GRID) ---');
  await page.click('#btn-cut-360');
  await page.waitForTimeout(400);

  // Enable true scale mode
  await page.click('#btn-toggle-scale');
  await page.waitForTimeout(300);

  const presets = ['rutherford', 'merlin1d', 'raptor2', 'rs25', 'rd180', 'rl10', 'lmde'];
  const presetScales = {};

  for (const p of presets) {
    await page.selectOption('#inp-engine-preset', p);
    await page.waitForTimeout(500);

    const topo = await page.evaluate(() => window.inspectCurrentCadTopology());
    presetScales[p] = topo;
    console.log(`[Preset: ${p.toUpperCase()}] True-scale BBox: ${topo.bboxMm.dimensionsMm.join(' x ')} mm, Meshes: ${topo.meshCount}`);

    const canvas = await page.locator('#view-3d-wrapper');
    await canvas.screenshot({ path: path.join(outDir, `truescale_${p}.png`) });
  }

  // Also capture fit-to-view for comparison
  await page.click('#btn-toggle-scale'); // back to fit-to-view
  await page.waitForTimeout(300);
  for (const p of ['rutherford', 'raptor2']) {
    await page.selectOption('#inp-engine-preset', p);
    await page.waitForTimeout(400);
    const canvas = await page.locator('#view-3d-wrapper');
    await canvas.screenshot({ path: path.join(outDir, `fittoview_${p}.png`) });
  }

  console.log('\n--- 3. DAY 8 SLSQP OPTIMIZER & APPLY-TO-DESIGN VERIFICATION ---');
  // Load baseline
  await page.selectOption('#inp-engine-preset', 'custom');
  await page.fill('#inp-thrust', '30000');
  await page.fill('#inp-pc', '120');
  await page.fill('#inp-eps', '30');
  await page.selectOption('#inp-prop', 'LOX/CH4');
  await page.selectOption('#inp-mat', 'CuCrZr');
  await page.click('#btn-recompute-sizing');
  await page.waitForTimeout(400);

  const baselineTopo = await page.evaluate(() => window.inspectCurrentCadTopology());
  const baselineGeom = await page.evaluate(() => window.latestEngineGeometry);
  console.log('Baseline Geometry:');
  console.log(`Pc = ${baselineGeom.pc_bar} bar, eps = ${baselineGeom.eps}`);
  console.log(`Dt = ${baselineGeom.dt_mm.toFixed(2)} mm, De = ${baselineGeom.de_mm.toFixed(2)} mm, Ltot = ${(baselineGeom.lcyl_mm + baselineGeom.lconv_mm + baselineGeom.lnoz_mm).toFixed(2)} mm`);
  console.log(`Geometry Hash = ${baselineTopo.geometryHash}, Revision = ${baselineTopo.revisionId}`);

  // Switch to MDO tab
  await page.click('#btn-view-mdo');
  await page.waitForTimeout(400);

  // Set constraint inputs
  await page.fill('#mdo-inp-maxtwg', '950');
  await page.fill('#mdo-inp-maxdp', '20.0');

  // Trigger Authentic SLSQP Solver
  console.log('\nTriggering Authentic SLSQP Solver in Browser...');
  await page.click('button[onclick="runSlsqpOptimizer()"]');

  // Wait for convergence log
  await page.waitForFunction(() => {
    const log = document.getElementById('mdo-opt-log');
    return log && log.innerText.includes('CONVERGED');
  }, { timeout: 15000 });

  const optLogText = await page.evaluate(() => document.getElementById('mdo-opt-log').innerText);
  console.log('SLSQP Execution Log:');
  console.log(optLogText);

  const optDesign = await page.evaluate(() => window.latestOptimalDesign);
  console.log('\nSLSQP Converged Design:');
  console.log(`Optimal Pc: ${optDesign.pc.toFixed(2)} bar`);
  console.log(`Optimal eps: ${optDesign.eps.toFixed(2)}`);
  console.log(`Optimal Mass Proxy: ${optDesign.mass.toFixed(3)} kg`);
  console.log(`Generated Revision ID: ${optDesign.revId}`);

  // Capture MDO panel screenshot
  const mdoPanel = await page.locator('#view-mdo-wrapper');
  await mdoPanel.screenshot({ path: path.join(outDir, 'day8_slsqp_kkt_converged.png') });

  // Apply to 3D CAD
  console.log('\nClicking "Apply to 3D CAD"...');
  await page.click('#btn-apply-opt');
  await page.waitForTimeout(600);

  const postOptTopo = await page.evaluate(() => window.inspectCurrentCadTopology());
  const postOptGeom = await page.evaluate(() => window.latestEngineGeometry);
  const pcInputVal = await page.inputValue('#inp-pc');
  const epsInputVal = await page.inputValue('#inp-eps');

  console.log('\nPost-Optimization Applied Geometry:');
  console.log(`UI Input Pc: ${pcInputVal} bar, Input eps: ${epsInputVal}`);
  console.log(`Applied Dt: ${postOptGeom.dt_mm.toFixed(2)} mm, De: ${postOptGeom.de_mm.toFixed(2)} mm, Ltot = ${(postOptGeom.lcyl_mm + postOptGeom.lconv_mm + postOptGeom.lnoz_mm).toFixed(2)} mm`);
  console.log(`New Geometry Hash: ${postOptTopo.geometryHash}`);
  console.log(`New Active Revision: ${postOptTopo.revisionId}`);

  // Capture optimized 3D CAD screenshot
  const postOptCanvas = await page.locator('#view-3d-wrapper');
  await postOptCanvas.screenshot({ path: path.join(outDir, 'day8_optimized_cad_applied.png') });

  // Write full JSON report of evidence
  const fullAuditEvidence = {
    topologyReport,
    presetScales,
    optimization: {
      baseline: {
        pc: baselineGeom.pc_bar,
        eps: baselineGeom.eps,
        dt_mm: baselineGeom.dt_mm,
        de_mm: baselineGeom.de_mm,
        ltot_mm: baselineGeom.lcyl_mm + baselineGeom.lconv_mm + baselineGeom.lnoz_mm,
        geometryHash: baselineTopo.geometryHash,
        revisionId: baselineTopo.revisionId
      },
      converged: optDesign,
      applied: {
        pc: postOptGeom.pc_bar,
        eps: postOptGeom.eps,
        dt_mm: postOptGeom.dt_mm,
        de_mm: postOptGeom.de_mm,
        ltot_mm: postOptGeom.lcyl_mm + postOptGeom.lconv_mm + postOptGeom.lnoz_mm,
        geometryHash: postOptTopo.geometryHash,
        revisionId: postOptTopo.revisionId
      }
    },
    uncaughtErrors,
    consoleLogsCount: consoleLogs.length
  };

  fs.writeFileSync(path.resolve(__dirname, 'day8_acceptance_evidence.json'), JSON.stringify(fullAuditEvidence, null, 2));
  console.log('\nWrote full audit evidence to day8_acceptance_evidence.json');

  await browser.close();
  console.log('Playwright Acceptance Journey Complete.');
})();
