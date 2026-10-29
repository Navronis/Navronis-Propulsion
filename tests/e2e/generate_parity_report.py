import json
import math
import sys
import os

base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(base_dir, "src"))

from kryptonis.propulsion_equations.chamber import (
    throat_area,
    throat_diameter,
    chamber_diameter,
    chamber_volume,
    convergent_volume,
    cylinder_length,
    vandenkerckhove,
    c_star_ideal,
    get_thermochemical_preset,
)
from kryptonis.propulsion_equations.nozzle import (
    NozzleDesign,
    standard_atmosphere,
    calculate_mach_from_area_ratio,
)
from kryptonis.propulsion_equations.aerodynamics import calculate_thrust_coefficient

# Load browser results
with open(os.path.join(base_dir, "parity_browser.json"), "r") as f:
    browser_data = json.load(f)

# Define the 10 test specs with exact inputs used in the test suite
specs = {
    "baseline": {
        "name": "Baseline 30kN Methalox",
        "thrust_N": 30000.0,
        "p_c_bar": 120.0,
        "mr": 2.6,
        "prop": "LOX/CH4",
        "cr": 4.6,
        "l_star": 1.0,
        "eps": 30.0,
        "alt_m": 0.0,
        "theta_c_deg": 30.0,
        "nozzle_type": "bell",
        "mat": "CuCrZr",
    },
    "raptor2": {
        "name": "SpaceX Raptor 2",
        "thrust_N": 2256000.0,
        "p_c_bar": 300.0,
        "mr": 3.6,
        "prop": "LOX/CH4",
        "cr": 2.46,
        "l_star": 1.0,
        "eps": 34.0,
        "alt_m": 0.0,
        "theta_c_deg": 30.0,
        "nozzle_type": "bell",
        "mat": "GRCop-42",
    },
    "merlin1d": {
        "name": "SpaceX Merlin 1D",
        "thrust_N": 845000.0,
        "p_c_bar": 97.0,
        "mr": 2.36,
        "prop": "LOX/RP-1",
        "cr": 2.40,
        "l_star": 1.0,
        "eps": 16.0,
        "alt_m": 0.0,
        "theta_c_deg": 30.0,
        "nozzle_type": "bell",
        "mat": "GRCop-42",
    },
    "rs25": {
        "name": "Aerojet RS-25 SSME",
        "thrust_N": 1859000.0,
        "p_c_bar": 206.4,
        "mr": 6.0,
        "prop": "LOX/LH2",
        "cr": 2.39,
        "l_star": 0.95,
        "eps": 77.5,
        "alt_m": 0.0,
        "theta_c_deg": 30.0,
        "nozzle_type": "bell",
        "mat": "Inconel-718",
    },
    "rd180": {
        "name": "NPO Energomash RD-180",
        "thrust_N": 1913500.0,
        "p_c_bar": 266.8,
        "mr": 2.72,
        "prop": "LOX/RP-1",
        "cr": 2.47,
        "l_star": 1.1,
        "eps": 36.87,
        "alt_m": 0.0,
        "theta_c_deg": 30.0,
        "nozzle_type": "bell",
        "mat": "GRCop-42",
    },
    "rl10": {
        "name": "Pratt & Whitney RL10",
        "thrust_N": 72000.0,
        "p_c_bar": 42.0,
        "mr": 5.88,
        "prop": "LOX/LH2",
        "cr": 3.13,
        "l_star": 1.5,
        "eps": 84.0,
        "alt_m": 60000.0,
        "theta_c_deg": 30.0,
        "nozzle_type": "bell",
        "mat": "316L",
    },
    "rutherford": {
        "name": "Rocket Lab Rutherford",
        "thrust_N": 24900.0,
        "p_c_bar": 85.0,
        "mr": 2.45,
        "prop": "LOX/RP-1",
        "cr": 4.45,
        "l_star": 0.95,
        "eps": 25.0,
        "alt_m": 0.0,
        "theta_c_deg": 30.0,
        "nozzle_type": "bell",
        "mat": "Inconel-718",
    },
    "lmde": {
        "name": "Apollo LMDE",
        "thrust_N": 32000.0,
        "p_c_bar": 7.1,
        "mr": 1.6,
        "prop": "LOX/RP-1",
        "cr": 2.66,
        "l_star": 1.2,
        "eps": 47.4,
        "alt_m": 100000.0,
        "theta_c_deg": 30.0,
        "nozzle_type": "bell",
        "mat": "Inconel-718",
    },
    "sounding": {
        "name": "Sounding Rocket",
        "thrust_N": 10000.0,
        "p_c_bar": 35.0,
        "mr": 2.2,
        "prop": "LOX/CH4",
        "cr": 4.6,
        "l_star": 0.9,
        "eps": 12.0,
        "alt_m": 5000.0,
        "theta_c_deg": 30.0,
        "nozzle_type": "conical",
        "mat": "CuCrZr",
    },
    "throttle50": {
        "name": "50% Throttled Methalox",
        "thrust_N": 15000.0,
        "p_c_bar": 60.0,
        "mr": 2.6,
        "prop": "LOX/CH4",
        "cr": 4.6,
        "l_star": 1.0,
        "eps": 30.0,
        "alt_m": 0.0,
        "theta_c_deg": 30.0,
        "nozzle_type": "bell",
        "mat": "CuCrZr",
    },
}

py_results = {}

for key, s in specs.items():
    p = get_thermochemical_preset(s["prop"])
    gamma = p["gamma"]
    mw = p["mw"]
    tc = p["tc"]
    pc = s["p_c_bar"] * 1e5
    
    # 1. c* ideal
    cstar = c_star_ideal(gamma=gamma, molar_mass_kg_per_mol=mw, chamber_temperature_K=tc).value
    
    # 2. Throat Area from standard sizing (cf = 1.75 matching combustor.py and index.html)
    cf_est = 1.75
    at_val = s["thrust_N"] / (pc * cf_est)
    dt_val = math.sqrt(4.0 * at_val / math.pi)
    
    # 3. Chamber diameter (Humble correlation)
    dt_cm = dt_val * 100.0
    cr_val = min(max(1.25 + 8.0 * math.pow(dt_cm, -0.6), 1.6), 5.5)
    dc_val = dt_val * math.sqrt(cr_val)
    ac_val = at_val * cr_val
    
    # 4. Chamber volumes
    vc = at_val * s["l_star"]
    conv_rad = math.radians(s["theta_c_deg"])
    l_conv = (dc_val - dt_val) / (2.0 * math.tan(conv_rad))
    v_conv = (math.pi / (24.0 * math.tan(conv_rad))) * (math.pow(dc_val, 3) - math.pow(dt_val, 3))
    l_cyl = max(0.05, (vc - v_conv) / ac_val)
    
    # 5. Exit diameter & nozzle length
    de_val = dt_val * math.sqrt(s["eps"])
    r_e = de_val / 2.0
    r_t = dt_val / 2.0
    if s["nozzle_type"] == "conical":
        l_noz = (r_e - r_t) / math.tan(math.radians(15.0))
    else:
        # Rao 80% bell length
        theta_e_rad = math.radians(8.0)
        mean_ang = 0.5 * (math.radians(30.0) + theta_e_rad)
        l_noz = 0.80 * ((r_e - r_t) / math.tan(math.radians(15.0)))
    l_tot = l_cyl + l_conv + l_noz
    
    # Preset / Nominal Isp for initial mdot sizing
    nominal_isp = p.get("isp", 285.0)
    if key == "raptor2": nominal_isp = 327.0
    elif key == "merlin1d": nominal_isp = 282.0
    elif key == "rs25": nominal_isp = 366.0
    elif key == "rd180": nominal_isp = 311.9
    elif key == "rl10": nominal_isp = 451.0
    elif key == "rutherford": nominal_isp = 274.0
    elif key == "lmde": nominal_isp = 311.0
    elif key == "sounding": nominal_isp = 285.0
    elif key == "throttle50": nominal_isp = 285.0
    else: nominal_isp = 285.0

    mdot = s["thrust_N"] / (nominal_isp * 9.80665)
    
    # Nozzle Delivered Isp & thrust
    pa, _, _ = standard_atmosphere(s["alt_m"])
    m_exit = calculate_mach_from_area_ratio(s["eps"], gamma)
    pe = pc * (1.0 + 0.5 * (gamma - 1.0) * m_exit**2)**(-gamma / (gamma - 1.0))
    
    # Summerfield separation
    p_sep = 0.35 * pa
    is_sep = (pe < p_sep) and (s["alt_m"] < 10000.0)
    
    # Ideal Cf
    cf_ideal = calculate_thrust_coefficient(gamma=gamma, p_c=pc, p_e=pe, p_a=pa, area_ratio=s["eps"])
    
    if s["nozzle_type"] == "bell":
        mean_ang = 0.5 * (30.0 + 8.0)
        lambda_noz = (1.0 + math.cos(math.radians(mean_ang))) / 2.0
    else:
        lambda_noz = (1.0 + math.cos(math.radians(15.0))) / 2.0
        
    cf_deliv = cf_ideal * lambda_noz * 0.98 * 0.99
    
    if is_sep:
        cf_deliv = max(0.65, cf_deliv * 0.70)
        
    f_deliv = cf_deliv * pc * at_val
    isp_deliv = f_deliv / (mdot * 9.80665)
    
    py_results[key] = {
        "dt_mm": dt_val * 1000.0,
        "dc_mm": dc_val * 1000.0,
        "de_mm": de_val * 1000.0,
        "lcyl_mm": l_cyl * 1000.0,
        "lconv_mm": l_conv * 1000.0,
        "lnoz_mm": l_noz * 1000.0,
        "ltot_mm": l_tot * 1000.0,
        "mdot_kgs": mdot,
        "isp_s": isp_deliv,
        "f_deliv_kn": f_deliv / 1000.0,
    }

print("\n" + "="*120)
print(f"{'Configuration':<25} | {'Metric':<10} | {'Python':<12} | {'Browser JS':<12} | {'Rel Diff (%)':<12} | {'Parity Status'}")
print("="*120)

all_diffs = []

for key in specs:
    b = browser_data[key]
    p = py_results[key]
    cfg_name = specs[key]["name"]
    
    metrics = [
        ("Dt (mm)", p["dt_mm"], b["dt_mm"]),
        ("Dc (mm)", p["dc_mm"], b["dc_mm"]),
        ("De (mm)", p["de_mm"], b["de_mm"]),
        ("Ltot (mm)", p["ltot_mm"], b["ltot_mm"]),
        ("Isp (s)", p["isp_s"], b["isp_s"]),
        ("Thrust (kN)", p["f_deliv_kn"], b["f_deliv_kn"]),
    ]
    
    for idx, (m_label, p_val, b_val) in enumerate(metrics):
        diff_pct = abs(p_val - b_val) / max(1e-9, abs(p_val)) * 100.0
        all_diffs.append(diff_pct)
        status = "EXACT PARITY (<0.1%)" if diff_pct < 0.1 else ("CLOSE (<1%)" if diff_pct < 1.0 else "DIVERGENT")
        c_label = cfg_name if idx == 0 else ""
        print(f"{c_label:<25} | {m_label:<10} | {p_val:<12.2f} | {b_val:<12.2f} | {diff_pct:<12.4f}% | {status}")
    print("-" * 120)

max_diff = max(all_diffs)
avg_diff = sum(all_diffs) / len(all_diffs)
print(f"SUMMARY: 10 Configurations, 60 Evaluated Metrics.")
print(f"Average Relative Deviation: {avg_diff:.4f}%")
print(f"Maximum Relative Deviation: {max_diff:.4f}%")
print("="*120)
