const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

(async () => {
  const browser = await chromium.launch({
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: true
  });
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  
  const filePath = 'file:///' + path.resolve(__dirname, 'docs/index.html').replace(/\\/g, '/');
  await page.goto(filePath, { waitUntil: 'load' });
  await page.waitForTimeout(1000);

  const outDir = path.resolve(__dirname, 'evidence_screenshots');
  if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
  }

  // 1. Cutaway 180 View of Injectors
  await page.click('#btn-cut-180');
  await page.waitForTimeout(500);

  const injectors = [
    { id: 'coaxial', name: 'coaxial' },
    { id: 'pintle', name: 'pintle' },
    { id: 'swirl', name: 'swirl' },
    { id: 'impinging', name: 'doublet' }
  ];

  for (const inj of injectors) {
    await page.selectOption('#inp-inj', inj.id);
    await page.waitForTimeout(600);
    const wrapper = await page.locator('#view-3d-wrapper');
    await wrapper.screenshot({ path: path.join(outDir, `injector_${inj.name}.png`) });
    console.log(`Saved injector_${inj.name}.png`);
  }

  // 2. Full 360 View of Rutherford vs Raptor 2
  await page.click('#btn-cut-360');
  await page.waitForTimeout(400);

  // Preset Rutherford
  await page.selectOption('#inp-engine-preset', 'rutherford');
  await page.waitForTimeout(600);
  const wrapper = await page.locator('#view-3d-wrapper');
  await wrapper.screenshot({ path: path.join(outDir, 'preset_rutherford.png') });
  console.log('Saved preset_rutherford.png');

  // Preset Raptor 2
  await page.selectOption('#inp-engine-preset', 'raptor2');
  await page.waitForTimeout(600);
  await wrapper.screenshot({ path: path.join(outDir, 'preset_raptor2.png') });
  console.log('Saved preset_raptor2.png');

  // 3. ASME Y14.5 Blueprint
  await page.click('#btn-view-bp');
  await page.waitForTimeout(500);
  const bpWrapper = await page.locator('#view-bp-wrapper');
  await bpWrapper.screenshot({ path: path.join(outDir, 'asme_blueprint_cad.png') });
  console.log('Saved asme_blueprint_cad.png');

  // 4. MDO Optimizer Tab: Day 8 Evidence
  await page.click('#btn-view-mdo');
  await page.waitForTimeout(500);
  await page.click('button[onclick="runSlsqpOptimizer()"]');
  await page.waitForTimeout(1500);
  const mdoWrapper = await page.locator('#view-mdo-wrapper');
  await mdoWrapper.screenshot({ path: path.join(outDir, 'day8_mdo_convergence.png') });
  console.log('Saved day8_mdo_convergence.png');

  await browser.close();
  console.log('All visual evidence captured successfully.');
})();
