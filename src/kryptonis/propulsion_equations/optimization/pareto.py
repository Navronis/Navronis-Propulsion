"""
Multi-Objective Pareto Frontier Generator (Day 8).
=================================================

Computes the non-dominated Pareto trade-off curve between conflicting
propulsion objectives (e.g. Engine Dry Mass vs Vacuum Specific Impulse)
subject to all thermal, structural, and hydraulic constraints.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from kryptonis.propulsion_equations.optimization.problem import (
    OptimizationProblem,
    Objective,
    ObjectiveType,
    OptimizationResult,
)
from kryptonis.propulsion_equations.optimization.slsqp_solver import SLSQPOptimizer


def is_pareto_efficient(costs: np.ndarray) -> np.ndarray:
    """
    Finds Pareto-efficient (non-dominated) points in a cost matrix (minimization).
    Point i is dominated if there exists another point j such that:
       np.all(costs[j] <= costs[i]) and np.any(costs[j] < costs[i])
    """
    n_points = costs.shape[0]
    is_efficient = np.ones(n_points, dtype=bool)
    for i in range(n_points):
        # A point is dominated if any other candidate is <= in all objectives and < in at least one
        dominated = np.any(
            np.all(costs <= costs[i], axis=1) & np.any(costs < costs[i], axis=1)
        )
        if dominated:
            is_efficient[i] = False
    return is_efficient


class ParetoFrontierGenerator:
    """Generates Pareto-optimal trade studies across two competing objectives."""

    def __init__(
        self,
        problem: OptimizationProblem,
        secondary_objective: Objective,
        num_points: int = 15,
    ):
        self.problem = problem
        self.secondary_objective = secondary_objective
        self.num_points = max(5, num_points)

    def generate(self) -> List[Dict[str, Any]]:
        """
        Sweeps the trade-off space using normalized weighted scalarization.
        Returns ordered list of non-dominated Pareto design candidates.
        """
        candidates: List[Dict[str, Any]] = []
        weights = np.linspace(0.0, 1.0, self.num_points)

        obj1 = self.problem.objective
        obj2 = self.secondary_objective

        for idx, w1 in enumerate(weights):
            w2 = 1.0 - w1

            # Formulate scalarized single-objective subproblem
            sub_problem = OptimizationProblem(
                name=f"Pareto Sweep #{idx+1} (w1={w1:.2f}, w2={w2:.2f})",
                variables=self.problem.variables,
                objective=obj1,
                constraints=self.problem.constraints,
            )

            solver = SLSQPOptimizer(sub_problem, max_iter=35)
            orig_eval = solver.evaluator.evaluate_vector

            def composite_eval(x):
                _, margins, out_vals = orig_eval(x)
                val1 = out_vals[obj1.quantity_key]
                val2 = out_vals[obj2.quantity_key]

                # Normalization proxies
                scale1 = 100.0 if "mass" in obj1.quantity_key or "vol" in obj1.quantity_key else (300.0 if "isp" in obj1.quantity_key else 1000.0)
                scale2 = 100.0 if "mass" in obj2.quantity_key or "vol" in obj2.quantity_key else (300.0 if "isp" in obj2.quantity_key else 1000.0)

                cost1 = (val1 / scale1) if obj1.objective_type == ObjectiveType.MINIMIZE else (-val1 / scale1)
                cost2 = (val2 / scale2) if obj2.objective_type == ObjectiveType.MINIMIZE else (-val2 / scale2)

                composite_cost = w1 * cost1 + w2 * cost2
                return composite_cost, margins, out_vals

            solver.evaluator.evaluate_vector = composite_eval
            result = solver.solve()

            if result.success or all(m >= -0.05 for m in result.constraint_margins.values()):
                out = result.optimal_outputs
                val1 = out.get(obj1.quantity_key, 0.0)
                val2 = out.get(obj2.quantity_key, 0.0)

                candidates.append({
                    "point_index": idx + 1,
                    "w1": float(w1),
                    "w2": float(w2),
                    "obj1_name": obj1.name,
                    "obj1_key": obj1.quantity_key,
                    "obj1_value": float(val1),
                    "obj2_name": obj2.name,
                    "obj2_key": obj2.quantity_key,
                    "obj2_value": float(val2),
                    "variables": result.optimal_variables,
                    "outputs": result.optimal_outputs,
                    "constraint_margins": result.constraint_margins,
                    "feasible": all(m >= -1e-4 for m in result.constraint_margins.values()),
                    "revision_id": result.revision_id,
                })

        # Filter strictly non-dominated designs
        if len(candidates) >= 2:
            costs = []
            for c in candidates:
                c1 = c["obj1_value"] if obj1.objective_type == ObjectiveType.MINIMIZE else -c["obj1_value"]
                c2 = c["obj2_value"] if obj2.objective_type == ObjectiveType.MINIMIZE else -c["obj2_value"]
                costs.append([c1, c2])

            costs_arr = np.array(costs)
            mask = is_pareto_efficient(costs_arr)
            pareto_front = [cand for cand, is_eff in zip(candidates, mask) if is_eff]
        else:
            pareto_front = candidates

        return pareto_front
