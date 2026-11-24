"""Load a SciForge-style evidence export into a reviewable graph.

Shape follows ``triage_bench/SCIFORGE_ASK.md`` §4. Nothing here writes, seals,
or mutates an evidence record; this module only reads one JSON file.

Validation is deliberately noisy: anything unusable is counted and reported,
never silently dropped. The rule the sleep side taught us: a queue that quietly
loses rows produces a number nobody can defend.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

NODE_TYPES = ("claim", "dataset", "run", "figure")
EDGE_RELS = ("derived_from", "supports", "contradicts")
# Mirrors review-control/src/contract.ts (reviewReceiptSchema.verdict).
VERDICTS = ("accepted", "corrected", "rejected", "needs_revision", "unresolved", "skipped")


class ExportError(ValueError):
    """The file does not satisfy the export contract."""


@dataclass(frozen=True)
class ExportGraph:
    project: str
    snapshot_at: str
    synthetic: bool
    ids: tuple[str, ...]
    types: tuple[str, ...]
    is_sink: tuple[bool, ...]
    parents: tuple[tuple[int, ...], ...]
    children: tuple[tuple[int, ...], ...]
    topo: tuple[int, ...]
    reach: tuple[int, ...]
    corrections: dict[int, dict[str, Any]]
    receipts: tuple[dict[str, Any], ...]
    report: dict[str, Any] = field(default_factory=dict)

    @property
    def n(self) -> int:
        return len(self.ids)

    @property
    def edge_count(self) -> int:
        return sum(len(p) for p in self.parents)


def _require(mapping: dict, key: str, where: str) -> Any:
    if key not in mapping:
        raise ExportError(f"{where}: missing required field {key!r}")
    return mapping[key]


def _topological(n: int, parents: tuple[tuple[int, ...], ...]) -> tuple[int, ...]:
    indeg = [len(p) for p in parents]
    children: list[list[int]] = [[] for _ in range(n)]
    for v, ps in enumerate(parents):
        for u in ps:
            children[u].append(v)
    ready = [v for v in range(n) if indeg[v] == 0]
    out: list[int] = []
    while ready:
        v = ready.pop()
        out.append(v)
        for c in children[v]:
            indeg[c] -= 1
            if indeg[c] == 0:
                ready.append(c)
    if len(out) != n:
        raise ExportError("derived_from edges contain a cycle; an evidence chain must be acyclic")
    return tuple(out)


def load_export(path: str | Path) -> ExportGraph:
    path = Path(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ExportError(f"{path}: not valid JSON ({exc})") from exc
    return from_payload(payload, source=str(path))


def from_payload(payload: dict, source: str = "<memory>") -> ExportGraph:
    if not isinstance(payload, dict):
        raise ExportError(f"{source}: top level must be an object")
    project = _require(payload, "project", source)
    snapshot_at = _require(payload, "snapshot_at", source)
    nodes = _require(payload, "nodes", source)
    edges = _require(payload, "edges", source)
    corrections_raw = payload.get("corrections", [])
    receipts_raw = payload.get("receipts", [])
    if not isinstance(nodes, list) or not nodes:
        raise ExportError(f"{source}: 'nodes' must be a non-empty list")

    ids: list[str] = []
    types: list[str] = []
    is_sink: list[bool] = []
    index: dict[str, int] = {}
    unknown_types: list[str] = []
    for i, node in enumerate(nodes):
        where = f"{source}: nodes[{i}]"
        node_id = str(_require(node, "id", where))
        if not node_id:
            raise ExportError(f"{where}: empty id")
        if node_id in index:
            raise ExportError(f"{where}: duplicate id {node_id!r}")
        node_type = str(_require(node, "type", where))
        if node_type not in NODE_TYPES:
            unknown_types.append(node_type)
        index[node_id] = i
        ids.append(node_id)
        types.append(node_type)
        is_sink.append(bool(node.get("is_sink", False)))

    parents: list[list[int]] = [[] for _ in ids]
    rel_counts: dict[str, int] = {}
    skipped_edges = 0
    for i, edge in enumerate(edges):
        where = f"{source}: edges[{i}]"
        src = str(_require(edge, "src", where))
        dst = str(_require(edge, "dst", where))
        rel = str(_require(edge, "rel", where))
        if src not in index or dst not in index:
            raise ExportError(f"{where}: unknown endpoint {src!r}->{dst!r}")
        if src == dst:
            raise ExportError(f"{where}: self edge on {src!r}")
        rel_counts[rel] = rel_counts.get(rel, 0) + 1
        if rel != "derived_from":
            skipped_edges += 1
            continue
        parents[index[dst]].append(index[src])

    parents_t = tuple(tuple(dict.fromkeys(ps)) for ps in parents)
    topo = _topological(len(ids), parents_t)

    children: list[list[int]] = [[] for _ in ids]
    for v, ps in enumerate(parents_t):
        for u in ps:
            children[u].append(v)
    children_t = tuple(tuple(c) for c in children)

    reach = [0] * len(ids)
    for v in reversed(topo):
        seen: set[int] = set()
        stack = list(children_t[v])
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(children_t[cur])
        reach[v] = len(seen)

    corrections: dict[int, dict[str, Any]] = {}
    duplicate_corrections: list[str] = []
    for i, row in enumerate(corrections_raw):
        where = f"{source}: corrections[{i}]"
        node_id = str(_require(row, "node_id", where))
        if node_id not in index:
            raise ExportError(f"{where}: node {node_id!r} not in nodes")
        v = index[node_id]
        if v in corrections:
            duplicate_corrections.append(node_id)
            continue
        corrections[v] = {
            "error_type": row.get("error_type"),
            "severity": row.get("severity"),
            "agreed_by": row.get("agreed_by"),
        }

    receipts: list[dict[str, Any]] = []
    bad_receipts = 0
    for i, row in enumerate(receipts_raw):
        where = f"{source}: receipts[{i}]"
        node_id = str(_require(row, "node_id", where))
        if node_id not in index:
            raise ExportError(f"{where}: node {node_id!r} not in nodes")
        verdict = str(_require(row, "verdict", where))
        if verdict not in VERDICTS:
            raise ExportError(f"{where}: verdict {verdict!r} not in {VERDICTS}")
        duration = row.get("duration_min")
        if duration is not None and float(duration) < 0:
            bad_receipts += 1
            continue
        receipts.append({
            "node": index[node_id],
            "reviewer_hash": row.get("reviewer_hash"),
            "reviewed_at": row.get("reviewed_at"),
            "duration_min": None if duration is None else float(duration),
            "verdict": verdict,
            "synthetic": bool(row.get("synthetic", False)),
        })

    report = {
        "source": source,
        "synthetic": bool(payload.get("synthetic", False)),
        "nodes": len(ids),
        "derived_edges": sum(len(p) for p in parents_t),
        "edge_relations": rel_counts,
        "non_propagation_edges_ignored": skipped_edges,
        "unknown_node_types": sorted(set(unknown_types)),
        "corrections": len(corrections),
        "duplicate_corrections_dropped": len(duplicate_corrections),
        "receipts": len(receipts),
        "receipts_dropped_invalid_duration": bad_receipts,
        "with_duration": sum(1 for r in receipts if r["duration_min"] is not None),
        "sinks": sum(1 for s in is_sink if s),
    }
    return ExportGraph(
        project=str(project),
        snapshot_at=str(snapshot_at),
        synthetic=report["synthetic"],
        ids=tuple(ids),
        types=tuple(types),
        is_sink=tuple(is_sink),
        parents=parents_t,
        children=children_t,
        topo=topo,
        reach=tuple(reach),
        corrections=corrections,
        receipts=tuple(receipts),
        report=report,
    )
