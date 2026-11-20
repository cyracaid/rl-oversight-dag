"""Read-only evidence graph used by the review control plane.

Phase 0 uses the N=21 sleep-pipeline DAG as a stand-in for a SciForge
evidence graph.  The node/edge vocabulary matches the export described in
``triage_bench/SCIFORGE_ASK.md``:

    node: id, type, layer, is_sink
    edge: parent -> child  (derived_from / supports)

Nothing here writes, seals, or mutates an evidence record.
"""

from __future__ import annotations

from dataclasses import dataclass
from experiments.real_pipeline_graph import (
    NODES,
    PARENTS,
    SINKS,
    TYPE_RATE,
    NAME2ID,
)


@dataclass(frozen=True)
class EvidenceNode:
    idx: int
    name: str
    layer: int
    error_type: str
    is_sink: bool
    parents: tuple[int, ...]
    children: tuple[int, ...]
    base_error_rate: float


@dataclass(frozen=True)
class EvidenceGraph:
    nodes: tuple[EvidenceNode, ...]
    name2id: dict[str, int]

    @property
    def n(self) -> int:
        return len(self.nodes)

    @property
    def sinks(self) -> tuple[int, ...]:
        return tuple(n.idx for n in self.nodes if n.is_sink)

    def downstream_sinks(self, idx: int) -> int:
        """Number of distinct sink nodes reachable from ``idx`` (inclusive)."""
        return _reachable_sinks(self, idx)


def _reachable_sinks(graph: EvidenceGraph, idx: int) -> int:
    seen: set[int] = set()
    stack = [idx]
    sinks: set[int] = set()
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        if graph.nodes[cur].is_sink:
            sinks.add(cur)
        stack.extend(graph.nodes[cur].children)
    return len(sinks)


def from_sleep_pipeline() -> EvidenceGraph:
    """Build the 21-node DAG from the lab's SCHEMA-derived pipeline."""
    children: dict[int, list[int]] = {i: [] for i in range(len(NODES))}
    for name, parents in PARENTS.items():
        child = NAME2ID[name]
        for parent in parents:
            children[NAME2ID[parent]].append(child)

    nodes = []
    for idx, (name, layer, error_type) in enumerate(NODES):
        nodes.append(
            EvidenceNode(
                idx=idx,
                name=name,
                layer=layer,
                error_type=error_type,
                is_sink=idx in SINKS,
                parents=tuple(NAME2ID[p] for p in PARENTS[name]),
                children=tuple(sorted(children[idx])),
                base_error_rate=TYPE_RATE[error_type],
            )
        )
    return EvidenceGraph(nodes=tuple(nodes), name2id=dict(NAME2ID))
