"""
Navronis Truth Layer, Digital Thread & Recompute Graph (Day 7).
==============================================================

Provides strongly typed intermediate representations, verifiable citations,
selective dependency recomputation, and backwards provenance tracing.
"""

from __future__ import annotations

from kryptonis.propulsion_equations.truth.dag import (
    ComputationNode,
    DependencyCycleError,
    DependencyDAG,
    RecomputeReport,
)
from kryptonis.propulsion_equations.truth.evidence import (
    LITERATURE_CATALOG,
    EvidenceRecord,
    SourceAuthority,
    ValidationState,
)
from kryptonis.propulsion_equations.truth.ir import (
    CADArtifact,
    DesignRequirements,
    EngineeringValue,
    GeometrySpec,
    MaterialSpec,
    OperatingConditions,
    PhysicsInputs,
    SolverConfig,
)
from kryptonis.propulsion_equations.truth.propulsion_dag import (
    build_propulsion_dag,
)
from kryptonis.propulsion_equations.truth.thread import (
    DesignRevision,
    DigitalThread,
)
from kryptonis.propulsion_equations.truth.units_safe import (
    UnitDimension,
    UnitDimensionError,
    UnitSafety,
    UnknownUnitError,
)

__all__ = [
    "SourceAuthority",
    "ValidationState",
    "EvidenceRecord",
    "LITERATURE_CATALOG",
    "UnitDimension",
    "UnitDimensionError",
    "UnknownUnitError",
    "UnitSafety",
    "EngineeringValue",
    "DesignRequirements",
    "OperatingConditions",
    "MaterialSpec",
    "PhysicsInputs",
    "GeometrySpec",
    "SolverConfig",
    "CADArtifact",
    "ComputationNode",
    "DependencyCycleError",
    "DependencyDAG",
    "RecomputeReport",
    "DesignRevision",
    "DigitalThread",
    "build_propulsion_dag",
]
