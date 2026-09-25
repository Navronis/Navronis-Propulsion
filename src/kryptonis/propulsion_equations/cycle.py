"""
Liquid Rocket Engine Power Balance & Turbomachinery Sizing Module (Day 5).
========================================================================

Authoritative, first-principles analytical sizing of liquid rocket turbopumps
and engine power balance cycles across the 5 canonical architectures:

1. Pressure-Fed Cycle (Apollo LMDE, SuperDraco, Kestrel, Electron RCS)
2. Open Gas Generator Cycle (GG) (Merlin 1D, F-1, Vulcain 2, Vikas)
3. Closed Expander Cycle & Expander Bleed (RL10, Vinci, LE-5B)
4. Staged Combustion Cycle:
   - Oxidizer-Rich Staged Combustion (ORSC) (RD-180, RD-170, NK-33)
   - Fuel-Rich Staged Combustion (FRSC) (RS-25 SSME)
5. Full-Flow Staged Combustion (FFSC) (SpaceX Raptor, RD-270)

Governing Literature References:
- Huzel, D. K. & Huang, D. H. (1992), Modern Engineering for Design of
  Liquid-Propellant Rocket Engines, AIAA, Chapter 2 (Engine Systems) & Chapter 6 (Turbopumps).
- Sutton, G. P. & Biblarz, O. (2016), Rocket Propulsion Elements, 9th Ed.,
  Wiley, Chapter 6 (Turbopump Feed Systems) & Chapter 10 (Engine Systems).
- Humble, R. W., Henry, G. N. & Larson, W. J. (1995), Space Propulsion Analysis
  and Design, McGraw-Hill, Chapter 6.
- Stepanoff, A. J. (1957), Centrifugal and Axial Flow Pumps: Theory, Design,
  and Application, John Wiley & Sons.
- NASA SP-8107 (1973), Turbopump Systems for Liquid Rocket Engines.
- NASA SP-8110 (1974), Liquid Rocket Engine Turbopump Inducers.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from kryptonis.propulsion_equations.units import Result, Status

# --------------------------------------------------------------------------
# Literature Provenance Citations
# --------------------------------------------------------------------------
CITATIONS: Dict[str, str] = {
    "pump_hydraulics": "Huzel & Huang (1992), Modern Engineering for Design of Liquid Rocket Engines, Ch. 6, Eq. (6-1)",
    "pump_specific_speed": "Stepanoff, A. J. (1957), Centrifugal and Axial Flow Pumps, Wiley; NASA SP-8107 (1973)",
    "suction_specific_speed": "NASA SP-8110 (1974), Liquid Rocket Engine Turbopump Inducers, p. 12",
    "cavitation_npsh": "Sutton & Biblarz (2016), Rocket Propulsion Elements, 9th Ed., Eq. (6-13)",
    "turbine_enthalpy": "Huzel & Huang (1992), Ch. 6, Eq. (6-28); Sutton & Biblarz (2016), Eq. (6-16)",
    "gas_generator_balance": "Humble, Henry & Larson (1995), Space Propulsion Analysis and Design, Ch. 6, Eq. (6-23)",
    "expander_balance": "Sutton & Biblarz (2016), Ch. 10.3, Expander Cycle Heat Balance Limit",
    "staged_combustion_balance": "Huzel & Huang (1992), Ch. 2.4, High-Pressure Staged Combustion Cycles",
    "ffsc_balance": "Sutton & Biblarz (2016), Ch. 10.4; Yang & Anderson (1995), Liquid Rocket Engine Combustion Instability",
    "pressure_fed_pressurant": "Huzel & Huang (1992), Ch. 7, Pressurization Systems, Eq. (7-4)",
}

STANDARD_GRAVITY: float = 9.80665


# --------------------------------------------------------------------------
# 1. Turbopump Hydraulic & Aerodynamic Fundamentals
# --------------------------------------------------------------------------

def pump_head(delta_p_Pa: float, density_kg_m3: float) -> float:
    """Calculates developed pump head H in meters of fluid.

    .. math:: H = \\frac{\\Delta P}{\\rho g_0}

    Parameters
    ----------
    delta_p_Pa : float
        Total pump pressure rise from suction to discharge (Pa).
    density_kg_m3 : float
        Fluid density at pump inlet (kg/m^3).
    """
    if delta_p_Pa <= 0.0:
        raise ValueError(f"Pump delta_p must be positive, got {delta_p_Pa} Pa")
    if density_kg_m3 <= 0.0:
        raise ValueError(f"Fluid density must be positive, got {density_kg_m3} kg/m^3")
    return delta_p_Pa / (density_kg_m3 * STANDARD_GRAVITY)


def pump_power(
    mass_flow_kg_s: float,
    delta_p_Pa: float,
    density_kg_m3: float,
    efficiency: float = 0.72,
) -> float:
    """Calculates required shaft mechanical power to drive the pump (Watts).

    .. math:: \\dot{W}_{pump} = \\frac{\\dot{m} \\Delta P}{\\rho \\eta_{pump}}

    Parameters
    ----------
    mass_flow_kg_s : float
        Mass flow rate through pump (kg/s).
    delta_p_Pa : float
        Pump pressure rise (Pa).
    density_kg_m3 : float
        Fluid density (kg/m^3).
    efficiency : float
        Total pump isentropic/hydraulic efficiency (typical 0.65 - 0.82).
    """
    if mass_flow_kg_s <= 0.0:
        raise ValueError("Mass flow rate must be positive")
    if efficiency <= 0.0 or efficiency > 1.0:
        raise ValueError(f"Pump efficiency must be in (0, 1], got {efficiency}")
    return (mass_flow_kg_s * delta_p_Pa) / (density_kg_m3 * efficiency)


def pump_specific_speed(
    rpm: float,
    flow_m3_s: float,
    head_m: float,
) -> Dict[str, Any]:
    """Calculates pump dimensionless specific speed and US customary specific speed.

    .. math:: N_s = \\frac{\\omega \\sqrt{Q}}{(g_0 H)^{3/4}}
    .. math:: N_{s,US} = \\frac{N_{rpm} \\sqrt{Q_{gpm}}}{H_{ft}^{3/4}}

    Parameters
    ----------
    rpm : float
        Pump shaft rotational speed (revolutions per minute).
    flow_m3_s : float
        Volumetric flow rate (m^3/s).
    head_m : float
        Total pump head (m).

    Returns
    -------
    Dict with:
    - Ns_dimensionless (rad)
    - Ns_US (rpm*gpm^0.5 / ft^0.75)
    - impeller_type ("radial", "mixed_flow", "axial")
    """
    if rpm <= 0.0 or flow_m3_s <= 0.0 or head_m <= 0.0:
        raise ValueError("RPM, flow rate, and head must be strictly positive")

    omega_rad_s = rpm * (2.0 * math.pi / 60.0)
    ns_dim = (omega_rad_s * math.sqrt(flow_m3_s)) / ((STANDARD_GRAVITY * head_m) ** 0.75)

    # US Customary units: Q in gpm, H in ft
    flow_gpm = flow_m3_s * 15850.323
    head_ft = head_m * 3.28084
    ns_us = rpm * math.sqrt(flow_gpm) / (head_ft ** 0.75)

    if ns_us < 1500.0:
        impeller_type = "radial_centrifugal"
    elif ns_us < 4500.0:
        impeller_type = "mixed_flow"
    else:
        impeller_type = "axial_flow"

    return {
        "Ns_dimensionless": float(ns_dim),
        "Ns_US": float(ns_us),
        "impeller_type": impeller_type,
    }


def pump_suction_specific_speed(
    rpm: float,
    flow_m3_s: float,
    npsh_m: float,
) -> float:
    """Calculates pump suction specific speed Nss (US customary units).

    .. math:: N_{ss} = \\frac{N_{rpm} \\sqrt{Q_{gpm}}}{NPSH^{3/4}}

    Standard limits (NASA SP-8110):
    - Without inducer: Nss ~ 6,000 - 9,000
    - With helical inducer: Nss ~ 20,000 - 45,000
    """
    if npsh_m <= 0.0:
        raise ValueError("NPSH must be positive to avoid complete vapor locking")
    flow_gpm = flow_m3_s * 15850.323
    npsh_ft = npsh_m * 3.28084
    return float(rpm * math.sqrt(flow_gpm) / (npsh_ft ** 0.75))


def pump_npsh_required(
    rpm: float,
    flow_m3_s: float,
    target_nss: float = 25000.0,
) -> float:
    """Calculates Net Positive Suction Head Required (NPSH_R) in meters for a given target Nss.

    .. math:: NPSH_R = \\left(\\frac{N_{rpm} \\sqrt{Q_{gpm}}}{N_{ss}}\\right)^{4/3} \\times 0.3048
    """
    flow_gpm = flow_m3_s * 15850.323
    npsh_ft = ((rpm * math.sqrt(flow_gpm)) / target_nss) ** (4.0 / 3.0)
    return float(npsh_ft * 0.3048)


def pump_impeller_tip_speed(head_m: float, head_coefficient_psi: float = 0.55) -> float:
    """Estimates impeller outer tip tangential speed u_tip in m/s.

    .. math:: u_{tip} = \\sqrt{\\frac{g_0 H}{\\psi}}

    Typical head coefficient psi is 0.50 - 0.60 for backward-curved rocket impellers.
    Maximum structural tip speed is typically 450 - 550 m/s for titanium/Inconel.
    """
    if head_coefficient_psi <= 0.0:
        raise ValueError("Head coefficient must be positive")
    return math.sqrt((STANDARD_GRAVITY * head_m) / head_coefficient_psi)


def turbine_power(
    mass_flow_kg_s: float,
    cp_J_kgK: float,
    t_inlet_K: float,
    pressure_ratio: float,
    gamma: float,
    efficiency: float = 0.68,
) -> float:
    """Calculates turbine mechanical shaft power output (Watts).

    .. math:: \\dot{W}_{turb} = \\dot{m}_t \\cdot c_p T_{in} \\eta_{turb} \\left[1 - \\left(\\frac{1}{PR}\\right)^{\\frac{\\gamma-1}{\\gamma}}\\right]
    """
    if mass_flow_kg_s <= 0.0:
        raise ValueError("Turbine mass flow must be positive")
    if pressure_ratio <= 1.0:
        raise ValueError(f"Turbine pressure ratio must be > 1.0, got {pressure_ratio}")
    if efficiency <= 0.0 or efficiency > 1.0:
        raise ValueError("Turbine efficiency must be in (0, 1]")
    if gamma <= 1.0:
        raise ValueError("Specific heat ratio must be > 1.0")

    expansion_ratio_term = 1.0 - (1.0 / pressure_ratio) ** ((gamma - 1.0) / gamma)
    delta_h_isentropic = cp_J_kgK * t_inlet_K * expansion_ratio_term
    return mass_flow_kg_s * delta_h_isentropic * efficiency


# --------------------------------------------------------------------------
# 2. Cycle Sizing Algorithms
# --------------------------------------------------------------------------

def size_pressure_fed_cycle(
    p_chamber_Pa: float,
    m_dot_ox_kg_s: float,
    m_dot_fuel_kg_s: float,
    rho_ox_kg_m3: float,
    rho_fuel_kg_m3: float,
    burn_time_s: float,
    delta_p_injector_fraction: float = 0.20,
    delta_p_feedlines_Pa: float = 2.0e5,
    pressurant_gas: str = "Helium",
    tank_ullage_fraction: float = 0.08,
) -> Dict[str, Any]:
    """Sizes a pressure-fed engine system with pressurant gas mass requirements."""
    p_tank_ox = p_chamber_Pa * (1.0 + delta_p_injector_fraction) + delta_p_feedlines_Pa
    p_tank_fuel = p_chamber_Pa * (1.0 + delta_p_injector_fraction) + delta_p_feedlines_Pa

    vol_ox = (m_dot_ox_kg_s * burn_time_s) / rho_ox_kg_m3 * (1.0 + tank_ullage_fraction)
    vol_fuel = (m_dot_fuel_kg_s * burn_time_s) / rho_fuel_kg_m3 * (1.0 + tank_ullage_fraction)

    if pressurant_gas.lower() == "helium":
        r_gas = 2077.2  # J/(kg*K)
    elif pressurant_gas.lower() == "nitrogen":
        r_gas = 296.8   # J/(kg*K)
    else:
        r_gas = 2077.2

    t_pressurant_K = 293.15
    pressurant_collapse_factor = 1.35  # NASA SP-125 thermal chilling factor
    m_pressurant_ox = (p_tank_ox * vol_ox) / (r_gas * t_pressurant_K) * pressurant_collapse_factor
    m_pressurant_fuel = (p_tank_fuel * vol_fuel) / (r_gas * t_pressurant_K) * pressurant_collapse_factor
    m_pressurant_total = m_pressurant_ox + m_pressurant_fuel

    return {
        "cycle_type": "pressure_fed",
        "p_tank_ox_Pa": p_tank_ox,
        "p_tank_fuel_Pa": p_tank_fuel,
        "p_tank_bar": p_tank_ox / 1.0e5,
        "volume_ox_m3": vol_ox,
        "volume_fuel_m3": vol_fuel,
        "pressurant_gas": pressurant_gas,
        "pressurant_mass_kg": m_pressurant_total,
        "turbopump_required": False,
        "provenance": CITATIONS["pressure_fed_pressurant"],
    }


def size_gas_generator_cycle(
    p_chamber_Pa: float,
    m_dot_ox_kg_s: float,
    m_dot_fuel_kg_s: float,
    rho_ox_kg_m3: float,
    rho_fuel_kg_m3: float,
    main_isp_vac_s: float,
    delta_p_injector_fraction: float = 0.20,
    delta_p_cooling_fraction: float = 0.35,
    pump_eff_ox: float = 0.74,
    pump_eff_fuel: float = 0.70,
    turbine_eff: float = 0.65,
    mechanical_eff: float = 0.96,
    t_turbine_inlet_K: float = 950.0,
    turbine_pressure_ratio: float = 16.0,
    turbine_cp_J_kgK: float = 2750.0,
    turbine_gamma: float = 1.25,
) -> Dict[str, Any]:
    """Sizes an open Gas Generator (GG) cycle power balance (Merlin 1D, F-1, Vulcain)."""
    dp_ox_inj = delta_p_injector_fraction * p_chamber_Pa
    dp_fuel_inj = delta_p_injector_fraction * p_chamber_Pa
    dp_cool = delta_p_cooling_fraction * p_chamber_Pa
    dp_valves = 0.05 * p_chamber_Pa

    p_discharge_ox = p_chamber_Pa + dp_ox_inj + dp_valves
    p_discharge_fuel = p_chamber_Pa + dp_fuel_inj + dp_cool + dp_valves

    head_ox = pump_head(p_discharge_ox, rho_ox_kg_m3)
    head_fuel = pump_head(p_discharge_fuel, rho_fuel_kg_m3)

    power_ox = pump_power(m_dot_ox_kg_s, p_discharge_ox, rho_ox_kg_m3, pump_eff_ox)
    power_fuel = pump_power(m_dot_fuel_kg_s, p_discharge_fuel, rho_fuel_kg_m3, pump_eff_fuel)
    total_pump_power = power_ox + power_fuel

    w_turb_required = total_pump_power / mechanical_eff

    expansion_term = 1.0 - (1.0 / turbine_pressure_ratio) ** ((turbine_gamma - 1.0) / turbine_gamma)
    dh_sp_turb = turbine_cp_J_kgK * t_turbine_inlet_K * expansion_term * turbine_eff

    m_dot_turb = w_turb_required / dh_sp_turb
    m_dot_main = m_dot_ox_kg_s + m_dot_fuel_kg_s
    m_dot_total_engine = m_dot_main + m_dot_turb
    alpha_gg = m_dot_turb / m_dot_total_engine

    isp_turb_exhaust = 115.0
    net_isp_vac_s = (main_isp_vac_s * m_dot_main + isp_turb_exhaust * m_dot_turb) / m_dot_total_engine
    isp_loss_percent = ((main_isp_vac_s - net_isp_vac_s) / main_isp_vac_s) * 100.0

    return {
        "cycle_type": "gas_generator",
        "p_pump_ox_discharge_Pa": p_discharge_ox,
        "p_pump_fuel_discharge_Pa": p_discharge_fuel,
        "p_pump_ox_bar": p_discharge_ox / 1.0e5,
        "p_pump_fuel_bar": p_discharge_fuel / 1.0e5,
        "head_ox_m": head_ox,
        "head_fuel_m": head_fuel,
        "power_pump_ox_kW": power_ox / 1.0e3,
        "power_pump_fuel_kW": power_fuel / 1.0e3,
        "total_pump_power_kW": total_pump_power / 1.0e3,
        "turbine_shaft_power_kW": w_turb_required / 1.0e3,
        "m_dot_gas_generator_kg_s": m_dot_turb,
        "alpha_gas_generator_fraction": alpha_gg,
        "alpha_percent": alpha_gg * 100.0,
        "main_isp_vac_s": main_isp_vac_s,
        "net_isp_vac_s": net_isp_vac_s,
        "isp_penalty_s": main_isp_vac_s - net_isp_vac_s,
        "isp_loss_percent": isp_loss_percent,
        "power_balance_closed": True,
        "provenance": CITATIONS["gas_generator_balance"],
    }


def size_expander_cycle(
    p_chamber_Pa: float,
    m_dot_ox_kg_s: float,
    m_dot_fuel_kg_s: float,
    rho_ox_kg_m3: float,
    rho_fuel_kg_m3: float,
    main_isp_vac_s: float,
    coolant_cp_J_kgK: float = 3500.0,
    delta_t_coolant_K: float = 140.0,
    delta_p_injector_fraction: float = 0.20,
    delta_p_cooling_fraction: float = 0.35,
    pump_eff_ox: float = 0.72,
    pump_eff_fuel: float = 0.68,
    turbine_eff: float = 0.70,
    mechanical_eff: float = 0.95,
    turbine_gamma: float = 1.30,
) -> Dict[str, Any]:
    """Sizes a closed Expander Cycle power balance (RL10, Vinci)."""
    dp_ox_inj = delta_p_injector_fraction * p_chamber_Pa
    dp_fuel_inj = delta_p_injector_fraction * p_chamber_Pa
    dp_cool = delta_p_cooling_fraction * p_chamber_Pa
    dp_valves = 0.05 * p_chamber_Pa

    pr_target = 1.65
    p_turb_out = p_chamber_Pa + dp_fuel_inj + dp_valves
    p_turb_in = p_turb_out * pr_target
    p_discharge_fuel = p_turb_in + dp_cool + dp_valves
    p_discharge_ox = p_chamber_Pa + dp_ox_inj + dp_valves

    power_ox = pump_power(m_dot_ox_kg_s, p_discharge_ox, rho_ox_kg_m3, pump_eff_ox)
    power_fuel = pump_power(m_dot_fuel_kg_s, p_discharge_fuel, rho_fuel_kg_m3, pump_eff_fuel)
    total_pump_power = power_ox + power_fuel

    q_absorbed_W = m_dot_fuel_kg_s * coolant_cp_J_kgK * delta_t_coolant_K
    t_turb_in_K = 300.0 + delta_t_coolant_K
    expansion_term = 1.0 - (1.0 / pr_target) ** ((turbine_gamma - 1.0) / turbine_gamma)
    w_turb_avail = m_dot_fuel_kg_s * coolant_cp_J_kgK * t_turb_in_K * expansion_term * turbine_eff

    power_margin = (w_turb_avail * mechanical_eff) / total_pump_power
    feasible = power_margin >= 1.0

    return {
        "cycle_type": "expander_closed",
        "p_pump_ox_bar": p_discharge_ox / 1.0e5,
        "p_pump_fuel_bar": p_discharge_fuel / 1.0e5,
        "power_pump_ox_kW": power_ox / 1.0e3,
        "power_pump_fuel_kW": power_fuel / 1.0e3,
        "total_pump_power_kW": total_pump_power / 1.0e3,
        "thermal_heat_absorbed_kW": q_absorbed_W / 1.0e3,
        "turbine_power_available_kW": w_turb_avail / 1.0e3,
        "power_balance_margin": power_margin,
        "cycle_feasible": feasible,
        "net_isp_vac_s": main_isp_vac_s,
        "isp_penalty_s": 0.0,
        "pinch_point_margin_percent": (power_margin - 1.0) * 100.0,
        "provenance": CITATIONS["expander_balance"],
    }


def size_staged_combustion_cycle(
    p_chamber_Pa: float,
    m_dot_ox_kg_s: float,
    m_dot_fuel_kg_s: float,
    rho_ox_kg_m3: float,
    rho_fuel_kg_m3: float,
    main_isp_vac_s: float,
    staged_type: str = "oxidizer_rich",
    delta_p_injector_fraction: float = 0.20,
    delta_p_cooling_fraction: float = 0.35,
    pump_eff_ox: float = 0.76,
    pump_eff_fuel: float = 0.73,
    turbine_eff: float = 0.72,
    mechanical_eff: float = 0.96,
    preburner_t_inlet_K: float = 750.0,
    turbine_pressure_ratio: float = 1.45,
    turbine_gamma: float = 1.22,
) -> Dict[str, Any]:
    """Sizes a single-shaft Staged Combustion Cycle (RD-180 ORSC or RS-25 FRSC)."""
    dp_ox_inj = delta_p_injector_fraction * p_chamber_Pa
    dp_fuel_inj = delta_p_injector_fraction * p_chamber_Pa
    dp_cool = delta_p_cooling_fraction * p_chamber_Pa
    dp_valves = 0.05 * p_chamber_Pa

    p_pb_exit = p_chamber_Pa + dp_ox_inj + dp_valves
    p_pb_chamber = p_pb_exit * turbine_pressure_ratio

    if staged_type.lower() in ["oxidizer_rich", "orsc"]:
        p_discharge_ox = p_pb_chamber + 0.15 * p_pb_chamber
        p_discharge_fuel = p_chamber_Pa + dp_fuel_inj + dp_cool + dp_valves
        m_dot_drive = m_dot_ox_kg_s
        cp_drive = 1750.0
    else:
        p_discharge_fuel = p_pb_chamber + 0.25 * p_pb_chamber
        p_discharge_ox = p_chamber_Pa + dp_ox_inj + dp_valves
        m_dot_drive = m_dot_fuel_kg_s
        cp_drive = 14200.0 if rho_fuel_kg_m3 < 100.0 else 3200.0

    power_ox = pump_power(m_dot_ox_kg_s, p_discharge_ox, rho_ox_kg_m3, pump_eff_ox)
    power_fuel = pump_power(m_dot_fuel_kg_s, p_discharge_fuel, rho_fuel_kg_m3, pump_eff_fuel)
    total_pump_power = power_ox + power_fuel

    expansion_term = 1.0 - (1.0 / turbine_pressure_ratio) ** ((turbine_gamma - 1.0) / turbine_gamma)
    w_turb_avail = m_dot_drive * cp_drive * preburner_t_inlet_K * expansion_term * turbine_eff
    power_margin = (w_turb_avail * mechanical_eff) / total_pump_power

    return {
        "cycle_type": f"staged_combustion_{staged_type.lower()}",
        "preburner_pressure_bar": p_pb_chamber / 1.0e5,
        "p_pump_ox_bar": p_discharge_ox / 1.0e5,
        "p_pump_fuel_bar": p_discharge_fuel / 1.0e5,
        "power_pump_ox_kW": power_ox / 1.0e3,
        "power_pump_fuel_kW": power_fuel / 1.0e3,
        "total_pump_power_kW": total_pump_power / 1.0e3,
        "turbine_power_available_kW": w_turb_avail / 1.0e3,
        "power_balance_margin": power_margin,
        "cycle_feasible": power_margin >= 1.0,
        "net_isp_vac_s": main_isp_vac_s,
        "isp_penalty_s": 0.0,
        "provenance": CITATIONS["staged_combustion_balance"],
    }


def size_full_flow_staged_combustion_cycle(
    p_chamber_Pa: float,
    m_dot_ox_kg_s: float,
    m_dot_fuel_kg_s: float,
    rho_ox_kg_m3: float,
    rho_fuel_kg_m3: float,
    main_isp_vac_s: float,
    delta_p_injector_fraction: float = 0.15,
    delta_p_cooling_fraction: float = 0.30,
    pump_eff_ox: float = 0.78,
    pump_eff_fuel: float = 0.76,
    turbine_eff: float = 0.74,
    t_ox_preburner_K: float = 680.0,
    t_fuel_preburner_K: float = 850.0,
    pr_ox_turb: float = 1.35,
    pr_fuel_turb: float = 1.38,
) -> Dict[str, Any]:
    """Sizes a Full-Flow Staged Combustion (FFSC) Cycle (SpaceX Raptor)."""
    dp_ox_inj = delta_p_injector_fraction * p_chamber_Pa
    dp_fuel_inj = delta_p_injector_fraction * p_chamber_Pa
    dp_cool = delta_p_cooling_fraction * p_chamber_Pa
    dp_valves = 0.05 * p_chamber_Pa

    p_ox_pb = (p_chamber_Pa + dp_ox_inj + dp_valves) * pr_ox_turb
    p_pump_ox = p_ox_pb + 0.12 * p_ox_pb

    p_fuel_pb = (p_chamber_Pa + dp_fuel_inj + dp_valves) * pr_fuel_turb
    p_pump_fuel = p_fuel_pb + dp_cool + dp_valves

    power_ox_pump = pump_power(m_dot_ox_kg_s, p_pump_ox, rho_ox_kg_m3, pump_eff_ox)
    power_fuel_pump = pump_power(m_dot_fuel_kg_s, p_pump_fuel, rho_fuel_kg_m3, pump_eff_fuel)

    gamma_ox = 1.23
    cp_ox = 1820.0
    exp_ox = 1.0 - (1.0 / pr_ox_turb) ** ((gamma_ox - 1.0) / gamma_ox)
    power_ox_turb = m_dot_ox_kg_s * cp_ox * t_ox_preburner_K * exp_ox * turbine_eff

    gamma_fuel = 1.26
    cp_fuel = 3100.0
    exp_fuel = 1.0 - (1.0 / pr_fuel_turb) ** ((gamma_fuel - 1.0) / gamma_fuel)
    power_fuel_turb = m_dot_fuel_kg_s * cp_fuel * t_fuel_preburner_K * exp_fuel * turbine_eff

    margin_ox = power_ox_turb / power_ox_pump
    margin_fuel = power_fuel_turb / power_fuel_pump

    return {
        "cycle_type": "full_flow_staged_combustion",
        "ox_preburner_pressure_bar": p_ox_pb / 1.0e5,
        "fuel_preburner_pressure_bar": p_fuel_pb / 1.0e5,
        "p_pump_ox_bar": p_pump_ox / 1.0e5,
        "p_pump_fuel_bar": p_pump_fuel / 1.0e5,
        "power_ox_pump_kW": power_ox_pump / 1.0e3,
        "power_fuel_pump_kW": power_fuel_pump / 1.0e3,
        "power_ox_turbine_kW": power_ox_turb / 1.0e3,
        "power_fuel_turbine_kW": power_fuel_turb / 1.0e3,
        "ox_turbopump_margin": margin_ox,
        "fuel_turbopump_margin": margin_fuel,
        "cycle_feasible": (margin_ox >= 1.0 and margin_fuel >= 1.0),
        "net_isp_vac_s": main_isp_vac_s,
        "gas_gas_injection": True,
        "provenance": CITATIONS["ffsc_balance"],
    }


# --------------------------------------------------------------------------
# 3. High-Level Facade: EngineCycleDesign & EngineCycleResult
# --------------------------------------------------------------------------

@dataclass
class EngineCycleResult:
    """Strongly-typed container for liquid rocket cycle power balance results."""
    cycle_type: str
    p_chamber_bar: float
    m_dot_ox_kg_s: float
    m_dot_fuel_kg_s: float
    m_dot_total_kg_s: float
    power_pump_ox_kW: float
    power_pump_fuel_kW: float
    total_pump_power_kW: float
    net_isp_vac_s: float
    isp_penalty_s: float
    cycle_feasible: bool
    details: Dict[str, Any] = field(default_factory=dict)
    provenance: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def explain(self, parameter: str) -> str:
        """Returns literature citation and physical explanation for any parameter."""
        p_lower = parameter.lower()
        if "pump" in p_lower:
            return f"Pump Hydraulics: {CITATIONS['pump_hydraulics']}"
        elif "npsh" in p_lower or "cavitation" in p_lower:
            return f"Cavitation & NPSH: {CITATIONS['cavitation_npsh']}"
        elif "gas_generator" in p_lower or "gg" in p_lower:
            return f"Gas Generator Power Balance: {CITATIONS['gas_generator_balance']}"
        elif "expander" in p_lower:
            return f"Expander Heat Balance Limit: {CITATIONS['expander_balance']}"
        elif "staged" in p_lower or "sc" in p_lower:
            return f"Staged Combustion Balance: {CITATIONS['staged_combustion_balance']}"
        elif "ffsc" in p_lower or "full_flow" in p_lower:
            return f"Full-Flow Staged Combustion: {CITATIONS['ffsc_balance']}"
        return f"Cycle Power Balance: {CITATIONS['pump_hydraulics']}"


class EngineCycleDesign:
    """High-level analytical sizer for engine turbomachinery cycles."""

    def __init__(
        self,
        cycle_type: str = "gas_generator",
        p_chamber_Pa: float = 50.0e5,
        m_dot_ox_kg_s: float = 6.46,
        m_dot_fuel_kg_s: float = 2.15,
        rho_ox_kg_m3: float = 1141.0,
        rho_fuel_kg_m3: float = 422.0,
        main_isp_vac_s: float = 320.0,
        **kwargs: Any,
    ) -> None:
        self.cycle_type = cycle_type.lower()
        self.p_chamber_Pa = p_chamber_Pa
        self.m_dot_ox_kg_s = m_dot_ox_kg_s
        self.m_dot_fuel_kg_s = m_dot_fuel_kg_s
        self.rho_ox_kg_m3 = rho_ox_kg_m3
        self.rho_fuel_kg_m3 = rho_fuel_kg_m3
        self.main_isp_vac_s = main_isp_vac_s
        self.kwargs = kwargs

    def solve(self) -> EngineCycleResult:
        m_tot = self.m_dot_ox_kg_s + self.m_dot_fuel_kg_s

        if self.cycle_type in ["gas_generator", "gg", "open_gg"]:
            res = size_gas_generator_cycle(
                p_chamber_Pa=self.p_chamber_Pa,
                m_dot_ox_kg_s=self.m_dot_ox_kg_s,
                m_dot_fuel_kg_s=self.m_dot_fuel_kg_s,
                rho_ox_kg_m3=self.rho_ox_kg_m3,
                rho_fuel_kg_m3=self.rho_fuel_kg_m3,
                main_isp_vac_s=self.main_isp_vac_s,
                **self.kwargs,
            )
            return EngineCycleResult(
                cycle_type="gas_generator",
                p_chamber_bar=self.p_chamber_Pa / 1.0e5,
                m_dot_ox_kg_s=self.m_dot_ox_kg_s,
                m_dot_fuel_kg_s=self.m_dot_fuel_kg_s,
                m_dot_total_kg_s=m_tot + res["m_dot_gas_generator_kg_s"],
                power_pump_ox_kW=res["power_pump_ox_kW"],
                power_pump_fuel_kW=res["power_pump_fuel_kW"],
                total_pump_power_kW=res["total_pump_power_kW"],
                net_isp_vac_s=res["net_isp_vac_s"],
                isp_penalty_s=res["isp_penalty_s"],
                cycle_feasible=True,
                details=res,
                provenance={"balance": CITATIONS["gas_generator_balance"]},
            )

        elif self.cycle_type in ["expander", "expander_closed"]:
            res = size_expander_cycle(
                p_chamber_Pa=self.p_chamber_Pa,
                m_dot_ox_kg_s=self.m_dot_ox_kg_s,
                m_dot_fuel_kg_s=self.m_dot_fuel_kg_s,
                rho_ox_kg_m3=self.rho_ox_kg_m3,
                rho_fuel_kg_m3=self.rho_fuel_kg_m3,
                main_isp_vac_s=self.main_isp_vac_s,
                coolant_cp_J_kgK=self.kwargs.get("coolant_cp_J_kgK", 3500.0),
                delta_t_coolant_K=self.kwargs.get("delta_t_coolant_K", 140.0),
            )
            return EngineCycleResult(
                cycle_type="expander_closed",
                p_chamber_bar=self.p_chamber_Pa / 1.0e5,
                m_dot_ox_kg_s=self.m_dot_ox_kg_s,
                m_dot_fuel_kg_s=self.m_dot_fuel_kg_s,
                m_dot_total_kg_s=m_tot,
                power_pump_ox_kW=res["power_pump_ox_kW"],
                power_pump_fuel_kW=res["power_pump_fuel_kW"],
                total_pump_power_kW=res["total_pump_power_kW"],
                net_isp_vac_s=res["net_isp_vac_s"],
                isp_penalty_s=0.0,
                cycle_feasible=res["cycle_feasible"],
                details=res,
                provenance={"balance": CITATIONS["expander_balance"]},
            )

        elif "staged" in self.cycle_type and "full" not in self.cycle_type:
            stype = "oxidizer_rich" if "ox" in self.cycle_type else "fuel_rich"
            res = size_staged_combustion_cycle(
                p_chamber_Pa=self.p_chamber_Pa,
                m_dot_ox_kg_s=self.m_dot_ox_kg_s,
                m_dot_fuel_kg_s=self.m_dot_fuel_kg_s,
                rho_ox_kg_m3=self.rho_ox_kg_m3,
                rho_fuel_kg_m3=self.rho_fuel_kg_m3,
                main_isp_vac_s=self.main_isp_vac_s,
                staged_type=stype,
            )
            return EngineCycleResult(
                cycle_type=res["cycle_type"],
                p_chamber_bar=self.p_chamber_Pa / 1.0e5,
                m_dot_ox_kg_s=self.m_dot_ox_kg_s,
                m_dot_fuel_kg_s=self.m_dot_fuel_kg_s,
                m_dot_total_kg_s=m_tot,
                power_pump_ox_kW=res["power_pump_ox_kW"],
                power_pump_fuel_kW=res["power_pump_fuel_kW"],
                total_pump_power_kW=res["total_pump_power_kW"],
                net_isp_vac_s=res["net_isp_vac_s"],
                isp_penalty_s=0.0,
                cycle_feasible=res["cycle_feasible"],
                details=res,
                provenance={"balance": CITATIONS["staged_combustion_balance"]},
            )

        elif self.cycle_type in ["full_flow", "ffsc", "full_flow_staged"]:
            res = size_full_flow_staged_combustion_cycle(
                p_chamber_Pa=self.p_chamber_Pa,
                m_dot_ox_kg_s=self.m_dot_ox_kg_s,
                m_dot_fuel_kg_s=self.m_dot_fuel_kg_s,
                rho_ox_kg_m3=self.rho_ox_kg_m3,
                rho_fuel_kg_m3=self.rho_fuel_kg_m3,
                main_isp_vac_s=self.main_isp_vac_s,
            )
            return EngineCycleResult(
                cycle_type="full_flow_staged_combustion",
                p_chamber_bar=self.p_chamber_Pa / 1.0e5,
                m_dot_ox_kg_s=self.m_dot_ox_kg_s,
                m_dot_fuel_kg_s=self.m_dot_fuel_kg_s,
                m_dot_total_kg_s=m_tot,
                power_pump_ox_kW=res["power_ox_pump_kW"],
                power_pump_fuel_kW=res["power_fuel_pump_kW"],
                total_pump_power_kW=res["power_ox_pump_kW"] + res["power_fuel_pump_kW"],
                net_isp_vac_s=res["net_isp_vac_s"],
                isp_penalty_s=0.0,
                cycle_feasible=res["cycle_feasible"],
                details=res,
                provenance={"balance": CITATIONS["ffsc_balance"]},
            )

        elif self.cycle_type in ["pressure_fed", "pressure"]:
            res = size_pressure_fed_cycle(
                p_chamber_Pa=self.p_chamber_Pa,
                m_dot_ox_kg_s=self.m_dot_ox_kg_s,
                m_dot_fuel_kg_s=self.m_dot_fuel_kg_s,
                rho_ox_kg_m3=self.rho_ox_kg_m3,
                rho_fuel_kg_m3=self.rho_fuel_kg_m3,
                burn_time_s=self.kwargs.get("burn_time_s", 60.0),
            )
            return EngineCycleResult(
                cycle_type="pressure_fed",
                p_chamber_bar=self.p_chamber_Pa / 1.0e5,
                m_dot_ox_kg_s=self.m_dot_ox_kg_s,
                m_dot_fuel_kg_s=self.m_dot_fuel_kg_s,
                m_dot_total_kg_s=m_tot,
                power_pump_ox_kW=0.0,
                power_pump_fuel_kW=0.0,
                total_pump_power_kW=0.0,
                net_isp_vac_s=self.main_isp_vac_s,
                isp_penalty_s=0.0,
                cycle_feasible=True,
                details=res,
                provenance={"balance": CITATIONS["pressure_fed_pressurant"]},
            )

        else:
            raise ValueError(f"Unknown cycle type: '{self.cycle_type}'. Supported: gas_generator, expander, staged_combustion_ox, staged_combustion_fuel, full_flow_staged, pressure_fed")
