"""
Unit and verification tests for Day 6 Flight Engine Benchmark Decks.
====================================================================
Tests reference database lookups, multi-chamber scaling, vacuum-only handling,
and literature verification benchmarks against NASA, AIAA, and manufacturer test-stand data.
"""

from __future__ import annotations

import json
import pytest

from kryptonis.propulsion_equations.engine_deck import (
    ENGINE_DECKS,
    LIST_ENGINES,
    EngineBenchmark,
    EngineReferenceDeck,
    benchmark_all_engines,
    get_engine_reference,
)


class TestEngineDeckDatabase:
    """Verifies flight engine database integrity and retrieval."""

    def test_all_seven_engines_present(self) -> None:
        expected = {"merlin1d", "raptor2", "rs25", "rd180", "rl10", "rutherford", "lmde"}
        assert expected.issubset(set(LIST_ENGINES))
        assert len(ENGINE_DECKS) >= 7

    def test_alias_resolution(self) -> None:
        assert get_engine_reference("merlin1d").name == "SpaceX Merlin 1D"
        assert get_engine_reference("Merlin-1D").alias == "merlin1d"
        assert get_engine_reference("RS-25").alias == "rs25"
        assert get_engine_reference("rd-180").alias == "rd180"
        assert get_engine_reference("RL10").alias == "rl10"
        assert get_engine_reference("rutherford").alias == "rutherford"
        assert get_engine_reference("LMDE").alias == "lmde"

    def test_unknown_engine_raises_keyerror(self) -> None:
        with pytest.raises(KeyError, match="not found"):
            get_engine_reference("nonexistent_engine_xyz")

    def test_deck_physical_sanity(self) -> None:
        for key, deck in ENGINE_DECKS.items():
            assert isinstance(deck, EngineReferenceDeck)
            assert deck.chamber_pressure_bar > 0.0
            assert deck.thrust_vac_kN > 0.0
            assert deck.isp_vac_s > 200.0
            assert deck.throat_diameter_mm > 0.0
            assert deck.mass_flow_total_kg_s > 0.0
            assert deck.number_of_chambers >= 1
            assert len(deck.literature_source) > 5


class TestEngineBenchmarkVerification:
    """Runs high-fidelity verification benchmarks for each flight engine."""

    @pytest.mark.parametrize("engine_key", LIST_ENGINES)
    def test_individual_engine_benchmark_passes(self, engine_key: str) -> None:
        bm = EngineBenchmark(engine_key, error_tolerance_percent=15.0)
        res = bm.run()
        assert res.passed, (
            f"Engine {engine_key} failed benchmark: max error {res.max_error_percent:.2f}% > 15%\n"
            f"{res.summary_table()}"
        )
        assert res.mean_absolute_error_percent < 10.0

    def test_rd180_dual_chamber_throat_scaling(self) -> None:
        bm = EngineBenchmark("rd180")
        res = bm.run()
        # Single throat diameter should match ~236 mm, not single-chamber 336 mm
        throat_metric = next(m for m in res.metrics if m.parameter == "Throat Diameter")
        assert throat_metric.percent_error < 2.0
        assert throat_metric.status == "PASS"

    def test_vacuum_only_engines_omit_sea_level_isp(self) -> None:
        for vac_eng in ["rl10", "lmde"]:
            bm = EngineBenchmark(vac_eng)
            res = bm.run()
            parameters = [m.parameter for m in res.metrics]
            assert "Sea Level Isp" not in parameters
            assert res.deck.vacuum_only is True

    def test_benchmark_all_engines_aggregate(self) -> None:
        results = benchmark_all_engines(error_tolerance_percent=15.0)
        assert len(results) == len(LIST_ENGINES)
        for name, res in results.items():
            assert res.passed is True
            assert res.mean_absolute_error_percent < 10.0

    def test_serialization_and_reporting(self) -> None:
        bm = EngineBenchmark("merlin1d")
        res = bm.run()
        table = res.summary_table()
        assert "SPACEX MERLIN 1D" in table
        assert "Mean Absolute Error" in table

        d = res.to_dict()
        assert d["passed"] is True
        assert len(d["metrics"]) == 5

        js = res.to_json()
        parsed = json.loads(js)
        assert parsed["engine_name"] == "SpaceX Merlin 1D"
