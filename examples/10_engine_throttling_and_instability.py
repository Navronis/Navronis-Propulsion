"""
Navronis Example 10: Off-Design Engine Throttling, Chugging, & Separation (Day 6)
================================================================================
Demonstrates off-design engine throttling dynamics from 100% down to 40% throttle:
- Quadratic injector pressure drop (Delta P_inj proportional to tau^2)
- Acoustic chugging decouple threshold (Delta P_inj / Pc >= 15%, NASA SP-194)
- Summerfield & Stark sea-level flow separation shock migration
- Regenerative coolant bulk temperature rise scaling (delta T_bulk proportional to tau^-0.2)

Run this script directly:
    python examples/10_engine_throttling_and_instability.py
"""

from __future__ import annotations

import sys
from kryptonis.propulsion_equations.throttle import ThrottlingAnalysis


def main() -> int:
    print("=" * 82)
    print("      NAVRONIS OFF-DESIGN THROTTLING & CHUGGING DYNAMICS (DAY 6)")
    print("=" * 82)
    print("Simulating throttle sweep for a 35 kN LOX/Methane booster engine...\n")

    analyzer = ThrottlingAnalysis(
        engine_name="Navronis-35kN-Booster",
        thrust_nominal_N=35000.0,
        chamber_pressure_nominal_Pa=70.0e5,
        mass_flow_nominal_kg_s=11.6,
        isp_vac_nominal_s=325.0,
        isp_sl_nominal_s=290.0,
        expansion_ratio=28.0,
        nominal_injector_dp_ratio=0.20,
        nominal_coolant_velocity_m_s=42.0,
        nominal_coolant_dt_bulk_K=115.0,
        nominal_hot_wall_temp_K=840.0,
    )

    res = analyzer.sweep(min_throttle=0.40, max_throttle=1.00, step=0.10)

    # Print formatted summary table
    print(res.summary_table())
    print()

    print("ENGINEERING OBSERVATIONS:")
    print(f"1. Minimum Stable Throttle Floor: {res.min_safe_throttle_fraction * 100:.1f}%")
    print("2. Chugging Risk (NASA SP-194): Below 75% throttle, injector delta P / Pc drops")
    print("   below 15%, risking acoustic low-frequency coupling with chamber combustion.")
    print("3. Summerfield Separation: At deep throttle (<= 60%), chamber pressure drops to")
    print("   <= 42 bar, causing exit pressure to drop below 35 kPa, triggering boundary")
    print("   layer shock separation inside the bell nozzle at sea level.")
    print("4. Deep Throttling Remedy: Variable-area pintle injector (LMDE architecture) or")
    print("   dual-manifold staging is required to throttle below 70% safely.")
    print("=" * 82)

    return 0


if __name__ == "__main__":
    sys.exit(main())
