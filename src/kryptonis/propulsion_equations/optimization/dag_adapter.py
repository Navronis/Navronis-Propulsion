"""
DAG Adapter for Optimization (Day 8).
=====================================

Bridges an OptimizationProblem to an underlying DependencyDAG:
  - Marshals continuous variable vectors into DAG inputs with units
  - Selectively recomputes downstream propulsion nodes
  - Extracts objective values and normalized constraint margins
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from kryptonis.propulsion_equations.truth.dag import DependencyDAG
from kryptonis.propulsion_equations.truth.ir import EngineeringValue
from kryptonis.propulsion_equations.truth.propulsion_dag import build_propulsion_dag
from kryptonis.propulsion_equations.optimization.problem import (
    OptimizationProblem,
    ObjectiveType,
    ConstraintType,
)


class DAGEvaluator:
    """Evaluates design vectors against the propulsion DependencyDAG."""

    def __init__(self, problem: OptimizationProblem, base_dag: Optional[DependencyDAG] = None):
        self.problem = problem
        self.dag = base_dag or build_propulsion_dag()
        # Ensure base DAG is computed once initially
        self.dag.recompute(trigger_reason="Initialization of DAGEvaluator")
        self.eval_count = 0

    def evaluate_vector(self, x: List[float]) -> Tuple[float, Dict[str, float], Dict[str, float]]:
        """
        Evaluates candidate vector x:
        Returns:
            (objective_value, constraint_margins_dict, output_values_dict)
        """
        self.eval_count += 1
        var_dict: Dict[str, float] = {}

        for var, val in zip(self.problem.variables, x):
            var_dict[var.name] = val
            current_ev = self.dag.get_value(var.name)
            unit = current_ev.unit if current_ev else var.unit
            method = f"MDO Candidate Iteration #{self.eval_count}"

            new_ev = EngineeringValue(
                name=var.name,
                value=float(val),
                unit=unit,
                method=method,
                description=var.description or f"Optimized {var.name}",
            )
            self.dag.set_input(var.name, new_ev, reason=f"Optimization Step #{self.eval_count}")

        # Selective topological DAG execution
        self.dag.recompute(trigger_reason=f"MDO Iteration #{self.eval_count}")

        # Collect all active outputs
        outputs = self.dag.get_all_outputs()
        out_vals: Dict[str, float] = {k: v.value for k, v in outputs.items()}

        # Evaluate primary objective
        obj_key = self.problem.objective.quantity_key
        if obj_key not in out_vals:
            raise KeyError(f"Objective quantity '{obj_key}' not found in DAG outputs.")

        raw_obj = out_vals[obj_key]
        # Invert sign if MAXIMIZE so solvers can minimize universally
        if self.problem.objective.objective_type == ObjectiveType.MAXIMIZE:
            obj_val = -raw_obj * self.problem.objective.weight
        else:
            obj_val = raw_obj * self.problem.objective.weight

        # Evaluate constraints
        margins: Dict[str, float] = {}
        for c in self.problem.constraints:
            if c.quantity_key not in out_vals:
                raise KeyError(f"Constraint quantity '{c.quantity_key}' not found in DAG outputs.")
            c_val = out_vals[c.quantity_key]
            margins[c.name] = c.evaluate_margin(c_val)

        return obj_val, margins, out_vals
