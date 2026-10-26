"""
Strict Unit Safety & Dimension Verification (Day 7).
====================================================

Prevents silent unit mismatch bugs across engineering boundaries.
All internal calculations are conducted strictly in canonical SI units:
- Length: meters [m]
- Pressure: pascals [Pa]
- Temperature: kelvin [K]
- Mass flow: kilograms per second [kg/s]
- Force: newtons [N]
- Heat flux: watts per square meter [W/m²]
- Power: watts [W]
- Velocity: meters per second [m/s]
- Mass: kilograms [kg]
- Angle: radians [rad]

Conversion occurs explicitly at input/output boundaries with dimensional validation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Tuple


class UnitDimension(str, Enum):
    """Physical dimensions for dimensional compatibility analysis."""
    LENGTH = "LENGTH"
    PRESSURE = "PRESSURE"
    TEMPERATURE = "TEMPERATURE"
    MASS_FLOW = "MASS_FLOW"
    FORCE = "FORCE"
    VELOCITY = "VELOCITY"
    MASS = "MASS"
    TIME = "TIME"
    AREA = "AREA"
    VOLUME = "VOLUME"
    HEAT_FLUX = "HEAT_FLUX"
    HEAT_TRANSFER_COEFF = "HEAT_TRANSFER_COEFF"
    ENERGY = "ENERGY"
    POWER = "POWER"
    DENSITY = "DENSITY"
    SPECIFIC_HEAT = "SPECIFIC_HEAT"
    THERMAL_CONDUCTIVITY = "THERMAL_CONDUCTIVITY"
    DYNAMIC_VISCOSITY = "DYNAMIC_VISCOSITY"
    ANGLE = "ANGLE"
    FREQUENCY = "FREQUENCY"
    DIMENSIONLESS = "DIMENSIONLESS"


class UnitDimensionError(TypeError):
    """Raised when an operation attempts conversion between incompatible physical dimensions."""
    pass


class UnknownUnitError(KeyError):
    """Raised when an unregistered unit symbol is supplied."""
    pass


@dataclass(frozen=True)
class UnitSpec:
    symbol: str
    dimension: UnitDimension
    canonical_symbol: str
    factor: float = 1.0  # multiplier to convert from this unit to canonical SI
    offset: float = 0.0  # additive offset for affine scales (e.g. °C -> K)


# Complete Aerospace Unit Registry with Canonical SI Mapping
_REGISTRY: Dict[str, UnitSpec] = {
    # Length [canonical: m]
    "m": UnitSpec("m", UnitDimension.LENGTH, "m", 1.0),
    "mm": UnitSpec("mm", UnitDimension.LENGTH, "m", 1.0e-3),
    "cm": UnitSpec("cm", UnitDimension.LENGTH, "m", 1.0e-2),
    "km": UnitSpec("km", UnitDimension.LENGTH, "m", 1.0e3),
    "in": UnitSpec("in", UnitDimension.LENGTH, "m", 0.0254),
    "inch": UnitSpec("inch", UnitDimension.LENGTH, "m", 0.0254),
    "ft": UnitSpec("ft", UnitDimension.LENGTH, "m", 0.3048),
    "µm": UnitSpec("µm", UnitDimension.LENGTH, "m", 1.0e-6),
    "um": UnitSpec("um", UnitDimension.LENGTH, "m", 1.0e-6),

    # Pressure [canonical: Pa]
    "Pa": UnitSpec("Pa", UnitDimension.PRESSURE, "Pa", 1.0),
    "kPa": UnitSpec("kPa", UnitDimension.PRESSURE, "Pa", 1.0e3),
    "MPa": UnitSpec("MPa", UnitDimension.PRESSURE, "Pa", 1.0e6),
    "bar": UnitSpec("bar", UnitDimension.PRESSURE, "Pa", 1.0e5),
    "mbar": UnitSpec("mbar", UnitDimension.PRESSURE, "Pa", 100.0),
    "atm": UnitSpec("atm", UnitDimension.PRESSURE, "Pa", 101325.0),
    "psi": UnitSpec("psi", UnitDimension.PRESSURE, "Pa", 6894.757),
    "psia": UnitSpec("psia", UnitDimension.PRESSURE, "Pa", 6894.757),

    # Temperature [canonical: K]
    "K": UnitSpec("K", UnitDimension.TEMPERATURE, "K", 1.0, 0.0),
    "degC": UnitSpec("degC", UnitDimension.TEMPERATURE, "K", 1.0, 273.15),
    "C": UnitSpec("C", UnitDimension.TEMPERATURE, "K", 1.0, 273.15),
    "°C": UnitSpec("°C", UnitDimension.TEMPERATURE, "K", 1.0, 273.15),
    "degR": UnitSpec("degR", UnitDimension.TEMPERATURE, "K", 1.0 / 1.8, 0.0),
    "R": UnitSpec("R", UnitDimension.TEMPERATURE, "K", 1.0 / 1.8, 0.0),

    # Mass flow [canonical: kg/s]
    "kg/s": UnitSpec("kg/s", UnitDimension.MASS_FLOW, "kg/s", 1.0),
    "g/s": UnitSpec("g/s", UnitDimension.MASS_FLOW, "kg/s", 1.0e-3),
    "lbm/s": UnitSpec("lbm/s", UnitDimension.MASS_FLOW, "kg/s", 0.45359237),

    # Force [canonical: N]
    "N": UnitSpec("N", UnitDimension.FORCE, "N", 1.0),
    "kN": UnitSpec("kN", UnitDimension.FORCE, "N", 1.0e3),
    "MN": UnitSpec("MN", UnitDimension.FORCE, "N", 1.0e6),
    "lbf": UnitSpec("lbf", UnitDimension.FORCE, "N", 4.4482216),

    # Velocity [canonical: m/s]
    "m/s": UnitSpec("m/s", UnitDimension.VELOCITY, "m/s", 1.0),
    "km/s": UnitSpec("km/s", UnitDimension.VELOCITY, "m/s", 1.0e3),
    "ft/s": UnitSpec("ft/s", UnitDimension.VELOCITY, "m/s", 0.3048),

    # Mass [canonical: kg]
    "kg": UnitSpec("kg", UnitDimension.MASS, "kg", 1.0),
    "g": UnitSpec("g", UnitDimension.MASS, "kg", 1.0e-3),
    "tonne": UnitSpec("tonne", UnitDimension.MASS, "kg", 1.0e3),
    "lbm": UnitSpec("lbm", UnitDimension.MASS, "kg", 0.45359237),

    # Time [canonical: s]
    "s": UnitSpec("s", UnitDimension.TIME, "s", 1.0),
    "ms": UnitSpec("ms", UnitDimension.TIME, "s", 1.0e-3),
    "min": UnitSpec("min", UnitDimension.TIME, "s", 60.0),
    "hr": UnitSpec("hr", UnitDimension.TIME, "s", 3600.0),

    # Area [canonical: m²]
    "m^2": UnitSpec("m^2", UnitDimension.AREA, "m^2", 1.0),
    "m²": UnitSpec("m²", UnitDimension.AREA, "m^2", 1.0),
    "cm^2": UnitSpec("cm^2", UnitDimension.AREA, "m^2", 1.0e-4),
    "cm²": UnitSpec("cm²", UnitDimension.AREA, "m^2", 1.0e-4),
    "mm^2": UnitSpec("mm^2", UnitDimension.AREA, "m^2", 1.0e-6),
    "mm²": UnitSpec("mm²", UnitDimension.AREA, "m^2", 1.0e-6),
    "in^2": UnitSpec("in^2", UnitDimension.AREA, "m^2", 0.00064516),

    # Volume [canonical: m³]
    "m^3": UnitSpec("m^3", UnitDimension.VOLUME, "m^3", 1.0),
    "m³": UnitSpec("m³", UnitDimension.VOLUME, "m^3", 1.0),
    "L": UnitSpec("L", UnitDimension.VOLUME, "m^3", 1.0e-3),
    "liter": UnitSpec("liter", UnitDimension.VOLUME, "m^3", 1.0e-3),
    "mL": UnitSpec("mL", UnitDimension.VOLUME, "m^3", 1.0e-6),
    "cm^3": UnitSpec("cm^3", UnitDimension.VOLUME, "m^3", 1.0e-6),

    # Heat Flux [canonical: W/m²]
    "W/m^2": UnitSpec("W/m^2", UnitDimension.HEAT_FLUX, "W/m^2", 1.0),
    "W/m²": UnitSpec("W/m²", UnitDimension.HEAT_FLUX, "W/m^2", 1.0),
    "kW/m^2": UnitSpec("kW/m^2", UnitDimension.HEAT_FLUX, "W/m^2", 1.0e3),
    "kW/m²": UnitSpec("kW/m²", UnitDimension.HEAT_FLUX, "W/m^2", 1.0e3),
    "MW/m^2": UnitSpec("MW/m^2", UnitDimension.HEAT_FLUX, "W/m^2", 1.0e6),
    "MW/m²": UnitSpec("MW/m²", UnitDimension.HEAT_FLUX, "W/m^2", 1.0e6),
    "Btu/(s-in^2)": UnitSpec("Btu/(s-in^2)", UnitDimension.HEAT_FLUX, "W/m^2", 1634246.0),

    # Heat Transfer Coefficient [canonical: W/(m²-K)]
    "W/(m^2-K)": UnitSpec("W/(m^2-K)", UnitDimension.HEAT_TRANSFER_COEFF, "W/(m^2-K)", 1.0),
    "W/(m²-K)": UnitSpec("W/(m²-K)", UnitDimension.HEAT_TRANSFER_COEFF, "W/(m^2-K)", 1.0),
    "kW/(m^2-K)": UnitSpec("kW/(m^2-K)", UnitDimension.HEAT_TRANSFER_COEFF, "W/(m^2-K)", 1.0e3),
    "kW/(m²-K)": UnitSpec("kW/(m²-K)", UnitDimension.HEAT_TRANSFER_COEFF, "W/(m^2-K)", 1.0e3),

    # Power [canonical: W]
    "W": UnitSpec("W", UnitDimension.POWER, "W", 1.0),
    "kW": UnitSpec("kW", UnitDimension.POWER, "W", 1.0e3),
    "MW": UnitSpec("MW", UnitDimension.POWER, "W", 1.0e6),
    "hp": UnitSpec("hp", UnitDimension.POWER, "W", 745.69987),

    # Energy [canonical: J]
    "J": UnitSpec("J", UnitDimension.ENERGY, "J", 1.0),
    "kJ": UnitSpec("kJ", UnitDimension.ENERGY, "J", 1.0e3),
    "MJ": UnitSpec("MJ", UnitDimension.ENERGY, "J", 1.0e6),
    "kWh": UnitSpec("kWh", UnitDimension.ENERGY, "J", 3.6e6),

    # Density [canonical: kg/m³]
    "kg/m^3": UnitSpec("kg/m^3", UnitDimension.DENSITY, "kg/m^3", 1.0),
    "kg/m³": UnitSpec("kg/m³", UnitDimension.DENSITY, "kg/m^3", 1.0),
    "g/cm^3": UnitSpec("g/cm^3", UnitDimension.DENSITY, "kg/m^3", 1.0e3),

    # Thermal Conductivity [canonical: W/(m-K)]
    "W/(m-K)": UnitSpec("W/(m-K)", UnitDimension.THERMAL_CONDUCTIVITY, "W/(m-K)", 1.0),
    "kW/(m-K)": UnitSpec("kW/(m-K)", UnitDimension.THERMAL_CONDUCTIVITY, "W/(m-K)", 1.0e3),

    # Angle [canonical: rad]
    "rad": UnitSpec("rad", UnitDimension.ANGLE, "rad", 1.0),
    "deg": UnitSpec("deg", UnitDimension.ANGLE, "rad", math.pi / 180.0),
    "°": UnitSpec("°", UnitDimension.ANGLE, "rad", math.pi / 180.0),

    # Frequency [canonical: Hz]
    "Hz": UnitSpec("Hz", UnitDimension.FREQUENCY, "Hz", 1.0),
    "kHz": UnitSpec("kHz", UnitDimension.FREQUENCY, "Hz", 1.0e3),

    # Dimensionless
    "-": UnitSpec("-", UnitDimension.DIMENSIONLESS, "-", 1.0),
    "": UnitSpec("", UnitDimension.DIMENSIONLESS, "", 1.0),
    "ratio": UnitSpec("ratio", UnitDimension.DIMENSIONLESS, "ratio", 1.0),
    "%": UnitSpec("%", UnitDimension.DIMENSIONLESS, "ratio", 0.01),
}


class UnitSafety:
    """Core dimensional safety validation and conversion engine."""

    @staticmethod
    def get_spec(symbol: str) -> UnitSpec:
        norm = symbol.strip()
        if norm not in _REGISTRY:
            raise UnknownUnitError(f"Unit symbol '{symbol}' is not registered in the Navronis unit system.")
        return _REGISTRY[norm]

    @staticmethod
    def check_compatibility(unit_a: str, unit_b: str) -> None:
        """Verifies that two unit symbols share identical physical dimensions."""
        spec_a = UnitSafety.get_spec(unit_a)
        spec_b = UnitSafety.get_spec(unit_b)
        if spec_a.dimension != spec_b.dimension:
            raise UnitDimensionError(
                f"Dimensional mismatch: Cannot convert '{unit_a}' ({spec_a.dimension.value}) "
                f"to '{unit_b}' ({spec_b.dimension.value})."
            )

    @staticmethod
    def to_canonical(value: float, from_unit: str) -> Tuple[float, str]:
        """Converts an engineering value to canonical SI."""
        spec = UnitSafety.get_spec(from_unit)
        canonical_val = (value + spec.offset) * spec.factor
        return canonical_val, spec.canonical_symbol

    @staticmethod
    def from_canonical(canonical_value: float, target_unit: str) -> float:
        """Converts an engineering value from canonical SI to user-requested target unit."""
        spec = UnitSafety.get_spec(target_unit)
        return (canonical_value / spec.factor) - spec.offset

    @classmethod
    def convert(cls, value: float, from_unit: str, to_unit: str) -> float:
        """Direct dimensional conversion with mismatch protection."""
        cls.check_compatibility(from_unit, to_unit)
        canonical_val, _ = cls.to_canonical(value, from_unit)
        return cls.from_canonical(canonical_val, to_unit)
