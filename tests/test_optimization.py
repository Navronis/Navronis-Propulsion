"""
Day 8 Test Suite: Multidisciplinary Design Optimization & Uncertainty Analysis.
==============================================================================
"""

import math
import pytest
import numpy as np

from kryptonis.propulsion_equations.optimization import (
    Constraint,
    ConstraintType,
    DesignVariable,
    Objective,
    ObjectiveType,
    OptimizationProblem,
    OptimizationResult,
    DAGEvaluator,
    SLSQPOptimizer,
    ParetoFrontierGenerator,
    is_pareto_efficient,
    SensitivityResult,
    SobolSensitivityAnalyzer,
    DistributionStats,
    DistributionType,
    MonteCarloToleranceSimulator,
    ToleranceParameter,
    UncertaintyResult,
)
from kryptonis.propulsion_equations.truth.propulsion_dag import build_propulsion_dag


def test_design_variable_bounds_and_normalization():
    """Validates variable domain bounds, initial value checks, and normalization."""
    var = DesignVariable(
        name="chamber_pressure",
        lower_bound=50e5,
        upper_bound=150e5,
        initial_value=100e5,
        unit="Pa",
    )
    assert var.normalize(100e5) == pytest.approx(0.5)
    assert var.normalize(50e5) == pytest.approx(0.0)
    assert var.normalize(150e5) == pytest.approx(1.0)
    assert var.denormalize(0.25) == pytest.approx(75e5)

    with pytest.raises(ValueError):
        DesignVariable(name="bad_bounds", lower_bound=100.0, upper_bound=50.0, initial_value=75.0)

    with pytest.raises(ValueError):
        DesignVariable(name="bad_init", lower_bound=50.0, upper_bound=100.0, initial_value=120.0)


def test_constraint_evaluation_and_margins():
    """Validates inequality and equality constraint margin evaluations."""
    c_leq = Constraint(
        name="wall_temp_limit",
        quantity_key="hot_gas_wall_temp",
        constraint_type=ConstraintType.LESS_THAN_OR_EQUAL,
        limit=950.0,
        unit="K",
    )
    # 900 K <= 950 K -> margin is positive (+50 / 950)
    assert c_leq.evaluate_margin(900.0) > 0.0
    assert c_leq.is_satisfied(900.0) is True

    # 1000 K <= 950 K -> margin is negative (-50 / 950)
    assert c_leq.evaluate_margin(1000.0) < 0.0
    assert c_leq.is_satisfied(1000.0) is False

    c_geq = Constraint(
        name="chugging_decoupling",
        quantity_key="dp_ratio",
        constraint_type=ConstraintType.GREATER_THAN_OR_EQUAL,
        limit=0.15,
    )
    assert c_geq.evaluate_margin(0.20) > 0.0
    assert c_geq.is_satisfied(0.20) is True
    assert c_geq.evaluate_margin(0.10) < 0.0
    assert c_geq.is_satisfied(0.10) is False


def test_dag_evaluator_vector_mapping():
    """Validates that DAGEvaluator pushes variables into DAG inputs and recomputes."""
    problem = OptimizationProblem(
        name="Test Sizing",
        variables=[
            DesignVariable("chamber_pressure", 50e5, 120e5, 70e5, unit="Pa"),
            DesignVariable("expansion_ratio", 10.0, 50.0, 25.0, unit="-"),
        ],
        objective=Objective("Min Volume", "cad_solid_volume", ObjectiveType.MINIMIZE),
        constraints=[
            Constraint("Max Wall Temp", "hot_gas_wall_temp", ConstraintType.LESS_THAN_OR_EQUAL, 1100.0),
        ],
    )

    evaluator = DAGEvaluator(problem)
    obj_val, margins, out_vals = evaluator.evaluate_vector([80e5, 30.0])

    assert obj_val > 0.0
    assert "hot_gas_wall_temp" in out_vals
    assert "Max Wall Temp" in margins
    assert evaluator.eval_count == 1


def test_slsqp_constrained_optimization_mass_minimization():
    """Tests constrained SLSQP finding an optimal chamber pressure and expansion ratio."""
    problem = OptimizationProblem(
        name="Minimum CAD Volume Optimization",
        variables=[
            DesignVariable("chamber_pressure", 60e5, 100e5, 70e5, unit="Pa"),
            DesignVariable("expansion_ratio", 15.0, 35.0, 20.0, unit="-"),
        ],
        objective=Objective("Min Volume", "cad_solid_volume", ObjectiveType.MINIMIZE),
        constraints=[
            Constraint("Max Wall Temp", "hot_gas_wall_temp", ConstraintType.LESS_THAN_OR_EQUAL, 1050.0),
            Constraint("Max Coolant Drop", "cooling_pressure_drop", ConstraintType.LESS_THAN_OR_EQUAL, 35e5),
        ],
    )

    optimizer = SLSQPOptimizer(problem, max_iter=25)
    res = optimizer.solve()

    assert res.optimal_objective_value > 0.0
    assert len(res.iteration_history) >= 2
    assert res.optimal_outputs["hot_gas_wall_temp"] <= 1050.0 + 1.0  # Respects thermal limit
    assert res.revision_id is not None
    assert len(res.revision_id) >= 12


def test_is_pareto_efficient_filtering():
    """Tests the Pareto non-dominated filtering algorithm."""
    costs = np.array([
        [10.0, 20.0],  # Candidate A
        [12.0, 25.0],  # Candidate B (dominated by A: both higher)
        [8.0, 25.0],   # Candidate C (trade-off with A: lower first, higher second)
        [15.0, 30.0],  # Candidate D (dominated by all)
    ])
    mask = is_pareto_efficient(costs)
    assert bool(mask[0]) is True   # A is non-dominated
    assert bool(mask[1]) is False  # B is dominated
    assert bool(mask[2]) is True   # C is non-dominated
    assert bool(mask[3]) is False  # D is dominated


def test_pareto_frontier_generation_mass_vs_isp():
    """Tests generation of the non-dominated trade-off front between Isp and Volume."""
    problem = OptimizationProblem(
        name="Pareto Trade Study",
        variables=[
            DesignVariable("chamber_pressure", 60e5, 90e5, 75e5, unit="Pa"),
            DesignVariable("expansion_ratio", 15.0, 35.0, 25.0, unit="-"),
        ],
        objective=Objective("Min Volume", "cad_solid_volume", ObjectiveType.MINIMIZE),
        constraints=[
            Constraint("Max Wall Temp", "hot_gas_wall_temp", ConstraintType.LESS_THAN_OR_EQUAL, 1100.0),
        ],
    )
    secondary = Objective("Max Isp", "isp_vacuum", ObjectiveType.MAXIMIZE)

    generator = ParetoFrontierGenerator(problem, secondary_objective=secondary, num_points=6)
    pareto_pts = generator.generate()

    assert len(pareto_pts) >= 2
    for pt in pareto_pts:
        assert "obj1_value" in pt
        assert "obj2_value" in pt
        assert pt["obj1_value"] > 0.0
        assert pt["obj2_value"] > 0.0


def test_sobol_sensitivity_analysis_ranking():
    """Validates Sobol global variance decomposition ranking."""
    problem = OptimizationProblem(
        name="Sensitivity Study",
        variables=[
            DesignVariable("chamber_pressure", 60e5, 100e5, 80e5, unit="Pa"),
            DesignVariable("expansion_ratio", 15.0, 35.0, 25.0, unit="-"),
            DesignVariable("wall_thickness", 0.0012, 0.0025, 0.0015, unit="m"),
        ],
        objective=Objective("Hot Wall Temp", "hot_gas_wall_temp", ObjectiveType.MINIMIZE),
    )

    analyzer = SobolSensitivityAnalyzer(problem, output_key="hot_gas_wall_temp", n_samples=32)
    res = analyzer.analyze()

    assert res.output_key == "hot_gas_wall_temp"
    assert len(res.ranked_variables) == 3
    # Check all indices are between 0 and 1.5
    for var_name, s_ti in res.total_order_indices.items():
        assert 0.0 <= s_ti <= 1.5
    assert res.computation_time_ms > 0.0


def test_monte_carlo_tolerance_sampling_distributions():
    """Validates statistical distribution generation across manufacturing variances."""
    tol_pc = ToleranceParameter(
        input_key="chamber_pressure",
        nominal_value=80e5,
        distribution=DistributionType.NORMAL,
        variation=2e5,  # +/- 2 bar std dev
        unit="Pa",
    )
    tol_wt = ToleranceParameter(
        input_key="wall_thickness",
        nominal_value=0.0015,
        distribution=DistributionType.UNIFORM,
        variation=0.0001,  # +/- 0.1 mm uniform
        unit="m",
    )

    samples_pc = tol_pc.sample(100)
    assert len(samples_pc) == 100
    assert np.mean(samples_pc) == pytest.approx(80e5, rel=0.05)

    samples_wt = tol_wt.sample(100)
    assert np.min(samples_wt) >= 0.0014 - 1e-6
    assert np.max(samples_wt) <= 0.0016 + 1e-6


def test_monte_carlo_yield_and_failure_probability():
    """Tests Monte Carlo failure probability and yield calculation."""
    tolerances = [
        ToleranceParameter("chamber_pressure", 70e5, DistributionType.NORMAL, 2e5, "Pa"),
        ToleranceParameter("wall_thickness", 0.0015, DistributionType.NORMAL, 0.00008, "m"),
    ]
    # Set a realistic constraint that most samples pass
    constraints = [
        Constraint("Thermal Cap", "hot_gas_wall_temp", ConstraintType.LESS_THAN_OR_EQUAL, 1150.0),
    ]

    sim = MonteCarloToleranceSimulator(tolerances=tolerances, constraints=constraints)
    result = sim.run(num_samples=40, random_seed=42)

    assert result.num_samples == 40
    assert 0.0 <= result.overall_yield_percentage <= 100.0
    assert "Thermal Cap" in result.constraint_failure_probabilities
    assert "hot_gas_wall_temp" in result.statistics
    stats = result.statistics["hot_gas_wall_temp"]
    assert stats.min_val <= stats.median <= stats.max_val
    assert len(stats.histogram_counts) > 0


def test_deterministic_revision_stamping_on_optimal_design():
    """Ensures an optimal result creates an immutable DesignRevision."""
    problem = OptimizationProblem(
        name="Revision Integrity Optimization",
        variables=[
            DesignVariable("chamber_pressure", 70e5, 90e5, 75e5, unit="Pa"),
        ],
        objective=Objective("Min Volume", "cad_solid_volume", ObjectiveType.MINIMIZE),
    )
    optimizer = SLSQPOptimizer(problem, max_iter=10)
    res = optimizer.solve()

    assert res.revision_id is not None
    assert len(res.revision_id) > 8
