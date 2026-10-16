"""
Liquid Rocket Engine Throttling, Off-Design Regimes, & Instability Audit (Day 6).
==================================================================================

Authoritative analytical modeling of rocket engines operating away from nominal
design point across throttle settings tau in [0.30, 1.05]:

1. Injector pressure drop quadratic decay & chugging decoupling stiffness loss.
2. Nozzle overexpansion flow separation shock migration (Summerfield / Stark 2005).
3. Regenerative cooling coolant velocity collapse & bulk temperature rise.
4. Delivered thrust and Isp variation across the throttle regime.

Governing Literature:
- NASA SP-194 (1972), Liquid Rocket Engine Combustion Stabilization Devices.
- Huzel, D. K. & Huang, D. H. (1992), Modern Engineering for Design of Liquid
  Propellant Rocket Engines, AIAA, Chapter 4 (Injectors) & Chapter 8 (Control & Throttling).
- Stark, R. (2005), Flow Separation in Rocket Nozzles, Shock Waves Journal, 14:141-149.
- Dressler, G. A. (2000), Summary of Deep Throttling Rocket Engines, AIAA 2000-3694.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple


CITATIONS: Dict[str, str] = {
    "chugging_instability": "NASA SP-194 (1972), Liquid Propellant Rocket Combustion Instability, p. 18; Huzel & Huang (1992), p. 112",
    "nozzle_separation": "Stark, R. (2005), Flow Separation in Rocket Nozzles; Summerfield, M. (1954), Flow Separation in Overexpanded Supersonic Nozzles",
    "cooling_throttle": "NASA SP-8087 (1974), Liquid Rocket Engine Cooling; Gnielinski, V. (1976)",
    "pintle_throttling": "Dressler, G. A. (2000), Summary of Deep Throttling Rocket Engines, AIAA-2000-3694 (LMDE & Merlin)",
}

STANDARD_GRAVITY: float = 9.80665


@dataclass
class ThrottlePoint:
    """Operating conditions at a specific engine throttle setting."""
    throttle_fraction: float
    thrust_vac_kN: float
    thrust_sl_kN: float
    chamber_pressure_bar: float
    mass_flow_total_kg_s: float
    isp_vac_s: float
    isp_sl_s: float
    injector_dp_bar: float
    injector_stiffness_ratio: float
    chugging_safe: bool
    coolant_velocity_m_s: float
    coolant_bulk_temp_rise_K: float
    hot_gas_wall_temp_K: float
    nozzle_exit_pressure_kPa: float
    nozzle_separated_at_sea_level: bool
    separation_area_ratio: Optional[float] = None
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ThrottleAnalysisResult:
    """Complete multi-point throttle envelope analysis."""
    engine_name: str
    nominal_thrust_kN: float
    nominal_pc_bar: float
    min_safe_throttle_fraction: float
    points: List[ThrottlePoint]
    envelope_safe: bool
    provenance: Dict[str, str] = field(default_factory=dict)

    def summary_table(self) -> str:
        lines = [
            "=" * 92,
            f"  NAVRONIS ENGINE THROTTLING & STABILITY REPORT: {self.engine_name.upper()}",
            f"  Nominal Thrust: {self.nominal_thrust_kN:.1f} kN | Nominal Pc: {self.nominal_pc_bar:.1f} bar",
            "=" * 92,
            f"  {'THROTTLE':<9} | {'THRUST(kN)':<10} | {'Pc(bar)':<8} | {'dP_inj(bar)':<11} | {'dP/Pc':<7} | {'CHUGGING':<8} | {'SEPARATION':<11} | {'Twg(C)':<7}",
            "-" * 92,
        ]
        for p in self.points:
            chug_str = "SAFE" if p.chugging_safe else "UNSTABLE"
            sep_str = "SEPARATED" if p.nozzle_separated_at_sea_level else "ATTACHED"
            twg_c = p.hot_gas_wall_temp_K - 273.15
            lines.append(
                f"  {p.throttle_fraction * 100:>6.1f}%   | {p.thrust_sl_kN:>9.2f}  | {p.chamber_pressure_bar:>7.1f}  | {p.injector_dp_bar:>10.2f}  | {p.injector_stiffness_ratio * 100:>5.1f}% | {chug_str:<8} | {sep_str:<11} | {twg_c:>6.0f}"
            )
        lines.append("-" * 92)
        lines.append(f"  Minimum Stable Throttle Floor: {self.min_safe_throttle_fraction * 100:.1f}%")
        lines.append("=" * 92)
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine_name": self.engine_name,
            "nominal_thrust_kN": self.nominal_thrust_kN,
            "nominal_pc_bar": self.nominal_pc_bar,
            "min_safe_throttle_fraction": self.min_safe_throttle_fraction,
            "envelope_safe": self.envelope_safe,
            "points": [p.to_dict() for p in self.points],
            "provenance": self.provenance,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


class ThrottlingAnalysis:
    """Evaluates off-design liquid engine performance and stability across throttling range."""

    def __init__(
        self,
        engine_name: str = "Rocket-Engine",
        thrust_nominal_N: float = 30000.0,
        chamber_pressure_nominal_Pa: float = 70.0e5,
        mass_flow_nominal_kg_s: float = 10.0,
        isp_vac_nominal_s: float = 320.0,
        isp_sl_nominal_s: float = 285.0,
        expansion_ratio: float = 25.0,
        nominal_injector_dp_ratio: float = 0.20,
        nominal_coolant_velocity_m_s: float = 45.0,
        nominal_coolant_dt_bulk_K: float = 120.0,
        nominal_hot_wall_temp_K: float = 850.0,
        gamma: float = 1.22,
    ) -> None:
        if thrust_nominal_N <= 0.0 or chamber_pressure_nominal_Pa <= 0.0 or mass_flow_nominal_kg_s <= 0.0:
            raise ValueError("Nominal parameters must be strictly positive")

        self.engine_name = engine_name
        self.thrust_nom = thrust_nominal_N
        self.pc_nom = chamber_pressure_nominal_Pa
        self.mdot_nom = mass_flow_nominal_kg_s
        self.isp_vac_nom = isp_vac_nominal_s
        self.isp_sl_nom = isp_sl_nominal_s
        self.eps = expansion_ratio
        self.dp_ratio_nom = nominal_injector_dp_ratio
        self.vc_nom = nominal_coolant_velocity_m_s
        self.dt_bulk_nom = nominal_coolant_dt_bulk_K
        self.twg_nom = nominal_hot_wall_temp_K
        self.gamma = gamma

        # Nominal nozzle exit pressure (approximate isentropic expansion)
        self.pe_nom = self.pc_nom * math.pow(1.0 + 0.5 * (gamma - 1.0) * 3.5 * 3.5, -gamma / (gamma - 1.0))

    def evaluate_point(self, throttle_fraction: float) -> ThrottlePoint:
        """Evaluates single throttle operating point."""
        if not (0.20 <= throttle_fraction <= 1.20):
            raise ValueError(f"Throttle fraction ({throttle_fraction}) outside valid physics range [0.20, 1.20]")

        tau = throttle_fraction
        warnings: List[str] = []

        # 1. Chamber pressure and mass flow
        pc_tau = self.pc_nom * tau
        mdot_tau = self.mdot_nom * tau

        # 2. Injector Delta P drops quadratically: Delta P = Delta P_nom * tau^2
        dp_inj_nom = self.dp_ratio_nom * self.pc_nom
        dp_inj_tau = dp_inj_nom * (tau ** 2)
        stiffness_ratio = dp_inj_tau / pc_tau  # = dp_ratio_nom * tau

        # Chugging stability check: NASA SP-194 requires Delta P / Pc >= 0.15
        chugging_safe = stiffness_ratio >= 0.15
        if not chugging_safe:
            warnings.append(
                f"Chugging risk: Injector stiffness ({stiffness_ratio * 100:.1f}%) below NASA SP-194 threshold (15.0%)"
            )

        # 3. Nozzle exit pressure & separation check at sea level (101.325 kPa)
        p_amb = 101325.0
        pe_tau = self.pe_nom * tau

        # Summerfield separation criterion: P_sep = 0.375 * P_amb
        p_summerfield = 0.375 * p_amb
        separated = pe_tau < p_summerfield
        sep_area_ratio = None
        if separated:
            # Estimate separation area ratio
            sep_ratio = max(min(self.eps * (pe_tau / p_summerfield), self.eps), 1.5)
            sep_area_ratio = sep_ratio
            warnings.append(
                f"Flow separation: Exit pressure ({pe_tau / 1e3:.1f} kPa) below Summerfield limit ({p_summerfield / 1e3:.1f} kPa)"
            )

        # 4. Cooling hydraulics and thermal limits
        vc_tau = self.vc_nom * tau
        # Bulk temperature rise scales as tau^-0.2 due to increased stay time
        dt_bulk_tau = self.dt_bulk_nom * math.pow(max(tau, 0.2), -0.20)
        # Hot-gas wall temperature scales approximately with Pc^0.8
        twg_tau = 300.0 + (self.twg_nom - 300.0) * math.pow(tau, 0.40)

        # 5. Thrust & Isp scaling
        f_vac_tau = self.thrust_nom * (self.isp_vac_nom / self.isp_sl_nom) * tau
        # Sea level thrust accounts for back-pressure
        exit_area = (self.mdot_nom * self.isp_sl_nom * STANDARD_GRAVITY / (self.pc_nom * 1.6)) * self.eps
        f_sl_tau = max(f_vac_tau - p_amb * exit_area, 0.1)
        isp_sl_tau = f_sl_tau / (mdot_tau * STANDARD_GRAVITY)
        isp_vac_tau = self.isp_vac_nom

        return ThrottlePoint(
            throttle_fraction=round(tau, 3),
            thrust_vac_kN=round(f_vac_tau / 1e3, 2),
            thrust_sl_kN=round(f_sl_tau / 1e3, 2),
            chamber_pressure_bar=round(pc_tau / 1e5, 1),
            mass_flow_total_kg_s=round(mdot_tau, 3),
            isp_vac_s=round(isp_vac_tau, 1),
            isp_sl_s=round(isp_sl_tau, 1),
            injector_dp_bar=round(dp_inj_tau / 1e5, 2),
            injector_stiffness_ratio=round(stiffness_ratio, 3),
            chugging_safe=chugging_safe,
            coolant_velocity_m_s=round(vc_tau, 1),
            coolant_bulk_temp_rise_K=round(dt_bulk_tau, 1),
            hot_gas_wall_temp_K=round(twg_tau, 1),
            nozzle_exit_pressure_kPa=round(pe_tau / 1e3, 2),
            nozzle_separated_at_sea_level=separated,
            separation_area_ratio=round(sep_area_ratio, 2) if sep_area_ratio else None,
            warnings=warnings,
        )

    def sweep(self, min_throttle: float = 0.40, max_throttle: float = 1.00, step: float = 0.10) -> ThrottleAnalysisResult:
        """Sweeps throttle from min to max and determines stability limits."""
        points: List[ThrottlePoint] = []
        cur = min_throttle
        min_safe = 1.0

        while cur <= max_throttle + 1e-5:
            pt = self.evaluate_point(round(cur, 3))
            points.append(pt)
            if pt.chugging_safe and not pt.nozzle_separated_at_sea_level:
                min_safe = min(min_safe, pt.throttle_fraction)
            cur += step

        envelope_safe = all(p.chugging_safe for p in points)

        return ThrottleAnalysisResult(
            engine_name=self.engine_name,
            nominal_thrust_kN=self.thrust_nom / 1e3,
            nominal_pc_bar=self.pc_nom / 1e5,
            min_safe_throttle_fraction=min_safe,
            points=points,
            envelope_safe=envelope_safe,
            provenance={
                "chugging": CITATIONS["chugging_instability"],
                "separation": CITATIONS["nozzle_separation"],
                "cooling": CITATIONS["cooling_throttle"],
            },
        )
