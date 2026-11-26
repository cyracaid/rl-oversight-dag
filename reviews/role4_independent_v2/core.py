"""Clean-room core: rewire rules + map-mismatch environment.

Written from role4_controls/README.md only.  The frozen environment package
`dag_role3` is imported read-only, never copied or edited.
"""
from __future__ import annotations

import math
import random
import sys

import numpy as np

REPO = "/Users/sloblucyra/Documents/강화학습"
sys.path.insert(0, f"{REPO}/role3 improvement")

from dag_role3 import (  # noqa: E402
    DAG, EpisodeSnapshot, OversightEnv, generate_graph, propagate, sample_episode,
)
from dag_role3.policies import choose, marginal_scores  # noqa: E402,F401

REWIRE_SEED_INDEX = 4_040_000
REWIRE_SEED_ORDER = 5_050_000
DRAW_STRIDE = 100_000


# ---------------------------------------------------------------- rewire rules
def _rebuild(graph, new_parents, family):
    """Same types/rates/sinks as the original, new parent sets."""
    return DAG(
        parents=tuple(tuple(sorted(ps)) for ps in new_parents),
        types=graph.types,
        rates=graph.rates,
        family=graph.family,
        names=graph.names,
        sink_override=graph.sinks,
        lam=graph.lam,
        spike_probability=graph.spike_probability,
    )


def rewire_index(graph, graph_seed, k=0):
    """v1 rule (k=0) and its ten fixed-seed draws.

    spike: parents from the previous layer; real: from strictly lower layers;
    modular/ba/er: from all nodes with a lower index.  Parent counts, types and
    the sink set are kept, nodes visited in index order.
    """
    rng = random.Random(REWIRE_SEED_INDEX + DRAW_STRIDE * k + graph_seed)
    n = graph.n
    parents = []
    for v in range(n):
        count = len(graph.parents[v])
        if count == 0:
            parents.append(())
            continue
        if graph.family == "spike":
            cands = [u for u in range(n) if graph.layers[u] == graph.layers[v] - 1]
        elif graph.family == "real":
            cands = [u for u in range(n) if graph.layers[u] < graph.layers[v]]
        else:
            cands = list(range(v))
        if count > len(cands):
            raise ValueError(f"node {v}: {count} parents but only {len(cands)} candidates")
        parents.append(tuple(sorted(rng.sample(cands, count))))
    return _rebuild(graph, parents, graph.family)


def rewire_order(graph, graph_seed, k=0):
    """Hub-breaking rewire: random feasible order, parents from placed nodes."""
    if graph.family not in ("modular", "ba", "er"):
        raise ValueError("rewire_order is defined for modular, ba, er only")
    rng = random.Random(REWIRE_SEED_ORDER + DRAW_STRIDE * k + graph_seed)
    n = graph.n
    remaining = list(range(n))
    order = []
    parents = [()] * n
    while remaining:
        feasible = [v for v in remaining if len(graph.parents[v]) <= len(order)]
        if not feasible:
            raise ValueError("no feasible node to place")
        v = rng.choice(feasible)
        count = len(graph.parents[v])
        parents[v] = tuple(sorted(rng.sample(order, count))) if count else ()
        order.append(v)
        remaining.remove(v)
    return _rebuild(graph, parents, graph.family)


# ------------------------------------------------------------- mismatch env
class MapMismatchEnv(OversightEnv):
    """Policy plans on ``view_graph``; hidden error state lives on the true graph.

    Only the hidden error state is recomputed on the true graph: source errors,
    confidences and reviewer uniforms are shared cell by cell, and the reviewer
    draws/flags/reward come from the true propagation.  All structure-facing
    observation fields (edge index, edge probabilities, topological order, sink
    ids, sink reach, forward public error proxy) come from the view.
    """

    def __init__(self, true_graph, true_snapshot, view_graph, view_snapshot,
                 budget=None, p_catch=0.9):
        self.view_graph = view_graph
        self.view_snapshot = view_snapshot
        self._view_edges = view_graph.edge_index()
        self._view_prob = np.array(
            [view_snapshot.edge_probs[u, v] for u, v in self._view_edges.T], dtype=float
        )
        super().__init__(true_graph, true_snapshot, budget=budget, p_catch=p_catch)

    def _public_error_probabilities(self):
        g = self.view_graph
        p = np.zeros(g.n, dtype=np.float64)
        for i in g.topo:
            clean = 1.0
            for u in g.parents[i]:
                clean *= 1 - p[u] * self.view_snapshot.edge_probs[u, i]
            p[i] = 1 - (1 - self._belief_base[i]) * clean
        return p

    def observation(self):
        g, n = self.view_graph, self.view_graph.n
        k = len(g.rates)
        f = np.zeros((n, k + 7), dtype=np.float32)
        f[np.arange(n), list(g.types)] = 1.0
        f[:, k] = np.asarray(self.snapshot.confidence, dtype=np.float32)
        f[:, k + 1] = np.log1p(g.sink_reach) / math.log1p(n)
        f[:, k + 2] = self._belief_base
        f[:, k + 3] = self._public_error_probabilities()
        f[:, k + 4] = self._reviewed
        f[:, k + 5] = self._flagged
        f[:, k + 6] = self._budget_left / max(1, self.budget)
        return {
            "features": f.copy(),
            "mask": np.logical_not(self._reviewed) & (not self.done),
            "edge_index": self._view_edges.copy(),
            "edge_probability": self._view_prob.copy(),
            "topological_order": np.array(g.topo),
            "sink_ids": np.asarray(g.sinks, dtype=np.int64),
            "budget_left": self._budget_left,
            "family": g.family,
            "node_names": list(g.names) if g.names else [f"v{i}" for i in range(n)],
        }


def run_policy(true_graph, true_snapshot, view_graph, view_snapshot, policy, budget):
    env = MapMismatchEnv(true_graph, true_snapshot, view_graph, view_snapshot, budget)
    obs = env.observation()
    actions = []
    while not env.done:
        action = choose(obs, policy)
        actions.append(int(action))
        obs, _reward, _done, _info = env.step(action)
    return env.final_audit()["final_sink_errors"], actions


# ---------------------------------------------------------------- conditions
def flatten_snapshot(snapshot):
    """Same episode, every edge coin False; probabilities untouched."""
    return EpisodeSnapshot(
        snapshot.source_errors,
        {edge: False for edge in snapshot.edge_coins},
        dict(snapshot.edge_probs),
        snapshot.confidence,
        snapshot.review_uniforms,
        snapshot.seed,
    )


def assert_same_episode(a, b):
    assert tuple(a.source_errors) == tuple(b.source_errors), "source errors differ"
    assert tuple(a.confidence) == tuple(b.confidence), "confidence differs"
    assert tuple(a.review_uniforms) == tuple(b.review_uniforms), "reviewer differs"


def episode_for(graph, graph_seed):
    return sample_episode(graph, 20_000 + graph_seed)


def budget_for(family):
    return {"spike": 16, "real": 8}.get(family, 50)
