"""
Evidence & Source Authority Classification (Day 7).
===================================================

Formalizes the provenance and authority behind every equation, constant,
and engineering assumption in the Navronis Propulsion toolkit.

Rule: A unit test passing verifies that the code matches the mathematics.
It does NOT validate that the model matches physical rocket hardware.
Verification and Validation must never be conflated.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, Optional


class SourceAuthority(str, Enum):
    """Hierarchy of epistemic authority for engineering information."""
    PRIMARY_LITERATURE = "PRIMARY_LITERATURE"
    MANUFACTURER_DATA = "MANUFACTURER_DATA"
    EXPERIMENTAL_DATA = "EXPERIMENTAL_DATA"
    DERIVED_PHYSICS = "DERIVED_PHYSICS"
    ENGINEERING_ASSUMPTION = "ENGINEERING_ASSUMPTION"
    USER_INPUT = "USER_INPUT"
    EMPIRICAL_CORRELATION = "EMPIRICAL_CORRELATION"
    NUMERICAL_RESULT = "NUMERICAL_RESULT"


class ValidationState(str, Enum):
    """Explicit lifecycle status distinguishing verification from validation."""
    #: Software/math implementation has not yet been audited against independent reference.
    UNVERIFIED = "UNVERIFIED"
    #: Software and algebra have been verified by unit tests, boundary tests, or dimensional checks.
    VERIFIED = "VERIFIED"
    #: Numerical code has been compared against an independent reference solver (e.g. CEA, RPA).
    BENCHMARKED = "BENCHMARKED"
    #: Predictions have been validated against published manufacturer/literature engine decks (e.g. Merlin 1D, Raptor).
    VALIDATED_AGAINST_PUBLISHED_DATA = "VALIDATED_AGAINST_PUBLISHED_DATA"
    #: Model predictions have been validated against direct physical test-stand or telemetry measurements.
    EXPERIMENTALLY_VALIDATED = "EXPERIMENTALLY_VALIDATED"


@dataclass(frozen=True)
class EvidenceRecord:
    """Detailed bibliographic and provenance record supporting an engineering model."""
    source_type: SourceAuthority
    publication: str
    author: str = ""
    year: Optional[int] = None
    equation: str = ""
    page_section: str = ""
    doi: str = ""
    url: str = ""
    notes: str = ""

    def citation(self) -> str:
        """Formatted academic or industrial engineering citation."""
        parts = []
        if self.author:
            parts.append(self.author)
        if self.year:
            parts.append(f"({self.year})")
        if self.publication:
            parts.append(f'"{self.publication}"')
        if self.page_section:
            parts.append(f"[{self.page_section}]")
        if self.equation:
            parts.append(f"Eq. {self.equation}")
        if self.doi:
            parts.append(f"DOI: {self.doi}")
        return " ".join(parts) if parts else "Unspecified Source"

    def as_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["source_type"] = self.source_type.value
        d["citation"] = self.citation()
        return d


# --------------------------------------------------------------------------
# Authoritative Literature Catalog
# --------------------------------------------------------------------------

LITERATURE_CATALOG: Dict[str, EvidenceRecord] = {
    "NASA_SP_125_ISENTROPIC": EvidenceRecord(
        source_type=SourceAuthority.PRIMARY_LITERATURE,
        author="Sutton, G. P. & Biblarz, O.",
        year=2016,
        publication="Rocket Propulsion Elements (9th Edition)",
        equation="Eq. 3-13 to 3-33",
        page_section="Chapter 3: Nozzle Theory and Thermodynamic Relations",
        url="https://www.wiley.com/en-us/Rocket+Propulsion+Elements%2C+9th+Edition-p-9781118753651",
        notes="Ideal 1D choked isentropic gas dynamics for supersonic convergent-divergent nozzles.",
    ),
    "BARTZ_1957": EvidenceRecord(
        source_type=SourceAuthority.PRIMARY_LITERATURE,
        author="Bartz, D. R.",
        year=1957,
        publication="A Simple Equation for Rapid Estimation of Rocket Nozzle Convective Heat Transfer Coefficients",
        equation="Eq. 1-8",
        page_section="Jet Propulsion, Vol. 27, No. 1, pp. 49-51",
        doi="10.2514/8.12572",
        notes="Modified Dittus-Boelter boundary layer heat flux correlation using boundary layer property correction.",
    ),
    "HUZEL_HUANG_1992": EvidenceRecord(
        source_type=SourceAuthority.PRIMARY_LITERATURE,
        author="Huzel, D. K. & Huang, D. H.",
        year=1992,
        publication="Modern Engineering for Design of Liquid-Propellant Rocket Engines",
        equation="Section 4.1 & 4.2",
        page_section="NASA SP-125 / AIAA Progress in Astronautics and Aeronautics, Vol. 147",
        url="https://ntrs.nasa.gov/citations/19710019929",
        notes="Standard empirical chamber sizing, contraction ratio curves, and injector pressure drop design guidelines.",
    ),
    "NASA_SP_194_ACOUSTICS": EvidenceRecord(
        source_type=SourceAuthority.PRIMARY_LITERATURE,
        author="Harrje, D. T. & Reardon, F. H.",
        year=1972,
        publication="Liquid Propellant Rocket Combustion Instability",
        equation="Section 2.3 Bessel Eigenvalues",
        page_section="NASA SP-194, pp. 35-78",
        url="https://ntrs.nasa.gov/citations/19730006798",
        notes="1T, 1R, 1L acoustic wave mode cavity eigenvalue formulation and low-frequency chugging limits.",
    ),
    "STARK_2005_SEPARATION": EvidenceRecord(
        source_type=SourceAuthority.PRIMARY_LITERATURE,
        author="Stark, R. & Wagner, B.",
        year=2005,
        publication="Experimental Study of Flow Separation in Truncated Ideal and Parabolic Rocket Nozzles",
        equation="Eq. 3-7",
        page_section="Journal of Propulsion and Power, Vol. 21, No. 4, pp. 700-705",
        doi="10.2514/1.12781",
        notes="Free shock separation (FSS) and restricted shock separation (RSS) criteria for high-expansion nozzles.",
    ),
    "GNIELINSKI_1976": EvidenceRecord(
        source_type=SourceAuthority.PRIMARY_LITERATURE,
        author="Gnielinski, V.",
        year=1976,
        publication="New Equations for Heat and Mass Transfer in Turbulent Pipe and Channel Flow",
        equation="Eq. 5-12",
        page_section="International Chemical Engineering, Vol. 16, pp. 359-368",
        notes="Transitional and turbulent internal channel convective heat transfer correlation.",
    ),
    "HAALAND_1983": EvidenceRecord(
        source_type=SourceAuthority.PRIMARY_LITERATURE,
        author="Haaland, S. E.",
        year=1983,
        publication="Simple and Explicit Formulas for the Friction Factor in Turbulent Pipe Flow",
        equation="Eq. 13",
        page_section="Journal of Fluids Engineering, Vol. 105, No. 1, pp. 89-90",
        doi="10.1115/1.3240948",
        notes="Explicit approximation to Colebrook-White hydraulic friction factor.",
    ),
    "NASA_SP_8107_TURBOPUMP": EvidenceRecord(
        source_type=SourceAuthority.PRIMARY_LITERATURE,
        author="NASA Lewis Research Center",
        year=1974,
        publication="Turbopump Systems for Liquid Rocket Engines",
        equation="NASA SP-8107, Design Criteria Monograph",
        page_section="pp. 12-45",
        url="https://ntrs.nasa.gov/citations/19750005703",
        notes="Turbomachinery stage power balance, specific speed Ns, impeller cavitation, and mass scaling.",
    ),
    "RAO_1958_BELL": EvidenceRecord(
        source_type=SourceAuthority.PRIMARY_LITERATURE,
        author="Rao, G. V. R.",
        year=1958,
        publication="Exhaust Nozzle Contour for Optimum Thrust",
        equation="Eq. 1-14",
        page_section="Jet Propulsion, Vol. 28, No. 6, pp. 377-382",
        doi="10.2514/8.7324",
        notes="Calculus of variations method of characteristics optimum 80% parabolic bell contour.",
    ),
    "US_STD_ATMOSPHERE_1976": EvidenceRecord(
        source_type=SourceAuthority.PRIMARY_LITERATURE,
        author="NOAA, NASA, USAF",
        year=1976,
        publication="U.S. Standard Atmosphere, 1976",
        equation="NOAA-S/T 76-1562",
        page_section="Barometric Formula Layer Inversion 0-86 km",
        url="https://ntrs.nasa.gov/citations/19770009539",
        notes="Standard pressure, temperature, and density lapse rates as a function of geopotential altitude.",
    ),
}
