"""Boundary of the shared (q, delta) model: off-grid shifts and two deltas at once.

The scope model was fitted and confirmed where its own assumption holds: one
locality, one shared delta, and a delta that sits exactly on the grid. Those are
properties of the generator, not of a real score pipeline. Two questions follow,
and this sweep answers only these two:

  off-grid   the same single-delta corruption, but the delta is between grid
             points (+-1.6, +-2.37, +-3.6). Does the model still find the nearest
             cell, and does undoing that cell still recover the ordering scale?
  two deltas two disjoint layers (source and sink) moved by different amounts
             (+-3/+3 and -4/+2 in both orders), at half and full coverage. The
             model carries one delta per graph, so this is outside its envelope;
             the question is how much that costs relative to `shrink`, which
             already represents "each node moved by any delta".

No parameter is refitted. p0 = 0.20 comes from scope-v1's calibration fit and
pi = 0.15 from shrink-v1; both are constants here. Graphs are seeds 3800-3999,
never used before. Rules and predictions are frozen in
PREREGISTER_SCOPE_ROBUST.md before the first 3800 seed is evaluated.
"""

import argparse
import csv
from dataclasses import replace
from functools import partial
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import platform

import numpy as np

from _env import ROLE3, ROOT, ensure_role3

ensure_role3()
from dag_role3 import OversightEnv, generate_graph, sample_episode
from dag_role3.policies import choose
from evaluate_conditions import BUDGET, sha256
from evaluate_corruption import (corruption_pool, corrupt_snapshot, vector_logit,
                                 vector_sigmoid)
from evaluate_scope import (DELTAS, EPISODE_OFFSET, PI, Q_GRID, plain, run_scope)
from evaluate_shrink import MU_ERR, MU_GOOD, SIGMA, run_shrink

P0 = 0.20                 # scope-v1's calibration fit; not refitted here
POLICIES = ("oracle", "trust", "shrink", "scope")
CELL_POLICIES = ("trust", "shrink", "scope")

OFFGRID_SHIFTS = (-3.6, -2.37, -1.6, 1.6, 2.37, 3.6)
OFFGRID_FRACTIONS = (0.5, 1.0)
TWO_DELTA_COMBOS = ((-3.0, 3.0), (3.0, -3.0), (-4.0, 2.0), (2.0, -4.0))
TWO_DELTA_FRACTIONS = (0.5, 1.0)

FIELDS = ("graph_seed", "episode_seed", "cell", "locality_a", "fraction", "shift_a",
          "locality_b", "shift_b", "policy", "p0", "belief_shift", "post_none",
          "post_frac", "post_global", "map_q", "map_delta", "changed_a", "changed_b",
          "initial_sink_errors", "sink_errors", "flags", "reviews")


def corrupt_two(graph, snapshot, episode_seed, locality_a, locality_b, fraction,
                shift_a, shift_b):
    """Shift two disjoint locality pools by different amounts, one delta each."""
    pool_a = corruption_pool(graph, locality_a, snapshot)
    pool_b = corruption_pool(graph, locality_b, snapshot)
    if np.intersect1d(pool_a, pool_b).size:
        raise ValueError(f"overlapping pools: {locality_a} and {locality_b}")

    def pick(pool, offset):
        count = 0 if fraction == 0 else max(1, min(len(pool), round(fraction * len(pool))))
        rng = np.random.default_rng(episode_seed + offset)
        return np.sort(rng.choice(pool, size=count, replace=False))

    selected_a = pick(pool_a, 991)
    selected_b = pick(pool_b, 992)
    z = vector_logit(snapshot.confidence)
    z[selected_a] = z[selected_a] + shift_a
    z[selected_b] = z[selected_b] + shift_b
    corrupted = replace(snapshot, confidence=tuple(vector_sigmoid(z)))
    return corrupted, selected_a, selected_b


def evaluate_graph(graph_seed, p0):
    graph = generate_graph("spike", graph_seed)
    if graph.n != 80 or len(graph.sinks) != 20:
        raise ValueError("unexpected graph dimensions")
    episode_seed = graph_seed + EPISODE_OFFSET
    clean = sample_episode(graph, episode_seed, "normal")
    rows = []

    def emit(cell, locality_a, fraction, shift_a, locality_b, shift_b, snapshot,
             changed_a, changed_b):
        names = POLICIES if cell == "clean" else CELL_POLICIES
        diagnostics = {"post_none": 0.0, "post_frac": 0.0, "post_global": 0.0,
                       "map_q": 0.0, "map_delta": 0.0}
        for name in names:
            belief_shift = 0.0
            if name == "scope":
                audit, belief_shift, diagnostics = run_scope(graph, snapshot, p0)
            elif name == "shrink":
                audit, belief_shift = run_shrink(graph, snapshot, PI)
            else:
                audit = plain(graph, snapshot, "normal")
            if len(audit["trace"]) != BUDGET:
                raise ValueError(f"review budget violated on {graph_seed}/{cell}/{name}")
            rows.append((graph_seed, episode_seed, cell, locality_a, fraction, shift_a,
                         locality_b, shift_b, name, p0, round(belief_shift, 6),
                         round(diagnostics["post_none"], 6),
                         round(diagnostics["post_frac"], 6),
                         round(diagnostics["post_global"], 6),
                         diagnostics["map_q"], diagnostics["map_delta"],
                         int(changed_a), int(changed_b), audit["initial_sink_errors"],
                         audit["final_sink_errors"],
                         sum(step["flagged"] for step in audit["trace"]),
                         len(audit["trace"])))

    emit("clean", "clean", 0.0, 0.0, "clean", 0.0, clean, 0, 0)
    if rows[0][19] != rows[1][19]:
        raise ValueError(f"clean trust must reproduce oracle on graph {graph_seed}")

    hidden = ("source_errors", "edge_coins", "edge_probs", "review_uniforms")
    for locality in ("uniform",):
        for fraction in OFFGRID_FRACTIONS:
            for shift in OFFGRID_SHIFTS:
                corrupted, (selected, changed) = corrupt_snapshot(
                    graph, clean, episode_seed, locality, fraction, shift)
                for field in hidden:
                    if getattr(corrupted, field) != getattr(clean, field):
                        raise ValueError(f"off-grid corruption changed hidden field {field}")
                if changed == 0:
                    raise ValueError(f"off-grid corruption had no effect on {graph_seed}")
                emit("off_grid", locality, fraction, shift, "", 0.0, corrupted,
                     len(selected), 0)

    for fraction in TWO_DELTA_FRACTIONS:
        for shift_a, shift_b in TWO_DELTA_COMBOS:
            corrupted, selected_a, selected_b = corrupt_two(
                graph, clean, episode_seed, "source", "sink", fraction, shift_a, shift_b)
            for field in hidden:
                if getattr(corrupted, field) != getattr(clean, field):
                    raise ValueError(f"two-delta corruption changed hidden field {field}")
            if len(selected_a) == 0 or len(selected_b) == 0:
                raise ValueError(f"two-delta corruption had no effect on {graph_seed}")
            emit("two_delta", "source", fraction, shift_a, "sink", shift_b, corrupted,
                 len(selected_a), len(selected_b))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="new output directory")
    parser.add_argument("--start", type=int, default=3800,
                        help="first graph seed; 3800-3899 is fresh")
    parser.add_argument("--graphs", type=int, default=200)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if (args.start < 3800 or args.start + args.graphs > 70000
            or args.graphs < 1 or args.workers < 1):
        parser.error("graph seeds must stay in the fresh range [3800, 70000); "
                     "3600-3799 is spent and 70000-70099 is calibration")
    out = args.out.resolve()
    try:
        out.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error(f"output directory already exists: {out}")

    graph_seeds = list(range(args.start, args.start + args.graphs))
    evaluate = partial(evaluate_graph, p0=P0)
    pending = out / "episodes.csv.partial"
    with pending.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(FIELDS)
        if args.workers > 1:
            with ProcessPoolExecutor(args.workers) as pool:
                for index, rows in enumerate(pool.map(evaluate, graph_seeds), start=1):
                    writer.writerows(rows)
                    if index % 25 == 0 or index == args.graphs:
                        stream.flush()
                        print(f"Evaluated {index}/{args.graphs} graphs", flush=True)
        else:
            for index, graph_seed in enumerate(graph_seeds, start=1):
                writer.writerows(evaluate(graph_seed))
                if index % 25 == 0 or index == args.graphs:
                    stream.flush()
                    print(f"Evaluated {index}/{args.graphs} graphs", flush=True)
    pending.replace(out / "episodes.csv")

    here = Path(__file__).resolve()
    sources = [here, here.with_name("evaluate_scope.py"), here.with_name("evaluate_shrink.py"),
               here.with_name("evaluate_corruption.py"), here.with_name("evaluate_conditions.py"),
               here.with_name("PREREGISTER_SCOPE_ROBUST.md"),
               ROLE3 / "dag_role3" / "policies.py",
               ROLE3 / "dag_role3" / "environment.py", ROLE3 / "dag_role3" / "graphs.py"]
    manifest = {
        "status": "complete", "family": "spike", "nodes": 80, "sinks": 20,
        "budget": BUDGET, "particles": 0, "graph_seeds": graph_seeds,
        "episode_seeds": [seed + EPISODE_OFFSET for seed in graph_seeds],
        "policies": list(POLICIES),
        "cells": {
            "clean": 1,
            "off_grid": {"locality": "uniform", "fractions": list(OFFGRID_FRACTIONS),
                         "shifts": list(OFFGRID_SHIFTS)},
            "two_delta": {"localities": ["source", "sink"],
                          "fractions": list(TWO_DELTA_FRACTIONS),
                          "shift_pairs": [list(pair) for pair in TWO_DELTA_COMBOS]},
        },
        "scope": {
            "p0": P0, "p0_source": "scope-v1 calibration fit on 70000-70029; not refitted",
            "q_grid": list(Q_GRID), "delta_grid": DELTAS.tolist(),
            "sigma": SIGMA, "mu_err": MU_ERR, "mu_good": MU_GOOD,
            "shrink_reference_pi": PI,
            "model": "one shared (q, delta) per graph, as in PREREGISTER_SCOPE_V2.md",
            "policy": "unchanged marginal with budget 16; only the input posterior changes",
        },
        "corruption": {
            "off_grid": "sigmoid(logit(c) + shift) on a deterministic subset of the pool",
            "two_delta": "source and sink pools shifted by different deltas; pools are disjoint",
            "selection_seed_offsets": [991, 992],
        },
        "preregistration": "PREREGISTER_SCOPE_ROBUST.md",
        "python": platform.python_version(), "numpy": np.__version__,
        "episodes_sha256": sha256(out / "episodes.csv"),
        "source_sha256": {p.relative_to(ROOT).as_posix(): sha256(p) for p in sources},
    }
    receipt = out / "manifest.json.partial"
    receipt.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    receipt.replace(out / "manifest.json")
    print(f"Completed {out}", flush=True)


if __name__ == "__main__":
    main()
