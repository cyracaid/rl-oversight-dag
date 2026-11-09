#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Real sleep-pipeline dependency DAG (from splsleep SCHEMA / operational definitions).

Leaves (raw diary fields) → derived diffs → sleep metrics → conclusion nodes.

Error types and rates come from manual_error_correction_updated.csv:
  order_error 76%, then awake_getup_diff / bed_sleep_diff / sleep_awake_equal / 24h.

This is the "real pipeline" answer to "the 80/500-node graph is a toy".
"""
import math
import random
import numpy as np

N_SEEDS = 8
P_CATCH = 0.9
BUDGET = 8            # ~25% of 32 nodes
LAMBDA = 0.9

# ---- nodes (id, layer, type) -------------------------------------------------
# types follow the real correction file's relative frequencies
TYPES = [
    "order_error",             # 76% of corrections
    "awake_getup_diff_error",  # 5.3%
    "bed_sleep_diff_error",    # 4.0%
    "sleep_awake_equal_error", # 2.7%
    "sleep_awake_24h_error",   # 1.3%
    "metric_spike",            # residual / other
]
TYPE_RATE = {          # per-node base error rate by type (order_error highest)
    "order_error": 0.35,
    "awake_getup_diff_error": 0.15,
    "bed_sleep_diff_error": 0.12,
    "sleep_awake_equal_error": 0.10,
    "sleep_awake_24h_error": 0.08,
    "metric_spike": 0.05,
}

# (name, layer, type)
NODES = [
    # layer 0: raw diary leaves
    ("time_bed",            0, "order_error"),
    ("time_sleep",          0, "order_error"),
    ("time_awake",          0, "order_error"),
    ("time_getup",          0, "order_error"),
    ("sol_self",            0, "bed_sleep_diff_error"),
    ("waso_self",           0, "metric_spike"),
    ("waso_count",          0, "metric_spike"),
    ("nap",                 0, "metric_spike"),
    # layer 1: pairwise diffs / calculated durations
    ("bed_sleep_diff",      1, "bed_sleep_diff_error"),
    ("sleep_awake_diff",    1, "sleep_awake_24h_error"),
    ("awake_getup_diff",    1, "awake_getup_diff_error"),
    ("SOL_calc",            1, "bed_sleep_diff_error"),
    ("WASO_calc",           1, "metric_spike"),
    # layer 2: sleep metrics
    ("TST",                 2, "order_error"),
    ("TIB",                 2, "order_error"),
    ("SE",                  2, "order_error"),
    ("TST_TIB_ratio",       2, "order_error"),
    # layer 3: conclusions / deliverables (sinks)
    ("SOL_validity",        3, "order_error"),
    ("WASO_validity",       3, "metric_spike"),
    ("SE_conclusion",       3, "order_error"),
    ("record_quality",      3, "order_error"),
]
NAME = [n[0] for n in NODES]
LAYER = [n[1] for n in NODES]
TYPE = [n[2] for n in NODES]
N = len(NODES)
SINKS = [i for i in range(N) if LAYER[i] == 3]

# parents (DAG)
PARENTS = {
    "time_bed": [],
    "time_sleep": [],
    "time_awake": [],
    "time_getup": [],
    "sol_self": [],
    "waso_self": [],
    "waso_count": [],
    "nap": [],
    "bed_sleep_diff": ["time_bed", "time_sleep"],
    "sleep_awake_diff": ["time_sleep", "time_awake"],
    "awake_getup_diff": ["time_awake", "time_getup"],
    "SOL_calc": ["bed_sleep_diff", "sol_self"],
    "WASO_calc": ["waso_self", "waso_count"],
    "TST": ["sleep_awake_diff", "WASO_calc"],
    "TIB": ["time_bed", "time_getup"],
    "SE": ["TST", "TIB"],
    "TST_TIB_ratio": ["TST", "TIB"],
    "SOL_validity": ["SOL_calc", "bed_sleep_diff"],
    "WASO_validity": ["WASO_calc", "nap"],
    "SE_conclusion": ["SE", "TST_TIB_ratio"],
    "record_quality": ["SOL_validity", "SE_conclusion", "WASO_validity"],
}
NAME2ID = {n: i for i, n in enumerate(NAME)}


def propagate(base, coins, rng):
    err = [False] * N
    for i, nd in enumerate(NODES):
        err[i] = base[i]
        if not err[i]:
            for p in PARENTS[nd[0]]:
                pi = NAME2ID[p]
                if err[pi] and coins[(pi, i)]:
                    err[i] = True
                    break
    return err


def run_seed(seed):
    rng = random.Random(seed)
    coins = {}
    for name, ps in PARENTS.items():
        i = NAME2ID[name]
        for p in ps:
            pi = NAME2ID[p]
            w = rng.uniform(0.6, 1.4)
            coins[(pi, i)] = rng.random() < (1.0 - math.exp(-LAMBDA * w))

    base = [rng.random() < TYPE_RATE[TYPE[i]] for i in range(N)]
    conf = []
    for i in range(N):
        sig = -1.5 if base[i] else 1.5
        sig -= 0.5 * (TYPE_RATE[TYPE[i]] - 0.15)
        conf.append(1.0 / (1.0 + math.exp(-(sig + rng.gauss(0, 1.0)))))

    topo = sorted(range(N), key=lambda i: (LAYER[i], i))

    def sinks_err(err):
        return sum(1 for i in SINKS if err[i])

    no_rev = sinks_err(propagate(base, coins, rng))

    idx = list(range(N))
    rng.shuffle(idx)
    pol_rand = idx[:BUDGET]
    pol_thresh = sorted(idx, key=lambda i: conf[i])[:BUDGET]
    # hub = number of children
    children = [0] * N
    for name, ps in PARENTS.items():
        i = NAME2ID[name]
        for p in ps:
            children[pi] += 1
    pol_hub = sorted(idx, key=lambda i: -children[i])[:BUDGET]

    def apply(order):
        b = list(base)
        e = propagate(b, coins, rng)
        for i in order:
            if e[i] and rng.random() < P_CATCH:
                b[i] = False
                e = propagate(b, coins, rng)
        return sinks_err(e)

    return {
        "no_review": no_rev,
        "random": apply(pol_rand),
        "threshold": apply(pol_thresh),
        "hub": apply(pol_hub),
        "n_base_err": sum(base),
    }


def main():
    print("=" * 60)
    print(f"Real sleep-pipeline DAG: N={N} nodes, sinks={len(SINKS)}, "
          f"budget={BUDGET}, λ={LAMBDA}")
    print("Types:", {t: round(TYPE_RATE[t], 2) for t in TYPES})
    agg = {k: [] for k in ("no_review", "random", "threshold", "hub", "n_base_err")}
    for seed in range(1, N_SEEDS + 1):
        r = run_seed(seed)
        for k, v in r.items():
            agg[k].append(v)
        print(f"  seed {seed}  no={r['no_review']}  rand={r['random']}  "
              f"thr={r['threshold']}  hub={r['hub']}  base_err={r['n_base_err']}")
    print("\nmean over seeds:")
    for k, v in agg.items():
        print(f"  {k:<12}{sum(v)/len(v):.2f}  {v}")
    lines = [
        f"Real sleep-pipeline DAG N={N}, budget={BUDGET}, {N_SEEDS} seeds",
        "",
        "| policy | sink errors |",
        "|---|---|",
        f"| no review | {sum(agg['no_review'])/N_SEEDS:.2f} |",
        f"| random | {sum(agg['random'])/N_SEEDS:.2f} |",
        f"| conf threshold | {sum(agg['threshold'])/N_SEEDS:.2f} |",
        f"| hub (children) | {sum(agg['hub'])/N_SEEDS:.2f} |",
    ]
    with open("real_pipeline_table.md", "w") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote real_pipeline_table.md")


if __name__ == "__main__":
    main()
