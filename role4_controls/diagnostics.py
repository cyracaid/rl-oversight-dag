"""Post-hoc diagnostics quoted in results/controls.md section 3 (NOT pre-registered).

Writes results/diagnostics.csv so every diagnostic number in controls.md is a cell of a committed file:

  hub_rank_corr     Spearman correlation of out-degree (number of children), original graph vs the
                    v1 rewired graph, per graph; median over the 100 graphs per family.
  sink_review_share share of all reviews spent on conclusion (sink) nodes, spike / flatten, per policy,
                    read from results/controls.csv.

    python3 diagnostics.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_controls as rc  # noqa: E402
from dag_role3 import generate_graph  # noqa: E402


def rankdata(x):
    """Average ranks (ties share the mean rank), numpy only."""
    x = np.asarray(x, dtype=float)
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty(len(x))
    ranks[order] = np.arange(len(x), dtype=float)
    for value in np.unique(x):
        tie = x == value
        ranks[tie] = ranks[tie].mean()
    return ranks


def spearman(a, b):
    ra, rb = rankdata(a), rankdata(b)
    if ra.std() == 0 or rb.std() == 0:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


def out_degrees(graph):
    return [len(c) for c in graph.children]


def hub_rank_corr(family, rewire_fn, seeds):
    rhos = []
    for s in seeds:
        g = generate_graph(family, s)
        rhos.append(spearman(out_degrees(g), out_degrees(rewire_fn(g, s))))
    return float(np.nanmedian(rhos))


def main():
    seeds = range(rc.START_SEED, rc.START_SEED + rc.N_SEEDS)
    rows = []
    for family in rc.FAMILIES:
        rows.append(dict(diagnostic="hub_rank_corr", family=family, condition="rewire_v1",
                         policy="", value=f"{hub_rank_corr(family, rc.rewire, seeds):.4f}"))
    with open(HERE / "results" / "controls.csv", encoding="utf-8") as f:
        episodes = [r for r in csv.DictReader(f)
                    if r["family"] == "spike" and r["condition"] == "flatten"]
    for policy in rc.POLICIES:
        total = on_sink = 0
        for r in episodes:
            if r["policy"] != policy:
                continue
            sinks = set(generate_graph("spike", int(r["graph_seed"])).sinks)
            actions = [int(a) for a in r["actions"].split()]
            total += len(actions)
            on_sink += sum(a in sinks for a in actions)
        rows.append(dict(diagnostic="sink_review_share", family="spike", condition="flatten",
                         policy=policy, value=f"{on_sink / total:.4f}"))
    rc.save(HERE / "results" / "diagnostics.csv", rows)
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
