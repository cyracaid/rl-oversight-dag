"""Read-only review-order policies.

All policies return a full ranking of node ids.  None of them writes to the
graph, produces a receipt, or seals anything.  The caller decides how many
minutes of human review to spend and stops when the budget is exhausted.

``belief_greedy`` is a simplified, influence-weighted version of the deployable
baseline: rank by source-error probability times downstream sink influence,
divided by review cost.  The paper's version maintains a particle-filter
posterior over source vs inherited error; this Phase 0 version uses the
per-type base rate, so it is a ranking heuristic, not a reproduction.
"""

from __future__ import annotations

from .graph import EvidenceGraph

# A row review reads four diary fields; a witness-pair review reads two.
ROW_FIELDS = 4
WITNESS_FIELDS = 2

# Median per-field reading time from the audit demo (62 s per row review).
PER_FIELD_MINUTES = 62.0 / 60.0 / ROW_FIELDS


def field_count(mode: str) -> int:
    if mode == "row":
        return ROW_FIELDS
    if mode == "witness":
        return WITNESS_FIELDS
    raise ValueError(f"unknown review mode: {mode!r}")


def queue_order(graph: EvidenceGraph) -> list[int]:
    """The order the pipeline currently presents (node index)."""
    return list(range(graph.n))


def type_prior(graph: EvidenceGraph) -> list[int]:
    """Type-rate first, then downstream influence, then upstream layer."""
    return sorted(
        range(graph.n),
        key=lambda i: (
            -graph.nodes[i].base_error_rate,
            -graph.downstream_sinks(i),
            graph.nodes[i].layer,
            i,
        ),
    )


def belief_greedy(
    graph: EvidenceGraph,
    posterior: dict[int, float] | None = None,
    cost: dict[int, float] | None = None,
) -> list[int]:
    """Expected sink-error reduction per unit cost, made explicit.

    ``posterior`` defaults to the per-type base rate (the only calibrated
    signal available in Phase 0).  ``cost`` defaults to one review unit per
    node; a field-scoped caller can pass 0.5 for witness-pair nodes.
    """
    posterior = posterior or {i: graph.nodes[i].base_error_rate for i in range(graph.n)}
    cost = cost or {i: 1.0 for i in range(graph.n)}

    def score(i: int) -> float:
        influence = max(1, graph.downstream_sinks(i))
        return -(posterior[i] * influence / max(cost[i], 1e-9))

    return sorted(range(graph.n), key=lambda i: (score(i), graph.nodes[i].layer, i))
