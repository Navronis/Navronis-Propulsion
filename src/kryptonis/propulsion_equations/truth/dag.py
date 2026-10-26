"""
Dependency Directed Acyclic Graph (DAG) & Selective Recomputation Engine (Day 7).
=================================================================================

Represents all propulsion calculations and their explicit dependencies.
Enables:
- Explicit input and output declaration mapping
- Strict cycle detection (DependencyCycleError)
- Topological execution order
- Fine-grained dirty/stale marking
- Selective recomputation (only affected downstream calculations run; unaffected results are preserved)
- Clear visualization and inspection
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from kryptonis.propulsion_equations.truth.ir import EngineeringValue


class DependencyCycleError(ValueError):
    """Raised when a cycle is detected within the engineering computation graph."""
    pass


@dataclass
class ComputationNode:
    """A single discrete calculation node within the propulsion dependency DAG."""
    key: str
    label: str
    inputs: Tuple[str, ...]
    compute_fn: Callable[[Dict[str, Any]], Dict[str, EngineeringValue]]
    outputs_declared: Tuple[str, ...] = ()
    outputs: Dict[str, EngineeringValue] = field(default_factory=dict)
    stale: bool = True
    execution_count: int = 0
    last_recomputed_at: Optional[str] = None
    last_recompute_reason: Optional[str] = None
    is_source_input: bool = False

    def execute(self, upstream_context: Dict[str, Any], reason: str = "Recompute requested") -> Dict[str, EngineeringValue]:
        """Executes the node's computation function with upstream outputs."""
        self.outputs = self.compute_fn(upstream_context)
        self.stale = False
        self.execution_count += 1
        self.last_recomputed_at = datetime.now(timezone.utc).isoformat()
        self.last_recompute_reason = reason
        return self.outputs


@dataclass
class RecomputeReport:
    """Detailed audit report generated following a graph recomputation pass."""
    recomputed_nodes: List[str]
    preserved_nodes: List[str]
    execution_order: List[str]
    total_stale_before: int
    duration_ms: float
    trigger_reason: str = ""

    def summary(self) -> str:
        lines = [
            f"--- Selective Recomputation Report ({self.duration_ms:.2f} ms) ---",
            f"Trigger Reason: {self.trigger_reason}",
            f"Nodes Recomputed ({len(self.recomputed_nodes)}): {', '.join(self.recomputed_nodes) or 'None'}",
            f"Nodes Preserved  ({len(self.preserved_nodes)}): {', '.join(self.preserved_nodes) or 'None'}",
        ]
        return "\n".join(lines)


class DependencyDAG:
    """Directed Acyclic Graph governing propulsion system calculations."""

    def __init__(self, name: str = "Navronis Propulsion DAG"):
        self.name = name
        self.nodes: Dict[str, ComputationNode] = {}
        # Mapping from output quantity key -> node key that produces it
        self.output_to_node: Dict[str, str] = {}
        # Adjacency list: node key -> set of downstream node keys that depend on it
        self.downstream_edges: Dict[str, Set[str]] = defaultdict(set)
        # Upstream list: node key -> set of upstream node keys it depends on
        self.upstream_edges: Dict[str, Set[str]] = defaultdict(set)
        self.last_report: Optional[RecomputeReport] = None

    def register_input(self, key: str, initial_value: EngineeringValue, label: str = "") -> None:
        """Registers a root design requirement or operating condition input node."""
        node_label = label or f"Input: {key}"

        def input_identity(ctx: Dict[str, Any]) -> Dict[str, EngineeringValue]:
            return {key: initial_value}

        node = ComputationNode(
            key=key,
            label=node_label,
            inputs=(),
            compute_fn=input_identity,
            outputs_declared=(key,),
            outputs={key: initial_value},
            stale=False,
            execution_count=1,
            last_recomputed_at=datetime.now(timezone.utc).isoformat(),
            last_recompute_reason="Initial registration",
            is_source_input=True,
        )
        self.nodes[key] = node
        self.output_to_node[key] = key

    def register_node(
        self,
        key: str,
        label: str,
        inputs: Tuple[str, ...],
        outputs: Any,
        compute_fn: Optional[Callable[[Dict[str, Any]], Dict[str, EngineeringValue]]] = None,
    ) -> None:
        """Registers an intermediate or terminal engineering calculation node."""
        # Support signature both with and without explicit outputs tuple
        if callable(outputs) and compute_fn is None:
            compute_fn = outputs
            outputs_tuple: Tuple[str, ...] = ()
        else:
            outputs_tuple = tuple(outputs)

        node = ComputationNode(
            key=key,
            label=label,
            inputs=inputs,
            outputs_declared=outputs_tuple,
            compute_fn=compute_fn,
            stale=True,
            is_source_input=False,
        )
        self.nodes[key] = node

        # Register output quantity mappings
        for out in outputs_tuple:
            self.output_to_node[out] = key

        # Resolve upstream dependencies
        for inp in inputs:
            upstream_node_key = self.output_to_node.get(inp, inp)
            self.downstream_edges[upstream_node_key].add(key)
            self.upstream_edges[key].add(upstream_node_key)

        # Check for cycles immediately upon registration
        self.check_cycles()

    def set_input(self, key: str, new_value: EngineeringValue, reason: str = "Design update") -> None:
        """Updates a root design input and marks all affected downstream nodes as stale."""
        node_key = self.output_to_node.get(key, key)
        if node_key not in self.nodes:
            raise KeyError(f"Input '{key}' is not registered in the DAG.")

        node = self.nodes[node_key]
        node.outputs[key] = new_value
        node.last_recomputed_at = datetime.now(timezone.utc).isoformat()
        node.last_recompute_reason = reason

        # Mark all downstream dependent nodes stale
        self.invalidate_downstream(node_key, reason=f"Upstream input '{key}' changed to {new_value.display_value:.4g} {new_value.display_unit or new_value.unit}")

    def invalidate_downstream(self, root_key: str, reason: str) -> List[str]:
        """Traverses downstream edges from root_key and marks every reachable node stale."""
        stale_marked = []
        queue = deque(list(self.downstream_edges[root_key]))
        visited = set()

        while queue:
            curr = queue.popleft()
            if curr in visited:
                continue
            visited.add(curr)
            if curr in self.nodes:
                self.nodes[curr].stale = True
                self.nodes[curr].last_recompute_reason = reason
                stale_marked.append(curr)
            for downstream in self.downstream_edges[curr]:
                if downstream not in visited:
                    queue.append(downstream)

        return stale_marked

    def check_cycles(self) -> None:
        """Checks for cycles in the dependency graph using Kahn's algorithm."""
        in_degree = {k: 0 for k in self.nodes}
        for u in self.nodes:
            for v in self.downstream_edges[u]:
                if v in in_degree:
                    in_degree[v] += 1

        queue = deque([k for k, deg in in_degree.items() if deg == 0])
        visited_count = 0

        while queue:
            curr = queue.popleft()
            visited_count += 1
            for nxt in self.downstream_edges[curr]:
                if nxt in in_degree:
                    in_degree[nxt] -= 1
                    if in_degree[nxt] == 0:
                        queue.append(nxt)

        if visited_count != len(self.nodes):
            raise DependencyCycleError("Cycle detected in engineering dependency DAG!")

    def get_topological_order(self) -> List[str]:
        """Returns the valid topological execution order of all nodes in the DAG."""
        self.check_cycles()
        in_degree = {k: 0 for k in self.nodes}
        for u in self.nodes:
            for v in self.downstream_edges[u]:
                if v in in_degree:
                    in_degree[v] += 1

        queue = deque([k for k, deg in in_degree.items() if deg == 0])
        order = []

        while queue:
            curr = queue.popleft()
            order.append(curr)
            for nxt in sorted(self.downstream_edges[curr]):
                if nxt in in_degree:
                    in_degree[nxt] -= 1
                    if in_degree[nxt] == 0:
                        queue.append(nxt)

        return order

    def recompute(self, trigger_reason: str = "Selective recomputation") -> RecomputeReport:
        """Selectively recomputes only nodes currently flagged as stale in topological order."""
        t_start = time.perf_counter()
        order = self.get_topological_order()

        stale_nodes_before = [k for k, node in self.nodes.items() if node.stale]
        recomputed = []
        preserved = []

        # Accumulate context dictionary of all current outputs
        context: Dict[str, Any] = {}
        for k in order:
            context.update(self.nodes[k].outputs)

        for k in order:
            node = self.nodes[k]
            if node.is_source_input:
                preserved.append(k)
                continue

            if node.stale:
                # Gather upstream inputs for this specific node
                node_ctx = {inp_key: context[inp_key] for inp_key in node.inputs if inp_key in context}
                out = node.execute(node_ctx, reason=trigger_reason)
                # Register output quantity mappings
                for out_k in out.keys():
                    self.output_to_node[out_k] = k
                context.update(out)
                recomputed.append(k)
            else:
                preserved.append(k)

        duration_ms = (time.perf_counter() - t_start) * 1000.0
        report = RecomputeReport(
            recomputed_nodes=recomputed,
            preserved_nodes=preserved,
            execution_order=order,
            total_stale_before=len(stale_nodes_before),
            duration_ms=duration_ms,
            trigger_reason=trigger_reason,
        )
        self.last_report = report
        return report

    def get_value(self, key: str) -> Optional[EngineeringValue]:
        """Retrieves an engineering quantity by its unique output key."""
        node_key = self.output_to_node.get(key)
        if node_key and node_key in self.nodes:
            if key in self.nodes[node_key].outputs:
                return self.nodes[node_key].outputs[key]

        for node in self.nodes.values():
            if key in node.outputs:
                return node.outputs[key]
        return None

    def get_all_outputs(self) -> Dict[str, EngineeringValue]:
        """Collates all active outputs across every node in the graph."""
        res: Dict[str, EngineeringValue] = {}
        for node in self.nodes.values():
            res.update(node.outputs)
        return res

    def visualize_ascii(self) -> str:
        """Generates an ASCII visualization of the computation graph."""
        order = self.get_topological_order()
        lines = [f"=== {self.name} ==="]
        for k in order:
            node = self.nodes[k]
            status = "STALE" if node.stale else "CLEAN"
            inputs_str = ", ".join(node.inputs) if node.inputs else "(Root Input)"
            outputs_str = ", ".join(node.outputs_declared) if node.outputs_declared else ", ".join(node.outputs.keys())
            lines.append(f"[{status:5s}] {k:22s} ({node.label})")
            lines.append(f"        <- Inputs : {inputs_str}")
            lines.append(f"        -> Outputs: {outputs_str}")
        return "\n".join(lines)

    def visualize_mermaid(self) -> str:
        """Generates a Mermaid flowchart diagram of the DAG."""
        lines = ["flowchart TD"]
        for k, node in self.nodes.items():
            stale_style = ":::stale" if node.stale else ":::clean"
            label = node.label.replace('"', "'")
            lines.append(f'    {k}["{label}"]{stale_style}')
            for down in self.downstream_edges[k]:
                lines.append(f"    {k} --> {down}")
        lines.append("    classDef clean fill:#0f172a,stroke:#38bdf8,stroke-width:1px,color:#f1f5f9;")
        lines.append("    classDef stale fill:#450a0a,stroke:#ef4444,stroke-width:2px,color:#fca5a5;")
        return "\n".join(lines)
