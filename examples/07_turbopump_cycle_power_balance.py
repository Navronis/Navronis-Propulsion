"""
Example 07: Liquid Rocket Turbopump Power Balance & Engine Cycles (Day 5).
========================================================================

Demonstrates first-principles sizing and comparison across the canonical rocket engine cycles:
1. Gas Generator Cycle (Merlin 1D, F-1, Vulcain 2)
2. Closed Expander Cycle (RL10, Vinci)
3. Oxidizer-Rich Staged Combustion Cycle (RD-180, RD-170, NK-33)
4. Full-Flow Staged Combustion Cycle (SpaceX Raptor, RD-270)
5. Pressure-Fed System (Apollo LMDE, SuperDraco, Kestrel)

Literature References:
- Huzel & Huang (1992), Modern Engineering for Design of Liquid Rocket Engines, Ch. 2 & 6.
- Sutton & Biblarz (2016), Rocket Propulsion Elements, 9th Ed., Ch. 6 & 10.
"""

from kryptonis.propulsion_equations.cycle import (
    EngineCycleDesign,
    pump_head,
    pump_power,
    pump_specific_speed,
    pump_suction_specific_speed,
    pump_npsh_required,
)

def main():
    print("=" * 80)
    print("  NAVRONIS DAY 5: TURBOMACHINERY & ENGINE CYCLES POWER BALANCE")
    print("=" * 80)

    # 1. 30 kN Methalox (LOX/CH4) at 70 bar Chamber Pressure
    pc_pa = 70.0e5
    m_ox = 7.50   # kg/s LOX (rho = 1141 kg/m3)
    m_f = 2.50    # kg/s CH4 (rho = 422 kg/m3)
    main_isp_vac = 328.0

    print("\n[Baseline Operating Condition]")
    print(f"  Chamber Pressure: {pc_pa/1e5:.1f} bar | LOX Flow: {m_ox:.2f} kg/s | Fuel Flow: {m_f:.2f} kg/s")

    # Cycle Comparison Matrix
    cycles = [
        ("gas_generator", "Open Gas Generator (Merlin / F-1 style)"),
        ("expander", "Closed Expander Cycle (RL10 style)"),
        ("staged_combustion_ox", "Oxidizer-Rich Staged Combustion (RD-180 style)"),
        ("full_flow_staged", "Full-Flow Staged Combustion (SpaceX Raptor style)"),
        ("pressure_fed", "Pressure-Fed System (Apollo LMDE style)"),
    ]

    print("\n" + "-" * 80)
    print(f"{'Cycle Architecture':<36} | {'Pump Pwr (kW)':<13} | {'Net Isp (s)':<11} | {'Feasible?'}")
    print("-" * 80)

    for ckey, cdesc in cycles:
        des = EngineCycleDesign(
            cycle_type=ckey,
            p_chamber_Pa=pc_pa,
            m_dot_ox_kg_s=m_ox,
            m_dot_fuel_kg_s=m_f,
            rho_ox_kg_m3=1141.0,
            rho_fuel_kg_m3=422.0,
            main_isp_vac_s=main_isp_vac,
        )
        res = des.solve()
        pwr_str = f"{res.total_pump_power_kW:.1f}" if res.total_pump_power_kW > 0 else "N/A (Tanks)"
        feas_str = "YES (Closed)" if res.cycle_feasible else "PINCH LIMIT"
        print(f"{cdesc:<36} | {pwr_str:<13} | {res.net_isp_vac_s:11.1f} | {feas_str}")

    # 2. Detailed Turbopump Hydraulic Analysis
    print("\n" + "=" * 80)
    print("  TURBOPUMP HYDRAULICS & CAVITATION SUCTION SPECIFIC SPEED (Nss)")
    print("=" * 80)
    rpm = 36000.0  # High-speed turbopump shaft
    flow_ox_m3_s = m_ox / 1141.0
    flow_fuel_m3_s = m_f / 422.0
    head_ox = pump_head(pc_pa * 1.35, 1141.0)
    head_fuel = pump_head(pc_pa * 1.45, 422.0)

    ns_ox = pump_specific_speed(rpm, flow_ox_m3_s, head_ox)
    ns_fuel = pump_specific_speed(rpm, flow_fuel_m3_s, head_fuel)

    npsh_r_ox = pump_npsh_required(rpm, flow_ox_m3_s, target_nss=25000.0)
    npsh_r_fuel = pump_npsh_required(rpm, flow_fuel_m3_s, target_nss=25000.0)

    print(f"  LOX Pump:  Head = {head_ox:.1f} m  | Ns (US) = {ns_ox['Ns_US']:.0f} ({ns_ox['impeller_type']}) | NPSH_R = {npsh_r_ox:.2f} m")
    print(f"  Fuel Pump: Head = {head_fuel:.1f} m | Ns (US) = {ns_fuel['Ns_US']:.0f} ({ns_fuel['impeller_type']}) | NPSH_R = {npsh_r_fuel:.2f} m")
    print("=" * 80)

if __name__ == "__main__":
    main()
