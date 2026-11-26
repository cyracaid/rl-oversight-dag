"""Test whether rewire_order views omit sink_override (derived sinks instead)."""
import multiprocessing as mp
import random
import sys

import numpy as np

import core
from core import (REWIRE_SEED_ORDER, DRAW_STRIDE, DAG, episode_for, run_policy,
                  budget_for)


def build(graph, parents, keep_sinks):
    return DAG(parents=tuple(tuple(sorted(p)) for p in parents), types=graph.types,
               rates=graph.rates, family=graph.family, names=graph.names,
               sink_override=graph.sinks if keep_sinks else (),
               lam=graph.lam, spike_probability=graph.spike_probability)


def rewire_order_v(graph, graph_seed, k, keep_sinks):
    rng = random.Random(REWIRE_SEED_ORDER + DRAW_STRIDE * k + graph_seed)
    remaining = list(range(graph.n))
    order, parents = [], [()] * graph.n
    while remaining:
        feasible = [v for v in remaining if len(graph.parents[v]) <= len(order)]
        v = rng.choice(feasible)
        c = len(graph.parents[v])
        parents[v] = tuple(sorted(rng.sample(order, c))) if c else ()
        order.append(v)
        remaining.remove(v)
    return build(graph, parents, keep_sinks)


def work(args):
    family, seed, keep = args
    graph = core.generate_graph(family, seed)
    snap = episode_for(graph, seed)
    budget = budget_for(family)
    errs = []
    for k in range(10):
        view = rewire_order_v(graph, seed, k, keep)
        vsnap = episode_for(view, seed)
        e, _ = run_policy(graph, snap, view, vsnap, "marginal", budget)
        errs.append(e)
    return family, seed, errs


if __name__ == "__main__":
    want = sys.argv[1] if len(sys.argv) > 1 else "nosink"
    tasks = [(f, s, want == "keepsink") for f in ("ba", "er")
             for s in range(90000, 90100)]
    ctx = mp.get_context("fork")
    with ctx.Pool(6) as pool:
        results = list(pool.imap_unordered(work, tasks, chunksize=1))
    agg = {}
    for family, seed, errs in results:
        agg.setdefault(family, []).append(errs)
    for family in sorted(agg):
        arr = np.array(agg[family], dtype=float)
        print(want, family, "mean", round(float(arr.mean()), 4),
              "within", round(float(np.sqrt(np.mean(np.var(arr, axis=1, ddof=1)))), 4))
