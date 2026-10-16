"""
Unit and physical verification tests for Day 6 Throttling Dynamics & Acoustic Chugging (NASA SP-194).
==================================================================================================
Tests quadratic injector stiffness drop, flow separation shock migration, coolant bulk heating,
and multi-point sweep validation across deep throttling regimes.
"""

from __future__ import annotations

import json
import pytest

from kryptonis.propulsion_equations.throttle import (
    ThrottlingAnalysis,
    ThrottlePoint,
    ThrottleAnalysisResult,
)


class TestThrottlePhysics:
    """Verifies off-design throttle mechanics against primary literature."""

    def test_nominal_full_power_point(self) -> None:
        analyzer = ThrottlingAnalysis(
            engine_name="Test-Engine",
            thrust_nominal_N=30000.0,
            chamber_pressure_nominal_Pa=70.0e5,
            nominal_injector_dp_ratio=0.20,
        )
        pt = analyzer.evaluate_point(1.00)
        assert isinstance(pt, ThrottlePoint)
        assert pt.throttle_fraction == 1.00
        assert pytest.approx(pt.chamber_pressure_bar, rel=1e-3) == 70.0
        assert pytest.approx(pt.injector_stiffness_ratio, rel=1e-3) == 0.20
        assert pt.chugging_safe is True
        assert pt.nozzle_separated_at_sea_level is False

    def test_quadratic_injector_pressure_drop(self) -> None:
        """Delta P_inj drops as tau^2, so delta P_inj / Pc drops linearly as tau."""
        analyzer = ThrottlingAnalysis(
            thrust_nominal_N=50000.0,
            chamber_pressure_nominal_Pa=80.0e5,
            nominal_injector_dp_ratio=0.20,
        )
        pt_100 = analyzer.evaluate_point(1.00)
        pt_50 = analyzer.evaluate_point(0.50)

        # Delta P at 50% should be (0.5)^2 = 0.25 of 100% Delta P
        assert pytest.approx(pt_50.injector_dp_bar, rel=1e-3) == pt_100.injector_dp_bar * 0.25
        # Stiffness ratio (Delta P / Pc) at 50% should be 0.20 * 0.50 = 0.10 (10%)
        assert pytest.approx(pt_50.injector_stiffness_ratio, rel=1e-3) == 0.10

    def test_chugging_instability_trip_at_fifteen_percent(self) -> None:
        """NASA SP-194 requires Delta P_inj / Pc >= 0.15 for acoustic decouple."""
        analyzer = ThrottlingAnalysis(
            thrust_nominal_N=30000.0,
            chamber_pressure_nominal_Pa=70.0e5,
            nominal_injector_dp_ratio=0.20,
        )
        # At tau = 0.80 -> stiffness = 0.20 * 0.80 = 0.16 (> 0.15) -> SAFE
        pt_80 = analyzer.evaluate_point(0.80)
        assert pt_80.chugging_safe is True

        # At tau = 0.70 -> stiffness = 0.20 * 0.70 = 0.14 (< 0.15) -> UNSTABLE
        pt_70 = analyzer.evaluate_point(0.70)
        assert pt_70.chugging_safe is False
        assert any("Chugging" in w for w in pt_70.warnings)

    def test_sea_level_flow_separation_on_deep_throttle(self) -> None:
        """At lower chamber pressures, exit pressure drops below Summerfield criterion."""
        analyzer = ThrottlingAnalysis(
            thrust_nominal_N=30000.0,
            chamber_pressure_nominal_Pa=60.0e5,
            expansion_ratio=30.0,
        )
        res = analyzer.sweep(min_throttle=0.40, max_throttle=1.00, step=0.10)
        # At 40% throttle, Pc = 24 bar, exit pressure collapses and triggers separation
        pt_40 = res.points[0]
        assert pt_40.nozzle_separated_at_sea_level is True
        assert pt_40.separation_area_ratio is not None
        assert pt_40.separation_area_ratio < 30.0

    def test_coolant_bulk_temperature_scaling(self) -> None:
        """Coolant bulk temperature rise scales inversely with coolant mass flow: delta T_bulk ~ tau^-0.2."""
        analyzer = ThrottlingAnalysis(
            nominal_coolant_dt_bulk_K=100.0,
        )
        pt_100 = analyzer.evaluate_point(1.00)
        pt_50 = analyzer.evaluate_point(0.50)
        assert pt_50.coolant_bulk_temp_rise_K > pt_100.coolant_bulk_temp_rise_K

    def test_multi_point_sweep_and_minimum_stable_floor(self) -> None:
        analyzer = ThrottlingAnalysis(
            thrust_nominal_N=30000.0,
            chamber_pressure_nominal_Pa=70.0e5,
            nominal_injector_dp_ratio=0.20,
        )
        res = analyzer.sweep(min_throttle=0.40, max_throttle=1.00, step=0.10)
        assert isinstance(res, ThrottleAnalysisResult)
        assert len(res.points) == 7
        assert res.min_safe_throttle_fraction >= 0.70
        assert "NAVRONIS ENGINE THROTTLING" in res.summary_table()

    def test_invalid_throttle_inputs_rejected(self) -> None:
        with pytest.raises(ValueError, match="strictly positive"):
            ThrottlingAnalysis(thrust_nominal_N=-1000.0)

        analyzer = ThrottlingAnalysis()
        with pytest.raises(ValueError, match="outside valid physics range"):
            analyzer.evaluate_point(0.10)  # below 0.20

        with pytest.raises(ValueError, match="outside valid physics range"):
            analyzer.evaluate_point(1.50)  # above 1.20
