"""
SLSQP Constrained Optimization Solver (Day 8).
==============================================

Solves non-linear constrained propulsion MDO problems using Sequential Least
Squares Programming (SLSQP) directly connected to the DependencyDAG.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
import numpy as np
from scipy.optimize import minimize

from kryptonis.propulsion_equations.optimization.problem import (
    OptimizationProblem,
    OptimizationResult,
    ObjectiveType,
    ConstraintType,
)
from kryptonis.propulsion_equations.optimization.dag_adapter import DAGEvaluator
from kryptonis.propulsion_equations.truth.thread import DigitalThread


class SLSQPOptimizer:
    """Nonlinear constrained optimizer for propulsion systems."""

    def __init__(self, problem: OptimizationProblem, max_iter: int = 50, ftol: float = 1e-5):
        self.problem = problem
        self.max_iter = max_iter
        self.ftol = ftol
        self.evaluator = DAGEvaluator(problem)
        self.history: List[Dict[str, Any]] = []

    def solve(self) -> OptimizationResult:
        """Executes the constrained optimization search."""
        t_start = time.perf_counter()
        x0 = np.array(self.problem.get_initial_vector(), dtype=float)
        bounds = self.problem.get_variable_bounds()

        # Build scipy constraint specifications
        scipy_constraints = []
        for c in self.problem.constraints:
            if c.constraint_type in (ConstraintType.LESS_THAN_OR_EQUAL, ConstraintType.GREATER_THAN_OR_EQUAL):
                # in scipy: ineq constraint c(x) >= 0
                def make_ineq(constraint_obj):
                    return lambda x: constraint_obj.evaluate_margin(
                        self.evaluator.evaluate_vector(list(x))[2][constraint_obj.quantity_key]
                    )
                scipy_constraints.append({
                    "type": "ineq",
                    "fun": make_ineq(c)
                })
            else:
                # eq constraint h(x) == 0
                def make_eq(constraint_obj):
                    return lambda x: (
                        self.evaluator.evaluate_vector(list(x))[2][constraint_obj.quantity_key] - constraint_obj.limit
                    )
                scipy_constraints.append({
                    "type": "eq",
                    "fun": make_eq(c)
                })

        # Objective wrapper with history recording
        def objective_wrapper(x):
            obj_val, margins, out_vals = self.evaluator.evaluate_vector(list(x))
            var_dict = {var.name: float(val) for var, val in zip(self.problem.variables, x)}
            # Undo sign flip if maximized for user-facing log
            reported_obj = -obj_val if self.problem.objective.objective_type == ObjectiveType.MAXIMIZE else obj_val
            
            step_record = {
                "iteration": len(self.history) + 1,
                "variables": var_dict,
                "objective": float(reported_obj),
                "margins": {k: float(v) for k, v in margins.items()},
                "feasible": all(m >= -c.tolerance for c, m in zip(self.problem.constraints, margins.values())),
            }
            self.history.append(step_record)
            return obj_val

        # Execute SLSQP
        res = minimize(
            fun=objective_wrapper,
            x0=x0,
            method="SLSQP",
            bounds=bounds,
            constraints=scipy_constraints,
            options={
                "maxiter": self.max_iter,
                "ftol": self.ftol,
                "disp": False,
            }
        )

        duration_ms = (time.perf_counter() - t_start) * 1000.0

        # Final evaluation at the optimal point
        opt_x = list(res.x)
        final_obj_raw, final_margins, final_outputs = self.evaluator.evaluate_vector(opt_x)
        opt_obj_reported = -final_obj_raw if self.problem.objective.objective_type == ObjectiveType.MAXIMIZE else final_obj_raw

        opt_vars = {var.name: float(val) for var, val in zip(self.problem.variables, opt_x)}

        # Stamp deterministic DesignRevision via DigitalThread
        thread = DigitalThread(self.evaluator.dag)
        rev = thread.commit_revision(
            notes=f"SLSQP Optimization result: {self.problem.objective.name} = {opt_obj_reported:.4g}"
        )

        return OptimizationResult(
            success=bool(res.success),
            status_message=str(res.message),
            optimal_variables=opt_vars,
            optimal_objective_value=float(opt_obj_reported),
            optimal_outputs=final_outputs,
            constraint_margins=final_margins,
            iterations=int(res.nit),
            function_evaluations=int(res.nfev),
            execution_time_ms=duration_ms,
            iteration_history=self.history,
            revision_id=rev.revision_id,
        )
