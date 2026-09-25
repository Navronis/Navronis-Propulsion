"""
Unit and verification test suite for liquid rocket engine cycles & turbopump sizing (Day 5).
========================================================================================

Verifies:
- Pump hydraulic head, power, and efficiency scaling (Huzel-Huang 1992)
- Specific speed (Ns) and suction specific speed (Nss) impeller classification
- NPSH required and cavitation avoidance (NASA SP-8110, Sutton-Biblarz 2016)
- Turbine isentropic expansion and gas generator power balance closure
- Closed Expander cycle heat-absorption pinch-point limits
- Oxidizer-rich and fuel-rich staged combustion cycle pressures
- Full-Flow Staged Combustion (FFSC) dual-preburner power closure
- Input validation and exception rejection
"""

import math
import pytest

from kryptonis.propulsion_equations.cycle import (
    pump_head,
    pump_power,
    pump_specific_speed,
    pump_suction_specific_speed,
    pump_npsh_required,
    pump_impeller_tip_speed,
    turbine_power,
    size_pressure_fed_cycle,
    size_gas_generator_cycle,
    size_expander_cycle,
    size_staged_combustion_cycle,
    size_full_flow_staged_combustion_cycle,
    EngineCycleDesign,
    EngineCycleResult,
)


class TestPumpHydraulicsAndMechanics:
    """Tests fundamental turbopump hydraulic equations."""

    def test_pump_head_and_power_nominal(self):
        # 10 MPa (100 bar) LOX pump (density 1141 kg/m3)
        delta_p = 10.0e6
        rho = 1141.0
        m_dot = 20.0  # kg/s

        h = pump_head(delta_p, rho)
        assert 880.0 < h < 910.0  # H ~ 893.7 m

        pwr = pump_power(m_dot, delta_p, rho, efficiency=0.75)
        # Power = (20 * 10e6) / (1141 * 0.75) = 233,713 W ~ 233.7 kW
        assert 220.0e3 < pwr < 250.0e3

    def test_pump_specific_speed_classification(self):
        # High head, moderate flow -> radial centrifugal
        ns_rad = pump_specific_speed(rpm=30000.0, flow_m3_s=0.015, head_m=1200.0)
        assert ns_rad["impeller_type"] == "radial_centrifugal"
        assert ns_rad["Ns_US"] < 1500.0

        # Very high flow, low head -> axial flow
        ns_ax = pump_specific_speed(rpm=12000.0, flow_m3_s=0.50, head_m=80.0)
        assert ns_ax["impeller_type"] == "axial_flow"
        assert ns_ax["Ns_US"] >= 4500.0

    def test_pump_suction_specific_speed_and_npsh(self):
        rpm = 25000.0
        flow_m3_s = 0.02
        target_nss = 25000.0  # With high-performance inducer

        npsh_r = pump_npsh_required(rpm, flow_m3_s, target_nss)
        assert 5.0 < npsh_r < 30.0

        # Back-calculate Nss to ensure inversion identity
        nss_calc = pump_suction_specific_speed(rpm, flow_m3_s, npsh_r)
        assert nss_calc == pytest.approx(target_nss, rel=1e-3)

    def test_impeller_tip_speed(self):
        # Head of 1500 m
        u_tip = pump_impeller_tip_speed(head_m=1500.0, head_coefficient_psi=0.55)
        # u = sqrt(9.80665 * 1500 / 0.55) ~ 163.5 m/s
        assert 150.0 < u_tip < 180.0

    def test_invalid_pump_inputs_rejected(self):
        with pytest.raises(ValueError):
            pump_head(-5.0, 1000.0)
        with pytest.raises(ValueError):
            pump_power(10.0, 50e5, 1000.0, efficiency=1.5)
        with pytest.raises(ValueError):
            pump_specific_speed(0.0, 0.01, 100.0)


class TestTurbineMechanics:
    """Tests turbine isentropic expansion and power extraction."""

    def test_turbine_power_nominal(self):
        # 1.0 kg/s gas at 1000 K, cp = 2500 J/kg*K, PR = 16
        m_dot_t = 1.0
        cp = 2500.0
        t_in = 1000.0
        pr = 16.0
        gamma = 1.25
        pwr = turbine_power(m_dot_t, cp, t_in, pr, gamma, efficiency=0.70)
        # Expansion term = 1 - (1/16)^(0.20) = 1 - 0.5743 = 0.4256
        # dh = 2500 * 1000 * 0.4256 = 1,064,175 J/kg
        # Power = 1.0 * 1.064e6 * 0.70 = 744,922 W ~ 745 kW
        assert 700.0e3 < pwr < 780.0e3

    def test_invalid_turbine_inputs_rejected(self):
        with pytest.raises(ValueError):
            turbine_power(1.0, 2000.0, 800.0, pressure_ratio=0.8, gamma=1.2)
        with pytest.raises(ValueError):
            turbine_power(1.0, 2000.0, 800.0, pressure_ratio=10.0, gamma=0.9)


class TestCyclePowerBalances:
    """Tests power balance closure across the 5 canonical engine cycles."""

    def test_gas_generator_cycle_balance(self):
        res = size_gas_generator_cycle(
            p_chamber_Pa=60.0e5,
            m_dot_ox_kg_s=15.0,
            m_dot_fuel_kg_s=5.0,
            rho_ox_kg_m3=1141.0,
            rho_fuel_kg_m3=810.0,
            main_isp_vac_s=315.0,
        )
        assert res["power_balance_closed"] is True
        assert res["total_pump_power_kW"] > 0
        # Gas generator mass flow should typically be 1.0% to 3.5% of engine flow
        assert 0.010 < res["alpha_gas_generator_fraction"] < 0.035
        # Net Isp reflects exhaust dumping loss
        assert res["net_isp_vac_s"] < res["main_isp_vac_s"]
        assert 0.5 < res["isp_penalty_s"] < 10.0

    def test_expander_cycle_closed_heat_limit(self):
        # 40 bar LOX/CH4 expander
        res = size_expander_cycle(
            p_chamber_Pa=40.0e5,
            m_dot_ox_kg_s=6.0,
            m_dot_fuel_kg_s=2.0,
            rho_ox_kg_m3=1141.0,
            rho_fuel_kg_m3=422.0,
            main_isp_vac_s=330.0,
            coolant_cp_J_kgK=3500.0,
            delta_t_coolant_K=150.0,
        )
        assert res["cycle_feasible"] is True
        assert res["power_balance_margin"] >= 1.0
        # Zero dumping loss
        assert res["net_isp_vac_s"] == 330.0
        assert res["isp_penalty_s"] == 0.0

    def test_staged_combustion_ox_and_fuel_rich(self):
        # Oxidizer-rich staged combustion (RD-180 style)
        res_ox = size_staged_combustion_cycle(
            p_chamber_Pa=100.0e5,
            m_dot_ox_kg_s=30.0,
            m_dot_fuel_kg_s=11.5,
            rho_ox_kg_m3=1141.0,
            rho_fuel_kg_m3=810.0,
            main_isp_vac_s=338.0,
            staged_type="oxidizer_rich",
        )
        assert res_ox["preburner_pressure_bar"] > 100.0
        assert res_ox["cycle_feasible"] is True
        assert res_ox["net_isp_vac_s"] == 338.0

        # Fuel-rich staged combustion (RS-25 SSME style)
        res_f = size_staged_combustion_cycle(
            p_chamber_Pa=100.0e5,
            m_dot_ox_kg_s=30.0,
            m_dot_fuel_kg_s=5.0,
            rho_ox_kg_m3=1141.0,
            rho_fuel_kg_m3=71.0,
            main_isp_vac_s=452.0,
            staged_type="fuel_rich",
            preburner_t_inlet_K=850.0,
        )
        assert res_f["preburner_pressure_bar"] > 100.0
        assert res_f["cycle_feasible"] is True

    def test_full_flow_staged_combustion_raptor(self):
        # 150 bar Methalox FFSC
        res = size_full_flow_staged_combustion_cycle(
            p_chamber_Pa=150.0e5,
            m_dot_ox_kg_s=50.0,
            m_dot_fuel_kg_s=14.0,
            rho_ox_kg_m3=1141.0,
            rho_fuel_kg_m3=422.0,
            main_isp_vac_s=350.0,
        )
        assert res["ox_turbopump_margin"] >= 1.0
        assert res["fuel_turbopump_margin"] >= 1.0
        assert res["cycle_feasible"] is True
        assert res["gas_gas_injection"] is True

    def test_pressure_fed_cycle_and_pressurant_mass(self):
        res = size_pressure_fed_cycle(
            p_chamber_Pa=20.0e5,
            m_dot_ox_kg_s=4.0,
            m_dot_fuel_kg_s=2.0,
            rho_ox_kg_m3=1141.0,
            rho_fuel_kg_m3=800.0,
            burn_time_s=60.0,
            pressurant_gas="Helium",
        )
        assert res["p_tank_bar"] > 20.0
        assert res["pressurant_mass_kg"] > 0.0
        assert res["turbopump_required"] is False

    def test_engine_cycle_design_facade_and_explain(self):
        des = EngineCycleDesign(
            cycle_type="gas_generator",
            p_chamber_Pa=50e5,
            m_dot_ox_kg_s=6.46,
            m_dot_fuel_kg_s=2.15,
            rho_ox_kg_m3=1141.0,
            rho_fuel_kg_m3=422.0,
            main_isp_vac_s=320.0,
        )
        res = des.solve()
        assert isinstance(res, EngineCycleResult)
        assert res.cycle_type == "gas_generator"
        assert res.total_pump_power_kW > 0
        assert "Pump Hydraulics" in res.explain("pump_power")
        assert "Gas Generator" in res.explain("alpha_gas_generator")
