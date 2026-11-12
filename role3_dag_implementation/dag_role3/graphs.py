"""DAG generators for the oversight/review-scheduling simulator.

Uses independent public graph seeds; nodes are indexed in topological order except
for validation-friendly custom DAGs. No restricted sleep records are used.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from collections import deque
from typing import Tuple
import math
import random

import networkx as nx
import numpy as np

SPIKE_RATES = (0.01, 0.03, 0.08, 0.15, 0.25)
REAL_RATES = (0.35, 0.15, 0.12, 0.10, 0.08, 0.05)


def scaled_rates(k: int = 10, s: float = 1.2):
    weights = np.arange(1, k + 1, dtype=np.float64) ** (-s)
    weights /= weights.sum()
    return tuple((0.02 + 0.38 * weights).tolist())


@dataclass(frozen=True)
class DAG:
    parents: Tuple[Tuple[int, ...], ...]
    types: Tuple[int, ...]
    rates: Tuple[float, ...]
    family: str = "custom"
    names: Tuple[str, ...] = ()
    sink_override: Tuple[int, ...] = ()
    lam: float = 0.8
    spike_probability: float | None = None
    topo: Tuple[int, ...] = field(init=False, repr=False)
    children: Tuple[Tuple[int, ...], ...] = field(init=False, repr=False)
    sinks: Tuple[int, ...] = field(init=False)
    sink_reach: Tuple[int, ...] = field(init=False)
    layers: Tuple[int, ...] = field(init=False)

    def __post_init__(self):
        n = len(self.parents)
        if n == 0 or len(self.types) != n:
            raise ValueError("parents/types dimensions disagree or empty DAG")
        if any(not 0 <= t < len(self.rates) for t in self.types):
            raise ValueError("type outside rate table")
        if self.names and len(self.names) != n:
            raise ValueError("names length disagrees")
        if any(not 0.0 <= r <= 1.0 for r in self.rates):
            raise ValueError("invalid base error probability")
        indeg = [0] * n
        children = [[] for _ in range(n)]
        for v, ps in enumerate(self.parents):
            if len(set(ps)) != len(ps):
                raise ValueError("duplicate parents")
            for u in ps:
                if u < 0 or u >= n or u == v:
                    raise ValueError("invalid edge or self-loop")
                children[u].append(v)
                indeg[v] += 1
        q = deque(i for i in range(n) if indeg[i] == 0)
        topo = []
        while q:
            u = q.popleft()
            topo.append(u)
            for v in children[u]:
                indeg[v] -= 1
                if indeg[v] == 0:
                    q.append(v)
        if len(topo) != n:
            raise ValueError("graph must be a DAG; cycle found")
        sinks = tuple(self.sink_override) if self.sink_override else tuple(i for i in range(n) if not children[i])
        if not sinks or any(i < 0 or i >= n for i in sinks) or len(set(sinks)) != len(sinks):
            raise ValueError("invalid sinks")
        # A named conclusion can have outgoing edges to another conclusion;
        # the real-pipeline reference explicitly lists four layer-3 conclusions.
        sinkset = set(sinks)
        reach = [set() for _ in range(n)]
        layer = [0] * n
        for u in topo:
            for v in children[u]:
                layer[v] = max(layer[v], layer[u] + 1)
        for u in reversed(topo):
            r = {u} if u in sinkset else set()
            for v in children[u]:
                r.update(reach[v])
            reach[u] = r
        object.__setattr__(self, "topo", tuple(topo))
        object.__setattr__(self, "children", tuple(tuple(x) for x in children))
        object.__setattr__(self, "sinks", sinks)
        object.__setattr__(self, "sink_reach", tuple(len(x) for x in reach))
        object.__setattr__(self, "layers", tuple(layer))

    @property
    def n(self):
        return len(self.parents)

    @property
    def edge_count(self):
        return sum(len(x) for x in self.parents)

    def edge_index(self):
        """Shape (2, E) numpy int64 array: source parent, target child."""
        src, dst = [], []
        for v, ps in enumerate(self.parents):
            for u in ps:
                src.append(u)
                dst.append(v)
        return np.asarray([src, dst], dtype=np.int64).reshape(2, -1)


def _make_random_types(n, k, rng, clustered=False):
    if clustered:
        # Experimental assumption, not estimated from real records.
        block = max(1, n // 10)
        major = [rng.randrange(k) for _ in range(10)]
        return tuple(major[min(9, i // block)] if rng.random() < 0.65
                     else rng.randrange(k) for i in range(n))
    return tuple(rng.randrange(k) for _ in range(n))


def gen_spike(seed: int, n: int = 80, layers: int = 4) -> DAG:
    if n < layers or layers < 2:
        raise ValueError("n must be >= layers >= 2")
    rng = random.Random(seed)
    partitions = [[] for _ in range(layers)]
    # contiguous layers; works even when n not divisible by layers
    for i in range(n):
        partitions[min(layers - 1, i * layers // n)].append(i)
    parents = [[] for _ in range(n)]
    for l in range(1, layers):
        for i in partitions[l]:
            cands = partitions[l - 1]
            parents[i] = sorted(rng.sample(cands, k=min(rng.choice((1, 2)), len(cands))))
    # Exactly the 80-node spike environment's 0.6 Bernoulli edge propagation.
    return DAG(tuple(map(tuple, parents)), _make_random_types(n, 5, rng),
               SPIKE_RATES, "spike", lam=0.0, spike_probability=0.6,
               sink_override=tuple(partitions[-1]))


def gen_modular(seed: int, n: int = 500, clusters: int = 10) -> DAG:
    if n < clusters * 2 or n % clusters != 0:
        raise ValueError("n must be divisible by clusters and at least 2*clusters")
    rng = random.Random(seed)
    per = n // clusters
    parents = [[] for _ in range(n)]
    for c in range(clusters):
        start = c * per
        for v in range(start + 1, start + per):
            parents[v] = rng.sample(range(start, v), k=min(rng.choice((1, 2)), v - start))
    for c in range(clusters - 1):
        interface = list(range((c+1) * per - min(3, per), (c+1)*per))
        for v in range((c+1)*per, min((c+1)*per+5, n)):
            if rng.random() < 0.5:
                parents[v].append(rng.choice(interface))
    parents = [tuple(sorted(set(ps))) for ps in parents]
    return DAG(tuple(parents), _make_random_types(n, 10, rng, clustered=True),
               scaled_rates(), "modular", lam=0.8)


def _orient_graph(undirected: nx.Graph, seed: int, family: str) -> DAG:
    n = undirected.number_of_nodes()
    parents = [[] for _ in range(n)]
    for u, v in undirected.edges:
        a, b = sorted((int(u), int(v)))
        parents[b].append(a)
    rng = random.Random(seed + 99_983)
    return DAG(tuple(tuple(sorted(ps)) for ps in parents),
               _make_random_types(n, 10, rng), scaled_rates(), family, lam=0.8)


def gen_ba(seed: int, n: int = 500, m: int = 3) -> DAG:
    if not (1 <= m < n):
        raise ValueError("1 <= m < n required")
    return _orient_graph(nx.barabasi_albert_graph(n, m, seed=seed), seed, "ba")


def gen_er(seed: int, n: int = 500, p: float = 0.015) -> DAG:
    if not 0.0 <= p <= 1.0:
        raise ValueError("p must be a probability")
    return _orient_graph(nx.erdos_renyi_graph(n, p, seed=seed), seed, "er")


# 21-node public domain-knowledge graph; it is NOT an individual-level dataset.
_REAL_ROWS = [
    ("time_bed", 0, 0, ()), ("time_sleep", 0, 0, ()),
    ("time_awake", 0, 0, ()), ("time_getup", 0, 0, ()),
    ("sol_self", 0, 2, ()), ("waso_self", 0, 5, ()),
    ("waso_count", 0, 5, ()), ("nap", 0, 5, ()),
    ("bed_sleep_diff", 1, 2, ("time_bed", "time_sleep")),
    ("sleep_awake_diff", 1, 4, ("time_sleep", "time_awake")),
    ("awake_getup_diff", 1, 1, ("time_awake", "time_getup")),
    ("SOL_calc", 1, 2, ("bed_sleep_diff", "sol_self")),
    ("WASO_calc", 1, 5, ("waso_self", "waso_count")),
    ("TST", 2, 0, ("sleep_awake_diff", "WASO_calc")),
    ("TIB", 2, 0, ("time_bed", "time_getup")),
    ("SE", 2, 0, ("TST", "TIB")),
    ("TST_TIB_ratio", 2, 0, ("TST", "TIB")),
    ("SOL_validity", 3, 0, ("SOL_calc", "bed_sleep_diff")),
    ("WASO_validity", 3, 5, ("WASO_calc", "nap")),
    ("SE_conclusion", 3, 0, ("SE", "TST_TIB_ratio")),
    ("record_quality", 3, 0, ("SOL_validity", "SE_conclusion", "WASO_validity")),
]


def gen_real() -> DAG:
    names = [row[0] for row in _REAL_ROWS]
    lookup = {name: i for i, name in enumerate(names)}
    parents = tuple(tuple(lookup[p] for p in r[3]) for r in _REAL_ROWS)
    sinks = tuple(i for i, r in enumerate(_REAL_ROWS) if r[1] == 3)
    return DAG(parents=parents, types=tuple(r[2] for r in _REAL_ROWS),
               rates=REAL_RATES, names=tuple(names),
               sink_override=sinks, family="real", lam=0.9)


def generate_graph(family: str, seed: int = 1, n: int | None = None) -> DAG:
    family = family.lower()
    if family == "spike":
        return gen_spike(seed, n=n or 80)
    if family == "modular":
        return gen_modular(seed, n=n or 500)
    if family == "ba":
        return gen_ba(seed, n=n or 500)
    if family == "er":
        return gen_er(seed, n=n or 500)
    if family == "real":
        return gen_real()
    raise ValueError("family must be spike, modular, ba, er or real")
