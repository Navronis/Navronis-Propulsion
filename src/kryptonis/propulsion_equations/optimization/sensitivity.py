"""
Global Sensitivity Analysis & Sobol Decomposition (Day 8).
==========================================================

Quantifies the contribution of each design input variable to the variance
of critical output performance metrics (heat flux, wall temperature, mass, Isp).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import numpy as np

from kryptonis.propulsion_equations.optimization.problem import OptimizationProblem, DesignVariable
from kryptonis.propulsion_equations.optimization.dag_adapter import DAGEvaluator


@dataclass
class SensitivityResult:
    """Statistical sensitivity analysis output."""
    output_key: str
    variable_names: List[str]
    first_order_indices: Dict[str, float]      # S_i (main effects)
    total_order_indices: Dict[str, float]      # S_Ti (total effects including interactions)
    ranked_variables: List[Tuple[str, float]]  # Ordered from highest to lowest influence
    sample_size: int
    computation_time_ms: float


class SobolSensitivityAnalyzer:
    """Saltelli sampling and Sobol variance decomposition on the DependencyDAG."""

    def __init__(self, problem: OptimizationProblem, output_key: str, n_samples: int = 128):
        self.problem = problem
        self.output_key = output_key
        self.n_samples = max(32, n_samples)
        self.evaluator = DAGEvaluator(problem)

    def analyze(self) -> SensitivityResult:
        """Executes Sobol sampling and calculates first-order and total-order indices."""
        t_start = time.perf_counter()
        k = self.problem.num_variables
        n = self.n_samples

        # 1. Generate two independent uniform matrices A and B in [0, 1]
        np.random.seed(42)  # Deterministic seed for reproducible testing
        A = np.random.rand(n, k)
        B = np.random.rand(n, k)

        bounds = self.problem.get_variable_bounds()

        def scale_row(unit_row: np.ndarray) -> List[float]:
            return [b[0] + unit_row[i] * (b[1] - b[0]) for i, b in enumerate(bounds)]

        def eval_single(unit_row: np.ndarray) -> float:
            phys_vec = scale_row(unit_row)
            _, _, out_vals = self.evaluator.evaluate_vector(phys_vec)
            return out_vals.get(self.output_key, 0.0)

        # 2. Evaluate base matrices f(A) and f(B)
        y_A = np.array([eval_single(A[i, :]) for i in range(n)])
        y_B = np.array([eval_single(B[i, :]) for i in range(n)])

        f_0 = np.mean(y_A)
        total_var = np.var(y_A, ddof=1)
        if total_var < 1e-12:
            total_var = 1e-12

        s_first: Dict[str, float] = {}
        s_total: Dict[str, float] = {}

        # 3. For each variable i, build AB_i matrix and evaluate
        for i, var in enumerate(self.problem.variables):
            AB_i = np.copy(A)
            AB_i[:, i] = B[:, i]
            y_AB_i = np.array([eval_single(AB_i[j, :]) for j in range(n)])

            # Jansen (1999) / Saltelli (2010) estimator:
            # First order: V_i = Var(y_A) - 0.5 * mean((y_B - y_AB_i)^2)
            # Total order: V_Ti = 0.5 * mean((y_A - y_AB_i)^2)
            v_i = total_var - 0.5 * np.mean((y_B - y_AB_i) ** 2)
            v_ti = 0.5 * np.mean((y_A - y_AB_i) ** 2)

            s_i = float(np.clip(v_i / total_var, 0.0, 1.0))
            s_ti = float(np.clip(v_ti / total_var, 0.0, 1.5))

            s_first[var.name] = s_i
            s_total[var.name] = s_ti

        # Rank variables by total influence
        ranked = sorted(s_total.items(), key=lambda kv: kv[1], reverse=True)
        duration_ms = (time.perf_counter() - t_start) * 1000.0

        return SensitivityResult(
            output_key=self.output_key,
            variable_names=[v.name for v in self.problem.variables],
            first_order_indices=s_first,
            total_order_indices=s_total,
            ranked_variables=ranked,
            sample_size=n * (k + 2),
            computation_time_ms=duration_ms,
        )
