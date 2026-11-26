"""Identify the rewire_order candidate-list convention: placement order vs sorted."""
import multiprocessing as mp
import random
import sys

import numpy as np

import core
from core import (REWIRE_SEED_ORDER, DRAW_STRIDE, episode_for, run_policy, budget_for,
                  _rebuild)


def rewire_order_variant(graph, graph_seed, k, sorted_cands):
    rng = random.Random(REWIRE_SEED_ORDER + DRAW_STRIDE * k + graph_seed)
    n = graph.n
    remaining = list(range(n))
    order = []
    parents = [()] * n
    while remaining:
        feasible = [v for v in remaining if len(graph.parents[v]) <= len(order)]
        v = rng.choice(feasible)
        count = len(graph.parents[v])
        pool = sorted(order) if sorted_cands else order
        parents[v] = tuple(sorted(rng.sample(pool, count))) if count else ()
        order.append(v)
        remaining.remove(v)
    return _rebuild(graph, parents, graph.family)


def work(args):
    family, seed, variant = args
    graph = core.generate_graph(family, seed)
    snap = episode_for(graph, seed)
    budget = budget_for(family)
    out = []
    for k in range(10):
        view = rewire_order_variant(graph, seed, k, variant == "sorted")
        vsnap = episode_for(view, seed)
        e, _ = run_policy(graph, snap, view, vsnap, "marginal", budget)
        out.append(e)
    return family, variant, seed, out


if __name__ == "__main__":
    tasks = [(f, s, v) for f in ("modular", "ba", "er")
             for s in range(90000, 90100) for v in ("placed", "sorted")]
    ctx = mp.get_context("fork")
    with ctx.Pool(6) as pool:
        results = list(pool.imap_unordered(work, tasks, chunksize=1))
    agg = {}
    for family, variant, seed, errs in results:
        agg.setdefault((family, variant), []).append(errs)
    for key in sorted(agg):
        arr = np.array(agg[key], dtype=float)  # (G, K)
        print(key, "mean", round(float(arr.mean()), 4),
              "per-draw means", [round(float(x), 3) for x in arr.mean(0)])
