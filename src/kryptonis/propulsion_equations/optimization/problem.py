"""
Multidisciplinary Design Optimization (MDO) Problem Definitions (Day 8).
========================================================================

Provides strongly typed representations for:
  - Design variables with physical bounds and units
  - Non-linear inequality & equality constraints
  - Objective formulations (single, weighted multi-objective, Pareto)
  - Optimization problem specifications tied to the Dependency DAG
  - Optimization result records with full Digital Thread provenance
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
import time


class ObjectiveType(str, Enum):
    """Supported optimization objective types."""
    MINIMIZE = "MINIMIZE"
    MAXIMIZE = "MAXIMIZE"


class ConstraintType(str, Enum):
    """Supported constraint types."""
    LESS_THAN_OR_EQUAL = "LEQ"      # g(x) <= limit
    GREATER_THAN_OR_EQUAL = "GEQ"   # g(x) >= limit
    EQUAL = "EQ"                    # h(x) == target


@dataclass
class DesignVariable:
    """Strongly typed continuous design parameter."""
    name: str
    lower_bound: float
    upper_bound: float
    initial_value: float
    unit: str = "-"
    description: str = ""

    def __post_init__(self):
        if self.lower_bound >= self.upper_bound:
            raise ValueError(f"Variable {self.name}: lower_bound ({self.lower_bound}) must be < upper_bound ({self.upper_bound})")
        if not (self.lower_bound <= self.initial_value <= self.upper_bound):
            raise ValueError(f"Variable {self.name}: initial_value ({self.initial_value}) outside [{self.lower_bound}, {self.upper_bound}]")

    def normalize(self, val: float) -> float:
        """Normalizes physical value into [0.0, 1.0]."""
        return (val - self.lower_bound) / (self.upper_bound - self.lower_bound)

    def denormalize(self, norm_val: float) -> float:
        """Denormalizes [0.0, 1.0] value into physical domain."""
        return self.lower_bound + norm_val * (self.upper_bound - self.lower_bound)


@dataclass
class Constraint:
    """Engineering constraint applied to DAG output or derived quantity."""
    name: str
    quantity_key: str
    constraint_type: ConstraintType
    limit: float
    unit: str = "-"
    tolerance: float = 1e-4
    description: str = ""

    def evaluate_margin(self, current_value: float) -> float:
        """
        Calculates normalized feasibility margin.
        Positive margin = FEASIBLE (satisfied).
        Negative margin = VIOLATED.
        """
        scale = abs(self.limit) if abs(self.limit) > 1e-9 else 1.0
        if self.constraint_type == ConstraintType.LESS_THAN_OR_EQUAL:
            # limit - value >= 0
            return (self.limit - current_value) / scale
        elif self.constraint_type == ConstraintType.GREATER_THAN_OR_EQUAL:
            # value - limit >= 0
            return (current_value - self.limit) / scale
        else:
            # Equality: -|value - target|
            return -abs(current_value - self.limit) / scale

    def is_satisfied(self, current_value: float) -> bool:
        """Returns True if constraint is satisfied within tolerance."""
        return self.evaluate_margin(current_value) >= -self.tolerance


@dataclass
class Objective:
    """Optimization objective definition."""
    name: str
    quantity_key: str
    objective_type: ObjectiveType = ObjectiveType.MINIMIZE
    weight: float = 1.0
    unit: str = "-"
    description: str = ""


@dataclass
class OptimizationProblem:
    """Complete mathematical formulation of an engine MDO problem."""
    name: str
    variables: List[DesignVariable]
    objective: Objective
    constraints: List[Constraint] = field(default_factory=list)
    secondary_objective: Optional[Objective] = None  # For Pareto multi-objective studies
    description: str = ""

    @property
    def num_variables(self) -> int:
        return len(self.variables)

    @property
    def num_constraints(self) -> int:
        return len(self.constraints)

    def get_variable_bounds(self) -> List[Tuple[float, float]]:
        return [(v.lower_bound, v.upper_bound) for v in self.variables]

    def get_initial_vector(self) -> List[float]:
        return [v.initial_value for v in self.variables]


@dataclass
class OptimizationResult:
    """Comprehensive output of an optimization execution."""
    success: bool
    status_message: str
    optimal_variables: Dict[str, float]
    optimal_objective_value: float
    optimal_outputs: Dict[str, float]
    constraint_margins: Dict[str, float]
    iterations: int
    function_evaluations: int
    execution_time_ms: float
    iteration_history: List[Dict[str, Any]] = field(default_factory=list)
    pareto_front: Optional[List[Dict[str, Any]]] = None
    revision_id: Optional[str] = None
