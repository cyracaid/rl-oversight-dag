"""Depth-two expectimax over the public belief, to price the one-step horizon.

``marginal`` scores a review by its forward derivative. That derivative is exact
for the quantity it names — the mean-field expected sink errors — so a depth-two
planner built on the *same* mean-field model isolates one thing: what a second
step of lookahead is worth. Nothing here reads the truth; inputs are the belief
column, the edge probabilities, the sinks, the mask and the hit rate.

Two variants, because the environment's miss update is itself approximate:

* ``full`` weights the second step by both review outcomes, using the same
  update ``OversightEnv.step`` performs on a miss. A planner can raise its score
  by exploiting that approximation, which is a finding about the update, not
  about planning, so it is not the only variant reported.
* ``catch`` only follows the success branch: an optimistic value that cannot
  profit from the miss update.

Both are truncated greedy planners, width-limited for compute, not optimal.
"""
from __future__ import annotations

import numpy as np


class Topology:
    """CSR view of the parent edges, held as Python lists.

    The graphs here have at most a handful of parents per node (757 edges over
    500 nodes on ``modular``), so a per-node numpy call costs more than the
    arithmetic it performs. Lists keep one pass at about a millisecond.
    """

    def __init__(self, observation):
        self.edge_index = np.asarray(observation["edge_index"])
        self.edge_prob = np.asarray(observation["edge_probability"], dtype=np.float64)
        self.topo = [int(v) for v in observation["topological_order"]]
        self.sinks = [int(v) for v in observation["sink_ids"]]
        self.n = observation["features"].shape[0]
        self.k = observation["features"].shape[1] - 7
        src, dst = self.edge_index
        order = np.argsort(dst, kind="stable")
        self.src = [int(v) for v in src[order]]
        self.prob = [float(v) for v in self.edge_prob[order]]
        self.start = [int(v) for v in np.searchsorted(dst[order], np.arange(self.n + 1))]

    def matches(self, observation):
        return (observation["features"].shape == (self.n, self.k + 7)
                and observation["edge_index"].shape == self.edge_index.shape
                and np.array_equal(observation["edge_index"], self.edge_index))

    def forward(self, belief):
        n, src, prob, start = self.n, self.src, self.prob, self.start
        values = belief.tolist()
        effective = [0.0] * n
        product = [1.0] * n
        for v in self.topo:
            share = 1.0
            for edge in range(start[v], start[v + 1]):
                share *= 1.0 - prob[edge] * effective[src[edge]]
            product[v] = share
            effective[v] = 1.0 - (1.0 - values[v]) * share
        return effective, product

    def derivatives(self, belief):
        """``d(expected sink errors)/d(belief[v])`` for every node, one backward pass."""
        n, src, prob, start = self.n, self.src, self.prob, self.start
        effective, product = self.forward(belief)
        survival = [1.0 - prob[e] * effective[src[e]] for e in range(len(prob))]
        values = belief.tolist()
        adjoint = [0.0] * n
        for sink in self.sinks:
            adjoint[sink] = 1.0
        for v in reversed(self.topo):
            lo, hi = start[v], start[v + 1]
            if hi <= lo:
                continue
            width = hi - lo
            # suffix[i] = prod_{j>i} survival[j]
            suffix = [1.0] * width
            for i in range(width - 2, -1, -1):
                suffix[i] = suffix[i + 1] * survival[lo + i + 1]
            prefix = adjoint[v] * (1.0 - values[v])
            for i in range(width):
                adjoint[src[lo + i]] += prefix * suffix[i] * prob[lo + i]
                prefix *= survival[lo + i]
        return np.asarray([product[v] * adjoint[v] for v in range(n)], dtype=np.float64)


def belief_column(observation):
    k = observation["features"].shape[1] - 7
    return observation["features"][:, k + 2].astype(np.float64)


def effective_column(observation):
    k = observation["features"].shape[1] - 7
    return observation["features"][:, k + 3].astype(np.float64)


def _top(scores, legal, count):
    candidates = np.flatnonzero(legal)
    if len(candidates) == 0:
        return []
    order = np.argsort(-scores[candidates], kind="stable")
    return [int(candidates[i]) for i in order[:count]]


class Planner:
    """Width-limited depth-two expectimax."""

    def __init__(self, width=6, second=4, p_catch=0.9, branches=("catch", "miss")):
        self.width, self.second = width, second
        self.p_catch = p_catch
        self.branches = branches
        self._topology = None

    def topology(self, observation):
        if self._topology is None or not self._topology.matches(observation):
            self._topology = Topology(observation)
        return self._topology

    def act(self, observation):
        topology = self.topology(observation)
        belief = belief_column(observation)
        effective = effective_column(observation)
        legal = np.asarray(observation["mask"], dtype=bool)
        base = topology.derivatives(belief)
        first_scores = base * belief
        shortlist = _top(first_scores, legal, self.width)
        if not shortlist:
            raise ValueError("no available nodes")

        best_value, best_node = -np.inf, shortlist[0]
        for node in shortlist:
            value = self._value_of(node, topology, belief, effective, legal, base)
            if value > best_value:
                best_value, best_node = value, node
            elif value == best_value and first_scores[node] > first_scores[best_node]:
                best_node = node
        return int(best_node)

    def _value_of(self, node, topology, belief, effective, legal, base):
        catch_probability = float(np.clip(self.p_catch * effective[node], 0.0, 1.0))
        caught = belief.copy()
        caught[node] = 0.0
        if "miss" in self.branches:
            missed = belief.copy()
            denominator = max(1e-12, 1.0 - self.p_catch * effective[node])
            missed[node] = min(1.0, belief[node] * (1.0 - self.p_catch) / denominator)
            outcomes = [(catch_probability, caught),
                        (1.0 - catch_probability, missed)]
        elif "catch" in self.branches:
            # Optimistic: follow only success with weight one, so the variant
            # cannot profit from the environment's approximate miss update.
            outcomes = [(1.0, caught)]
        else:
            raise ValueError("branches must contain 'catch'")

        legal_after = legal.copy()
        legal_after[node] = False
        total = 0.0
        for probability, after in outcomes:
            if probability <= 0.0:
                continue
            step_one = (belief[node] - after[node]) * base[node]
            gain = topology.derivatives(after) * after
            depth_two = max((gain[w] for w in _top(gain, legal_after, self.second)),
                            default=0.0)
            total += probability * (step_one + depth_two)
        return float(total)
