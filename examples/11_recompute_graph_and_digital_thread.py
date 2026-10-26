"""
Example 11: Engineering Truth Layer, Digital Thread & Recompute Graph (Day 7).
==============================================================================

Demonstrates the core Day 7 capabilities:
1. Baseline Design State (Pc = 70 bar, Thrust = 30 kN) in Revision REV-001.
2. Backwards Lineage Provenance (.explain()) for Throat Diameter and Peak Heat Flux.
3. Upstream Design Modification: Pc changed from 70 bar -> 90 bar.
4. Selective Recomputation: Only affected downstream nodes (throat, chamber,
   nozzle aero, cooling, thermal, CAD) are recomputed; unaffected nodes
   (propellant chemistry, payload mass, burn time) are preserved.
5. Versioned Design Artifacts: Immutable REV-001 is preserved; REV-002 is created.
6. Design Revision Diff exposing every changed engineering quantity and percentage delta.
"""

from __future__ import annotations

import sys
import io

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from kryptonis.propulsion_equations.truth import (
    EngineeringValue,
    LITERATURE_CATALOG,
    ValidationState,
    build_propulsion_dag,
    DigitalThread,
    CADArtifact,
)


def run_day7_demonstration():
    print("=" * 84)
    print("  NAVRONIS PROPULSION DAY 7: ENGINEERING TRUTH LAYER & RECOMPUTE GRAPH")
    print("=" * 84)

    # 1. Build Master Propulsion DAG at Baseline (Pc = 70 bar = 7.0 MPa)
    print("\n[STEP 1] Initializing Master Propulsion Dependency DAG...")
    dag = build_propulsion_dag(
        thrust_n=30000.0,
        pc_pa=70.0e5,  # 70 bar
        mixture_ratio=3.5,
        expansion_ratio=30.0,
        l_star_m=1.0,
        wall_k=340.0,
    )
    thread = DigitalThread(dag)

    # Initial full solve
    report1 = dag.recompute(trigger_reason="Initial baseline synthesis (Pc = 70 bar)")
    print(report1.summary())

    # Associate versioned CAD artifacts with this state
    artifacts_rev1 = [
        CADArtifact(
            artifact_type="STEP",
            filename="chamber_30kn_rev1.step",
            byte_size=794100,
            sha256_checksum="a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90",
            design_revision_id="PENDING",
            created_at="2026-10-26T12:00:00Z",
            metadata={"cad_tool": "OpenCASCADE", "wall_type": "hollow_vessel"},
        ),
        CADArtifact(
            artifact_type="STL",
            filename="chamber_30kn_rev1.stl",
            byte_size=1795584,
            sha256_checksum="f9e8d7c6b5a403928170f9e8d7c6b5a403928170f9e8d7c6b5a403928170f9e8",
            design_revision_id="PENDING",
            created_at="2026-10-26T12:00:00Z",
            metadata={"polygons": 35910},
        ),
    ]

    rev1 = thread.commit_revision(
        artifacts=artifacts_rev1,
        notes="Nominal baseline 30 kN Methalox engine at Pc = 70 bar",
    )
    print(f"\n[OK] Committed Baseline Revision [{rev1.revision_id}] (Revision #{rev1.revision_number})")
    print(f"  Throat Diameter:  {rev1.results['throat_diameter'].display_value:.2f} mm")
    print(f"  Chamber Diameter: {rev1.results['chamber_diameter'].display_value:.2f} mm")
    print(f"  Delivered Thrust: {rev1.results['thrust_delivered'].display_value:.2f} kN")
    print(f"  Peak Heat Flux:   {rev1.results['peak_heat_flux'].display_value:.2f} MW/m²")
    print(f"  Hot Gas Wall T:   {rev1.results['hot_gas_wall_temp'].display_value:.1f} °C")
    print(f"  Cooling Drop:     {rev1.results['cooling_pressure_drop'].display_value:.2f} bar")

    # 2. Backwards Lineage Trace (.explain())
    print("\n" + "=" * 84)
    print("[STEP 2] DIGITAL THREAD BACKWARDS AUDIT TRAIL (.explain())")
    print("=" * 84)
    print(thread.explain_text("throat_diameter"))
    print("\n" + "-" * 84)
    print(thread.explain_text("peak_heat_flux"))

    # 3. Dynamic Upstream Design Modification: Pc: 70 bar -> 90 bar
    print("\n" + "=" * 84)
    print("[STEP 3] UPSTREAM DESIGN CHANGE: Chamber Pressure Pc: 70 bar -> 90 bar")
    print("=" * 84)

    new_pc = EngineeringValue(
        name="chamber_pressure",
        value=90.0e5,  # 90 bar = 9.0 MPa
        unit="Pa",
        display_unit="bar",
        method="Operating Condition: Higher Chamber Pressure Trade",
        source=LITERATURE_CATALOG["HUZEL_HUANG_1992"],
        description="Stagnation chamber pressure Pc stepped to 90 bar",
    )
    dag.set_input("chamber_pressure", new_pc, reason="Trade study: Pc stepped 70 bar -> 90 bar")

    print("\nGraph State Immediately After Upstream Input Modification:")
    print("---------------------------------------------------------")
    for k in dag.get_topological_order():
        node = dag.nodes[k]
        state_icon = "[STALE]" if node.stale else "[CLEAN]"
        reason_str = node.last_recompute_reason or "N/A"
        print(f"  {state_icon:7s} | Node: {k:<24} | Reason: {reason_str}")

    # 4. Trigger Selective Recomputation
    print("\n" + "=" * 84)
    print("[STEP 4] EXECUTING SELECTIVE RECOMPUTATION...")
    print("=" * 84)
    report2 = dag.recompute(trigger_reason="Trade Study: Pc 70 -> 90 bar")
    print(report2.summary())

    # Generate new versioned CAD artifacts for REV-002
    artifacts_rev2 = [
        CADArtifact(
            artifact_type="STEP",
            filename="chamber_30kn_rev2_90bar.step",
            byte_size=788200,
            sha256_checksum="11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff",
            design_revision_id="PENDING",
            created_at="2026-10-26T12:05:00Z",
            metadata={"cad_tool": "OpenCASCADE", "throat_diameter_mm": dag.get_value("throat_diameter").to("mm")},
        ),
    ]

    rev2 = thread.commit_revision(
        artifacts=artifacts_rev2,
        notes="High-pressure trade study variant (Pc = 90 bar)",
    )
    print(f"\n[OK] Committed New Revision [{rev2.revision_id}] (Revision #{rev2.revision_number}, Parent: {rev2.parent_revision_id})")

    # 5. Full Revision History & Parametric Diff
    print("\n" + "=" * 84)
    print("[STEP 5] DESIGN REVISION COMPARISON (REV-001 vs REV-002)")
    print("=" * 84)
    diff = rev1.diff(rev2)

    print("\nInputs Modified:")
    for inp_k, inp_d in diff["changed_inputs"].items():
        print(f"  * {inp_k:<22}: {inp_d['from']} -> {inp_d['to']}")

    print("\nDownstream Results Recomputed & Updated:")
    print(f"  {'PARAMETER':<26} | {'REV-001 (70 bar)':<18} | {'REV-002 (90 bar)':<18} | {'DELTA (%)':<10}")
    print("  " + "-" * 78)
    for res_k, res_d in sorted(diff["changed_results"].items()):
        pct = res_d.get("percent_change", 0.0)
        pct_str = f"{pct:+.2f}%" if pct is not None else "N/A"
        print(f"  {res_k:<26} | {res_d['from']:<18} | {res_d['to']:<18} | {pct_str}")

    # 6. Verify Revision Immutability
    print("\n" + "=" * 84)
    print("[STEP 6] VERIFYING REVISION IMMUTABILITY & AUDITABILITY")
    print("=" * 84)
    print(f"Total Revisions Stored in Digital Thread: {len(thread.revisions)}")
    print(f"Revision 1 Stored Throat Diameter:        {rev1.results['throat_diameter'].display_value:.2f} mm (UNCHANGED)")
    print(f"Revision 2 Stored Throat Diameter:        {rev2.results['throat_diameter'].display_value:.2f} mm (NEW STATE)")
    assert rev1.results["throat_diameter"].value != rev2.results["throat_diameter"].value, "Immutability failure!"
    print("[OK] Immutability Verified: Previous engineering history was fully preserved without silent overwriting.")
    print("=" * 84)


if __name__ == "__main__":
    run_day7_demonstration()
