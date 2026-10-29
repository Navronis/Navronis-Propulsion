"""
Monte Carlo Manufacturing Tolerance & Uncertainty Propagation (Day 8).
======================================================================

Propagates physical manufacturing deviations (CNC lathe tolerances, wall
thickness variations, material property dispersions) through the DependencyDAG
to quantify defect probability and statistical performance margins.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from kryptonis.propulsion_equations.truth.dag import DependencyDAG
from kryptonis.propulsion_equations.truth.ir import EngineeringValue
from kryptonis.propulsion_equations.truth.propulsion_dag import build_propulsion_dag
from kryptonis.propulsion_equations.optimization.problem import Constraint, ConstraintType


class DistributionType(str, Enum):
    """Statistical distribution options for input tolerances."""
    NORMAL = "NORMAL"        # Gaussian: mu, sigma (truncated at +/- 3*sigma)
    UNIFORM = "UNIFORM"      # Uniform: [nominal - delta, nominal + delta]


@dataclass
class ToleranceParameter:
    """Specification of uncertainty on an input quantity."""
    input_key: str
    nominal_value: float
    distribution: DistributionType = DistributionType.NORMAL
    # For NORMAL: standard_deviation; for UNIFORM: half_width (delta)
    variation: float = 0.0
    unit: str = "-"
    description: str = ""

    def sample(self, size: int) -> np.ndarray:
        """Draws statistical realizations."""
        if self.distribution == DistributionType.NORMAL:
            samples = np.random.normal(loc=self.nominal_value, scale=self.variation, size=size)
            # Truncate at +/- 3.5 sigma to avoid unphysical negative dimensions
            lower = max(0.0001, self.nominal_value - 3.5 * self.variation)
            upper = self.nominal_value + 3.5 * self.variation
            return np.clip(samples, lower, upper)
        else:
            lower = max(0.0001, self.nominal_value - self.variation)
            upper = self.nominal_value + self.variation
            return np.random.uniform(low=lower, high=upper, size=size)


@dataclass
class DistributionStats:
    """Descriptive statistics for a single output quantity."""
    quantity_key: str
    mean: float
    std_dev: float
    min_val: float
    max_val: float
    p05: float
    median: float
    p95: float
    p99: float
    histogram_bins: List[float] = field(default_factory=list)
    histogram_counts: List[int] = field(default_factory=list)


@dataclass
class UncertaintyResult:
    """Complete summary of Monte Carlo tolerance propagation."""
    num_samples: int
    execution_time_ms: float
    statistics: Dict[str, DistributionStats]
    constraint_failure_probabilities: Dict[str, float]  # Probability of violating constraint (0.0 to 1.0)
    overall_yield_percentage: float                     # % of manufactured engines that pass ALL constraints
    worst_case_samples: List[Dict[str, float]]          # Edge case designs


class MonteCarloToleranceSimulator:
    """Monte Carlo engine evaluating manufacturing dispersion across the DAG."""

    def __init__(
        self,
        tolerances: List[ToleranceParameter],
        constraints: Optional[List[Constraint]] = None,
        base_dag: Optional[DependencyDAG] = None,
    ):
        self.tolerances = tolerances
        self.constraints = constraints or []
        self.dag = base_dag or build_propulsion_dag()
        self.dag.recompute(trigger_reason="Monte Carlo simulator init")

    def run(self, num_samples: int = 500, random_seed: int = 42) -> UncertaintyResult:
        """Executes Monte Carlo trials across the DependencyDAG."""
        t_start = time.perf_counter()
        np.random.seed(random_seed)

        # 1. Draw sample matrices for all uncertain inputs
        sample_matrix: Dict[str, np.ndarray] = {
            t.input_key: t.sample(num_samples) for t in self.tolerances
        }

        tracked_keys = [
            "T_wall_hot",
            "peak_heat_flux",
            "cooling_pressure_drop",
            "throat_diameter",
            "chamber_pressure",
            "cad_volume",
            "isp_vacuum",
        ]
        
        # Add any constraint keys that might not be in default tracked
        for c in self.constraints:
            if c.quantity_key not in tracked_keys:
                tracked_keys.append(c.quantity_key)

        results_by_key: Dict[str, List[float]] = {k: [] for k in tracked_keys}
        violation_counts: Dict[str, int] = {c.name: 0 for c in self.constraints}
        fully_compliant_count = 0
        worst_cases: List[Dict[str, float]] = []

        # 2. Iterate trials through the selective recompute DAG
        for i in range(num_samples):
            # Update inputs
            for t in self.tolerances:
                val = float(sample_matrix[t.input_key][i])
                ev = EngineeringValue(
                    name=t.input_key,
                    value=val,
                    unit=t.unit,
                    method="Monte Carlo Tolerance Sample",
                    description=f"Trial #{i+1}",
                )
                self.dag.set_input(t.input_key, ev, reason=f"MC Trial #{i+1}")

            # Recompute
            self.dag.recompute(trigger_reason=f"MC Trial #{i+1}")
            all_out = self.dag.get_all_outputs()

            trial_pass = True
            for c in self.constraints:
                c_val = all_out[c.quantity_key].value if c.quantity_key in all_out else 0.0
                if not c.is_satisfied(c_val):
                    violation_counts[c.name] += 1
                    trial_pass = False

            if trial_pass:
                fully_compliant_count += 1
            else:
                if len(worst_cases) < 5:
                    worst_cases.append({k: all_out[k].value for k in tracked_keys if k in all_out})

            for k in tracked_keys:
                if k in all_out:
                    results_by_key[k].append(all_out[k].value)

        # 3. Compute statistical distributions & histograms
        stats_dict: Dict[str, DistributionStats] = {}
        for k, arr in results_by_key.items():
            if not arr:
                continue
            np_arr = np.array(arr)
            counts, bin_edges = np.histogram(np_arr, bins=15)
            
            stats_dict[k] = DistributionStats(
                quantity_key=k,
                mean=float(np.mean(np_arr)),
                std_dev=float(np.std(np_arr, ddof=1)),
                min_val=float(np.min(np_arr)),
                max_val=float(np.max(np_arr)),
                p05=float(np.percentile(np_arr, 5)),
                median=float(np.median(np_arr)),
                p95=float(np.percentile(np_arr, 95)),
                p99=float(np.percentile(np_arr, 99)),
                histogram_bins=[float(b) for b in bin_edges],
                histogram_counts=[int(c) for c in counts],
            )

        duration_ms = (time.perf_counter() - t_start) * 1000.0
        failure_probs = {c_name: (count / num_samples) for c_name, count in violation_counts.items()}
        yield_pct = (fully_compliant_count / num_samples) * 100.0

        return UncertaintyResult(
            num_samples=num_samples,
            execution_time_ms=duration_ms,
            statistics=stats_dict,
            constraint_failure_probabilities=failure_probs,
            overall_yield_percentage=yield_pct,
            worst_case_samples=worst_cases,
        )
