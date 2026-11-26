"""v2 controls clean-room: conditions, aggregation, verdicts, gates.

Run:
  python runner.py --start-seed 90000 --jobs 6 --out out90000
  python runner.py --start-seed 7100  --jobs 6 --out out7100
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time

import numpy as np

import core
from core import (assert_same_episode, budget_for, episode_for, flatten_snapshot,
                  rewire_index, rewire_order, run_policy)

FAMILIES = ("spike", "modular", "ba", "er", "real")
POLICIES = ("confidence", "structural", "marginal")
RULES = ("intact", "flatten", "rewire_index", "rewire_order")
ORDER_FAMILIES = ("modular", "ba", "er")
DRAWS = 10

REPO = "/Users/sloblucyra/Documents/강화학습"


def interval(xs):
    # Copied verbatim from role3 improvement/run_benchmark.py::interval.
    xs = np.asarray(xs, dtype=float)
    if len(xs) < 2:
        return "", ""
    rng = np.random.default_rng(411)
    means = [xs[rng.integers(len(xs), size=(100, len(xs)))].mean(axis=1)
             for _ in range(20)]
    return tuple(np.quantile(np.concatenate(means), [.025, .975]))


# ------------------------------------------------------------------- worker
def run_graph(task):
    family, seed = task
    graph = core.generate_graph(family, seed)
    snap = episode_for(graph, seed)
    budget = budget_for(family)
    errors, actions0 = {}, {}

    def record(rule, draw, pol, e, acts=None):
        errors.setdefault((rule, pol), []).append(e)
        if draw == 0:
            actions0[(rule, pol)] = " ".join(map(str, acts))

    for pol in POLICIES:
        e, a = run_policy(graph, snap, graph, snap, pol, budget)
        record("intact", 0, pol, e, a)

    flat = flatten_snapshot(snap)
    for pol in POLICIES:
        e, a = run_policy(graph, flat, graph, snap, pol, budget)
        record("flatten", 0, pol, e, a)

    views = []
    for k in range(DRAWS):
        view = rewire_index(graph, seed, k)
        vsnap = episode_for(view, seed)
        assert_same_episode(snap, vsnap)
        views.append((view, vsnap))
    for k, (view, vsnap) in enumerate(views):
        for pol in POLICIES:
            e, a = run_policy(graph, snap, view, vsnap, pol, budget)
            record("rewire_index", k, pol, e, a)

    if family in ORDER_FAMILIES:
        for k in range(DRAWS):
            oview = rewire_order(graph, seed, k)
            osnap = episode_for(oview, seed)
            assert_same_episode(snap, osnap)
            for pol in POLICIES:
                e, a = run_policy(graph, snap, oview, osnap, pol, budget)
                record("rewire_order", k, pol, e, a)

    return dict(family=family, seed=seed, n=graph.n, edges=graph.edge_count,
                sinks=len(graph.sinks), budget=budget, errors=errors,
                actions0=actions0)


# ------------------------------------------------------------------- gates
def _read_rows(path):
    with open(path, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def check_gates(results, start_seed):
    bench = {(r["family"], int(r["graph_seed"]), r["policy"]): r
             for r in _read_rows(f"{REPO}/role3 improvement/outputs/v3/benchmark_role3.csv")}
    ctl = {}
    for r in _read_rows(f"{REPO}/role4_controls/results/controls.csv"):
        ctl[(r["family"], int(r["graph_seed"]), r["condition"], r["policy"])] = r
    failures = []
    for res in results:
        fam, seed = res["family"], res["seed"]
        for pol in POLICIES:
            ref = bench[(fam, seed, pol)]
            mine_e = res["errors"][("intact", pol)][0]
            mine_a = res["actions0"][("intact", pol)]
            if int(ref["sink_errors"]) != mine_e or ref["actions"] != mine_a:
                failures.append(("intact-bench", fam, seed, pol,
                                 int(ref["sink_errors"]), mine_e))
        for cond, rule in (("flatten", "flatten"), ("rewire", "rewire_index")):
            for pol in POLICIES:
                ref = ctl[(fam, seed, cond, pol)]
                mine_e = res["errors"][(rule, pol)][0]
                mine_a = res["actions0"][(rule, pol)]
                if int(ref["sink_errors"]) != mine_e or ref["actions"] != mine_a:
                    failures.append((cond, fam, seed, pol,
                                     int(ref["sink_errors"]), mine_e))
    return failures


# --------------------------------------------------------------- aggregation
def verdict(intact_lo, ctrl_lo, ctrl_hi, margin):
    if intact_lo <= 0:
        return "no-intact-advantage"
    if ctrl_lo > 0:
        return "survives"
    if ctrl_lo >= -margin and ctrl_hi <= margin:
        return "removed"
    return "inconclusive"


def summarise(err):
    """err[(family, rule, policy)][seed] -> list of per-draw sink errors."""
    rows = []
    for family in FAMILIES:
        for rule in RULES:
            if rule == "rewire_order" and family not in ORDER_FAMILIES:
                continue
            seeds = sorted(err[(family, "intact", "confidence")])
            for pol in POLICIES:
                per_graph = np.array([[float(x) for x in err[(family, rule, pol)][s]]
                                      for s in seeds])          # (G, K)
                mean_graph = per_graph.mean(axis=1)
                c_err = np.array([float(err[(family, rule, "confidence")][s][0])
                                  for s in seeds])
                gains = [float(np.mean(c_err - per_graph[:, k]))
                         for k in range(per_graph.shape[1])]
                graph_gain = c_err - mean_graph
                gain = float(np.mean(graph_gain))
                lo, hi = interval(graph_gain)
                if per_graph.shape[1] > 1:
                    # pooled within-graph SD across draws (sample variance, ddof=1)
                    within = float(np.sqrt(np.mean(np.var(per_graph, axis=1, ddof=1))))
                else:
                    within = 0.0
                between = float(np.std(mean_graph, ddof=1)) if len(seeds) > 1 else ""
                rows.append(dict(family=family, rule=rule, policy=pol,
                                 n_graphs=len(seeds), n_draws=per_graph.shape[1],
                                 mean_sink_errors=float(np.mean(per_graph)),
                                 gain_vs_confidence=gain, paired_lo=lo, paired_hi=hi,
                                 draw_gain_min=min(gains), draw_gain_max=max(gains),
                                 within_graph_sd=within, between_graph_sd=between))
    # margin + verdict: only for control rows; verdict only for non-reference policies
    intact = {(r["family"], r["policy"]): r for r in rows if r["rule"] == "intact"}
    for r in rows:
        m = 0.20 * intact[(r["family"], r["policy"])]["gain_vs_confidence"]
        if r["rule"] == "intact":
            r["margin"] = ""
            r["verdict"] = ""
        else:
            r["margin"] = m
            r["verdict"] = ("" if r["policy"] == "confidence"
                            else verdict(intact[(r["family"], r["policy"])]["paired_lo"],
                                         r["paired_lo"], r["paired_hi"], m))
        if r["n_draws"] == 1:
            r["draw_gain_min"] = ""
            r["draw_gain_max"] = ""
    return rows



COLUMNS = ["family", "rule", "policy", "n_graphs", "n_draws", "mean_sink_errors",
           "gain_vs_confidence", "paired_lo", "paired_hi", "margin",
           "draw_gain_min", "draw_gain_max", "within_graph_sd",
           "between_graph_sd", "verdict"]


def _fmt(value):
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, float):
        return f"{value:.4f}"
    return value


def write_csv(path, rows, columns, fmt=False):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=columns)
        w.writeheader()
        for r in rows:
            w.writerow({c: (_fmt(r[c]) if fmt else r[c]) for c in columns})


def load_rows(path):
    """Rebuild the aggregation structure from a rows.csv file."""
    import collections
    err = collections.defaultdict(dict)
    for r in _read_rows(path):
        err[(r["family"], r["condition"], r["policy"])].setdefault(
            int(r["graph_seed"]), {})[int(r["draw"])] = float(r["sink_errors"])
    return {k: {s: [v[d] for d in sorted(v)] for s, v in d.items()}
            for k, d in err.items()}



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start-seed", type=int, default=90000)
    ap.add_argument("--seeds", type=int, default=100)
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--out", type=str, required=True)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    tasks = [(f, s) for f in FAMILIES
             for s in range(args.start_seed, args.start_seed + args.seeds)]
    started = time.perf_counter()
    if args.jobs > 1:
        import multiprocessing as mp
        ctx = mp.get_context("fork")
        with ctx.Pool(args.jobs) as pool:
            results = list(pool.imap_unordered(run_graph, tasks, chunksize=1))
    else:
        results = [run_graph(t) for t in tasks]
    elapsed = time.perf_counter() - started
    print(f"graph runs done in {elapsed:.1f}s", flush=True)

    # row-level record (provenance; actions kept for draw 0 only)
    rows = []
    err = {}
    for res in sorted(results, key=lambda r: (FAMILIES.index(r["family"]), r["seed"])):
        for (rule, pol), vals in res["errors"].items():
            err.setdefault((res["family"], rule, pol), {})[res["seed"]] = vals
            for k, e in enumerate(vals):
                rows.append(dict(family=res["family"], graph_seed=res["seed"],
                                 episode_seed=20_000 + res["seed"], condition=rule,
                                 draw=k, policy=pol, budget=res["budget"],
                                 sink_errors=e,
                                 actions=res["actions0"].get((rule, pol), "") if k == 0 else ""))
    write_csv(f"{args.out}/rows.csv", rows,
              ["family", "graph_seed", "episode_seed", "condition", "draw", "policy",
               "budget", "sink_errors", "actions"])

    if args.start_seed == 90000:
        failures = check_gates(results, args.start_seed)
        if failures:
            print(f"GATE FAIL ({len(failures)} rows) — writing nothing else", flush=True)
            for f in failures[:20]:
                print("  ", f)
            sys.exit(2)
        print("GATES PASS (intact vs benchmark, flatten+rewire0 vs controls.csv)", flush=True)

    summary = summarise(err)
    write_csv(f"{args.out}/summary.csv", summary, COLUMNS, fmt=True)
    print(f"summary: {args.out}/summary.csv ({len(summary)} rows), "
          f"total {time.perf_counter() - started:.1f}s", flush=True)


if __name__ == "__main__":
    main()
