const { chromium } = require('playwright');
const path = require('path');

async function getPresetStats(page) {
  return await page.evaluate(() => {
    const g = window.latestEngineGeometry || {};
    let bBox = null;
    let meshVerts = 0;
    if (window.engineGroup) {
      const box = new window.THREE.Box3().setFromObject(window.engineGroup);
      bBox = {
        spanX: +(box.max.x - box.min.x).toFixed(3),
        spanY: +(box.max.y - box.min.y).toFixed(3),
        spanZ: +(box.max.z - box.min.z).toFixed(3)
      };
      window.engineGroup.traverse(child => {
        if (child.isMesh && child.geometry) {
          const pos = child.geometry.attributes.position;
          if (pos) meshVerts += pos.count;
        }
      });
    }

    return {
      thrust_kn: +g.f_deliv_kn?.toFixed(1),
      pc_bar: +g.pc_bar?.toFixed(1),
      eps: +g.eps?.toFixed(1),
      prop: document.getElementById('inp-prop')?.value,
      cycle: document.getElementById('inp-cycle')?.value,
      inj: g.injType,
      ne: g.n_elements,
      mat: g.mat,
      nch: g.nch,
      dt_mm: +g.dt_mm?.toFixed(1),
      dc_mm: +g.dc_mm?.toFixed(1),
      de_mm: +g.de_mm?.toFixed(1),
      lcyl_mm: +g.lcyl_mm?.toFixed(1),
      lnoz_mm: +g.lnoz_mm?.toFixed(1),
      ltot_mm: +(g.lcyl_mm + g.lconv_mm + g.lnoz_mm)?.toFixed(1),
      bBox,
      meshVerts
    };
  });
}

(async () => {
  const browser = await chromium.launch({
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: true
  });
  const page = await browser.newPage();
  const filePath = 'file:///' + path.resolve(__dirname, 'docs/index.html').replace(/\\/g, '/');
  await page.goto(filePath, { waitUntil: 'load' });
  await page.waitForTimeout(600);

  const presets = ['merlin1d', 'raptor2', 'rs25', 'rd180', 'rl10', 'rutherford', 'lmde'];
  const results = {};

  console.log('=== RUNNING PRESET AUDIT MATRIX ===\n');

  for (const p of presets) {
    await page.selectOption('#inp-engine-preset', p);
    await page.waitForTimeout(400);

    // Refresh global reference
    await page.evaluate(() => {
      window.latestEngineGeometry = latestEngineGeometry;
      window.engineGroup = engineGroup;
    });

    const stats = await getPresetStats(page);
    results[p] = stats;
    console.log(`[PRESET: ${p.toUpperCase()}]`);
    console.log(`  Thrust: ${stats.thrust_kn} kN | Pc: ${stats.pc_bar} bar | Cycle: ${stats.cycle}`);
    console.log(`  Prop: ${stats.prop} | Inj: ${stats.inj} (ne=${stats.ne}) | Mat: ${stats.mat}`);
    console.log(`  Geometry: Dt=⌀${stats.dt_mm}mm | Dc=⌀${stats.dc_mm}mm | De=⌀${stats.de_mm}mm | Ltot=${stats.ltot_mm}mm`);
    console.log(`  3D Bounding Box: Length=${stats.bBox?.spanX}m | Diam=${stats.bBox?.spanY}m | Vertices=${stats.meshVerts}\n`);
  }

  // Compare extreme presets: Rutherford vs Raptor 2
  const ruth = results['rutherford'];
  const rapt = results['raptor2'];

  console.log('=== COMPARISON: RUTHERFORD (25 kN) vs RAPTOR 2 (2,256 kN) ===');
  console.log(`Length:    ${ruth.ltot_mm} mm (${ruth.bBox?.spanX} m)  vs  ${rapt.ltot_mm} mm (${rapt.bBox?.spanX} m) -> ${(rapt.ltot_mm / ruth.ltot_mm).toFixed(1)}x larger`);
  console.log(`Throat Dt: ${ruth.dt_mm} mm  vs  ${rapt.dt_mm} mm -> ${(rapt.dt_mm / ruth.dt_mm).toFixed(1)}x larger`);
  console.log(`Exit De:   ${ruth.de_mm} mm  vs  ${rapt.de_mm} mm -> ${(rapt.de_mm / ruth.de_mm).toFixed(1)}x larger`);
  console.log(`Thrust:    ${ruth.thrust_kn} kN  vs  ${rapt.thrust_kn} kN -> ${(rapt.thrust_kn / ruth.thrust_kn).toFixed(1)}x larger`);

  await browser.close();
  process.exit(0);
})();
