#!/usr/bin/env python3
"""Where does graph-aware triage actually pay? Depth x concentration x size x budget.

The repo has three observations that do not fit on one axis: spike (graph-aware
clearly ahead), the N=21 sleep DAG (+0.03, indistinguishable), the hypothetical
ticket DAG (+0.03, indistinguishable). That looks like a boundary, so measure it
on a controlled generator: same environment, same budget fraction, same pairing,
only the graph shape changes.

Factors
    layers         number of layers in a layered DAG (2..8)
    s              concentration in scaled_rates(k=10, s); larger s = error mass
                   on fewer types
    n              node count
    budget_frac    reviews / n

Outcome
    residual sink errors after the budget saturates at 0 for most graphs at
    budget 0.2n, which makes mean differences look large while almost every
    graph is a tie. So the recorded outcome is

        caught = (e_none - e_policy) / e_none

    i.e. the fraction of the no-review error mass that the policy removed.
    Graphs with e_none == 0 carry no signal; they are counted in
    ``dropped_no_errors`` and excluded, never silently averaged in.

    Delta = mean(caught_marginal) - mean(caught_confidence): positive means the
    marginal rule removes more. win/tie/loss counts are over graphs.

Nothing here trains. All policies are the public rules from dag_role3.policies.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
import time
from pathlib import Path

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "role3 improvement"))

from dag_role3 import DAG, sample_episode                      # noqa: E402
from dag_role3.graphs import scaled_rates                     # noqa: E402
from dag_role3.policies import run_public_policy              # noqa: E402

POLICIES = ("random", "hub", "confidence", "structural", "type_prior", "marginal")
CELLS = {
    "n": (80, 200, 500),
    "layers": (2, 3, 4, 6, 8),
    "s": (0.8, 1.2, 1.6, 2.4),
}


def make_graph(n: int, layers: int, s: float, seed: int, k: int = 10, lam: float = 0.8,
               sinks: int = 20) -> DAG:
    """Layered DAG with a *fixed* sink-layer size.

    Fixing the sink layer is what makes depth comparable: with equal partitioning a
    deeper graph also gets a smaller sink layer, so "depth" would silently change both
    the path length and the number of graded conclusions.
    """
    if layers < 2 or n - sinks < layers - 1:
        raise ValueError("need n - sinks >= layers - 1 >= 1")
    rng = random.Random(seed)
    body = n - sinks
    parts: list[list[int]] = [[] for _ in range(layers)]
    start = 0
    for layer in range(layers - 1):
        end = body * (layer + 1) // (layers - 1)
        parts[layer] = list(range(start, end))
        start = end
    parts[-1] = list(range(body, n))
    parents: list[list[int]] = [[] for _ in range(n)]
    for layer in range(1, layers):
        for i in parts[layer]:
            cands = parts[layer - 1]
            parents[i] = sorted(rng.sample(cands, k=min(rng.choice((1, 2)), len(cands))))
    types = tuple(rng.randrange(k) for _ in range(n))
    return DAG(tuple(map(tuple, parents)), types, scaled_rates(k, s),
               f"phase-n{n}-L{layers}-s{s}", lam=lam, sink_override=tuple(parts[-1]))


def budget_for(n: int, frac: float) -> int:
    return max(2, int(round(frac * n)))


def run_cell(n: int, layers: int, s: float, frac: float, graphs: int,
             start_seed: int) -> dict:
    budget = budget_for(n, frac)
    caught: dict[str, list[float]] = {p: [] for p in POLICIES}
    residual: dict[str, list[float]] = {p: [] for p in POLICIES}
    dropped = 0
    for g in range(graphs):
        seed = start_seed + g
        graph = make_graph(n, layers, s, seed)
        snap = sample_episode(graph, seed + 20000)
        base, _ = run_public_policy(graph, snap, "none", budget)
        base = float(base)
        if base <= 0:
            dropped += 1
            continue
        for policy in POLICIES:
            errors, _ = run_public_policy(graph, snap, policy, budget)
            errors = float(errors)
            residual[policy].append(errors)
            caught[policy].append((base - errors) / base)
    return {"caught": caught, "residual": residual, "dropped": dropped,
            "budget": budget}


def paired_delta(a: list[float], b: list[float], reps: int = 2000, seed: int = 5) -> dict:
    x, y = np.array(a), np.array(b)
    d = x - y
    rng = np.random.default_rng(seed)
    if len(d) < 2:
        return {"delta": float(d.mean()) if len(d) else float("nan"),
                "lo": float("nan"), "hi": float("nan"),
                "win": float("nan"), "tie": float("nan"), "loss": float("nan")}
    idx = rng.integers(0, len(d), size=(reps, len(d)))
    boot = d[idx].mean(axis=1)
    return {"delta": float(d.mean()),
            "lo": float(np.percentile(boot, 2.5)),
            "hi": float(np.percentile(boot, 97.5)),
            "win": float((d > 1e-12).mean()),
            "tie": float((np.abs(d) <= 1e-12).mean()),
            "loss": float((d < -1e-12).mean())}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", nargs="+", type=int, default=list(CELLS["n"]))
    ap.add_argument("--layers", nargs="+", type=int, default=list(CELLS["layers"]))
    ap.add_argument("--s", nargs="+", type=float, default=list(CELLS["s"]))
    ap.add_argument("--budget-frac", type=float, default=0.10)
    ap.add_argument("--graphs", type=int, default=60)
    ap.add_argument("--start-seed", type=int, default=90000)
    ap.add_argument("--out", type=Path,
                    default=Path(__file__).resolve().parent / "results" / "boundary-phase-v1")
    args = ap.parse_args()
    if args.start_seed < 90000:
        ap.error("use held-out seeds >= 90000")

    args.out.mkdir(parents=True, exist_ok=True)
    cells, summary = [], []
    t0 = time.time()
    for n in args.n:
        for layers in args.layers:
            for s in args.s:
                res = run_cell(n, layers, s, args.budget_frac, args.graphs, args.start_seed)
                kept = len(res["caught"]["marginal"])
                for policy in POLICIES:
                    vals = np.array(res["caught"][policy])
                    cells.append({"n": n, "layers": layers, "s": s,
                                  "budget": res["budget"], "policy": policy,
                                  "n_graphs": kept, "dropped_no_errors": res["dropped"],
                                  "mean_caught": float(vals.mean()) if kept else float("nan"),
                                  "mean_residual": float(np.mean(res["residual"][policy]))
                                  if kept else float("nan")})
                d = paired_delta(res["caught"]["marginal"], res["caught"]["confidence"])
                summary.append({"n": n, "layers": layers, "s": s, "budget": res["budget"],
                                "n_graphs": kept, "dropped_no_errors": res["dropped"],
                                "none_residual": float(np.mean([
                                    r for r in res["residual"]["confidence"]])),
                                "confidence": float(np.mean(res["caught"]["confidence"]))
                                if kept else float("nan"),
                                "marginal": float(np.mean(res["caught"]["marginal"]))
                                if kept else float("nan"),
                                "type_prior": float(np.mean(res["caught"]["type_prior"]))
                                if kept else float("nan"),
                                "hub": float(np.mean(res["caught"]["hub"]))
                                if kept else float("nan"),
                                "random": float(np.mean(res["caught"]["random"]))
                                if kept else float("nan"),
                                **d})
                print(f"n={n:3d} L={layers} s={s:.1f} K={res['budget']:3d} "
                      f"conf={summary[-1]['confidence']:.3f} marg={summary[-1]['marginal']:.3f} "
                      f"prior={summary[-1]['type_prior']:.3f} "
                      f"Δ={d['delta']:+.3f} [{d['lo']:+.3f},{d['hi']:+.3f}] "
                      f"W/T/L={d['win']:.2f}/{d['tie']:.2f}/{d['loss']:.2f} "
                      f"({time.time()-t0:.0f}s)", flush=True)

    with (args.out / "cells.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(cells[0]))
        w.writeheader()
        w.writerows(cells)
    with (args.out / "summary.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary[0]))
        w.writeheader()
        w.writerows(summary)
    (args.out / "manifest.json").write_text(json.dumps({
        "python": sys.version.split()[0],
        "outcome": "caught = (none - policy) / none, per graph",
        "graphs": args.graphs,
        "start_seed": args.start_seed,
        "budget_frac": args.budget_frac,
        "lam": 0.8,
        "k_types": 10,
        "sink_layer": 20,
        "policies": list(POLICIES),
        "elapsed_s": round(time.time() - t0, 1),
    }, indent=2) + "\n")
    print(f"\nwrote {args.out}  ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
