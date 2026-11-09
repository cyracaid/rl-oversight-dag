#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Confidence model + particle-filter belief over the hidden error state of a DAG.

Everything a deployable policy is allowed to know lives here:
  - graph structure and per-edge propagation probabilities,
  - a calibrated per-node error prior derived from the confidence score,
  - the outcomes of its own reviews ("flagged" = reviewer found the node wrong).
The true error state is never read. Policies that read it are oracles.

Confidence model (shared by every simulator so generator and posterior agree):
    logit(conf_v) = s_v - TYPE_COEF * (p_type - 0.15) + N(0, SIGMA^2)
    s_v = -MU if v has a base error else +MU

Belief: M particles, each a full sample of (base errors, edge coins). Particles
are stored as bitsets (one Python int per node / edge, bit j = particle j), so
propagating all particles at once costs one pass over the DAG.

Review observation model (matches the simulators' transition):
    flagged  iff  err_v and caught,   caught ~ Bernoulli(p_catch)
    flagged  =>   base_v := False      (fixes v only if the error originated at v)
"""
import math
import numpy as np

CONF_MU = 1.5
CONF_TYPE_COEF = 0.4
CONF_SIGMA = 1.2


def sample_conf(is_err, p_type, rng):
    """Draw one confidence score. Uses exactly one rng.gauss call."""
    signal = -CONF_MU if is_err else CONF_MU
    signal -= CONF_TYPE_COEF * (p_type - 0.15)
    logit = signal + rng.gauss(0, CONF_SIGMA)
    return 1.0 / (1.0 + math.exp(-logit))


def conf_posterior(conf, p_type):
    """P(base error | conf) under the confidence model with prior p_type."""
    c = min(max(conf, 1e-12), 1.0 - 1e-12)
    logit = math.log(c / (1.0 - c))
    shift = CONF_TYPE_COEF * (p_type - 0.15)
    mu_err, mu_ok = -CONF_MU - shift, CONF_MU - shift
    s2 = 2.0 * CONF_SIGMA ** 2
    log_odds = (math.log(p_type) - math.log(1.0 - p_type)
                - (logit - mu_err) ** 2 / s2 + (logit - mu_ok) ** 2 / s2)
    return 1.0 / (1.0 + math.exp(-log_odds))


def _pack_rows(X):
    packed = np.packbits(X, axis=1, bitorder="little")
    return [int.from_bytes(row.tobytes(), "little") for row in packed]


class ParticleBelief:
    def __init__(self, parents, topo, sinks, edge_prob, base_prob, p_catch,
                 n_particles=128, seed=0):
        if n_particles % 8:
            raise ValueError("n_particles must be a multiple of 8")
        self.N = len(parents)
        self.M = n_particles
        self.p_catch = p_catch
        self.topo = list(topo)
        self.rng = np.random.default_rng(seed)

        self.in_edges = [[] for _ in range(self.N)]
        probs = []
        for i, ps in enumerate(parents):
            for p in ps:
                self.in_edges[i].append((p, len(probs)))
                probs.append(edge_prob[(p, i)])
        self.is_sink = [False] * self.N
        for s in sinks:
            self.is_sink[s] = True

        children = [[] for _ in range(self.N)]
        for i, ps in enumerate(parents):
            for p in ps:
                children[p].append(i)
        pos = {v: k for k, v in enumerate(self.topo)}
        reach = [None] * self.N
        for i in reversed(self.topo):
            r = set()
            for c in children[i]:
                r.add(c)
                r |= reach[c]
            reach[i] = r
        self.desc = [sorted(reach[i], key=pos.__getitem__) for i in range(self.N)]

        M = self.M
        self.B = self.rng.random((self.N, M)) < np.asarray(base_prob)[:, None]
        self.C = self.rng.random((len(probs), M)) < np.asarray(probs)[:, None]
        self.n_degenerate = 0
        self._refresh()

    # ------------------------------------------------------------ internals
    def _refresh(self):
        self.base_bits = _pack_rows(self.B)
        self.coin_bits = _pack_rows(self.C) if len(self.C) else []
        err = [0] * self.N
        for i in self.topo:
            x = self.base_bits[i]
            for p, e in self.in_edges[i]:
                x |= err[p] & self.coin_bits[e]
            err[i] = x
        self.err = err

    def _bits_to_bool(self, x):
        raw = np.frombuffer(x.to_bytes(self.M // 8, "little"), dtype=np.uint8)
        return np.unpackbits(raw, bitorder="little")[: self.M].astype(bool)

    def _resample(self, weights):
        total = weights.sum()
        cdf = np.cumsum(weights / total)
        u = (self.rng.random() + np.arange(self.M)) / self.M
        idx = np.minimum(np.searchsorted(cdf, u), self.M - 1)
        self.B = self.B[:, idx]
        self.C = self.C[:, idx]

    # ------------------------------------------------------------ queries
    def p_base(self):
        return self.B.mean(axis=1)

    def p_err(self):
        return np.array([x.bit_count() for x in self.err], dtype=float) / self.M

    def gain(self, i):
        """Expected drop in sink errors if node i is reviewed now."""
        if not self.base_bits[i]:
            return 0.0
        err, coin = self.err, self.coin_bits
        new = {}
        x = 0
        for p, e in self.in_edges[i]:
            x |= err[p] & coin[e]
        new[i] = x
        removed = (err[i].bit_count() - x.bit_count()) if self.is_sink[i] else 0
        for j in self.desc[i]:
            x = self.base_bits[j]
            for p, e in self.in_edges[j]:
                x |= new.get(p, err[p]) & coin[e]
            new[j] = x
            if self.is_sink[j]:
                removed += err[j].bit_count() - x.bit_count()
        return self.p_catch * removed / self.M

    def best_action(self, available):
        """Adaptive greedy: max expected sink-error reduction among available nodes."""
        best, best_gain = None, 0.0
        for i in range(self.N):
            if available[i]:
                g = self.gain(i)
                if g > best_gain:
                    best, best_gain = i, g
        if best is None:      # every gain is zero: fall back to most likely error
            pe = self.p_err()
            best = max((i for i in range(self.N) if available[i]), key=lambda i: pe[i])
        return best

    # ------------------------------------------------------------ update
    def observe(self, i, flagged):
        has_err = self._bits_to_bool(self.err[i])
        if flagged:
            if has_err.any():
                self._resample(has_err.astype(float))
            else:                       # no particle explains the flag
                self.n_degenerate += 1
            self.B[i, :] = False
        elif has_err.any():
            self._resample(1.0 - self.p_catch * has_err)
        self._refresh()
