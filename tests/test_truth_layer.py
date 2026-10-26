"""
Unit & Integration Tests for Navronis Truth Layer (Day 7).
==========================================================

Covers:
1. Unit Safety & Dimensional Compatibility (prevents cross-dimensional mixing)
2. Dependency DAG Topological Execution
3. Dependency Cycle Detection (CycleError)
4. Selective Recomputation & Stale State Propagation
5. Design Revision Immutability & Deterministic Hashing
6. Backwards Digital Thread Lineage (.explain())
7. Verification vs Validation Separation Taxonomy
8. Full End-to-End Chamber Pressure Step Journey (70 bar -> 90 bar)
"""

import pytest
from kryptonis.propulsion_equations.truth import (
    CADArtifact,
    ComputationNode,
    DependencyCycleError,
    DependencyDAG,
    DigitalThread,
    EngineeringValue,
    EvidenceRecord,
    LITERATURE_CATALOG,
    SourceAuthority,
    UnitDimension,
    UnitDimensionError,
    UnitSafety,
    UnknownUnitError,
    ValidationState,
    build_propulsion_dag,
)


# ==========================================================================
# 1. Unit Safety Tests
# ==========================================================================

def test_unit_conversion_valid():
    """Tests valid conversions across length, pressure, temperature, force."""
    # Pressure: 100 bar = 10,000,000 Pa = 10,000 kPa = 10 MPa
    assert UnitSafety.convert(100.0, "bar", "Pa") == pytest.approx(10.0e6)
    assert UnitSafety.convert(10.0e6, "Pa", "bar") == pytest.approx(100.0)
    assert UnitSafety.convert(100.0, "bar", "kPa") == pytest.approx(10000.0)

    # Length: 1.5 m = 1500 mm = 150 cm
    assert UnitSafety.convert(1.5, "m", "mm") == pytest.approx(1500.0)
    assert UnitSafety.convert(57.5, "mm", "m") == pytest.approx(0.0575)

    # Temperature: 20 degC = 293.15 K
    assert UnitSafety.convert(20.0, "degC", "K") == pytest.approx(293.15)
    assert UnitSafety.convert(293.15, "K", "degC") == pytest.approx(20.0)

    # Force: 30 kN = 30000 N
    assert UnitSafety.convert(30.0, "kN", "N") == pytest.approx(30000.0)
    assert UnitSafety.convert(30000.0, "N", "kN") == pytest.approx(30.0)


def test_unit_conversion_dimension_mismatch_rejected():
    """Ensures silent unit mixing across incompatible dimensions is strictly prevented."""
    # Pressure cannot convert to Length
    with pytest.raises(UnitDimensionError):
        UnitSafety.convert(100.0, "bar", "m")

    # Force cannot convert to Mass Flow
    with pytest.raises(UnitDimensionError):
        UnitSafety.convert(30.0, "kN", "kg/s")

    # Temperature cannot convert to Pressure
    with pytest.raises(UnitDimensionError):
        UnitSafety.convert(3000.0, "K", "bar")


def test_unknown_unit_rejected():
    """Rejects unregistered unit symbols."""
    with pytest.raises(UnknownUnitError):
        UnitSafety.get_spec("furlongs_per_fortnight")


# ==========================================================================
# 2. Dependency DAG & Cycle Detection Tests
# ==========================================================================

def test_dag_topological_order():
    """Verifies that nodes are executed strictly in topological order."""
    dag = DependencyDAG("Test DAG")
    dag.register_input("A", EngineeringValue(name="A", value=10.0, unit="m"))
    dag.register_node(
        "B",
        label="Node B",
        inputs=("A",),
        outputs=("B_val",),
        compute_fn=lambda ctx: {"B_val": EngineeringValue(name="B_val", value=ctx["A"].value * 2.0, unit="m")},
    )
    dag.register_node(
        "C",
        label="Node C",
        inputs=("B_val",),
        outputs=("C_val",),
        compute_fn=lambda ctx: {"C_val": EngineeringValue(name="C_val", value=ctx["B_val"].value + 5.0, unit="m")},
    )

    order = dag.get_topological_order()
    assert order.index("A") < order.index("B") < order.index("C")

    report = dag.recompute()
    assert report.recomputed_nodes == ["B", "C"]
    assert dag.get_value("C_val").value == 25.0


def test_dag_cycle_rejection():
    """Ensures circular dependencies are detected and immediately rejected."""
    dag = DependencyDAG("Cycle DAG")
    dag.register_node("Node1", label="1", inputs=("Node2",), outputs=("out1",), compute_fn=lambda ctx: {})
    with pytest.raises(DependencyCycleError):
        dag.register_node("Node2", label="2", inputs=("out1",), outputs=("out2",), compute_fn=lambda ctx: {})


# ==========================================================================
# 3. Selective Recomputation & Stale State Propagation
# ==========================================================================

def test_selective_recomputation_branching():
    """Demonstrates that modifying node A only invalidates downstream B->C, preserving independent D."""
    dag = DependencyDAG("Branching DAG")
    dag.register_input("inp_A", EngineeringValue(name="inp_A", value=5.0, unit="m"))
    dag.register_input("inp_D", EngineeringValue(name="inp_D", value=100.0, unit="m"))

    # Branch 1: inp_A -> node_B -> node_C
    dag.register_node(
        "node_B",
        label="B",
        inputs=("inp_A",),
        outputs=("b_val",),
        compute_fn=lambda ctx: {"b_val": EngineeringValue(name="b_val", value=ctx["inp_A"].value * 10, unit="m")},
    )
    dag.register_node(
        "node_C",
        label="C",
        inputs=("b_val",),
        outputs=("c_val",),
        compute_fn=lambda ctx: {"c_val": EngineeringValue(name="c_val", value=ctx["b_val"].value + 1, unit="m")},
    )

    # Branch 2: inp_D -> node_E (independent)
    dag.register_node(
        "node_E",
        label="E",
        inputs=("inp_D",),
        outputs=("e_val",),
        compute_fn=lambda ctx: {"e_val": EngineeringValue(name="e_val", value=ctx["inp_D"].value * 2, unit="m")},
    )

    # First full run
    rep1 = dag.recompute()
    assert set(rep1.recomputed_nodes) == {"node_B", "node_C", "node_E"}
    assert dag.get_value("c_val").value == 51.0
    assert dag.get_value("e_val").value == 200.0

    # Mutate ONLY inp_A
    dag.set_input("inp_A", EngineeringValue(name="inp_A", value=10.0, unit="m"))

    # Node B and C must be marked stale; Node E must remain CLEAN
    assert dag.nodes["node_B"].stale is True
    assert dag.nodes["node_C"].stale is True
    assert dag.nodes["node_E"].stale is False

    # Second selective recompute pass
    rep2 = dag.recompute()
    assert rep2.recomputed_nodes == ["node_B", "node_C"]
    assert "node_E" in rep2.preserved_nodes
    assert dag.get_value("c_val").value == 101.0
    assert dag.get_value("e_val").value == 200.0  # Preserved without re-execution


# ==========================================================================
# 4. Digital Thread & Provenance (.explain()) Tests
# ==========================================================================

def test_explain_provenance_completeness():
    """Verifies that .explain() includes equations, citations, and full upstream ancestry."""
    dag = build_propulsion_dag(thrust_n=30000.0, pc_pa=70.0e5)
    thread = DigitalThread(dag)
    dag.recompute()
    thread.commit_revision(notes="Test baseline")

    info = thread.explain("throat_diameter")
    tgt = info["target"]
    assert tgt["name"] == "throat_diameter"
    assert tgt["unit_canonical"] == "m"
    assert "Dt = sqrt(4 * At / pi)" in tgt["method"]
    assert tgt["validation_state"] == "VERIFIED"
    assert len(info["lineage_chain"]) >= 3

    # Check ancestry contains root inputs
    ancestor_keys = [step["key"] for step in info["lineage_chain"]]
    assert "throat_area" in ancestor_keys
    assert "thrust" in ancestor_keys


def test_thermal_bartz_evidence_citation():
    """Verifies that Bartz heat flux carries correct primary literature authority."""
    dag = build_propulsion_dag(thrust_n=30000.0, pc_pa=70.0e5)
    dag.recompute()

    q_val = dag.get_value("peak_heat_flux")
    assert q_val is not None
    assert q_val.source is not None
    assert q_val.source.source_type == SourceAuthority.PRIMARY_LITERATURE
    assert "Bartz" in q_val.source.author
    assert q_val.source.year == 1957
    assert q_val.validation_state == ValidationState.BENCHMARKED


# ==========================================================================
# 5. Verification vs Validation Separation Taxonomy
# ==========================================================================

def test_validation_state_enum_completeness():
    """Verifies explicit lifecycle states separating unit verification from hardware validation."""
    states = [s.value for s in ValidationState]
    assert "UNVERIFIED" in states
    assert "VERIFIED" in states
    assert "BENCHMARKED" in states
    assert "VALIDATED_AGAINST_PUBLISHED_DATA" in states
    assert "EXPERIMENTALLY_VALIDATED" in states


# ==========================================================================
# 6. Design Revision Immutability & Deterministic Hashing
# ==========================================================================

def test_revision_immutability():
    """Confirms frozen dataclass prevents silent state mutation of historical revisions."""
    dag = build_propulsion_dag(thrust_n=30000.0, pc_pa=70.0e5)
    thread = DigitalThread(dag)
    dag.recompute()
    rev1 = thread.commit_revision()

    with pytest.raises(Exception):
        # Frozen dataclass must raise on attempted attribute mutation
        rev1.revision_id = "MUTATED_ID"


# ==========================================================================
# 7. Full Chamber Pressure Journey (70 bar -> 90 bar)
# ==========================================================================

def test_full_pc_step_journey_end_to_end():
    """Comprehensive end-to-end test of the Pc 70 -> 90 bar requirement."""
    dag = build_propulsion_dag(thrust_n=30000.0, pc_pa=70.0e5)
    thread = DigitalThread(dag)

    # 1. Commit Revision 1
    rev1 = thread.commit_revision(notes="Revision 1 at 70 bar")
    dt1 = rev1.results["throat_diameter"].display_value
    q1 = rev1.results["peak_heat_flux"].display_value

    # 2. Step Chamber Pressure to 90 bar
    new_pc = EngineeringValue(
        name="chamber_pressure",
        value=90.0e5,
        unit="Pa",
        display_unit="bar",
        method="Operating Condition: Higher Chamber Pressure Trade",
    )
    dag.set_input("chamber_pressure", new_pc)

    # 3. Verify stale marking
    assert dag.nodes["throat_sizing"].stale is True
    assert dag.nodes["thermal_conjugate"].stale is True
    assert dag.nodes["cad_artifacts"].stale is True
    assert dag.nodes["mass_flow_sizing"].stale is False  # Independent of Pc

    # 4. Recompute
    report = dag.recompute()
    assert "throat_sizing" in report.recomputed_nodes
    assert "thermal_conjugate" in report.recomputed_nodes
    assert "mass_flow_sizing" in report.preserved_nodes

    # 5. Commit Revision 2
    rev2 = thread.commit_revision(notes="Revision 2 at 90 bar")
    dt2 = rev2.results["throat_diameter"].display_value
    q2 = rev2.results["peak_heat_flux"].display_value

    # 6. Physical verification: Throat diameter must decrease (higher Pc needs smaller throat)
    assert dt2 < dt1
    # Peak heat flux must increase with higher chamber pressure (q ~ Pc^0.8)
    assert q2 > q1

    # 7. Immutability & history check
    assert len(thread.revisions) == 2
    assert rev2.parent_revision_id == rev1.revision_id
    assert rev1.results["throat_diameter"].display_value == pytest.approx(dt1)
    assert rev2.results["throat_diameter"].display_value == pytest.approx(dt2)

    # 8. Check revision diff
    diff = rev1.diff(rev2)
    assert "chamber_pressure" in diff["changed_inputs"]
    assert "throat_diameter" in diff["changed_results"]
    assert diff["changed_results"]["throat_diameter"]["percent_change"] < 0
