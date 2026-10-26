"""
Engineering Intermediate Representation (IR) (Day 7).
======================================================

Strongly typed intermediate data structures for rocket propulsion engineering:
- Every engineering value is an `EngineeringValue` carrying value, canonical unit,
  method, dependencies, cryptographic calculation ID, validation state, and source evidence.
- Strongly typed domain specs for Design Requirements, Operating Conditions,
  Materials, Physics Inputs, Geometry, Solver Config, and CAD Artifacts.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from kryptonis.propulsion_equations.truth.evidence import (
    EvidenceRecord,
    SourceAuthority,
    ValidationState,
)
from kryptonis.propulsion_equations.truth.units_safe import (
    UnitSafety,
)


def _compute_calc_id(name: str, value: Any, unit: str, method: str, dependencies: Tuple[str, ...]) -> str:
    """Computes a deterministic content hash for an engineering calculation."""
    payload = f"{name}:{value}:{unit}:{method}:{','.join(sorted(dependencies))}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class EngineeringValue:
    """An annotated engineering quantity with complete provenance.

    No engineering quantity in Navronis exists as an unexplained raw float.
    Every number knows its unit, governing method, upstream dependencies,
    validation state, and literature source.
    """
    name: str
    value: float
    unit: str  # Canonical SI unit
    method: str = "Direct Specification"
    source: Optional[EvidenceRecord] = None
    dependencies: Tuple[str, ...] = ()
    calculation_id: str = ""
    validation_state: ValidationState = ValidationState.VERIFIED
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    display_unit: Optional[str] = None
    description: str = ""

    def __post_init__(self) -> None:
        if not self.calculation_id:
            calc_id = _compute_calc_id(self.name, self.value, self.unit, self.method, self.dependencies)
            object.__setattr__(self, "calculation_id", calc_id)

    def to(self, target_unit: str) -> float:
        """Converts canonical value into requested target engineering unit."""
        return UnitSafety.convert(self.value, self.unit, target_unit)

    @property
    def display_value(self) -> float:
        """Value in display unit if configured, otherwise canonical value."""
        if self.display_unit and self.display_unit != self.unit:
            return self.to(self.display_unit)
        return self.value

    def __float__(self) -> float:
        return float(self.value)

    def __repr__(self) -> str:
        disp_u = self.display_unit or self.unit
        disp_val = self.display_value
        return f"EngineeringValue({self.name}={disp_val:.4g} {disp_u} [{self.validation_state.value}])"

    def __str__(self) -> str:
        disp_u = self.display_unit or self.unit
        disp_val = self.display_value
        return f"{disp_val:.4g} {disp_u}"

    def explain(self) -> Dict[str, Any]:
        """Provides structured provenance output for the Digital Thread."""
        return {
            "name": self.name,
            "value_canonical": self.value,
            "unit_canonical": self.unit,
            "display_value": self.display_value,
            "display_unit": self.display_unit or self.unit,
            "method": self.method,
            "validation_state": self.validation_state.value,
            "calculation_id": self.calculation_id,
            "dependencies": list(self.dependencies),
            "timestamp": self.timestamp,
            "evidence": self.source.as_dict() if self.source else None,
            "description": self.description,
        }

    def as_dict(self) -> Dict[str, Any]:
        return self.explain()


# --------------------------------------------------------------------------
# Strongly Typed Domain Data Structures
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class DesignRequirements:
    """High-level mission and engine sizing requirements."""
    thrust_vac: EngineeringValue
    chamber_pressure: EngineeringValue
    propellant_pair: str
    mixture_ratio: EngineeringValue
    expansion_ratio: EngineeringValue
    characteristic_length: EngineeringValue
    burn_time: EngineeringValue
    description: str = "Preliminary Design Requirements"


@dataclass(frozen=True)
class OperatingConditions:
    """Current flight or test bench environment."""
    ambient_pressure: EngineeringValue
    altitude: EngineeringValue
    throttle_ratio: EngineeringValue
    g_local: EngineeringValue


@dataclass(frozen=True)
class MaterialSpec:
    """Aerospace alloy properties for combustion chamber liner and jacket."""
    name: str
    thermal_conductivity: EngineeringValue
    yield_strength: EngineeringValue
    elastic_modulus: EngineeringValue
    thermal_expansion: EngineeringValue
    poisson_ratio: EngineeringValue
    density: EngineeringValue
    max_service_temp: EngineeringValue
    jacket_material: str = "Inconel-718"


@dataclass(frozen=True)
class PhysicsInputs:
    """Gas-dynamic and thermodynamic combustion parameters."""
    c_star: EngineeringValue
    gamma: EngineeringValue
    molar_mass: EngineeringValue
    combustion_temp: EngineeringValue
    chamber_density: EngineeringValue
    oxidizer_density: EngineeringValue
    fuel_density: EngineeringValue
    fuel_cp: EngineeringValue
    fuel_viscosity: EngineeringValue
    fuel_conductivity: EngineeringValue


@dataclass(frozen=True)
class GeometrySpec:
    """Physical dimensions for the complete rocket thrust chamber assembly."""
    throat_diameter: EngineeringValue
    chamber_diameter: EngineeringValue
    exit_diameter: EngineeringValue
    length_cylinder: EngineeringValue
    length_convergent: EngineeringValue
    length_nozzle: EngineeringValue
    length_total: EngineeringValue
    wall_thickness: EngineeringValue
    channel_height: EngineeringValue
    fin_thickness: EngineeringValue
    number_channels: EngineeringValue
    nozzle_type: str = "bell"


@dataclass(frozen=True)
class SolverConfig:
    """Numerical solver convergence limits and discretization settings."""
    axial_stations: int = 100
    boundary_layer_displacement: bool = True
    stark_separation_check: bool = True
    tolerance: float = 1.0e-5
    max_iterations: int = 50


@dataclass(frozen=True)
class CADArtifact:
    """Generated geometric file artifact linked to exact design revision state."""
    artifact_type: str  # "STEP", "STL", "SVG_BLUEPRINT", "SPEC_JSON"
    filename: str
    byte_size: int
    sha256_checksum: str
    design_revision_id: str
    created_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)
