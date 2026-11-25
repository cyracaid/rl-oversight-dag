"""The prohibited loop: what happens when a delivery reads its own coverage as evidence.

`supervisor.py` computes what a delivery may *say*. `audit_policy.py` freezes who
may change what it may say. This module builds the one loop the construct mapping
forbids, so the prohibition can be tested instead of asserted.

The forbidden inference is short. A sink with *some* upstream sources reviewed and
some not is `partial`. The reviewers who did look found nothing. A system that
treats "nothing found" as weak evidence of cleanliness then lowers its belief that
the *unreviewed* sources in that region are wrong — and those are exactly the nodes
the router still has to choose between. The loop feeds the guarantee back into the
audited object, which `ENTROPY_LIMITS.md` §8 says cannot end well.

Two design choices, both fixed before the run:

* the multiplier is ``1 - p_catch``, the marginal likelihood of a miss under the
  reviewer's hit rate — not a tuned constant;
* it **compounds**. Each decision re-applies the multiplier to every unreviewed
  source still feeding a `partial` sink, so the pessimism decays geometrically
  while the source stays unreviewed. Single application would be a perturbation;
  repeated application is what "error accumulation" means.

Nothing here is imported by the frozen environment or by `supervisor.py`.
"""
from __future__ import annotations

import numpy as np

from .supervisor import ancestor_sources, coverage_truth

__all__ = [
    "downweight",
    "frontier_sources",
    "optimistic_features",
    "sink_depth",
]


def sink_depth(graph) -> dict[int, int]:
    """Longest number of edges from any source to each sink.

    Depth is a property of the graph, not of the episode, so a sink's bin is the
    same under both arms. Sources are depth 0.
    """
    depth = [0] * graph.n
    for v in graph.topo:
        if graph.parents[v]:
            depth[v] = 1 + max(depth[u] for u in graph.parents[v])
    return {int(s): int(depth[s]) for s in graph.sinks}


def frontier_sources(graph, reviewed, truth=None) -> set[int]:
    """Unreviewed sources that still feed a `partial` sink.

    ``truth`` may be passed to reuse an already computed coverage map; otherwise it
    is recomputed from the public review log. A source feeding only `inspected`
    sinks has nothing left to contribute, and one feeding only `untouched` sinks
    has produced no evidence to misread, so neither is on the frontier.
    """
    coverage = coverage_truth(graph, reviewed) if truth is None else truth
    ancestors = ancestor_sources(graph)
    reviewed = set(int(v) for v in reviewed)
    frontier: set[int] = set()
    for sink, status in coverage.items():
        if status != "partial":
            continue
        frontier |= set(ancestors[sink]) - reviewed
    return frontier


def downweight(state: dict[int, float], frontier, p_catch: float) -> dict[int, float]:
    """Apply the miss multiplier to the frontier, compounding over decisions.

    ``state`` is mutated and returned so a policy can carry it across steps. A
    source that leaves the frontier keeps whatever weight it accumulated: that is
    the drift, not an artefact.
    """
    factor = 1.0 - float(p_catch)
    for node in frontier:
        state[int(node)] = state.get(int(node), 1.0) * factor
    return state


def optimistic_features(observation, weights: dict[int, float]):
    """A copy of the observation with the belief column scaled by ``weights``.

    Only the belief channel is touched (`k + 2`), which is the channel
    `marginal_scores` reads as ``base``. The environment, the review log and every
    other field are left exactly as they were, so the two arms see the same
    episode and the difference is only what the machine believes about itself.
    """
    f = observation["features"].copy()
    if not weights:
        return f
    k = f.shape[1] - 7
    for node, factor in weights.items():
        f[node, k + 2] = np.float32(f[node, k + 2] * factor)
    return f
