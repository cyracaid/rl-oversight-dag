"""Probe rewire_order micro-variants: unsorted parent tuples / sorted pool ordering."""
import multiprocessing as mp
import random

import numpy as np

import core
from core import (REWIRE_SEED_ORDER, DRAW_STRIDE, DAG, episode_for, run_policy,
                  budget_for)


def build(graph, parents):
    return DAG(parents=tuple(tuple(p) for p in parents), types=graph.types,
               rates=graph.rates, family=graph.family, names=graph.names,
               sink_override=graph.sinks, lam=graph.lam,
               spike_probability=graph.spike_probability)


def rewire(graph, seed, k, sort_parents, sort_pool):
    rng = random.Random(REWIRE_SEED_ORDER + DRAW_STRIDE * k + seed)
    remaining, order, parents = list(range(graph.n)), [], [()] * graph.n
    while remaining:
        feasible = [v for v in remaining if len(graph.parents[v]) <= len(order)]
        v = rng.choice(feasible)
        c = len(graph.parents[v])
        pool = sorted(order) if sort_pool else order
        ps = rng.sample(pool, c) if c else []
        parents[v] = tuple(sorted(ps)) if sort_parents else tuple(ps)
        order.append(v)
        remaining.remove(v)
    return build(graph, parents)


def work(args):
    family, seed, sort_parents, sort_pool = args
    graph = core.generate_graph(family, seed)
    snap = episode_for(graph, seed)
    budget = budget_for(family)
    errs = []
    for k in range(10):
        view = rewire(graph, seed, k, sort_parents, sort_pool)
        vsnap = episode_for(view, seed)
        e, _ = run_policy(graph, snap, view, vsnap, "marginal", budget)
        errs.append(e)
    return family, sort_parents, sort_pool, errs


if __name__ == "__main__":
    variants = [(True, False), (False, False)]
    tasks = [(f, s, sp, sl) for f in ("ba", "er") for s in range(90000, 90100)
             for sp, sl in variants]
    ctx = mp.get_context("fork")
    with ctx.Pool(6) as pool:
        results = list(pool.imap_unordered(work, tasks, chunksize=1))
    agg = {}
    for family, sp, sl, errs in results:
        agg.setdefault((family, sp, sl), []).append(errs)
    for key in sorted(agg):
        arr = np.array(agg[key], dtype=float)
        print(key, "mean", round(float(arr.mean()), 4),
              "within", round(float(np.sqrt(np.mean(np.var(arr, axis=1, ddof=1)))), 4))
