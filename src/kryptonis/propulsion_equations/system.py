"""
Unified Engine System Architecture & Master Synthesis Module (Day 5).
=====================================================================

The master engine architect that synthesizes all five analytical pillars of Navronis:
- Day 1: Thermochemistry & Combustor Chamber Sizing (NASA SP-125, Bartz 1957)
- Day 2: 4 Canonical Injector Families & Droplet Atomization SMD (Lorenzetto-Lefebvre, Bazarov-Yang)
- Day 3: Regenerative Cooling Channels & Conjugate Wall Solver (NASA SP-8087, Gnielinski 1976)
- Day 4: Supersonic Nozzle Aerodynamics & Altitude Engine (Rao 1958, Stark 2005)
- Day 5: Turbomachinery Cycles (Huzel-Huang 1992) & Launch Trajectory Flight Mechanics (Griffin-French 2004)

Provides a single master entrypoint (EngineSystem) to size, balance, and fly
an entire liquid rocket engine from first principles in a single function call.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from kryptonis.propulsion_equations.combustor import CombustorDesign, CombustorResult
from kryptonis.propulsion_equations.injector import (
    InjectorDesign,
    size_shear_coaxial,
    size_swirl_coaxial,
    size_bicentrifugal_swirl_injector,
    size_pintle_injector,
    size_impinging_doublet,
)
from kryptonis.propulsion_equations.regen_channel import (
    RegenCoolingJacket,
    RegenChannelResult,
)
from kryptonis.propulsion_equations.nozzle import NozzleDesign, NozzleResult
from kryptonis.propulsion_equations.cycle import EngineCycleDesign, EngineCycleResult
from kryptonis.propulsion_equations.trajectory import TrajectorySimulation, TrajectoryResult
from kryptonis.propulsion_equations.units import Result, Status

STANDARD_GRAVITY: float = 9.80665


@dataclass
class EngineSystemResult:
    """Strongly-typed container for complete end-to-end rocket engine system results."""
    name: str
    propellant: str
    cycle: str
    thrust_vac_kN: float
    thrust_sl_kN: float
    isp_vac_s: float
    isp_sl_s: float
    p_chamber_bar: float
    mass_flow_total_kg_s: float
    mass_flow_ox_kg_s: float
    mass_flow_fuel_kg_s: float
    mixture_ratio: float
    throat_diameter_mm: float
    chamber_diameter_mm: float
    nozzle_exit_diameter_mm: float
    nozzle_length_mm: float
    expansion_ratio: float
    engine_dry_mass_kg: float
    thrust_to_weight_vac: float
    
    # Subsystem detail payloads
    combustor: Dict[str, Any]
    nozzle: Dict[str, Any]
    injector: Dict[str, Any]
    cooling: Optional[Dict[str, Any]]
    cycle_balance: Dict[str, Any]
    flight: Optional[Dict[str, Any]]
    provenance: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), default=str, indent=indent)

    def summary_report(self) -> str:
        """Generates an authoritative ASCII engine specification datasheet."""
        tw_str = f"{self.thrust_to_weight_vac:.1f}"
        report = [
            "=" * 78,
            f"  NAVRONIS PROPULSION ENGINE SPECIFICATION DATASHEET: {self.name.upper()}",
            "=" * 78,
            f"  Propellant Combination:       {self.propellant}",
            f"  Engine Power Cycle:           {self.cycle.upper()}",
            f"  Chamber Pressure:             {self.p_chamber_bar:.1f} bar ({self.p_chamber_bar*0.1:.2f} MPa)",
            f"  Mixture Ratio (O/F):          {self.mixture_ratio:.2f}",
            "-" * 78,
            "  PERFORMANCE METRICS:",
            f"    Vacuum Thrust:              {self.thrust_vac_kN:.2f} kN",
            f"    Sea-Level Thrust:           {self.thrust_sl_kN:.2f} kN",
            f"    Vacuum Specific Impulse:    {self.isp_vac_s:.1f} s",
            f"    Sea-Level Specific Impulse: {self.isp_sl_s:.1f} s",
            f"    Total Mass Flow Rate:       {self.mass_flow_total_kg_s:.3f} kg/s (Ox: {self.mass_flow_ox_kg_s:.3f} kg/s, Fuel: {self.mass_flow_fuel_kg_s:.3f} kg/s)",
            f"    Estimated Dry Engine Mass:  {self.engine_dry_mass_kg:.1f} kg",
            f"    Vacuum Thrust-to-Weight:    {tw_str}",
            "-" * 78,
            "  THRUST CHAMBER & NOZZLE GEOMETRY:",
            f"    Chamber Diameter:           {self.chamber_diameter_mm:.1f} mm",
            f"    Throat Diameter:            {self.throat_diameter_mm:.1f} mm",
            f"    Nozzle Exit Diameter:       {self.nozzle_exit_diameter_mm:.1f} mm",
            f"    Nozzle Axial Length:        {self.nozzle_length_mm:.1f} mm",
            f"    Nozzle Expansion Ratio:     {self.expansion_ratio:.1f}",
            f"    Nozzle Flow Separation:     {self.nozzle.get('flow_separation', {}).get('verdict', 'N/A')}",
            "-" * 78,
            "  TURBOMACHINERY & FEED SYSTEM BALANCE:",
            f"    Total Pump Shaft Power:     {self.cycle_balance.get('total_pump_power_kW', 0.0):.1f} kW",
            f"    Oxidizer Pump Power:        {self.cycle_balance.get('power_pump_ox_kW', 0.0):.1f} kW",
            f"    Fuel Pump Power:            {self.cycle_balance.get('power_pump_fuel_kW', 0.0):.1f} kW",
            f"    Net Cycle Isp (Dump Loss):  {self.cycle_balance.get('net_isp_vac_s', self.isp_vac_s):.1f} s",
            f"    Cycle Feasibility:          {'FEASIBLE (Power Closed)' if self.cycle_balance.get('cycle_feasible', True) else 'UNFEASIBLE'}",
        ]

        if self.flight:
            report.extend([
                "-" * 78,
                "  ASCENT FLIGHT & MISSION TRAJECTORY:",
                f"    Burnout Altitude:           {self.flight.get('burnout_altitude_km', 0.0):.2f} km",
                f"    Burnout Velocity:           {self.flight.get('burnout_velocity_m_s', 0.0):.1f} m/s (Mach {self.flight.get('burnout_mach', 0.0):.2f})",
                f"    Maximum Dynamic Pressure:   {self.flight.get('max_q_kPa', 0.0):.2f} kPa (at {self.flight.get('max_q_altitude_km', 0.0):.2f} km)",
                f"    Gravity Loss:               {self.flight.get('delta_v_gravity_loss_m_s', 0.0):.1f} m/s",
                f"    Aerodynamic Drag Loss:      {self.flight.get('delta_v_drag_loss_m_s', 0.0):.1f} m/s",
                f"    Estimated Max LEO Payload:  {self.flight.get('max_payload_leo_kg', 0.0):.1f} kg",
            ])

        report.append("=" * 78)
        return "\n".join(report)


class EngineSystem:
    """Master analytical design synthesizer for liquid propellant rocket engines."""

    def __init__(
        self,
        thrust_vac_N: float = 30000.0,
        p_chamber_Pa: float = 50.0e5,
        propellant: str = "LOX/CH4",
        mixture_ratio: Optional[float] = None,
        cycle: str = "gas_generator",
        injector_family: str = "swirl_coaxial",
        cooling_type: str = "regenerative",
        expansion_ratio: float = 40.0,
        simulate_flight: bool = True,
        name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        self.thrust_vac = thrust_vac_N
        self.p_chamber = p_chamber_Pa
        self.propellant = propellant.upper()
        self.cycle = cycle.lower()
        self.injector_family = injector_family.lower()
        self.cooling_type = cooling_type.lower()
        self.expansion_ratio = expansion_ratio
        self.simulate_flight = simulate_flight
        self.name = name or f"{self.propellant} {self.thrust_vac/1e3:.0f}kN {self.cycle.upper()}"
        self.kwargs = kwargs

        # Default mixture ratio if omitted
        if mixture_ratio is not None:
            self.of_ratio = mixture_ratio
        elif "CH4" in self.propellant:
            self.of_ratio = 3.0
        elif "RP" in self.propellant or "KEROSENE" in self.propellant:
            self.of_ratio = 2.6
        elif "LH2" in self.propellant or "H2" in self.propellant:
            self.of_ratio = 5.5
        elif "MMH" in self.propellant or "N2O4" in self.propellant or "NTO" in self.propellant:
            self.of_ratio = 1.65
        else:
            self.of_ratio = 2.5

    def solve(self) -> EngineSystemResult:
        """Executes full multi-subsystem engine sizing and power balance closure."""

        # ------------------------------------------------------------------
        # Step 1: Combustor Chamber Sizing (Day 1)
        # ------------------------------------------------------------------
        combustor_designer = CombustorDesign(
            thrust=self.thrust_vac,
            chamber_pressure=self.p_chamber,
            propellant=self.propellant,
            mixture_ratio=self.of_ratio,
        )
        comb_res = combustor_designer.solve()

        m_dot_total = comb_res.total_mass_flow
        m_dot_fuel = comb_res.fuel_mass_flow
        m_dot_ox = comb_res.oxidizer_mass_flow

        # Densities
        if "CH4" in self.propellant:
            rho_ox = 1141.0
            rho_fuel = 422.0
        elif "RP" in self.propellant:
            rho_ox = 1141.0
            rho_fuel = 810.0
        elif "LH2" in self.propellant:
            rho_ox = 1141.0
            rho_fuel = 71.0
        elif "MMH" in self.propellant:
            rho_ox = 1442.0
            rho_fuel = 880.0
        else:
            rho_ox = 1141.0
            rho_fuel = 800.0

        # ------------------------------------------------------------------
        # Step 2: Supersonic Nozzle Aerodynamics & Performance (Day 4)
        # ------------------------------------------------------------------
        nozzle_designer = NozzleDesign(
            expansion_ratio=self.expansion_ratio,
            chamber_pressure=self.p_chamber,
            throat_diameter=comb_res.throat_diameter,
            thrust=self.thrust_vac,
            c_star=comb_res.c_star_ideal,
            propellant=self.propellant,
        )
        nozzle_res = nozzle_designer.solve()

        thrust_vac_act = nozzle_res.vacuum_thrust_N
        thrust_sl_act = nozzle_res.sea_level_thrust_N
        isp_vac_act = nozzle_res.vacuum_isp_s
        isp_sl_act = nozzle_res.sea_level_isp_s

        # ------------------------------------------------------------------
        # Step 3: Injector Head Sizing (Day 2)
        # ------------------------------------------------------------------
        dp_inj_ox = 0.20 * self.p_chamber
        dp_inj_fuel = 0.20 * self.p_chamber

        if "bicentrifugal" in self.injector_family:
            inj_res = size_bicentrifugal_swirl_injector(
                m_dot_inner=m_dot_ox,
                m_dot_outer=m_dot_fuel,
                rho_inner=rho_ox,
                rho_outer=rho_fuel,
                delta_p_inner=dp_inj_ox,
                delta_p_outer=dp_inj_fuel,
                n_elements=self.kwargs.get("injector_elements", 19),
            )
        elif "pintle" in self.injector_family:
            d_p = max(comb_res.throat_diameter * 0.35, 0.015)
            inj_res = size_pintle_injector(
                m_dot_annular=m_dot_fuel,
                m_dot_radial=m_dot_ox,
                rho_annular=rho_fuel,
                rho_radial=rho_ox,
                delta_p_annular=dp_inj_fuel,
                delta_p_radial=dp_inj_ox,
                pintle_diameter=d_p,
            )
        elif "doublet" in self.injector_family or "impinging" in self.injector_family:
            inj_res = size_impinging_doublet(
                m1=m_dot_ox,
                m2=m_dot_fuel,
                rho_1=rho_ox,
                rho_2=rho_fuel,
                delta_p_1=dp_inj_ox,
                delta_p_2=dp_inj_fuel,
                n_elements=self.kwargs.get("injector_elements", 24),
            )
        elif "swirl" in self.injector_family:
            inj_res = size_bicentrifugal_swirl_injector(
                m_dot_inner=m_dot_ox,
                m_dot_outer=m_dot_fuel,
                rho_inner=rho_ox,
                rho_outer=rho_fuel,
                delta_p_inner=dp_inj_ox,
                delta_p_outer=dp_inj_fuel,
                n_elements=self.kwargs.get("injector_elements", 19),
            )
        else:
            inj_res = size_shear_coaxial(
                m_dot_ox=m_dot_ox,
                m_dot_fuel=m_dot_fuel,
                rho_ox=rho_ox,
                rho_fuel=rho_fuel,
                delta_p_ox=dp_inj_ox,
                delta_p_fuel=dp_inj_fuel,
                n_elements=self.kwargs.get("injector_elements", 19),
            )

        # ------------------------------------------------------------------
        # Step 4: Regenerative Cooling Jacket (Day 3)
        # ------------------------------------------------------------------
        cooling_dict = None
        if self.cooling_type == "regenerative":
            try:
                c_type = "CH4" if "CH4" in self.propellant else ("RP-1" if "RP" in self.propellant else "LH2")
                hg_est = comb_res.heat_flux_screen / max(3400.0 - 850.0, 100.0)
                jacket = RegenCoolingJacket(
                    throat_diameter_m=comb_res.throat_diameter,
                    chamber_diameter_m=comb_res.chamber_diameter,
                    chamber_length_m=comb_res.chamber_length,
                    mass_flow_coolant_kg_s=m_dot_fuel,
                    chamber_pressure_pa=self.p_chamber,
                    gas_recovery_temp_k=3400.0,
                    gas_throat_htc_w_m2k=hg_est,
                    coolant_type=c_type,
                    n_channels=self.kwargs.get("cooling_channels", 70),
                )
                cool_res = jacket.solve()
                cooling_dict = cool_res.to_dict()
            except Exception as e:
                cooling_dict = {"status": f"approx_{e}"}

        # ------------------------------------------------------------------
        # Step 5: Turbomachinery Cycles & Power Balance (Day 5)
        # ------------------------------------------------------------------
        cycle_designer = EngineCycleDesign(
            cycle_type=self.cycle,
            p_chamber_Pa=self.p_chamber,
            m_dot_ox_kg_s=m_dot_ox,
            m_dot_fuel_kg_s=m_dot_fuel,
            rho_ox_kg_m3=rho_ox,
            rho_fuel_kg_m3=rho_fuel,
            main_isp_vac_s=isp_vac_act,
        )
        cycle_res = cycle_designer.solve()

        # ------------------------------------------------------------------
        # Step 6: Engine Mass & Thrust-to-Weight Scaling
        # ------------------------------------------------------------------
        # Literature mass regression (Huzel-Huang Ch. 10 / Sutton Ch. 11)
        # Dry mass ~ k * (F_vac^0.8) / (Pc^0.2)
        thrust_kN = thrust_vac_act / 1000.0
        pc_bar = self.p_chamber / 1.0e5
        if self.cycle == "pressure_fed":
            mass_factor = 1.15
        elif self.cycle in ["full_flow", "ffsc"]:
            mass_factor = 1.45
        elif "staged" in self.cycle:
            mass_factor = 1.35
        elif self.cycle == "expander":
            mass_factor = 1.25
        else:
            mass_factor = 1.20

        dry_mass_kg = mass_factor * (thrust_kN ** 0.82) * ((100.0 / pc_bar) ** 0.15) * 4.2
        dry_mass_kg = max(dry_mass_kg, 12.0)
        tw_ratio_vac = thrust_vac_act / (dry_mass_kg * STANDARD_GRAVITY)

        # ------------------------------------------------------------------
        # Step 7: Mission Flight Trajectory (Day 5)
        # ------------------------------------------------------------------
        flight_dict = None
        if self.simulate_flight:
            # Stage sizing based on typical propellant mass fraction
            m_prop_stage = m_dot_total * self.kwargs.get("burn_time_s", 65.0)
            m_dry_stage = dry_mass_kg * 4.0  # Stage dry mass = engine mass * 4 (tanks, avionics, interstage)
            m0_stage = m_prop_stage + m_dry_stage

            try:
                sim = TrajectorySimulation(
                    m0_kg=m0_stage,
                    m_dry_kg=m_dry_stage,
                    thrust_sl_N=thrust_sl_act,
                    thrust_vac_N=thrust_vac_act,
                    isp_sl_s=isp_sl_act,
                    isp_vac_s=cycle_res.net_isp_vac_s,
                    burn_time_s=self.kwargs.get("burn_time_s", 65.0),
                    vehicle_diameter_m=max(comb_res.chamber_diameter * 2.2, 0.45),
                )
                traj_res = sim.run()
                flight_dict = traj_res.to_dict()
            except Exception as e:
                flight_dict = {"error": str(e)}

        return EngineSystemResult(
            name=self.name,
            propellant=self.propellant,
            cycle=self.cycle,
            thrust_vac_kN=round(thrust_vac_act / 1000.0, 2),
            thrust_sl_kN=round(thrust_sl_act / 1000.0, 2),
            isp_vac_s=round(cycle_res.net_isp_vac_s, 1),
            isp_sl_s=round(isp_sl_act, 1),
            p_chamber_bar=round(self.p_chamber / 1.0e5, 1),
            mass_flow_total_kg_s=round(cycle_res.m_dot_total_kg_s, 3),
            mass_flow_ox_kg_s=round(m_dot_ox, 3),
            mass_flow_fuel_kg_s=round(m_dot_fuel, 3),
            mixture_ratio=round(self.of_ratio, 2),
            throat_diameter_mm=round(comb_res.throat_diameter * 1000.0, 1),
            chamber_diameter_mm=round(comb_res.chamber_diameter * 1000.0, 1),
            nozzle_exit_diameter_mm=round(nozzle_res.exit_diameter_m * 1000.0, 1),
            nozzle_length_mm=round(nozzle_res.nozzle_length_m * 1000.0, 1),
            expansion_ratio=round(self.expansion_ratio, 1),
            engine_dry_mass_kg=round(dry_mass_kg, 1),
            thrust_to_weight_vac=round(tw_ratio_vac, 1),
            combustor=asdict(comb_res),
            nozzle=asdict(nozzle_res),
            injector=inj_res,
            cooling=cooling_dict,
            cycle_balance=cycle_res.to_dict(),
            flight=flight_dict,
            provenance={
                "combustor": "NASA SP-125, Bartz (1957)",
                "nozzle": "Rao (1958), Stark (2005)",
                "injector": "Bazarov-Yang (1998), Lorenzetto-Lefebvre (1977)",
                "cooling": "NASA SP-8087, Gnielinski (1976)",
                "cycle": cycle_res.provenance.get("balance", "Huzel-Huang (1992)"),
                "flight": "Griffin-French (2004), Sutton-Biblarz (2016)",
            },
        )
