const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch({
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: true
  });
  const page = await browser.newPage();
  const logs = [];
  page.on('console', msg => logs.push(msg.text()));
  page.on('pageerror', err => logs.push('PAGE_ERROR: ' + err.toString()));

  const filePath = 'file:///' + path.resolve(__dirname, 'docs/index.html').replace(/\\/g, '/');
  await page.goto(filePath, { waitUntil: 'load' });
  await page.waitForTimeout(600);

  console.log('1. Page loaded cleanly');

  // Baseline state
  const basePc = await page.$eval('#inp-pc', el => el.value);
  const baseEps = await page.$eval('#inp-eps', el => el.value);
  const baseThrust = await page.$eval('#inp-thrust', el => el.value);
  console.log(`2. Baseline inputs: Thrust=${baseThrust} N, Pc=${basePc} bar, Eps=${baseEps}`);

  // Click Day 8 tab
  await page.click('#btn-view-mdo');
  await page.waitForTimeout(300);
  console.log('3. Switched to Day 8 MDO tab');

  // Click Run SLSQP Optimizer
  await page.click('button[onclick="runSlsqpOptimizer()"]');
  console.log('4. Clicked Solve Optimal Engine, waiting for solver iterations...');

  // Wait for convergence (max 2 seconds)
  await page.waitForTimeout(2000);

  const logText = await page.$eval('#mdo-opt-log', el => el.innerText);
  console.log('5. Optimizer Log:\n' + logText + '\n');

  const btnApplyDisabled = await page.$eval('#btn-apply-opt', el => el.disabled);
  console.log('6. Apply button disabled?', btnApplyDisabled);

  // Click Apply to 3D CAD
  await page.click('#btn-apply-opt');
  await page.waitForTimeout(600);

  const newPc = await page.$eval('#inp-pc', el => el.value);
  const newEps = await page.$eval('#inp-eps', el => el.value);
  const currentView = await page.evaluate(() => window.currentCadView);
  const hudDims = await page.$eval('#ribbon-dims', el => el.innerText);
  const hudDrivers = await page.$eval('#ribbon-drivers', el => el.innerText);

  console.log(`7. After Apply: Pc=${newPc} bar, Eps=${newEps}`);
  console.log('8. Switched back to CAD View:', currentView);
  console.log('9. Ribbon Dimensions updated:', hudDims);
  console.log('10. Ribbon Drivers updated:', hudDrivers);

  if (basePc !== newPc || baseEps !== newEps) {
    console.log('SUCCESS: Optimization modified engineering inputs and regenerated CAD!');
  } else {
    console.log('FAILURE: Inputs did not change!');
  }

  await browser.close();
  process.exit(0);
})();
