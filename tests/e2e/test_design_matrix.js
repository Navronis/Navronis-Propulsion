const { chromium } = require('playwright');
const path = require('path');

async function getFingerprint(page) {
  return await page.evaluate(() => {
    const g = window.latestEngineGeometry || {};
    const ribbonDims = document.getElementById('ribbon-dims')?.innerText || '';
    const hudTri = document.getElementById('hud-tri-count')?.innerText || '';
    const hudModel = document.getElementById('hud-model-type')?.innerText || '';
    
    // Extract Three.js mesh stats from scene if available
    let meshVerts = 0;
    let meshFaces = 0;
    let bBox = null;
    if (window.engineGroup) {
      const box = new window.THREE.Box3().setFromObject(window.engineGroup);
      bBox = {
        minX: box.min.x.toFixed(3),
        maxX: box.max.x.toFixed(3),
        minY: box.min.y.toFixed(3),
        maxY: box.max.y.toFixed(3),
        minZ: box.min.z.toFixed(3),
        maxZ: box.max.z.toFixed(3),
        spanX: (box.max.x - box.min.x).toFixed(3),
        spanY: (box.max.y - box.min.y).toFixed(3),
        spanZ: (box.max.z - box.min.z).toFixed(3)
      };
      window.engineGroup.traverse(child => {
        if (child.isMesh && child.geometry) {
          const pos = child.geometry.attributes.position;
          if (pos) meshVerts += pos.count;
          if (child.geometry.index) meshFaces += child.geometry.index.count / 3;
        }
      });
    }

    return {
      dc_mm: g.dc_mm?.toFixed(2),
      dt_mm: g.dt_mm?.toFixed(2),
      de_mm: g.de_mm?.toFixed(2),
      lcyl_mm: g.lcyl_mm?.toFixed(2),
      lconv_mm: g.lconv_mm?.toFixed(2),
      lnoz_mm: g.lnoz_mm?.toFixed(2),
      ltot_mm: (g.lcyl_mm + g.lconv_mm + g.lnoz_mm)?.toFixed(2),
      tw_mm: g.tw_mm?.toFixed(2),
      hc_mm: g.hc_mm?.toFixed(2),
      nch: g.nch,
      mat: g.mat,
      injType: g.injType,
      ne: g.n_elements,
      nozType: g.nozType,
      thrust_kn: g.f_deliv_kn?.toFixed(2),
      pc_bar: g.pc_bar?.toFixed(2),
      isp_deliv: g.isp_deliv?.toFixed(1),
      twg_c: g.twg_c?.toFixed(1),
      ribbonDims,
      hudTri,
      hudModel,
      meshVerts,
      meshFaces,
      bBox
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

  // Expose global variable hook
  await page.evaluate(() => {
    window.latestEngineGeometry = latestEngineGeometry;
    window.currentCadView = currentCadView;
    window.engineGroup = engineGroup;
    window.THREE = THREE;
  });

  const baseline = await getFingerprint(page);
  console.log('=== BASELINE FINGERPRINT ===');
  console.log(JSON.stringify(baseline, null, 2));

  const tests = [
    {
      name: 'Change Thrust 30kN -> 120kN',
      action: async () => {
        await page.fill('#inp-thrust', '120000');
        await page.dispatchEvent('#inp-thrust', 'input');
        await page.dispatchEvent('#inp-thrust', 'change');
      },
      check: (b, a) => {
        console.log(`Thrust: ${b.thrust_kn} -> ${a.thrust_kn} kN`);
        console.log(`Dt: ${b.dt_mm} -> ${a.dt_mm} mm`);
        console.log(`Dc: ${b.dc_mm} -> ${a.dc_mm} mm`);
        console.log(`Ltot: ${b.ltot_mm} -> ${a.ltot_mm} mm`);
        console.log(`BBox spanX: ${b.bBox?.spanX} -> ${a.bBox?.spanX} m`);
        return parseFloat(a.dt_mm) > parseFloat(b.dt_mm) && parseFloat(a.ltot_mm) > parseFloat(b.ltot_mm);
      }
    },
    {
      name: 'Change Chamber Pressure 120 -> 50 bar',
      action: async () => {
        await page.fill('#inp-pc', '50');
        await page.dispatchEvent('#inp-pc', 'input');
        await page.dispatchEvent('#inp-pc', 'change');
      },
      check: (b, a) => {
        console.log(`Pc: ${b.pc_bar} -> ${a.pc_bar} bar`);
        console.log(`Dt: ${b.dt_mm} -> ${a.dt_mm} mm`);
        return parseFloat(a.dt_mm) > parseFloat(b.dt_mm); // Lower Pc requires larger throat for same thrust
      }
    },
    {
      name: 'Change Expansion Ratio 30 -> 70',
      action: async () => {
        await page.fill('#inp-eps', '70');
        await page.dispatchEvent('#inp-eps', 'input');
        await page.dispatchEvent('#inp-eps', 'change');
      },
      check: (b, a) => {
        console.log(`De: ${b.de_mm} -> ${a.de_mm} mm`);
        console.log(`Lnoz: ${b.lnoz_mm} -> ${a.lnoz_mm} mm`);
        return parseFloat(a.de_mm) > parseFloat(b.de_mm) && parseFloat(a.lnoz_mm) > parseFloat(b.lnoz_mm);
      }
    },
    {
      name: 'Change Nozzle Type Bell -> Conical',
      action: async () => {
        await page.selectOption('#inp-nozzle-type', 'conical');
      },
      check: (b, a) => {
        console.log(`NozType: ${b.nozType} -> ${a.nozType}`);
        console.log(`Model HUD: ${a.hudModel}`);
        return a.nozType === 'conical' && a.hudModel.includes('Conical');
      }
    },
    {
      name: 'Change Injector Coaxial -> Pintle',
      action: async () => {
        await page.selectOption('#inp-inj', 'pintle');
      },
      check: (b, a) => {
        console.log(`InjType: ${b.injType} -> ${a.injType}`);
        console.log(`Model HUD: ${a.hudModel}`);
        return a.injType === 'pintle' && a.hudModel.includes('Pintle');
      }
    },
    {
      name: 'Change Injector Pintle -> Swirl',
      action: async () => {
        await page.selectOption('#inp-inj', 'swirl');
      },
      check: (b, a) => {
        console.log(`InjType: ${b.injType} -> ${a.injType}`);
        console.log(`Model HUD: ${a.hudModel}`);
        return a.injType === 'swirl' && a.hudModel.includes('Swirl');
      }
    },
    {
      name: 'Change Element Count 19 -> 120',
      action: async () => {
        await page.selectOption('#inp-inj', 'coaxial');
        await page.fill('#inp-elements', '120');
        await page.dispatchEvent('#inp-elements', 'input');
        await page.dispatchEvent('#inp-elements', 'change');
      },
      check: (b, a) => {
        console.log(`Elements: ${b.ne} -> ${a.ne}`);
        console.log(`Mesh Vertices: ${b.meshVerts} -> ${a.meshVerts}`);
        return a.ne === 120 && a.meshVerts > b.meshVerts;
      }
    },
    {
      name: 'Change Cooling Channels 80 -> 160',
      action: async () => {
        await page.fill('#inp-channels', '160');
        await page.dispatchEvent('#inp-channels', 'input');
        await page.dispatchEvent('#inp-channels', 'change');
      },
      check: (b, a) => {
        console.log(`Channels: ${b.nch} -> ${a.nch}`);
        console.log(`Mesh Vertices: ${b.meshVerts} -> ${a.meshVerts}`);
        return a.nch === 160 && a.meshVerts > b.meshVerts;
      }
    },
    {
      name: 'Change Material CuCrZr -> Inconel-718',
      action: async () => {
        await page.selectOption('#inp-mat', 'Inconel-718');
      },
      check: (b, a) => {
        console.log(`Material: ${b.mat} -> ${a.mat}`);
        console.log(`Twg: ${b.twg_c} -> ${a.twg_c} °C`);
        return a.mat === 'Inconel-718' && parseFloat(a.twg_c) > parseFloat(b.twg_c); // Inconel has lower k -> higher Twg
      }
    }
  ];

  console.log('\n=== RUNNING ZERO-TRUST DESIGN CHANGE VERIFICATION ===');
  for (const t of tests) {
    const before = await getFingerprint(page);
    await t.action();
    await page.waitForTimeout(300);
    // Refresh global reference
    await page.evaluate(() => {
      window.latestEngineGeometry = latestEngineGeometry;
      window.engineGroup = engineGroup;
    });
    const after = await getFingerprint(page);
    const passed = t.check(before, after);
    console.log(`[${passed ? 'PASS' : 'FAIL'}] ${t.name}\n`);
  }

  await browser.close();
  process.exit(0);
})();
