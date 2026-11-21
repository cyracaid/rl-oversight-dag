#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Standard-library particle belief over the hidden error state of a DAG (port of `belief.ParticleBelief`).

Same model, same public methods (`gain`, `best_action`, `observe`, `p_err`, `p_base`, `n_degenerate`) and the same
bitset representation (one Python int per node / edge, bit j = particle j) as `belief.py`; numpy is not used. The target is
the evidence-dag Python runtime, which is standard-library only (`dependencies = []`).

What changes:
  * sampling: Bernoulli(p) bitsets are built from random bit strings by the binary-expansion recursion (K = 24 bits,
    so p is represented to about 6e-8); `random.Random(seed)` replaces numpy's generator, so the same seed does NOT give
    the same particles as `belief.py` (the two implementations are compared statistically and against exact enumeration);
  * resampling: systematic resampling over per-particle weights, applied to every bitset by permuting its bits;
  * an observation that is impossible under the model (a flag with no erroneous particle, or every particle excluded by a
    catch rate of 1) is counted in `n_degenerate` and leaves the particles unchanged.

Review observation model (matches the simulators' transition):
    flagged  iff  err_v and caught,   caught ~ Bernoulli(p_catch)
    flagged  =>   base_v := False      (fixes v only if the error originated at v)
"""
import random

PRECISION_BITS = 24


class ParticleBelief:
    def __init__(self, parents, topo, sinks, edge_prob, base_prob, p_catch, n_particles=128, seed=0):
        if n_particles % 8:
            raise ValueError("n_particles must be a multiple of 8")
        if not 0.0 <= p_catch <= 1.0:
            raise ValueError("p_catch must be in [0, 1]")
        self.N = len(parents)
        self.M = n_particles
        self.p_catch = p_catch
        self.topo = list(topo)
        self.rng = random.Random(seed)

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

        self.base_bits = [self._bernoulli_bits(base_prob[i]) for i in range(self.N)]
        self.coin_bits = [self._bernoulli_bits(p) for p in probs]
        self.n_degenerate = 0
        self._refresh()

    # ------------------------------------------------------------ internals
    def _bernoulli_bits(self, p):
        """M independent Bernoulli(p) bits as one int, from random bit strings (binary-expansion recursion)."""
        if p <= 0.0:
            return 0
        if p >= 1.0:
            return (1 << self.M) - 1
        value = round(p * (1 << PRECISION_BITS))
        bits = 0
        for k in range(PRECISION_BITS):          # least significant bit of the fraction first
            random_bits = self.rng.getrandbits(self.M)
            bits = (bits | random_bits) if (value >> k) & 1 else (bits & random_bits)
        return bits

    def _refresh(self):
        err = [0] * self.N
        for i in self.topo:
            x = self.base_bits[i]
            for p, e in self.in_edges[i]:
                x |= err[p] & self.coin_bits[e]
            err[i] = x
        self.err = err

    def _permute(self, row, index):
        """New int whose bit k is bit index[k] of `row`."""
        text = format(row, "b").zfill(self.M)[::-1]       # text[j] is bit j
        return int("".join(text[j] for j in index)[::-1], 2)

    def _resample(self, weights):
        total = sum(weights)
        running, cumulative = 0.0, []
        for w in weights:
            running += w / total
            cumulative.append(running)
        offset = self.rng.random()
        index, j = [], 0
        for k in range(self.M):
            u = (offset + k) / self.M
            while j < self.M - 1 and cumulative[j] < u:
                j += 1
            index.append(j)
        self.base_bits = [self._permute(row, index) for row in self.base_bits]
        self.coin_bits = [self._permute(row, index) for row in self.coin_bits]

    # ------------------------------------------------------------ queries
    def p_base(self):
        return [row.bit_count() / self.M for row in self.base_bits]

    def p_err(self):
        return [row.bit_count() / self.M for row in self.err]

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

    def ranking(self, available):
        """All available nodes with their expected sink-error reduction, best first (ties by node index)."""
        scored = [(self.gain(i), i) for i in range(self.N) if available[i]]
        return [(i, g) for g, i in sorted(scored, key=lambda t: (-t[0], t[1]))]

    # ------------------------------------------------------------ update
    def observe(self, i, flagged):
        has_err = [(self.err[i] >> j) & 1 for j in range(self.M)]
        if flagged:
            if any(has_err):
                self._resample([float(x) for x in has_err])
            else:                       # no particle explains the flag
                self.n_degenerate += 1
            self.base_bits[i] = 0
        elif any(has_err):
            weights = [1.0 - self.p_catch * x for x in has_err]
            if sum(weights) > 0:
                self._resample(weights)
            else:                       # the model excludes every particle
                self.n_degenerate += 1
        self._refresh()
