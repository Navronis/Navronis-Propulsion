"""
Automated unit tests for Cantera Thermochemical Equilibrium Parity.
===================================================================
Verifies Navronis combustion dynamics constants against Gibbs free energy
equilibrium solved by Cantera across GRI-Mech 3.0 mechanisms.
"""

from __future__ import annotations

import pytest

from kryptonis.propulsion_equations.thermochem_cantera import (
    CANTERA_AVAILABLE,
    calculate_cantera_equilibrium,
    verify_thermochem_parity,
)


@pytest.mark.skipif(not CANTERA_AVAILABLE, reason="Cantera library not available")
class TestCanteraThermochemistryParity:
    """Verifies combustor thermodynamics against Cantera chemical kinetics."""

    def test_methalox_gri30_equilibrium_nominal(self) -> None:
        res = calculate_cantera_equilibrium("LOX/CH4", p_chamber_bar=70.0, mixture_ratio_of=3.5)
        assert 3500.0 < res.t_combustion_k < 3750.0
        assert 20.0 < res.mean_molecular_weight < 23.0
        assert 1.18 < res.gamma < 1.22
        assert 1750.0 < res.c_star_m_s < 1900.0
        assert "CO" in res.species_fractions
        assert "H2O" in res.species_fractions
        assert res.mechanism == "GRI-Mech 3.0 (gri30.yaml)"

    def test_hydrolox_equilibrium_nominal(self) -> None:
        res = calculate_cantera_equilibrium("LOX/LH2", p_chamber_bar=100.0, mixture_ratio_of=6.0)
        assert 3200.0 < res.t_combustion_k < 3700.0
        assert 13.0 < res.mean_molecular_weight < 17.0
        assert 1.18 < res.gamma < 1.26
        assert 2200.0 < res.c_star_m_s < 2500.0

    def test_parity_verification_lox_ch4(self) -> None:
        comp = verify_thermochem_parity("LOX/CH4", p_chamber_bar=70.0, mixture_ratio_of=3.5)
        assert comp.passed is True
        assert comp.cstar_error_pct < 2.0
        assert comp.gamma_error_pct < 2.0
        assert comp.mw_error_pct < 3.0

    def test_parity_verification_lox_lh2(self) -> None:
        comp = verify_thermochem_parity("LOX/LH2", p_chamber_bar=100.0, mixture_ratio_of=6.0)
        assert comp.passed is True
        assert comp.cstar_error_pct < 5.0
        assert comp.gamma_error_pct < 3.0

    def test_cantera_export_dict(self) -> None:
        res = calculate_cantera_equilibrium("LOX/CH4", p_chamber_bar=70.0)
        d = res.to_dict()
        assert d["propellant"] == "LOX/CH4"
        assert "major_species" in d
        assert len(d["major_species"]) >= 2
