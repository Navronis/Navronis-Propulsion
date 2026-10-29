"""
Navronis Propulsion Optimization & Trade-Study Subsystem (Day 8).
=================================================================

Provides multidisciplinary design optimization, multi-objective Pareto trade-offs,
global sensitivity analysis (Sobol indices), and Monte Carlo manufacturing tolerance
uncertainty propagation integrated with the Day 7 Engineering Truth Layer.
"""

from kryptonis.propulsion_equations.optimization.problem import (
    Constraint,
    ConstraintType,
    DesignVariable,
    Objective,
    ObjectiveType,
    OptimizationProblem,
    OptimizationResult,
)
from kryptonis.propulsion_equations.optimization.dag_adapter import DAGEvaluator
from kryptonis.propulsion_equations.optimization.slsqp_solver import SLSQPOptimizer
from kryptonis.propulsion_equations.optimization.pareto import ParetoFrontierGenerator, is_pareto_efficient
from kryptonis.propulsion_equations.optimization.sensitivity import (
    SensitivityResult,
    SobolSensitivityAnalyzer,
)
from kryptonis.propulsion_equations.optimization.uncertainty import (
    DistributionStats,
    DistributionType,
    MonteCarloToleranceSimulator,
    ToleranceParameter,
    UncertaintyResult,
)

__all__ = [
    "Constraint",
    "ConstraintType",
    "DesignVariable",
    "Objective",
    "ObjectiveType",
    "OptimizationProblem",
    "OptimizationResult",
    "DAGEvaluator",
    "SLSQPOptimizer",
    "ParetoFrontierGenerator",
    "is_pareto_efficient",
    "SensitivityResult",
    "SobolSensitivityAnalyzer",
    "DistributionStats",
    "DistributionType",
    "MonteCarloToleranceSimulator",
    "ToleranceParameter",
    "UncertaintyResult",
]
