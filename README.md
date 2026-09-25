# Navronis (`navronis-propulsion`)

<div align="center">

[![Live Web App](https://img.shields.io/badge/Live%20Demo-Interactive%20Web%20App-blueviolet.svg?style=for-the-badge&logo=firefox)](https://navronis.github.io/Navronis-Propulsion/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-brightgreen.svg)](https://python.org)
[![Build & Test](https://img.shields.io/badge/Tests-100%20Passed-success.svg)](#running-tests--verification)
[![Engineering Pedigree](https://img.shields.io/badge/Physics-Strict%20Provenance-orange.svg)](#primary-literature--pedigree)
[![Release](https://img.shields.io/badge/Release-v0.5.0%20(Day%205)-blue.svg)](https://github.com/Navronis/Navronis-Propulsion/releases)

**An authority-controlled, first-principles liquid rocket preliminary propulsion analytical toolkit with primary literature provenance.**

[🚀 **Live Interactive App**](https://navronis.github.io/Navronis-Propulsion/) •
[What Is Launched](#what-is-currently-launched) •
[Step-by-Step Guide](#step-by-step-usage-instructions) •
[4 Canonical Injectors](#the-4-canonical-injector-families) •
[Day 3: Cooling Channels](#day-3-regenerative-cooling-channels) •
[Day 4: Supersonic Nozzle](#day-4-supersonic-nozzle-aerodynamics--altitude-engine) •
[Day 5: Turbomachinery & Cycles](#day-5-turbomachinery-cycles--power-balance) •
[Day 5: Flight Ascent Trajectory](#day-5-2d-powered-ascent-flight-mechanics--orbit-simulator) •
[Day 5: Master Engine Architecture](#day-5-master-enginesystem-architecture) •
[Governing Equations](#governing-equations--literature-provenance) •
[Architecture](#architecture--project-structure)

</div>

---

> 🚀 **Live Interactive Web Application:** [**navronis.github.io/Navronis-Propulsion**](https://navronis.github.io/Navronis-Propulsion/)
>
> Run combustor, injector, regenerative cooling, supersonic bell nozzle, turbopump cycle power balance, and 2D flight ascent trajectory sizing directly in your browser with real-time SVG CAD geometry and zero installation.

---

## Overview

Most preliminary rocket propulsion scripts in circulation rely on undocumented constants, uncalibrated combustion efficiencies, or misattributed empirical formulas.

**Navronis** is built on a strict mathematical foundation:
- **Zero Silent Defaults:** Inputs and intermediate results are strictly validated. Non-physical states (e.g. negative throat areas, sub-unity contraction ratios, negative injector pressure drops, or channels exceeding perimeter) fail explicitly rather than silently propagating errors.
- **Traceable Engineering Provenance:** Every computed parameter carries its governing equation, validity domain, and exact literature citation (NASA SP-125, NASA SP-194, NASA SP-8087, NASA SP-8107, NASA SP-8110, Bartz 1957, Gnielinski 1976, Haaland 1983, Rao 1958, Stark 2005, Huzel & Huang 1992, Sutton & Biblarz 2016, Griffin & French 2004).
- **Self-Explaining Engine:** The calculation engine explains every derived value upon request via `.explain("parameter_name")`.
- **Zero Heavy CAD/CFD Dependencies:** Pure Python, NumPy, and SciPy core. Runs instantaneously on Linux, macOS, and Windows.

---

## What Is Currently Launched

| Component | Status | Governing Physics & Scope | Primary References |
|---|---|---|---|
| **Day 1: Combustor Assembly** | 🟢 **Released (`v0.1.0`)** | Choked sonic throat continuity, Humble contraction ratio, barrel length, stay time, Bartz throat convective heat flux, NASA SP-194 acoustic cavity buzz modes (1T, 1R, 1L), ASME Section VIII hoop wall thickness. | NASA SP-125, Bartz (1957), NASA SP-194, ASME Sec VIII |
| **Day 2: 4 Canonical Injectors** | 🟢 **Released (`v0.2.0`)** | Torricelli hydraulics, chugging feed-system acoustic decoupling ($\Delta P / P_c \ge 15\%$), element packaging pitch, momentum flux ratio $J$, swirl sheet breakup, pintle momentum deflection, droplet atomization Sauter Mean Diameter ($D_{32}$). | NASA SP-194, Yang et al. (2004), Bazarov & Yang (1998), Dressler (2000), Rupe (1956) |
| **Day 3: Regen Cooling Channels** | 🟢 **Released (`v0.3.0`)** | Milled rectangular channel aspect ratio, Haaland friction factor, Gnielinski turbulent forced convection, fin efficiency enhancement ($\eta_{fin}$), 3-resistance conjugate wall thermal equilibrium ($T_{wg}$, $T_{wc}$), Darcy-Weisbach $\Delta P$, bulk $\Delta T$, and thermal-structural yield margin. | NASA SP-8087, Gnielinski (1976), Haaland (1983), Bartz (1957), Incropera |
| **Day 4: Supersonic Nozzle & Aero** | 🟢 **Released (`v0.4.0`)** | 1D isentropic Area-Mach inversion, Rao 80% parabolic bell contour quadratic Bézier, 1976 US Standard Atmosphere (0–85 km), Stark (2005) tri-criteria flow separation, divergence efficiency ($\lambda$), and boundary layer displacement thickness ($\delta^*$). | NASA SP-125, Rao (1958), Stark (2005), Summerfield (1954), NOAA/NASA 1976 |
| **Day 5: Turbomachinery Cycles** | 🟢 **Released (`v0.5.0`)** | Centrifugal pump hydraulic head ($H$), pump shaft power ($\dot{W}_p$), specific speed ($N_s$) & suction specific speed ($N_{ss}$) cavitation limits, turbine isentropic expansion, and 5 closed power balances: Gas Generator, Closed Expander, Staged Combustion (ORSC & FRSC), Full-Flow Staged Combustion (FFSC), and Pressure-Fed. | Huzel-Huang (1992), Sutton-Biblarz (2016), NASA SP-8107, NASA SP-8110 |
| **Day 5: 2D Powered Ascent Trajectory** | 🟢 **Released (`v0.5.0`)** | 2D point-mass gravity turn powered ascent, transonic wave drag curve $C_D(M)$, 1976 Standard Atmosphere continuous density/pressure, dynamic pressure Max Q magnitude & altitude, gravity loss $\Delta V_{grav}$, drag loss $\Delta V_{drag}$, and 200 km circular LEO payload capacity. | Griffin & French (2004), NASA SP-8087, Sutton-Biblarz (2016) |
| **Day 5: Master Engine Architecture** | 🟢 **Released (`v0.5.0`)** | Unified end-to-end `EngineSystem` synthesizer coupling Combustor + Injectors + Regen Jacket + Rao Nozzle + Turbomachinery Balance + Flight Trajectory into complete aerospace engine datasheets with JSON/CSV export. | AIAA / NASA Industry Standard Engine Datasheet Spec |
| **Live Browser Web Sizer** | 🟢 **Live** | Interactive client-side UI hosted on GitHub Pages. Real-time SVG CAD cross-section rendering with cooling channels, supersonic bell, cycle power gauges, flight trajectory simulator, and live 100-test verification matrix. | Client-side pure HTML5/SVG/JS |

---

## The 4 Canonical Injector Families

Rather than attempting to model dozens of obscure injector variations, Navronis strictly focuses on the **4 canonical injector families** that power virtually all operational liquid rocket propulsion systems:

```
   1. SHEAR COAXIAL                2. SWIRL COAXIAL                3. CENTRAL PINTLE               4. IMPINGING DOUBLET
  (SSME, RL10, Raptor)           (RD-170, RD-180, NK-33)           (LMDE, Merlin 1D)             (Apollo SPS, Titan II)

      Gas Annulus                     Swirl Outer Gas               Fuel Annular Sheet               Fuel      Oxidizer
     ┌───────────┐                   ┌───────────────┐              ┌────────────────┐                \          /
     │   ┌───┐   │                   │   ┌───────┐   │              │   ┌────────┐   │                 \        /
     │   │Ox │   │                   │   │ Vortex│   │              │   │ Radial │   │                  \      /
     │   │Liq│   │                   │   │ Liquid│   │              │   │ Pintle │   │                   ▼    ▼
     │   └───┘   │                   │   └───────┘   │              │   └────────┘   │                 Collision Fan
     └───────────┘                   └───────────────┘              └────────────────┘                 (Atomization)
```

1. **Shear Coaxial Injectors (`coaxial`):** High-speed annular gas shears a central liquid core (e.g. SSME / RS-25, RL10, Vulcain, Raptor).
   - *Key physics:* Momentum flux ratio $J = \frac{\rho_g V_g^2}{\rho_l V_l^2}$ ($2 \le J \le 20$), Lorenzetto-Lefebvre (1977) droplet atomization ($D_{32}$), recess ratio $R_L$.
2. **Centrifugal Swirl Coaxial Injectors (`swirl`):** Tangential inlet ports create a rotating liquid film with a hollow central gas core, enveloped in an annular gas stream (e.g. RD-170, RD-180, NK-33).
   - *Key physics:* Abramovich centrifugal swirl discharge coefficient ($C_d$) from geometric swirl characteristic ($K$), hollow gas core diameter, annular liquid film thickness, spray half-cone angle $\theta$, and Lefebvre (1989) pressure-swirl droplet SMD ($D_{32}$).
3. **Central Pintle Injectors (`pintle`):** Continuous annular sheet deflected outward by an impinging central radial spray, providing wide throttling margins (e.g. Apollo LMDE, SpaceX Merlin 1D).
   - *Key physics:* Total Momentum Ratio $TMR = \frac{\dot{m}_{rad} V_{rad}}{\dot{m}_{ann} V_{ann}}$, resultant spray cone half-angle $\beta = \arccos\left(\frac{1}{1 + TMR}\right)$, acoustic decoupling stiffness.
4. **Unlike Impinging Doublet Injectors (`impinging`):** Discrete intersecting liquid jets forming an atomizing spray fan (e.g. Apollo SPS, Titan II, Viking).
   - *Key physics:* Rupe (1956) dynamic head balance $\frac{\rho_1 v_1^2 d_1}{\rho_2 v_2^2 d_2} = 1.0$, free jet impingement length, Ingebo (1958) droplet atomization.

---

## Day 3: Regenerative Cooling Channels & 1D Conjugate Thermal Marching

Day 3 introduces high-pressure milled cooling jacket design. Fuel circulating through milled rectangular passages absorbs heat conducted through the chamber liner:

```
               COOLANT MANIFOLD / CHANNELS (High Speed Coolant vc ~ 50 m/s)
         ┌──────────────────────────────────────────────────────────────────┐
         │   CHANNEL   │   RIB FIN   │   CHANNEL   │   RIB FIN   │  CHANNEL │
         │ (w_c x h_c) │   (t_fin)   │ (w_c x h_c) │   (t_fin)   │          │
         └───────▲────────────▲──────────────▲────────────▲─────────────▲───┘
                 │            │              │            │             │  qc = hc,eff (Twc - Tbulk)
   ══════════════╪════════════╪══════════════╪════════════╪═════════════╪═══════ Coolant Wall (Twc)
                 │            │  RADIAL FOURIER CONDUCTION: q = (Twg - Twc) / (tw / kw)
   ══════════════╪════════════╪══════════════╪════════════╪═════════════╪═══════ Hot-Gas Wall (Twg)
                 │            │              │            │             │  qg = hg (Taw - Twg)
               HOT COMBUSTION GAS & NOZZLE ACCELERATION (Flame Temp Tc ~ 3,400 K)
```

### Governing Equations:
1. **Perimeter Packing:** $w_c = \frac{\pi D_t - N \cdot t_{fin}}{N}$, Aspect Ratio $AR = \frac{h_c}{w_c}$, $D_h = \frac{2 w_c h_c}{w_c + h_c}$
2. **Coolant Convection:** $Nu = \frac{(f/8)(Re - 1000)Pr}{1 + 12.7\sqrt{f/8}(Pr^{2/3} - 1)}$ (Gnielinski 1976 / Filonenko)
3. **Rough Channel Friction:** $\frac{1}{\sqrt{f}} = -1.8 \log_{10}\left[\left(\frac{\epsilon/D_h}{3.7}\right)^{1.11} + \frac{6.9}{Re}\right]$ (Haaland 1983)
4. **Fin Efficiency:** $\eta_{fin} = \frac{\tanh(m h_c)}{m h_c}$, where $m = \sqrt{\frac{2 h_c}{k_w t_{fin}}}$
5. **Conjugate Wall Closure:** $q = \frac{T_{aw} - T_{bulk}}{\frac{1}{h_g} + \frac{t_w}{k_w} + \frac{1}{h_{c,eff}}}$, $T_{wg} = T_{aw} - \frac{q}{h_g}$, $T_{wc} = T_{bulk} + \frac{q}{h_{c,eff}}$
6. **Coolant Pressure Drop:** $\Delta P = f \left(\frac{L_{channel}}{D_h}\right) \left(\frac{\rho_c v_c^2}{2}\right)$
7. **Thermal Stress:** $\sigma_{th} = \frac{E \alpha (T_{wg} - T_{wc})}{2(1 - \nu)}$, Yield Margin $MS = \frac{S_y}{\sigma_{th}} - 1.0$

---

## Day 4: Supersonic Nozzle Aerodynamics & Altitude Engine

Day 4 couples supersonic nozzle expansion to the 1976 US Standard Atmosphere:
- **Rao 80% Parabolic Bell Contour:** Sized using quadratic Bézier formulation from entrance angle $\theta_n \approx 30^\circ$ to exit lip angle $\theta_e \approx 8^\circ$, delivering $\sim 98.3\%$ divergence efficiency with $\sim 20\%$ shorter length than a $15^\circ$ conical bell.
- **1D Supersonic Area-Mach Inversion:** Solves the isentropic Area-Mach relation across expansion ratios $\varepsilon \in [2, 300]$ using Newton-Raphson and bracketed bisection.
- **1976 US Standard Atmosphere Model:** Barometric formula with continuous temperature lapse rates across Troposphere, Tropopause, and Stratosphere ($0$ to $85\text{ km}$).
- **Flow Separation & Side-Load Prevention:** Stark (2005) tri-criteria evaluation combining Summerfield ($P_{sep} \approx 0.375 P_a$), Schmucker Mach-scaled limit ($P_{sep} = 0.64 M^{-1.88} P_a$), and Kalt-Badal pressure criteria.

---

## Day 5: Turbomachinery Cycles & Power Balance

Day 5 introduces complete liquid rocket turbomachinery sizing and closed-loop engine cycle power balancing:

```text
               PRESSURE-FED                GAS GENERATOR                 EXPANDER (CLOSED)
           ┌──────────────────┐        ┌──────────────────┐            ┌──────────────────┐
           │ Regulated Helium │        │ Fuel + Ox Bleed  │            │ Regen Jacket     │
           │ High-P Tanks     │        │ Gas Generator    │            │ Vapor Heat Drive │
           └─────────┬────────┘        └─────────┬────────┘            └─────────┬────────┘
                     │                           │ (Dump Loss)                   │ (No Dump Loss)
                     ▼                           ▼                               ▼
                 Combustor               Turbine ──► Pumps               Turbine ──► Pumps
                                                 │                               │
                                                 ▼                               ▼
                                             Combustor                       Combustor

          STAGED COMBUSTION (ORSC / FRSC)               FULL-FLOW STAGED COMBUSTION (FFSC / RAPTOR)
           ┌────────────────────────────┐                ┌────────────────────────┐  ┌────────────────────────┐
           │ Single High-P Preburner    │                │ Ox-Rich Preburner      │  │ Fuel-Rich Preburner    │
           │ (100% of Ox or Fuel Flow)  │                │ Drives Ox Turbopump    │  │ Drives Fuel Turbopump  │
           └─────────────┬──────────────┘                └───────────┬────────────┘  └───────────┬────────────┘
                         ▼                                           │                           │
                   Preburner Gas                                     ▼                           ▼
                 Turbine ──► Pumps                             Hot Gas Oxidizer             Hot Gas Fuel
                         │                                           │                           │
                         ▼                                           └─────────────┬─────────────┘
                     Combustor                                                     ▼
                                                                        Gas-Gas Main Combustor
```

### Governing Equations:
1. **Pump Hydraulic Head:** $H = \frac{P_{discharge} - P_{inlet}}{\rho g_0}$ [meters]
2. **Pump Shaft Power:** $\dot{W}_p = \frac{\dot{m} \Delta P}{\rho \eta_p} = \frac{\dot{m} g_0 H}{\eta_p}$ [Watts]
3. **Specific Speed:** $N_s = \frac{N \sqrt{Q}}{H^{3/4}}$ (Classifies Radial Centrifugal $N_s < 1500$, Mixed $1500 \le N_s \le 4500$, or Axial $N_s > 4500$)
4. **Cavitation Margin & $N_{ss}$:** $N_{ss} = \frac{N \sqrt{Q}}{NPSH^{3/4}}$ with inducer cavitation threshold $NPSH_R = \left(\frac{N \sqrt{Q}}{N_{ss,limit}}\right)^{4/3}$
5. **Turbine Isentropic Work:** $\Delta h_{iso} = c_p T_{in} \left[1 - \left(\frac{1}{PR}\right)^{\frac{\gamma-1}{\gamma}}\right]$, Extraction Power $\dot{W}_t = \dot{m}_t \eta_t \Delta h_{iso}$
6. **Gas Generator Balance:** $\dot{m}_{gg} = \frac{\dot{W}_{p,ox} + \dot{W}_{p,fuel}}{\eta_t \Delta h_{iso}}$, Net Cycle $\text{Isp}_{vac} = \text{Isp}_{main} (1 - \alpha_{gg}) + \text{Isp}_{gg} \alpha_{gg}$
7. **Expander Heat Pinch:** Power margin $\chi_{exp} = \frac{\dot{m}_{cool} c_p \Delta T_{cool} \eta_t [1 - (1/PR)^{\frac{\gamma-1}{\gamma}}]}{\dot{W}_{p,ox} + \dot{W}_{p,fuel}} \ge 1.0$

---

## Day 5: 2D Powered Ascent Flight Mechanics & Orbit Simulator

Simulates point-mass powered flight from the launch pad through atmospheric pitch-over to orbital cutoff:
- **Gravity Turn Flight Dynamics:** $\frac{dv}{dt} = \frac{F - D}{m(t)} - g \sin\gamma$, $\frac{d\gamma}{dt} = -\left(\frac{g}{v} - \frac{v}{r}\right)\cos\gamma$
- **Transonic Wave Drag Curve:** $C_D(M)$ capturing subsonic drag ($C_D \approx 0.28$), transonic sonic-boom drag peak at Mach 1.05 ($C_D \approx 0.60$), and supersonic Prandtl-Glauert/von Kármán wave decay.
- **Atmospheric Max Q:** Dynamic pressure $q(t) = \frac{1}{2} \rho(z) v^2$, identifying peak aerodynamic structural load magnitude and altitude.
- **Flight Loss Accounting:** Numerical quadrature of gravity loss $\Delta V_{grav} = \int g \sin\gamma \, dt$, aerodynamic drag loss $\Delta V_{drag} = \int \frac{D}{m} \, dt$, and orbital velocity deficit against a $200\text{ km}$ circular LEO target ($v_{circ} = \sqrt{\mu / r_{LEO}} \approx 7784\text{ m/s}$).

---

## Day 5: Master `EngineSystem` Architecture

Couples all 5 subsystems into a single unified object:
```text
Combustor (Day 1) + 4 Injectors (Day 2) + Regen Cooling (Day 3) + Rao Nozzle (Day 4) + Turbopump (Day 5) + Ascent (Day 5)
                                                      │
                                                      ▼
                                       Unified EngineSystem Datasheet
```

---

## Step-by-Step Usage Instructions

### Method 1: Using the Live Web Application (Zero Installation)

1. Open [**https://navronis.github.io/Navronis-Propulsion/**](https://navronis.github.io/Navronis-Propulsion/).
2. Select engine cycle (Gas Generator, Expander, Staged Combustion, Full-Flow Staged, or Pressure-Fed).
3. Tweak parameters across Combustor, Injectors, Regen Cooling, Nozzle, and Flight Mass.
4. Inspect real-time 2D CAD assembly cross-section, turbopump shaft power gauges, and ascent flight trajectory telemetry.

---

### Method 2: Command-Line Interface (CLI)

#### 1. Installation
```bash
git clone https://github.com/Navronis/Navronis-Propulsion.git
cd Navronis-Propulsion
python -m pip install -e .
```

#### 2. Combustor Sizing (Day 1)
```bash
navronis --subsystem chamber --thrust 30000 --pc 70 --propellants LOX/CH4
```

#### 3. Injector Sizing (Day 2)
```bash
navronis --subsystem injector --injector-type coaxial --thrust 30000 --pc 70 --propellants LOX/CH4 --elements 19
```

#### 4. Regenerative Cooling Jacket (Day 3)
```bash
navronis --subsystem cooling --thrust 30000 --pc 70 --propellants LOX/CH4 --channels 80 --channel-height 1.8 --fin-thickness 0.8
```

#### 5. Supersonic Bell Nozzle & Altitude (Day 4)
```bash
navronis --subsystem nozzle --thrust 30000 --pc 70 --propellants LOX/CH4 --expansion-ratio 30 --altitude 12000
```

#### 6. Turbomachinery Power Balance (Day 5)
```bash
navronis --subsystem cycle --thrust 40000 --pc 70 --propellants LOX/CH4 --cycle gas_generator
```

#### 7. 2D Ascent Flight Simulator (Day 5)
```bash
navronis --subsystem trajectory --thrust 180000 --vehicle-mass 12000 --payload-mass 350 --burn-time 150
```

#### 8. Full Engine System Datasheet (Day 5)
```bash
navronis --subsystem system --thrust 50000 --pc 70 --propellants LOX/CH4 --cycle gas_generator
```

---

### Method 3: Python API

```python
from kryptonis.propulsion_equations import (
    CombustorDesign,
    InjectorDesign,
    RegenCoolingJacket,
    NozzleDesign,
    EngineCycleDesign,
    TrajectorySimulation,
    EngineSystem,
)

# Complete End-to-End Rocket Engine System
engine = EngineSystem(
    name="Methalox-50kN",
    thrust_sea_level=50000.0,
    chamber_pressure=70.0e5,
    propellant="LOX/CH4",
    cycle_type="gas_generator",
    expansion_ratio=35.0,
    vehicle_liftoff_mass_kg=12000.0,
    payload_mass_kg=350.0,
)
result = engine.solve()

# Print comprehensive aerospace engine datasheet
print(result.summary_report())

# Export full engineering JSON specification
json_spec = result.to_json(indent=2)
```

---

## Running Tests & Verification

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run all 100 automated verification tests
pytest tests/ -v
```

**Verification Suite Overview (100 / 100 Passed in 1.51s):**
- `test_chamber_and_combustion.py`: Sonic throat area, isentropic mass flow, Humble contraction ratio, and stay time.
- `test_bartz.py`: Bartz recovery temperature bounds, convective heat transfer coefficient, and $\sigma$ factor.
- `test_chamber_acoustics.py`: Exact Bessel roots for 1T, 1R, and 1L acoustic cavity frequencies (NASA SP-194).
- `test_injector.py`: Torricelli hydraulics, chugging decoupling stiffness ($\Delta P / P_c \ge 0.15$), coaxial, swirl, pintle, and doublet atomization.
- `test_coolant_and_conduction.py`: Fourier radial wall conduction, Haaland friction factor, and Gnielinski coolant heat transfer.
- `test_regen_channel.py`: Milled channel geometry, perimeter limits, Gnielinski HTC, Haaland friction, fin efficiency, 3-resistance conjugate closure, Darcy-Weisbach $\Delta P$, thermal stress.
- `test_nozzle.py`: 1D Area-Mach inversion, Rao 80% bell Bézier contour, Stark (2005) separation, 1976 Standard Atmosphere.
- `test_cycle.py` **(Day 5)**: Centrifugal pump hydraulics, $N_s$ impeller classification, $N_{ss}$ cavitation inversion, turbine isentropic expansion, and all 5 engine cycles (GG, Expander, ORSC, FRSC, FFSC, Pressure-Fed).
- `test_trajectory.py` **(Day 5)**: Transonic wave drag curve $C_D(M)$, 2D powered ascent gravity turn numerical integration, atmospheric density profile, Max Q magnitude and altitude, $\Delta V$ loss bookkeeping, and orbital deficit.
- `test_engine_system.py` **(Day 5)**: Master `EngineSystem` synthesizer end-to-end integration across Methalox, Hydrolox, Kerolox, automated datasheets, and JSON serialization.

---

## Architecture & Project Structure

```text
Navronis-Propulsion/
├── src/
│   └── kryptonis/
│       └── propulsion_equations/
│           ├── __init__.py           # Unified top-level API (v0.5.0)
│           ├── combustor.py          # Day 1: CombustorDesign & CombustorResult
│           ├── injector.py           # Day 2: 4 Canonical Injector Families
│           ├── regen_channel.py      # Day 3: RegenCoolingJacket & Conjugate Wall Solver
│           ├── nozzle.py             # Day 4: Rao 80% Bell Nozzle & Standard Atmosphere
│           ├── cycle.py              # Day 5: Turbomachinery Hydraulics & 5 Power Cycles
│           ├── trajectory.py         # Day 5: 2D Powered Ascent Gravity Turn Simulator
│           ├── system.py             # Day 5: Unified Master EngineSystem Synthesizer
│           ├── chamber.py            # NASA SP-125 throat, contraction & volume equations
│           ├── combustion.py         # Characteristic velocity c* & stay time
│           ├── bartz.py              # Canonical Bartz 1957 convective film coefficient
│           ├── chamber_acoustics.py  # NASA SP-194 Bessel acoustic cavity modes
│           ├── profile.py            # Axial (x, r) coordinate inner-wall generator
│           ├── plotting.py           # Matplotlib 2D cross-section visualizer
│           ├── export.py             # Structured JSON & CSV profile exporters
│           ├── units.py              # Strongly-typed Result, Status & provenance containers
│           ├── aerodynamics.py       # 1D isentropic gas dynamics Area-Mach solver
│           ├── thermal.py            # Conjugate heat transfer & thermal marching
│           ├── coolant.py            # Supercritical fluid convection & channel friction
│           ├── wall_conduction.py    # 1D radial Fourier heat conduction
│           └── cli.py                # Standalone terminal CLI (all 5 subsystems + system)
├── docs/
│   ├── index.html                    # Interactive Web App (Days 1–5 live simulator)
│   ├── .nojekyll                     # GitHub Pages static asset bypass
│   └── assets/                       # Dimensioned plots and figures
├── examples/
│   ├── combustor_30kn.py             # 30 kN LOX/CH4 chamber sizing
│   ├── 01_thrust_chamber_sizing.py   # SP-125 analytical chamber sizing
│   ├── 02_bartz_heat_flux.py         # Throat convective heat flux & conduction
│   ├── 03_regenerative_cooling.py    # Cooling channel friction & curvature
│   ├── 04_nozzle_divergence_and_separation.py # Gas dynamics & separation limits
│   ├── 05_injector_sizing.py         # Sizing the 4 canonical injector families
│   ├── 06_regenerative_cooling_channels.py # Day 3 regenerative cooling jacket sizing
│   ├── 07_turbopump_cycle_power_balance.py # Day 5: 5-cycle turbomachinery power balance
│   └── 08_integrated_engine_system_and_flight.py # Day 5: Master engine system & ascent flight
├── tests/                            # 100 automated unit tests (100% pass rate)
├── pyproject.toml                    # PEP 621 standard package build metadata (v0.5.0)
├── LICENSE                           # Apache-2.0 open-source license
└── README.md                         # Project documentation and engineering handbook
```

---

## License

This project is licensed under the **Apache License 2.0** — see the [LICENSE](LICENSE) file for details.

