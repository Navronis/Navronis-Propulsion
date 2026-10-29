"""
Example 12: Multidisciplinary Design Optimization (MDO) & Trade Studies (Day 8).
================================================================================

Demonstrates:
  1. Constrained SLSQP Optimization on the Dependency DAG
  2. Non-dominated Pareto Trade-Off Frontier (Isp vs Engine Mass/Volume)
  3. Sobol Global Variance Sensitivity Analysis (ranking drivers)
  4. Monte Carlo Manufacturing Tolerance Propagation (tolerance stack-up & yield)
"""

import sys
from kryptonis.propulsion_equations.optimization import (
    Constraint,
    ConstraintType,
    DesignVariable,
    Objective,
    ObjectiveType,
    OptimizationProblem,
    SLSQPOptimizer,
    ParetoFrontierGenerator,
    SobolSensitivityAnalyzer,
    DistributionType,
    MonteCarloToleranceSimulator,
    ToleranceParameter,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    print("=" * 80)
    print("      NAVRONIS DAY 8: MULTIDISCIPLINARY DESIGN OPTIMIZATION (MDO)")
    print("=" * 80)

    # --------------------------------------------------------------------------
    # 1. Constrained SLSQP Optimization
    # --------------------------------------------------------------------------
    print("\n[PART 1: Constrained SLSQP Optimization]")
    print("Goal: Minimize Engine Envelope Volume while strictly satisfying:")
    print("  - Hot-gas wall temperature Twg <= 950.0 K (CuCrZr limit)")
    print("  - Coolant jacket hydraulic drop dP <= 20.0 bar")
    print("  - Variables: Chamber Pressure Pc in [50, 120] bar, Expansion Ratio in [15, 45]")

    problem = OptimizationProblem(
        name="Thrust Chamber Volume Minimization",
        variables=[
            DesignVariable("chamber_pressure", 50e5, 120e5, 70e5, unit="Pa", description="Chamber Pressure Pc"),
            DesignVariable("expansion_ratio", 15.0, 45.0, 25.0, unit="-", description="Expansion Ratio eps"),
        ],
        objective=Objective("Min Volume", "cad_solid_volume", ObjectiveType.MINIMIZE),
        constraints=[
            Constraint("Max Wall Temp", "hot_gas_wall_temp", ConstraintType.LESS_THAN_OR_EQUAL, 950.0, unit="K"),
            Constraint("Max Coolant Drop", "cooling_pressure_drop", ConstraintType.LESS_THAN_OR_EQUAL, 20e5, unit="Pa"),
        ],
    )

    optimizer = SLSQPOptimizer(problem, max_iter=30)
    res = optimizer.solve()

    print(f"\nOptimization Result: {'SUCCESS' if res.success else 'FAILED'}")
    print(f"Status Message: {res.status_message}")
    print(f"Optimal Pc:     {res.optimal_variables['chamber_pressure']/1e5:.2f} bar")
    print(f"Optimal eps:    {res.optimal_variables['expansion_ratio']:.2f}")
    print(f"Min Envelope V: {res.optimal_objective_value*1000.0:.2f} Liters")
    print(f"Hot Wall Temp:  {res.optimal_outputs['hot_gas_wall_temp']:.1f} K (Margin: {res.constraint_margins['Max Wall Temp']*100:.1f}%)")
    print(f"Coolant Drop:   {res.optimal_outputs['cooling_pressure_drop']/1e5:.2f} bar (Margin: {res.constraint_margins['Max Coolant Drop']*100:.1f}%)")
    print(f"Iterations:     {res.iterations} (Time: {res.execution_time_ms:.2f} ms)")
    print(f"Stamped Rev ID: {res.revision_id}")

    # --------------------------------------------------------------------------
    # 2. Pareto Frontier: Vacuum Isp vs Solid Volume
    # --------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("[PART 2: Multi-Objective Pareto Frontier]")
    print("Trading off: Minimum Volume vs Maximum Vacuum Specific Impulse (Isp)")

    secondary = Objective("Max Isp", "isp_vacuum", ObjectiveType.MAXIMIZE)
    pareto_gen = ParetoFrontierGenerator(problem, secondary_objective=secondary, num_points=7)
    pareto_pts = pareto_gen.generate()

    print(f"\nGenerated {len(pareto_pts)} Non-Dominated Pareto Optimal Engine Designs:")
    print(f"{'Pt':<4} | {'Volume (L)':<12} | {'Isp Vac (s)':<12} | {'Pc (bar)':<10} | {'eps':<8} | {'Feasible'}")
    print("-" * 65)
    for p in pareto_pts:
        vol_l = p["obj1_value"] * 1000.0
        isp = p["obj2_value"]
        pc_bar = p["variables"]["chamber_pressure"] / 1e5
        eps = p["variables"]["expansion_ratio"]
        feas = "YES" if p["feasible"] else "WARN"
        print(f"#{p['point_index']:<3} | {vol_l:<12.2f} | {isp:<12.1f} | {pc_bar:<10.2f} | {eps:<8.2f} | {feas}")

    # --------------------------------------------------------------------------
    # 3. Sobol Global Variance Sensitivity Analysis
    # --------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("[PART 3: Sobol Global Sensitivity Analysis]")
    print("Evaluating which inputs drive variance in Peak Heat Flux (q_peak):")

    sobol_problem = OptimizationProblem(
        name="Heat Flux Sensitivity",
        variables=[
            DesignVariable("chamber_pressure", 60e5, 120e5, 80e5, unit="Pa"),
            DesignVariable("expansion_ratio", 15.0, 45.0, 30.0, unit="-"),
            DesignVariable("wall_thickness", 0.0012, 0.0025, 0.0015, unit="m"),
        ],
        objective=Objective("Heat Flux", "peak_heat_flux", ObjectiveType.MINIMIZE),
    )

    analyzer = SobolSensitivityAnalyzer(sobol_problem, output_key="peak_heat_flux", n_samples=48)
    sens_res = analyzer.analyze()

    print(f"\nSobol Indices Decomposition ({sens_res.sample_size} Evaluations in {sens_res.computation_time_ms:.2f} ms):")
    for rank, (var_name, s_tot) in enumerate(sens_res.ranked_variables, 1):
        s_first = sens_res.first_order_indices[var_name]
        print(f"  Rank #{rank}: {var_name:<20} Total S_Ti = {s_tot:.3f} | First-order S_i = {s_first:.3f}")

    # --------------------------------------------------------------------------
    # 4. Monte Carlo Manufacturing Tolerance Propagation
    # --------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("[PART 4: Monte Carlo Manufacturing Tolerance & Statistical Yield]")
    print("Simulating real manufacturing tolerances across 200 virtual engines:")
    print("  - Chamber Pressure dispersion: +/- 2.5 bar std dev")
    print("  - Liner wall thickness tolerance: +/- 0.08 mm uniform")

    tolerances = [
        ToleranceParameter("chamber_pressure", 70e5, DistributionType.NORMAL, 2.5e5, "Pa", "Regulator Dispersion"),
        ToleranceParameter("wall_thickness", 0.0015, DistributionType.UNIFORM, 0.00008, "m", "CNC Milling Tolerance"),
    ]
    constraints = [
        Constraint("Thermal Limit", "hot_gas_wall_temp", ConstraintType.LESS_THAN_OR_EQUAL, 980.0, unit="K"),
        Constraint("Coolant Pressure Cap", "cooling_pressure_drop", ConstraintType.LESS_THAN_OR_EQUAL, 22e5, unit="Pa"),
    ]

    mc_sim = MonteCarloToleranceSimulator(tolerances, constraints=constraints)
    mc_res = mc_sim.run(num_samples=200, random_seed=42)

    stats_twg = mc_res.statistics["hot_gas_wall_temp"]
    stats_dp = mc_res.statistics["cooling_pressure_drop"]

    print(f"\nMonte Carlo Results ({mc_res.num_samples} Engines Evaluated in {mc_res.execution_time_ms:.2f} ms):")
    print(f"Overall Manufacturing Yield: {mc_res.overall_yield_percentage:.1f}%")
    print(f"Defect / Violation Risk:    {100.0 - mc_res.overall_yield_percentage:.1f}%")
    print(f"\nHot Wall Temperature Twg Statistics:")
    print(f"  Mean:   {stats_twg.mean:.1f} K | Std Dev: {stats_twg.std_dev:.2f} K")
    print(f"  Min:    {stats_twg.min_val:.1f} K | Median:  {stats_twg.median:.1f} K | Max: {stats_twg.max_val:.1f} K")
    print(f"  95th Percentile: {stats_twg.p95:.1f} K | 99th Percentile: {stats_twg.p99:.1f} K")
    print(f"\nCoolant Pressure Drop dP Statistics:")
    print(f"  Mean:   {stats_dp.mean/1e5:.2f} bar | 95th Percentile: {stats_dp.p95/1e5:.2f} bar")

    print("\n" + "=" * 80)
    print("              DAY 8 MDO & STATISTICAL ANALYSIS VERIFIED")
    print("=" * 80)


if __name__ == "__main__":
    main()
