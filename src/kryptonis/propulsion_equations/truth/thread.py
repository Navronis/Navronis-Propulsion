"""
Digital Thread, Versioned Design Revisions & Lineage Provenance (Day 7).
========================================================================

Maintains immutable design history, deterministic revision IDs, and
the complete `.explain()` backwards lineage trace from any engineering number
all the way back to root requirements, literature citations, and equations.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from kryptonis.propulsion_equations.truth.dag import DependencyDAG, RecomputeReport
from kryptonis.propulsion_equations.truth.ir import CADArtifact, EngineeringValue


def _compute_revision_id(inputs: Dict[str, EngineeringValue], parent_id: Optional[str] = None) -> str:
    """Computes a deterministic cryptographic hash for an exact design state."""
    serialized_inputs = []
    for k in sorted(inputs.keys()):
        val = inputs[k]
        serialized_inputs.append(f"{k}={val.value}:{val.unit}")
    payload = ";".join(serialized_inputs)
    if parent_id:
        payload += f";parent={parent_id}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class DesignRevision:
    """An immutable, auditable snapshot of a rocket engine design state."""
    revision_id: str
    revision_number: int
    parent_revision_id: Optional[str]
    timestamp: str
    inputs: Dict[str, EngineeringValue]
    results: Dict[str, EngineeringValue]
    artifacts: Dict[str, CADArtifact]
    recompute_report: Optional[RecomputeReport] = None
    notes: str = ""

    def diff(self, other: DesignRevision) -> Dict[str, Any]:
        """Calculates precise parameter differences between two design revisions."""
        changed_inputs = {}
        all_inp_keys = set(self.inputs.keys()) | set(other.inputs.keys())
        for k in all_inp_keys:
            v_self = self.inputs.get(k)
            v_other = other.inputs.get(k)
            if v_self is None or v_other is None or abs(v_self.value - v_other.value) > 1e-9:
                changed_inputs[k] = {
                    "from": str(v_self) if v_self else "None",
                    "to": str(v_other) if v_other else "None",
                    "delta": (v_other.value - v_self.value) if (v_self and v_other) else None,
                }

        changed_results = {}
        all_res_keys = set(self.results.keys()) | set(other.results.keys())
        for k in all_res_keys:
            r_self = self.results.get(k)
            r_other = other.results.get(k)
            if r_self is None or r_other is None or abs(r_self.value - r_other.value) > 1e-9:
                pct = ((r_other.value - r_self.value) / r_self.value * 100.0) if (r_self and r_other and r_self.value != 0.0) else 0.0
                changed_results[k] = {
                    "from": str(r_self) if r_self else "None",
                    "to": str(r_other) if r_other else "None",
                    "percent_change": pct,
                }

        return {
            "from_revision": self.revision_id,
            "to_revision": other.revision_id,
            "changed_inputs": changed_inputs,
            "changed_results": changed_results,
        }

    def as_dict(self) -> Dict[str, Any]:
        return {
            "revision_id": self.revision_id,
            "revision_number": self.revision_number,
            "parent_revision_id": self.parent_revision_id,
            "timestamp": self.timestamp,
            "inputs": {k: v.explain() for k, v in self.inputs.items()},
            "results": {k: v.explain() for k, v in self.results.items()},
            "artifacts": {k: a.as_dict() for k, a in self.artifacts.items()},
            "notes": self.notes,
        }


class DigitalThread:
    """The central provenance coordinator connecting the DAG, Revisions, and Artifacts."""

    def __init__(self, dag: DependencyDAG):
        self.dag = dag
        self.revisions: List[DesignRevision] = []
        self._revision_counter = 0

    @property
    def current_revision(self) -> Optional[DesignRevision]:
        return self.revisions[-1] if self.revisions else None

    def commit_revision(
        self,
        artifacts: Optional[List[CADArtifact]] = None,
        notes: str = "",
    ) -> DesignRevision:
        """Freezes the current DAG outputs into an immutable, versioned DesignRevision."""
        # Ensure DAG is up to date before committing
        if any(node.stale for node in self.dag.nodes.values() if not node.is_source_input):
            self.dag.recompute(trigger_reason="Pre-commit graph synchronization")

        self._revision_counter += 1
        parent_id = self.current_revision.revision_id if self.current_revision else None

        inputs = {}
        results = {}
        for k, node in self.dag.nodes.items():
            if node.is_source_input:
                inputs.update(node.outputs)
            else:
                results.update(node.outputs)

        rev_id = _compute_revision_id(inputs, parent_id)
        art_map = {a.filename: a for a in artifacts} if artifacts else {}

        rev = DesignRevision(
            revision_id=rev_id,
            revision_number=self._revision_counter,
            parent_revision_id=parent_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            inputs=inputs,
            results=results,
            artifacts=art_map,
            recompute_report=self.dag.last_report,
            notes=notes,
        )
        self.revisions.append(rev)
        return rev

    def explain(self, target_key: str) -> Dict[str, Any]:
        """Provides full backwards provenance for any calculated engineering quantity."""
        target_val = self.dag.get_value(target_key)
        if target_val is None:
            raise KeyError(f"Engineering quantity '{target_key}' not found in the Digital Thread.")

        # Traverse upstream dependency lineage
        lineage_chain = []
        queue = [target_key]
        visited = set()

        while queue:
            curr_key = queue.pop(0)
            if curr_key in visited:
                continue
            visited.add(curr_key)

            # Find the node that produced this quantity
            producing_node = None
            for node in self.dag.nodes.values():
                if curr_key in node.outputs:
                    producing_node = node
                    break

            if producing_node:
                val = producing_node.outputs[curr_key]
                step = {
                    "key": curr_key,
                    "value_str": str(val),
                    "value_canonical": val.value,
                    "unit": val.unit,
                    "method": val.method,
                    "source": val.source.citation() if val.source else "None",
                    "validation_state": val.validation_state.value,
                    "calculation_id": val.calculation_id,
                    "dependencies": list(val.dependencies),
                    "is_root_input": producing_node.is_source_input,
                }
                lineage_chain.append(step)
                for dep in val.dependencies:
                    if dep not in visited:
                        queue.append(dep)

        return {
            "target": target_val.explain(),
            "lineage_depth": len(lineage_chain),
            "lineage_chain": lineage_chain,
            "software_version": "kryptonis-propulsion v0.7.0",
            "active_revision_id": self.current_revision.revision_id if self.current_revision else "UNCOMMITTED",
        }

    def explain_text(self, target_key: str) -> str:
        """Renders structured provenance into a clean human-readable audit text block."""
        data = self.explain(target_key)
        tgt = data["target"]
        lines = [
            f"=== ENGINEERING TRACE: {tgt['name']} ===",
            f"Result:             {tgt['display_value']:.4g} {tgt['display_unit']} (Canonical: {tgt['value_canonical']:.4g} {tgt['unit_canonical']})",
            f"Method:             {tgt['method']}",
            f"Validation State:   {tgt['validation_state']}",
            f"Calculation ID:     {tgt['calculation_id']}",
            f"Evidence Source:    {tgt['evidence']['citation'] if tgt['evidence'] else 'Internal Model'}",
            f"Depends Directly On:{', '.join(tgt['dependencies']) if tgt['dependencies'] else 'None (Root Input)'}",
            "",
            "--- Backwards Lineage Thread ---",
        ]
        for idx, step in enumerate(data["lineage_chain"]):
            indent = "  " * idx
            arrow = "->" if idx > 0 else "•"
            lines.append(f"{indent}{arrow} [{step['key']}] = {step['value_str']} via {step['method']}")
            if step["source"] != "None":
                lines.append(f"{indent}   Citation: {step['source']}")

        return "\n".join(lines)
