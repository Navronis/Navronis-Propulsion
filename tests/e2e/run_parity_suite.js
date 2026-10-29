const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const testCases = [
  { id: 'baseline', thrust: 30000, pc: 120, prop: 'LOX/RP-1', eps: 30.0, lstar: 1.0, ne: 19, nch: 80, mat: 'GRCop-42', inj: 'coaxial', nozType: 'bell', alt: 0 },
  { id: 'raptor2', thrust: 2200000, pc: 300, prop: 'LOX/CH4', eps: 34.0, lstar: 1.0, ne: 60, nch: 160, mat: 'GRCop-42', inj: 'coaxial', nozType: 'bell', alt: 0 },
  { id: 'merlin1d', thrust: 845000, pc: 97, prop: 'LOX/RP-1', eps: 16.0, lstar: 1.0, ne: 1, nch: 110, mat: 'GRCop-42', inj: 'pintle', nozType: 'bell', alt: 0 },
  { id: 'rs25', thrust: 1859000, pc: 206.4, prop: 'LOX/LH2', eps: 77.5, lstar: 0.95, ne: 600, nch: 390, mat: 'Inconel-718', inj: 'coaxial', nozType: 'bell', alt: 0 },
  { id: 'rd180', thrust: 1913500, pc: 266.8, prop: 'LOX/RP-1', eps: 36.8, lstar: 1.1, ne: 350, nch: 140, mat: 'GRCop-42', inj: 'swirl', nozType: 'bell', alt: 0 },
  { id: 'rl10', thrust: 72000, pc: 42.0, prop: 'LOX/LH2', eps: 84.0, lstar: 1.5, ne: 90, nch: 90, mat: '316L', inj: 'coaxial', nozType: 'bell', alt: 60000 },
  { id: 'rutherford', thrust: 24900, pc: 85.0, prop: 'LOX/RP-1', eps: 25.0, lstar: 0.95, ne: 1, nch: 60, mat: 'Inconel-718', inj: 'pintle', nozType: 'bell', alt: 0 },
  { id: 'lmde', thrust: 32000, pc: 7.1, prop: 'LOX/RP-1', eps: 47.4, lstar: 1.2, ne: 1, nch: 70, mat: 'Inconel-718', inj: 'pintle', nozType: 'bell', alt: 100000 },
  { id: 'sounding', thrust: 10000, pc: 40.0, prop: 'LOX/RP-1', eps: 12.0, lstar: 0.8, ne: 12, nch: 40, mat: 'CuCrZr', inj: 'impinging', nozType: 'conical', alt: 0 },
  { id: 'throttle50', thrust: 15000, pc: 60.0, prop: 'LOX/RP-1', eps: 30.0, lstar: 1.0, ne: 19, nch: 80, mat: 'GRCop-42', inj: 'coaxial', nozType: 'bell', alt: 0 }
];

(async () => {
  const browser = await chromium.launch({
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: true
  });
  const page = await browser.newPage();
  const filePath = 'file:///' + path.resolve(__dirname, 'docs/index.html').replace(/\\/g, '/');
  await page.goto(filePath, { waitUntil: 'load' });
  await page.waitForTimeout(600);

  const browserResults = {};

  for (const tc of testCases) {
    await page.fill('#inp-thrust', tc.thrust.toString());
    await page.fill('#inp-pc', tc.pc.toString());
    await page.selectOption('#inp-prop', tc.prop);
    await page.fill('#inp-eps', tc.eps.toString());
    await page.fill('#inp-lstar', tc.lstar.toString());
    await page.fill('#inp-elements', tc.ne.toString());
    await page.fill('#inp-channels', tc.nch.toString());
    await page.selectOption('#inp-mat', tc.mat);
    await page.selectOption('#inp-inj', tc.inj);
    await page.selectOption('#inp-nozzle-type', tc.nozType);
    await page.fill('#inp-alt', tc.alt.toString());

    // Trigger calculation
    await page.evaluate(() => calculateSizing(true));
    await page.waitForTimeout(100);

    const data = await page.evaluate(() => {
      const g = latestEngineGeometry || {};
      const mdotText = document.getElementById('res-mdot')?.innerText || '0';
      const mdot = parseFloat(mdotText);
      const dpCoolText = document.getElementById('res-dp-cool')?.innerText || '0';
      const dp_cool = parseFloat(dpCoolText);

      return {
        dt_mm: g.dt_mm,
        dc_mm: g.dc_mm,
        de_mm: g.de_mm,
        lcyl_mm: g.lcyl_mm,
        lconv_mm: g.lconv_mm,
        lnoz_mm: g.lnoz_mm,
        ltot_mm: g.lcyl_mm + g.lconv_mm + g.lnoz_mm,
        mdot_kgs: mdot,
        isp_s: g.isp_deliv,
        twg_c: g.twg_c,
        dp_cool_bar: dp_cool,
        f_deliv_kn: g.f_deliv_kn
      };
    });

    browserResults[tc.id] = data;
    console.log(`Evaluated [${tc.id.toUpperCase()}]: Dt=${data.dt_mm?.toFixed(1)}mm, Dc=${data.dc_mm?.toFixed(1)}mm, De=${data.de_mm?.toFixed(1)}mm, Ltot=${data.ltot_mm?.toFixed(1)}mm, Isp=${data.isp_s?.toFixed(1)}s`);
  }

  fs.writeFileSync(path.resolve(__dirname, 'parity_browser.json'), JSON.stringify(browserResults, null, 2));
  console.log('\nWrote browser parity results to parity_browser.json');

  await browser.close();
  process.exit(0);
})();
