"""
Unit and physical verification tests for Day 6 Electric Motor Turbopump Cycle (Rachov et al. 2010).
==================================================================================================
Tests BLDC motor sizing, inverter losses, Li-ion battery pack energy requirements,
and zero-dump performance balance.
"""

from __future__ import annotations

import pytest

from kryptonis.propulsion_equations.cycle import (
    EngineCycleDesign,
    size_electric_pump_cycle,
)


class TestElectricPumpCycle:
    """Verifies battery-electric turbopump mechanics and mass scaling."""

    def test_nominal_electric_pump_sizing(self) -> None:
        # Typical small launch vehicle stage (e.g. Rutherford-class): 25 kN, 85 bar, LOX/RP-1
        p_ch = 85.0e5
        m_ox = 6.0
        m_fuel = 2.5
        rho_ox = 1141.0
        rho_fuel = 810.0
        isp_vac = 311.0

        res = size_electric_pump_cycle(
            p_chamber_Pa=p_ch,
            m_dot_ox_kg_s=m_ox,
            m_dot_fuel_kg_s=m_fuel,
            rho_ox_kg_m3=rho_ox,
            rho_fuel_kg_m3=rho_fuel,
            main_isp_vac_s=isp_vac,
            burn_time_s=150.0,
        )
        assert isinstance(res, dict)

        # Shaft power should be positive and in reasonable range (~50-250 kW)
        assert 50.0 <= res["total_pump_power_kW"] <= 250.0
        assert res["power_electrical_kW"] > res["total_pump_power_kW"]

        # Motor mass should reflect modern aerospace BLDC power density (~5.5 kW/kg)
        assert res["motors_mass_kg"] > 5.0

        # Battery pack mass should reflect Li-ion storage (~250 Wh/kg)
        assert res["battery_mass_kg"] > 10.0
        assert res["battery_energy_kWh"] > 0.0

        # Electric cycle has zero exhaust dump penalty
        assert pytest.approx(res["net_isp_vac_s"], rel=1e-4) == isp_vac
        assert res["isp_penalty_s"] == 0.0
        assert res["cycle_feasible"] is True

    def test_battery_mass_scales_linearly_with_burn_time(self) -> None:
        kwargs = dict(
            p_chamber_Pa=70.0e5,
            m_dot_ox_kg_s=5.0,
            m_dot_fuel_kg_s=2.0,
            rho_ox_kg_m3=1141.0,
            rho_fuel_kg_m3=810.0,
            main_isp_vac_s=310.0,
        )
        res_100s = size_electric_pump_cycle(**kwargs, burn_time_s=100.0)
        res_200s = size_electric_pump_cycle(**kwargs, burn_time_s=200.0)

        # Doubling burn time should double energy and battery mass
        assert pytest.approx(res_200s["battery_mass_kg"], rel=1e-2) == (
            res_100s["battery_mass_kg"] * 2.0
        )

    def test_higher_chamber_pressure_requires_more_electric_power(self) -> None:
        kwargs = dict(
            m_dot_ox_kg_s=5.0,
            m_dot_fuel_kg_s=2.0,
            rho_ox_kg_m3=1141.0,
            rho_fuel_kg_m3=810.0,
            main_isp_vac_s=310.0,
            burn_time_s=120.0,
        )
        res_50bar = size_electric_pump_cycle(p_chamber_Pa=50.0e5, **kwargs)
        res_100bar = size_electric_pump_cycle(p_chamber_Pa=100.0e5, **kwargs)

        assert res_100bar["total_pump_power_kW"] > res_50bar["total_pump_power_kW"]
        assert res_100bar["motors_mass_kg"] > res_50bar["motors_mass_kg"]

    def test_electric_cycle_facade_integration(self) -> None:
        designer = EngineCycleDesign(
            cycle_type="electric_pump",
            p_chamber_Pa=80.0e5,
            m_dot_ox_kg_s=6.0,
            m_dot_fuel_kg_s=2.5,
            rho_ox_kg_m3=1141.0,
            rho_fuel_kg_m3=810.0,
            main_isp_vac_s=315.0,
        )
        res = designer.solve()
        assert res.cycle_type == "electric_pump"
        assert res.cycle_feasible is True
        assert res.net_isp_vac_s == 315.0
        assert "battery_mass_kg" in res.details

    def test_invalid_electric_inputs_rejected(self) -> None:
        with pytest.raises(ValueError, match="strictly positive"):
            size_electric_pump_cycle(
                p_chamber_Pa=-50.0e5,
                m_dot_ox_kg_s=5.0,
                m_dot_fuel_kg_s=2.0,
                rho_ox_kg_m3=1141.0,
                rho_fuel_kg_m3=810.0,
                main_isp_vac_s=310.0,
            )
