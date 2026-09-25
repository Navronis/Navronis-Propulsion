"""
End-to-End integration test suite for the unified EngineSystem master architecture (Day 5).
========================================================================================

Verifies full synthesis across all five days:
- Combustor sizing (Day 1)
- Injector family sizing (Day 2)
- Regenerative cooling jacket (Day 3)
- Supersonic Rao bell nozzle (Day 4)
- Turbomachinery cycle & power balance (Day 5)
- Powered ascent trajectory simulation (Day 5)
"""

import pytest

from kryptonis.propulsion_equations.system import EngineSystem, EngineSystemResult


class TestEngineSystemEndToEnd:
    """Tests multi-subsystem engine synthesis."""

    def test_nominal_gas_generator_methalox(self):
        sys = EngineSystem(
            thrust_vac_N=30000.0,
            p_chamber_Pa=50.0e5,
            propellant="LOX/CH4",
            cycle="gas_generator",
            injector_family="bicentrifugal_swirl",
            cooling_type="regenerative",
            expansion_ratio=35.0,
            simulate_flight=True,
        )
        res = sys.solve()

        assert isinstance(res, EngineSystemResult)
        assert res.thrust_vac_kN > 25.0
        assert res.isp_vac_s > 300.0
        assert res.throat_diameter_mm > 0.0
        assert res.chamber_diameter_mm > res.throat_diameter_mm
        assert res.nozzle_exit_diameter_mm > res.throat_diameter_mm
        assert res.engine_dry_mass_kg > 20.0
        assert res.thrust_to_weight_vac > 15.0

        # Subsystems are populated
        assert res.combustor is not None
        assert res.nozzle is not None
        assert res.injector is not None
        assert res.cycle_balance is not None
        assert res.flight is not None
        assert res.cycle_balance["cycle_feasible"] is True

    def test_expander_cycle_engine_system(self):
        sys = EngineSystem(
            thrust_vac_N=20000.0,
            p_chamber_Pa=35.0e5,
            propellant="LOX/CH4",
            cycle="expander",
            injector_family="shear_coaxial",
            cooling_type="regenerative",
            expansion_ratio=40.0,
            simulate_flight=False,
        )
        res = sys.solve()
        assert res.cycle == "expander"
        assert res.cycle_balance["cycle_feasible"] is True
        assert res.flight is None

    def test_staged_combustion_engine_system(self):
        sys = EngineSystem(
            thrust_vac_N=60000.0,
            p_chamber_Pa=80.0e5,
            propellant="LOX/RP-1",
            cycle="staged_combustion_ox",
            injector_family="bicentrifugal_swirl",
            expansion_ratio=50.0,
            simulate_flight=True,
        )
        res = sys.solve()
        assert "staged_combustion" in res.cycle
        assert res.cycle_balance["details"]["preburner_pressure_bar"] > 80.0
        assert res.flight is not None

    def test_full_flow_staged_combustion_raptor_style(self):
        sys = EngineSystem(
            thrust_vac_N=100000.0,
            p_chamber_Pa=100.0e5,
            propellant="LOX/CH4",
            cycle="full_flow_staged",
            injector_family="bicentrifugal_swirl",
            expansion_ratio=45.0,
            simulate_flight=True,
        )
        res = sys.solve()
        assert res.cycle == "full_flow_staged"
        assert res.cycle_balance["cycle_feasible"] is True

    def test_summary_report_and_serialization(self):
        sys = EngineSystem(
            thrust_vac_N=30000.0,
            p_chamber_Pa=50.0e5,
            propellant="LOX/CH4",
            cycle="gas_generator",
            expansion_ratio=35.0,
            simulate_flight=True,
        )
        res = sys.solve()
        report = res.summary_report()
        assert "NAVRONIS PROPULSION ENGINE SPECIFICATION DATASHEET" in report
        assert "PERFORMANCE METRICS:" in report
        assert "TURBOMACHINERY & FEED SYSTEM BALANCE:" in report
        assert "ASCENT FLIGHT & MISSION TRAJECTORY:" in report

        # JSON roundtrip
        j_str = res.to_json()
        assert len(j_str) > 100
