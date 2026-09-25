"""
Example 08: End-to-End Engine Sizing & Launch Ascent Trajectory (Day 5).
======================================================================

Demonstrates the master EngineSystem facade connecting:
- Combustor Chamber (Day 1)
- Bi-Centrifugal Swirl Injector (Day 2)
- Regenerative Cooling Channels (Day 3)
- Supersonic Rao 80% Bell Nozzle (Day 4)
- Gas Generator Turbopump Power Balance (Day 5)
- 2D Powered Ascent Gravity Turn Flight Mechanics to Orbit (Day 5)

Literature References:
- NASA SP-125, Bartz (1957), Huzel & Huang (1992), Rao (1958), Griffin & French (2004).
"""

from kryptonis.propulsion_equations.system import EngineSystem

def main():
    print("=" * 80)
    print("  NAVRONIS DAY 5: MASTER ENGINE SYSTEM & MISSION ASCENT SIMULATION")
    print("=" * 80)

    # Design a 50 kN Vacuum LOX/CH4 Booster Engine
    engine = EngineSystem(
        thrust_vac_N=50000.0,           # 50 kN
        p_chamber_Pa=60.0e5,            # 60 bar
        propellant="LOX/CH4",
        cycle="gas_generator",
        injector_family="bicentrifugal_swirl",
        cooling_type="regenerative",
        expansion_ratio=45.0,
        simulate_flight=True,
        burn_time_s=75.0,
    )

    result = engine.solve()

    # Print the authoritative ASCII engineering datasheet
    print(result.summary_report())

    print("\n[Trajectory Traversal Highlights]")
    if result.flight and "history" in result.flight:
        hist = result.flight["history"]
        times = hist["time_s"]
        alts = hist["altitude_km"]
        vels = hist["velocity_m_s"]
        machs = hist["mach"]
        q_kpas = hist["dynamic_pressure_kPa"]
        
        sample_indices = [0, len(times)//4, len(times)//2, 3*len(times)//4, -1]
        print(f"{'Time (s)':<10} | {'Alt (km)':<10} | {'Velocity (m/s)':<15} | {'Mach':<8} | {'Dynamic Pressure (kPa)'}")
        print("-" * 75)
        for idx in sample_indices:
            print(f"{times[idx]:<10.1f} | {alts[idx]:<10.2f} | {vels[idx]:<15.1f} | {machs[idx]:<8.2f} | {q_kpas[idx]:.2f} kPa")

    print("\n" + "=" * 80)
    print("  ENGINE SIZING & ASCENT TRAJECTORY CLOSURE SUCCESSFUL.")
    print("=" * 80)

if __name__ == "__main__":
    main()
