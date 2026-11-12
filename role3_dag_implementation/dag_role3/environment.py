"""Auditable finite-horizon oversight environment.

Hidden truth (source errors, edge coins, reviewer uniforms) is never included in
observations. A review, if it catches *observed* error, removes ONLY the local
source error; inherited errors survive until their upstream source is corrected.
This is explicitly not a do(X_v=correct) intervention.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Tuple
import math
import random

import numpy as np
from .graphs import DAG


def sigmoid(x):
    return 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, x))))


def logit(p):
    p = max(1e-8, min(1 - 1e-8, float(p)))
    return math.log(p / (1 - p))


@dataclass(frozen=True)
class EpisodeSnapshot:
    """Privileged frozen sample for repeated policy comparisons. Never feed to an agent."""
    source_errors: Tuple[bool, ...]
    edge_coins: Dict[Tuple[int, int], bool]
    edge_probs: Dict[Tuple[int, int], float]
    confidence: Tuple[float, ...]
    review_uniforms: Tuple[float, ...]
    seed: int


def sample_episode(graph: DAG, seed: int, confidence_mode: str = "normal") -> EpisodeSnapshot:
    if confidence_mode not in ("normal", "noise", "oracle"):
        raise ValueError("mode must be normal, noise, oracle")
    rng = random.Random(seed)
    edge_coins, edge_probs = {}, {}
    for v, ps in enumerate(graph.parents):
        for u in ps:
            p = graph.spike_probability
            if p is None:
                w = rng.uniform(0.5, 1.5)
                p = 1.0 - math.exp(-graph.lam * w)
            edge_probs[u, v] = p
            edge_coins[u, v] = rng.random() < p
    base = tuple(rng.random() < graph.rates[graph.types[i]] for i in range(graph.n))
    conf = []
    for i in range(graph.n):
        if confidence_mode == "noise":
            conf.append(rng.random())
        elif confidence_mode == "oracle":
            conf.append(0.0 if base[i] else 1.0)   # NOT deployable
        else:
            mean = (-1.5 if base[i] else 1.5) - 0.4 * (graph.rates[graph.types[i]] - 0.15)
            conf.append(sigmoid(mean + rng.gauss(0, 1.2)))
    # Strict common random numbers: reviewer outcomes depend on node, not review order.
    review_uniforms = tuple(rng.random() for _ in range(graph.n))
    return EpisodeSnapshot(base, edge_coins, edge_probs, tuple(conf), review_uniforms, seed)


def propagate(graph: DAG, source_errors, edge_coins):
    """Recompute entire graph with the SAME episode edge coins after every fix."""
    effective = [False] * graph.n
    for i in graph.topo:
        effective[i] = bool(source_errors[i]) or any(
            effective[parent] and edge_coins[parent, i] for parent in graph.parents[i]
        )
    return tuple(effective)


def initial_belief(graph: DAG, conf: Tuple[float, ...], confidence_mode: str = "normal"):
    """P(local source error | confidence, type), not ground truth.

    Normal mode uses the correct Gaussian confidence likelihood only. It is
    NOT the full particle filter posterior after sequential observations.
    """
    probs = []
    for i, c in enumerate(conf):
        prior = float(graph.rates[graph.types[i]])
        if confidence_mode == "noise":
            probs.append(prior)
        elif confidence_mode == "oracle":
            probs.append(1.0 - c)
        else:
            z = logit(c)
            bias = -0.4 * (prior - 0.15)
            mu_err, mu_good = -1.5 + bias, 1.5 + bias
            # log p(z|err) - log p(z|good), sigma=1.2
            llr = ((z - mu_good)**2 - (z - mu_err)**2) / (2 * 1.2**2)
            probs.append(sigmoid(logit(prior) + llr))
    return np.array(probs, dtype=np.float64)


class OversightEnv:
    """Gym-like interface: reset() -> obs; step(action) -> obs,reward,done,info.

    Every observation field is permissible for a deployable policy. For
    debugging only, use final_audit() after the episode is complete.
    """
    def __init__(self, graph: DAG, snapshot: EpisodeSnapshot,
                 budget: int | None = None, p_catch: float = 0.9,
                 confidence_mode: str = "normal"):
        if budget is None:
            budget = 16 if graph.family == "spike" else 8 if graph.family == "real" else 50
        if budget < 0 or budget > graph.n:
            raise ValueError("budget must be between 0 and n")
        if not (0 <= p_catch <= 1):
            raise ValueError("p_catch must be a probability")
        if len(snapshot.source_errors) != graph.n:
            raise ValueError("snapshot n mismatch")
        self.graph, self.snapshot = graph, snapshot
        self.budget, self.p_catch = int(budget), float(p_catch)
        self.confidence_mode = confidence_mode
        self.reset()

    @classmethod
    def from_seed(cls, graph: DAG, seed: int, budget: int | None = None,
                  p_catch: float = 0.9, confidence_mode: str = "normal"):
        return cls(graph, sample_episode(graph, seed, confidence_mode),
                   budget, p_catch, confidence_mode)

    def reset(self):
        self._base = list(self.snapshot.source_errors)
        self._effective = propagate(self.graph, self._base, self.snapshot.edge_coins)
        self._reviewed = [False] * self.graph.n
        self._flagged = [False] * self.graph.n
        self._belief_base = initial_belief(self.graph, self.snapshot.confidence, self.confidence_mode)
        self._budget_left = self.budget
        self._done = self.budget == 0
        self._trace = []
        self._initial_sink_errors = sum(self._effective[i] for i in self.graph.sinks)
        return self.observation()

    def _public_error_probabilities(self):
        """Forward mean-field proxy; not particle conditioning or hidden error."""
        p = np.zeros(self.graph.n, dtype=np.float64)
        for i in self.graph.topo:
            clean_from_parents = 1.0
            for u in self.graph.parents[i]:
                clean_from_parents *= (1 - p[u] * self.snapshot.edge_probs[u, i])
            p[i] = 1 - (1 - self._belief_base[i]) * clean_from_parents
        return p

    def observation(self):
        n, k = self.graph.n, len(self.graph.rates)
        f = np.zeros((n, k + 7), dtype=np.float32)
        f[np.arange(n), list(self.graph.types)] = 1.0
        f[:, k] = np.asarray(self.snapshot.confidence, dtype=np.float32)
        f[:, k + 1] = np.log1p(self.graph.sink_reach) / math.log1p(n)
        f[:, k + 2] = self._belief_base
        f[:, k + 3] = self._public_error_probabilities()
        f[:, k + 4] = self._reviewed
        f[:, k + 5] = self._flagged
        f[:, k + 6] = self._budget_left / max(1, self.budget)
        return {
            "features": f.copy(),
            "mask": np.logical_not(self._reviewed),
            "edge_index": self.graph.edge_index(),
            "sink_ids": np.asarray(self.graph.sinks, dtype=np.int64),
            "budget_left": self._budget_left,
            "family": self.graph.family,
            "node_names": list(self.graph.names) if self.graph.names else [f"v{i}" for i in range(n)],
        }

    def step(self, action: int):
        if self._done:
            raise RuntimeError("episode is done; call reset()")
        if not isinstance(action, (int, np.integer)) or not 0 <= action < self.graph.n:
            raise ValueError("action must be a valid node index")
        a = int(action)
        if self._reviewed[a]:
            raise ValueError("cannot inspect the same node twice")
        before = sum(self._effective[i] for i in self.graph.sinks)
        flagged = bool(self._effective[a]) and self.snapshot.review_uniforms[a] < self.p_catch
        self._reviewed[a] = True
        self._flagged[a] = flagged
        if flagged:
            self._base[a] = False
            self._effective = propagate(self.graph, self._base, self.snapshot.edge_coins)
            # The reviewed node now has no OWN source error, although it may remain
            # effectively wrong due to an unfixed parent.
            self._belief_base[a] = 0.0
        else:
            # A miss is weak evidence against a local source error. This is an
            # approximate belief update (ignores inherited-error correlations).
            q = self._belief_base[a]
            self._belief_base[a] = (q * (1 - self.p_catch)) / max(1e-12, 1 - self.p_catch*q)
        self._budget_left -= 1
        self._done = self._budget_left == 0
        after = sum(self._effective[i] for i in self.graph.sinks)
        self._trace.append({"step": len(self._trace) + 1, "node": a,
                            "node_name": (self.graph.names[a] if self.graph.names else f"v{a}"),
                            "flagged": flagged, "sink_errors_before": before,
                            "sink_errors_after": after})
        # Terminal-only reward; no intermediate privileged sink error is leaked.
        reward = -float(after) if self._done else 0.0
        info = {"flagged": flagged, "node": a}
        if self._done:
            info["sink_errors"] = after
            info["initial_sink_errors"] = self._initial_sink_errors
        return self.observation(), reward, self._done, info

    def final_audit(self):
        """For evaluators after completion only; NEVER pass to a learned policy."""
        if not self._done:
            raise RuntimeError("final_audit is available only after episode completion")
        return {"initial_sink_errors": self._initial_sink_errors,
                "final_sink_errors": sum(self._effective[i] for i in self.graph.sinks),
                "initial_base_errors": sum(self.snapshot.source_errors),
                "remaining_base_errors": sum(self._base),
                "trace": list(self._trace)}

    def no_review_score(self):
        """Evaluator-only reference; do not use this in a policy."""
        return self._initial_sink_errors
