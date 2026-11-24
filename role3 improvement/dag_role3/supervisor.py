"""The supervisor layer: what a delivery *declares* about its own coverage.

Everything else in this repository measures how many errors a policy leaves
behind. That is one axis, and it is nearly saturated: an optimal policy inside
the same model is worth 2.5 % (`outputs/dp-ceiling/`). This module adds the
second axis, which no published number here has touched: given the same
residual errors, can the delivery say *what it checked and what it did not*,
and is that statement true?

Three pieces:

* ``ancestor_sources`` — for each sink, the source nodes that can reach it. The
  environment only removes a node's *own* source error, so a sink can be
  guaranteed inspected only when every source feeding it was reviewed. This is
  the only coverage notion that matches the environment's semantics; a vertex
  cut is not enough, because an inherited error passes through a reviewed node.
* ``receipt`` — the delivery's public statement, one status per sink. Three
  statuses, and ``escalated`` is a refusal rather than a claim, so it can never
  be false.
* ``score`` — compares the receipt against what the machine can recompute, and
  against the hidden truth. ``fidelity`` needs only the public review log;
  ``false_inspection`` needs the truth and asks the question a reader actually
  cares about: how many sinks did we label as checked while they were wrong.

Nothing here changes a policy's actions. The receipt is a report about the
episode, so the two axes are orthogonal by construction -- which is the point,
and which the runner checks instead of assuming.
"""
from __future__ import annotations

from .environment import propagate

STATUSES = ("inspected", "partial", "untouched", "escalated")


def ancestor_sources(graph):
    """Source nodes that can structurally reach each sink."""
    reach = [frozenset() for _ in range(graph.n)]
    for v in graph.topo:
        if not graph.parents[v]:
            reach[v] = frozenset((v,))
        else:
            acc = set()
            for u in graph.parents[v]:
                acc |= reach[u]
            reach[v] = frozenset(acc)
    return {int(s): reach[int(s)] for s in graph.sinks}


def coverage_truth(graph, reviewed):
    """Per-sink status the review log supports, using public structure only."""
    ancestors = ancestor_sources(graph)
    reviewed = set(int(v) for v in reviewed)
    truth = {}
    for sink, sources in ancestors.items():
        total = len(sources)
        seen = len(sources & reviewed)
        if total == 0:
            truth[sink] = "untouched"          # no source can reach it
        elif seen == total:
            truth[sink] = "inspected"
        elif seen == 0:
            truth[sink] = "untouched"
        else:
            truth[sink] = "partial"
    return truth


def receipt(graph, reviewed, claim="honest", escalated=()):
    """The delivery's statement. ``claim`` is the honesty knob.

    ``honest``     copy the review log.
    ``overclaim``  label every sink inspected, which is what a system without a
                   coverage field effectively does when asked.
    ``silent``     claim nothing at all -- the arm with no receipt.
    """
    if claim == "silent":
        return None
    truth = coverage_truth(graph, reviewed)
    escalated = set(int(v) for v in escalated)
    if claim == "honest":
        status = {k: ("escalated" if k in escalated else v) for k, v in truth.items()}
    elif claim == "overclaim":
        status = {k: "inspected" for k in truth}
    else:
        raise ValueError(f"unknown claim mode: {claim}")
    return {"status": {int(k): status[k] for k in status}}


def sink_truth(graph, env):
    """Evaluator-only: which sinks are actually wrong at the end."""
    effective = propagate(graph, env._base, env.snapshot.edge_coins)
    return {int(s): bool(effective[int(s)]) for s in graph.sinks}


def score(graph, reviewed, statement, truth_of_sinks):
    """Compare a statement against the review log and the hidden truth.

    ``fidelity`` counts only claimed statuses (a refusal is never false, but a
    receipt that escalates everything has nothing to be faithful about, so
    ``judged`` reports how much of the delivery was actually described).
    """
    computed = coverage_truth(graph, reviewed)
    total = len(computed)
    if statement is None:
        return {"receipt": "absent", "judged": 0.0, "fidelity": None,
                "false_inspection": None, "declared_gap": None,
                "uninspected_errors": None, "status_counts": {}}
    claimed = statement["status"]
    correct = sum(1 for s in computed
                  if claimed.get(s) == "escalated" or claimed.get(s) == computed[s])
    judged = sum(1 for s in computed if claimed.get(s) != "escalated")
    false_inspection = sum(1 for s in computed
                           if claimed.get(s) == "inspected" and truth_of_sinks[s])
    declared_gap = sum(1 for s in computed
                       if claimed.get(s) in ("partial", "untouched") and truth_of_sinks[s])
    uninspected_errors = sum(1 for s in computed
                             if computed[s] != "inspected" and truth_of_sinks[s])
    counts = {}
    for value in claimed.values():
        counts[value] = counts.get(value, 0) + 1
    return {"receipt": "present",
            "judged": judged / total if total else 0.0,
            "fidelity": correct / total if total else None,
            "false_inspection": false_inspection,
            "declared_gap": declared_gap,
            "uninspected_errors": uninspected_errors,
            "status_counts": counts}
