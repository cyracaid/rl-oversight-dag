"""Sampled counterfactual value of one review, with shared random numbers.

``marginal`` scores a review with a mean-field forward pass, which multiplies the
per-parent probabilities of *independent* errors. Parents in these graphs share
ancestors, so one source error is counted once per open path to the sink. The
score is therefore not the expected gain of the review.

The gain cannot be computed exactly in general: it is a network-reliability
question, #P-hard, and the graphs here reach 500 nodes. This module estimates it
instead, with the pairing that makes the estimate usable:

* particles hold one draw of every source error and every edge coin,
* the same particles are replayed with the candidate's source error set to zero,
* the per-review gain is the sink-error difference *within* a particle.

The difference is then an unbiased estimate of the gain, and its noise is the
noise of a difference rather than the sum of two independent estimates.

Nothing here reads hidden truth. Inputs are the public belief, the public edge
probabilities, the sink ids and the hit rate, all present in the observation.
"""
from __future__ import annotations

import numpy as np

from .policies import marginal_scores

PARTICLES = 256
SHORTLIST = 16
P_CATCH = 0.9


class CounterfactualValue:
    """Particle view of one graph, refreshed each step with the public belief."""

    def __init__(self, observation, particles=PARTICLES, seed=0):
        self.particles = particles
        self.rng = np.random.default_rng(seed)
        self.edge_index = np.asarray(observation["edge_index"])
        self.edge_prob = np.asarray(observation["edge_probability"], dtype=np.float64)
        self.topo = np.asarray(observation["topological_order"])
        self.sinks = np.asarray(observation["sink_ids"], dtype=np.int64)
        self.n = observation["features"].shape[0]
        self.k = observation["features"].shape[1] - 7
        self.parents = [[] for _ in range(self.n)]
        for edge, (u, v) in enumerate(self.edge_index.T):
            self.parents[int(v)].append((int(u), edge))
        self.update(observation)

    def update(self, observation):
        """Re-read the public belief and redraw every latent variable."""
        self.belief = observation["features"][:, self.k + 2].astype(np.float64)
        self._source = self.rng.random((self.particles, self.n)) < self.belief
        self._coin = (self.rng.random((self.particles, self.edge_index.shape[1]))
                      < self.edge_prob)

    def effective(self, source=None):
        """Vectorised propagation: (particles, nodes) boolean effective errors."""
        source = self._source if source is None else source
        out = np.zeros((self.particles, self.n), dtype=bool)
        for node in self.topo:
            value = source[:, node].copy()
            for parent, edge in self.parents[node]:
                value |= out[:, parent] & self._coin[:, edge]
            out[:, node] = value
        return out

    def value(self, candidates, p_catch=P_CATCH):
        """Expected sink errors removed by one review of each candidate."""
        before = self.effective()
        counts_before = before[:, self.sinks].sum(axis=1)
        out = {}
        for node in candidates:
            source = self._source.copy()
            source[:, node] = False
            counts_after = self.effective(source)[:, self.sinks].sum(axis=1)
            # A review only corrects something when the node is *effectively*
            # wrong; a review that catches an inherited error changes nothing.
            gain = np.where(before[:, node], counts_before - counts_after, 0)
            out[int(node)] = float(p_catch * gain.mean())
        return out


def make_policy(p_catch=P_CATCH, particles=PARTICLES, shortlist=SHORTLIST, seed=0):
    """Shortlist by mean-field, then rank the shortlist by sampled gain."""
    state = {}

    def act(observation):
        scores = marginal_scores(observation)
        legal = np.flatnonzero(observation["mask"])
        count = min(shortlist, len(legal))
        shortlist_nodes = legal[np.argsort(-scores[legal], kind="stable")[:count]]
        view = state.get("view")
        if view is None:
            view = state["view"] = CounterfactualValue(observation, particles, seed)
        else:
            view.update(observation)
        gain = view.value(shortlist_nodes, p_catch)
        best = max(gain.values())
        tied = [n for n in shortlist_nodes if gain[n] == best]
        return int(max(tied, key=lambda n: (scores[n], -n)))

    return act
