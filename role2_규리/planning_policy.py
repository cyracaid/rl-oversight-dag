"""Two-review planning with public mean-field beliefs and reviewer feedback."""

from dataclasses import dataclass
import math

import numpy as np


WIDTH = 6
P_CATCH = 0.9
_EPSILON = 1e-6  # Same likelihood floor as the episode's feedback filter.
_TIE_TOL = 1e-12


@dataclass(frozen=True)
class Decision:
    action: int
    greedy_action: int
    adaptive_action: int
    open_loop_action: int
    flag_next: int
    miss_next: int
    flag_prob: float


def _best(nodes, values, immediate):
    """Break numerical ties by immediate gain, then ascending node ID."""
    tied = nodes[values >= np.max(values) - _TIE_TOL]
    tie_gains = immediate[tied]
    return int(np.min(tied[tie_gains >= np.max(tie_gains) - _TIE_TOL]))


class PlanningPolicy:
    def __init__(self, obs_at_start, width=WIDTH, p_catch=P_CATCH):
        if width < 1 or not 0 <= p_catch <= 1:
            raise ValueError("width must be positive and p_catch must be a probability")
        self.width = width
        self.p_catch = p_catch
        self.sinks = np.asarray(obs_at_start["sink_ids"], dtype=int)
        n = len(obs_at_start["mask"])
        parents = [[] for _ in range(n)]
        for (u, v), prob in zip(obs_at_start["edge_index"].T, obs_at_start["edge_probability"]):
            parents[v].append((u, prob))
        depth = np.zeros(n, dtype=int)
        for v in obs_at_start["topological_order"]:
            depth[v] = max((depth[u] + 1 for u, _ in parents[v]), default=0)
        self.layers = []
        for level in range(depth.max() + 1):
            nodes = np.flatnonzero(depth == level)
            slots = max(len(parents[v]) for v in nodes)
            parent_ids = np.zeros((len(nodes), slots), dtype=int)
            edge_probs = np.zeros((len(nodes), slots))
            for row, v in enumerate(nodes):
                for slot, (u, prob) in enumerate(parents[v]):
                    parent_ids[row, slot] = u
                    edge_probs[row, slot] = prob
            self.layers.append((nodes, parent_ids, edge_probs))

    def _marginal_scores(self, source):
        """Batched role3 marginal_scores: q times the derivative of sink risk."""
        effective = np.zeros_like(source)
        clean_parents = np.ones_like(source)
        survivals = []
        for nodes, parents, probs in self.layers:
            survival = 1.0 - effective[:, parents] * probs
            clean_parents[:, nodes] = np.prod(survival, axis=-1)
            effective[:, nodes] = 1.0 - (1.0 - source[:, nodes]) * clean_parents[:, nodes]
            survivals.append(survival)

        adjoint = np.zeros_like(source)
        adjoint[:, self.sinks] = 1.0
        for (nodes, parents, probs), survival in zip(reversed(self.layers), reversed(survivals)):
            left = adjoint[:, nodes] * (1.0 - source[:, nodes])
            prefixes = []
            for slot in range(parents.shape[1]):
                prefixes.append(left)
                left = left * survival[:, :, slot]
            right = 1.0
            for slot in reversed(range(parents.shape[1])):
                # Prefix/suffix products support certain propagation; siblings
                # may share a parent so its derivatives must be accumulated.
                contribution = prefixes[slot] * right * probs[:, slot]
                np.add.at(adjoint.T, parents[:, slot], contribution.T)
                right = right * survival[:, :, slot]
        return source * clean_parents * adjoint

    def decide(self, normal_obs, noise_obs, log_odds, kind):
        """Choose from two synchronized public observations at the current review."""
        if kind not in ("mixture", "open_loop", "adaptive"):
            raise ValueError(f"unknown planning policy {kind!r}")
        legal = np.flatnonzero(normal_obs["mask"])
        if not legal.size:
            raise ValueError("no available nodes")
        # Compute both weights directly, retaining small posterior masses.
        tail = math.exp(-abs(log_odds))
        weights = np.array([1.0, tail] if log_odds >= 0 else [tail, 1.0]) / (1.0 + tail)
        obs = (normal_obs, noise_obs)
        source = np.stack([o["features"][:, -5] for o in obs]).astype(float)
        effective = np.stack([o["features"][:, -4] for o in obs]).astype(float)
        raw_flag = self.p_catch * effective
        likelihood = np.clip(raw_flag, _EPSILON, 1.0 - _EPSILON)
        flag_prob = weights @ likelihood
        immediate = self.p_catch * (weights @ self._marginal_scores(source))
        greedy = _best(legal, immediate[legal], immediate)
        if kind == "mixture" or normal_obs["budget_left"] <= 1 or len(legal) == 1:
            return Decision(greedy, greedy, -1, -1, -1, -1, float(flag_prob[greedy]))

        # Prune only the first review. Every other eligible node remains a
        # possible second review under either observation.
        remaining = legal
        candidates = []
        for _ in range(min(self.width, len(legal))):
            a = _best(remaining, immediate[remaining], immediate)
            candidates.append(a)
            remaining = remaining[remaining != a]
        first = np.asarray(candidates)
        first_flag = likelihood[:, first].T
        per_model = np.stack([first_flag, 1.0 - first_flag], axis=1)
        joint = per_model * weights
        outcome_prob = joint.sum(axis=2)
        posterior = joint / outcome_prob[:, :, None]

        # Axes are first review, observed outcome (flag/miss), model and node.
        # On a flag the local source is repaired. A miss updates its probability
        # using the probability of an effective error, including inherited risk.
        k, n = len(first), source.shape[1]
        branch_source = np.broadcast_to(source, (k, 2, 2, n)).copy()
        miss = source[:, first] * (1.0 - self.p_catch) / np.maximum(1e-12, 1.0 - raw_flag[:, first])
        for i, a in enumerate(first):
            branch_source[i, 0, :, a] = 0.0
            branch_source[i, 1, :, a] = np.minimum(1.0, miss[:, i])
        gains = self._marginal_scores(branch_source.reshape(-1, n)).reshape(k, 2, 2, n)
        second = self.p_catch * np.einsum("kom,komn->kon", posterior, gains)
        fixed_second = np.einsum("ko,kon->kn", outcome_prob, second)
        fixed_second[:, ~normal_obs["mask"]] = -np.inf
        second[:, :, ~normal_obs["mask"]] = -np.inf
        fixed_second[np.arange(k), first] = -np.inf
        second[np.arange(k), :, first] = -np.inf
        adaptive_value = immediate[first] + np.sum(outcome_prob * second.max(axis=2), axis=1)
        open_value = immediate[first] + fixed_second.max(axis=1)
        adaptive = _best(first, adaptive_value, immediate)
        open_loop = _best(first, open_value, immediate)
        action = adaptive if kind == "adaptive" else open_loop
        i = candidates.index(action)
        if kind == "adaptive":
            flag_next, miss_next = (_best(legal, row[legal], immediate) for row in second[i])
        else:
            flag_next = miss_next = _best(legal, fixed_second[i, legal], immediate)
        return Decision(action, greedy, adaptive, open_loop, flag_next, miss_next, float(flag_prob[action]))
