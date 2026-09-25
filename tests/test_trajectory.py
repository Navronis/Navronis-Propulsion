"""
Unit and verification test suite for launch vehicle ascent trajectory (Day 5).
=============================================================================

Verifies:
- Transonic aerodynamic drag coefficient CD(M) curve
- Gravity turn powered ascent flight mechanics
- Dynamic pressure Max Q tracking in troposphere/stratosphere
- Loss bookkeeping: Gravity losses, Aerodynamic drag losses
- Low Earth Orbit (LEO) orbital target velocity and deficit
- Input validation and exception handling
"""

import math
import pytest

from kryptonis.propulsion_equations.trajectory import (
    transonic_drag_coefficient,
    TrajectorySimulation,
    TrajectoryResult,
)


class TestAerodynamicDrag:
    """Tests transonic drag rise and supersonic decay."""

    def test_transonic_drag_profile(self):
        cd_sub = transonic_drag_coefficient(0.4)
        assert cd_sub == pytest.approx(0.28, rel=1e-2)

        cd_transonic_peak = transonic_drag_coefficient(1.05)
        # Peak around Mach 1.05 should be noticeably higher than subsonic
        assert cd_transonic_peak > cd_sub
        assert cd_transonic_peak >= 0.50

        cd_supersonic = transonic_drag_coefficient(3.0)
        # Supersonic drag decays back toward lower values
        assert cd_supersonic < cd_transonic_peak


class TestAscentTrajectorySimulation:
    """Tests powered ascent trajectory mechanics."""

    def test_nominal_ascent_simulation(self):
        sim = TrajectorySimulation(
            m0_kg=2000.0,
            m_dry_kg=300.0,
            thrust_sl_N=30000.0,
            thrust_vac_N=36000.0,
            isp_sl_s=250.0,
            isp_vac_s=315.0,
            burn_time_s=45.0,
            vehicle_diameter_m=0.6,
        )
        res = sim.run()

        assert isinstance(res, TrajectoryResult)
        assert res.burnout_altitude_km > 5.0
        assert res.burnout_velocity_m_s > 300.0
        assert res.burnout_mach > 1.0
        assert res.trajectory_points_count > 50

        # Loss bookkeeping check
        assert res.delta_v_gravity_loss_m_s > 100.0
        assert res.delta_v_drag_loss_m_s > 10.0
        assert res.delta_v_delivered_m_s > 0.0

        # Max Q dynamic pressure check
        assert res.max_q_kPa > 10.0
        assert 5.0 <= res.max_q_altitude_km <= 20.0

    def test_target_orbital_velocity_and_deficit(self):
        sim = TrajectorySimulation(
            m0_kg=1500.0,
            m_dry_kg=200.0,
            thrust_sl_N=25000.0,
            thrust_vac_N=32000.0,
            isp_sl_s=245.0,
            isp_vac_s=318.0,
            burn_time_s=40.0,
            target_orbit_altitude_km=200.0,
        )
        res = sim.run()
        # Circular orbit velocity at 200 km is ~7784 m/s
        assert 7700.0 < res.orbital_velocity_target_m_s < 7900.0
        assert res.orbital_velocity_deficit_m_s >= 0.0

    def test_trajectory_explain_provenance(self):
        sim = TrajectorySimulation(
            m0_kg=1000.0,
            m_dry_kg=200.0,
            thrust_sl_N=15000.0,
            thrust_vac_N=18000.0,
            isp_sl_s=240.0,
            isp_vac_s=300.0,
            burn_time_s=30.0,
        )
        res = sim.run()
        assert "Drag" in res.explain("max_q")
        assert "Gravity Turn" in res.explain("gravity_turn")
        assert "Orbital" in res.explain("orbital_velocity")

    def test_invalid_trajectory_inputs_rejected(self):
        with pytest.raises(ValueError):
            # m0 <= m_dry
            TrajectorySimulation(
                m0_kg=500.0,
                m_dry_kg=600.0,
                thrust_sl_N=10000.0,
                thrust_vac_N=12000.0,
                isp_sl_s=240.0,
                isp_vac_s=300.0,
                burn_time_s=30.0,
            )
        with pytest.raises(ValueError):
            # Negative burn time
            TrajectorySimulation(
                m0_kg=1000.0,
                m_dry_kg=200.0,
                thrust_sl_N=10000.0,
                thrust_vac_N=12000.0,
                isp_sl_s=240.0,
                isp_vac_s=300.0,
                burn_time_s=-10.0,
            )
