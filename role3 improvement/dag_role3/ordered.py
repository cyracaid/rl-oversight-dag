"""Order-aware benchmark variant (v2) — the M2' order channel.

Pre-registration: `PREREGISTER_ORDERED_BENCHMARK.md`, including its same-day amendment.
Only the *segment chain* and the differences derived from it change; every other node keeps
v1 semantics.

What the mechanism is. A record can hold segment clocks in the wrong order: every value is
plausible for a segment of its kind, nothing about a single node looks wrong, and the only
evidence is that the chain as a whole cannot be increasing. Exactly one transposition happens
per affected episode, over two positions at distance >= 2, so the misplacement cannot be read
off one node's neighbours (see the amendment for why the adjacent version was rejected).

What the action does. Reviewing a misplaced segment repairs the differences that involve it,
with the usual `p_catch`. Reviewing an innocent segment spends the budget and repairs nothing.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Sequence, Tuple

import numpy as np

from .environment import EpisodeSnapshot, OversightEnv, sample_episode
from .graphs import DAG


@dataclass(frozen=True)
class OrderedSpec:
    family: str
    chain: Tuple[int, ...]          # segment nodes, chain[i] -> chain[i+1]
    derived: Tuple[Tuple[int, int, int], ...]   # (derived node, left position, right position)
    clock_start: Tuple[float, float]
    gap: Tuple[float, float]
    noise_sd: float = 8.0
    noise_clip: float = 30.0


ORDERED_SPECS = {
    "real": OrderedSpec(
        family="real",
        chain=(0, 1, 2, 3),
        derived=((8, 0, 1), (9, 1, 2), (10, 2, 3)),
        clock_start=(1200.0, 1560.0),
        gap=(20.0, 480.0),
    ),
    "ticket": OrderedSpec(
        family="ticket",
        chain=(0, 1, 2),
        derived=((9, 0, 1), (10, 0, 2)),
        clock_start=(0.0, 60.0),
        gap=(5.0, 900.0),
    ),
}

DEFAULT_Q = 0.50


@dataclass(frozen=True)
class OrderedEpisode:
    """A v1 snapshot plus the ordered view. `misplaced` is hidden truth."""
    snapshot: EpisodeSnapshot
    clocks: Tuple[float, ...]          # recorded clock per chain position
    misplaced: Tuple[int, ...]         # chain positions holding a value that is not theirs
    transposed: Tuple[int, int] | None # chain positions exchanged, in position order
    spec: OrderedSpec

    @property
    def chain(self):
        return self.spec.chain

    def monotone_residual(self) -> Tuple[float, ...]:
        """`clock[i] - clock[i+1]` for each adjacent pair; positive means the order is broken."""
        c = self.clocks
        return tuple(c[i] - c[i + 1] for i in range(len(c) - 1))


def eligible_pairs(spec: OrderedSpec) -> Tuple[Tuple[int, int], ...]:
    """Pairs at distance >= 2. Adjacent pairs are excluded on purpose (see the amendment)."""
    n = len(spec.chain)
    return tuple((i, j) for i in range(n) for j in range(i + 2, n))


def sample_ordered_episode(graph: DAG, seed: int, q: float = DEFAULT_Q,
                           confidence_mode: str = "normal") -> OrderedEpisode:
    """Sample a v2 episode. With `q = 0` the result is v1's episode, untouched."""
    if not 0.0 <= q <= 1.0:
        raise ValueError("q must be a probability")
    spec = ORDERED_SPECS[graph.family]
    base = sample_episode(graph, seed, confidence_mode)
    rng = random.Random(seed ^ 0x0DDBA11)

    # True clocks along the chain, increasing by construction.
    t = [rng.uniform(*spec.clock_start)]
    for _ in range(len(spec.chain) - 1):
        t.append(t[-1] + rng.uniform(*spec.gap))
    recorded = list(t)

    pairs = eligible_pairs(spec)
    transposed = None
    if pairs and rng.random() < q:
        transposed = pairs[rng.randrange(len(pairs))]
        i, j = transposed
        recorded[i], recorded[j] = recorded[j], recorded[i]

    clocks = tuple(v + max(-spec.noise_clip, min(spec.noise_clip, rng.gauss(0.0, spec.noise_sd)))
                   for v in recorded)

    if transposed is None:
        return OrderedEpisode(base, clocks, (), None, spec)

    i, j = transposed
    misplaced = tuple(sorted((i, j)))
    source = list(base.source_errors)
    # A segment whose recorded clock is not its own is wrong; a difference is wrong when the
    # recorded order makes it impossible.
    for pos in misplaced:
        source[spec.chain[pos]] = True
    for node, left, right in spec.derived:
        if clocks[left] >= clocks[right]:
            source[node] = True
        else:
            source[node] = bool(base.source_errors[node])
    snapshot = EpisodeSnapshot(
        source_errors=tuple(source),
        edge_coins=dict(base.edge_coins),
        edge_probs=dict(base.edge_probs),
        confidence=base.confidence,
        review_uniforms=base.review_uniforms,
        seed=base.seed,
    )
    return OrderedEpisode(snapshot, clocks, misplaced, transposed, spec)


class OrderedEnv(OversightEnv):
    """v1 environment with one added transition: repairing a misplaced segment repairs the
    differences that involve it. Everything else is inherited unchanged.
    """

    def __init__(self, graph: DAG, episode: OrderedEpisode, budget: int | None = None,
                 p_catch: float = 0.9, confidence_mode: str = "normal"):
        if episode.spec.family != graph.family:
            raise ValueError("episode and graph disagree on family")
        self.episode = episode
        super().__init__(graph, episode.snapshot, budget=budget, p_catch=p_catch,
                         confidence_mode=confidence_mode)

    def observation(self):
        obs = super().observation()
        spec = self.episode.spec
        obs = dict(obs)
        obs["chain_ids"] = np.asarray(spec.chain, dtype=np.int64)
        obs["clocks"] = np.asarray(self.episode.clocks, dtype=np.float64)
        obs["monotone_residual"] = np.asarray(self.episode.monotone_residual(), dtype=np.float64)
        obs["family"] = f"{spec.family}_order"
        return obs

    def _derived_touching(self, position: int) -> Tuple[int, ...]:
        spec = self.episode.spec
        return tuple(node for node, left, right in spec.derived
                     if position in (left, right))

    def step(self, action: int):
        obs, reward, done, info = super().step(action)
        # The only deviation from v1: a misplaced segment repairs the differences derived
        # from it, in addition to its own source error.
        spec = self.episode.spec
        position = next((p for p, node in enumerate(spec.chain) if node == int(action)), None)
        if position is None or position not in self.episode.misplaced or not info["flagged"]:
            return obs, reward, done, info
        from .environment import propagate
        touched = [node for node in self._derived_touching(position)
                   if self._base[node] and self._repaired(node)]
        for node in touched:
            self._base[node] = False
        if touched:
            self._effective = propagate(self.graph, self._base, self.snapshot.edge_coins)
            after = sum(self._effective[i] for i in self.graph.sinks)
            self._trace[-1]["sink_errors_after"] = after
            if done:
                reward = -float(after)
                info["sink_errors"] = after
            # The observation above was built before this repair; rebuild it so no policy
            # acts on a stale derived state.
            obs = self.observation()
        return obs, reward, done, info

    def _repaired(self, derived_node: int) -> bool:
        """A difference can be re-derived once every misplaced position it depends on has been
        reviewed. The action being processed is already marked reviewed by `super().step`."""
        spec = self.episode.spec
        left, right = next((l, r) for node, l, r in spec.derived if node == derived_node)
        return all(spec.chain[pos] in (None,) or self._reviewed[spec.chain[pos]]
                   for pos in (left, right) if pos in self.episode.misplaced)
