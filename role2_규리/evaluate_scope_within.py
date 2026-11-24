"""Compare frozen score repairs when two logit shifts share one Spike layer."""

import argparse
import csv
import json
import platform
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from _env import ROLE3, ROOT, ensure_role3

ensure_role3()
from dag_role3 import generate_graph, sample_episode
from evaluate_conditions import BUDGET, sha256
from evaluate_corruption import corruption_pool, vector_logit, vector_sigmoid
from evaluate_scope import DELTAS, EPISODE_OFFSET, P_CATCH, PI, Q_GRID, plain, run_scope
from evaluate_scope_robust import P0
from evaluate_shrink import run_shrink


HERE = Path(__file__).resolve().parent
SEEDS = range(4600, 4700)
LAYERS = {"source": 991, "sink": 992}
FRACTIONS = (0.5, 1.0)
PAIRS = ((-3, 3), (-4, 2), (-2, 4), (-4, -2), (2, 4))
POLICIES = ("trust", "shrink", "scope")
FIELDS = ("graph_seed", "episode_seed", "cell", "layer", "fraction", "shift_a", "shift_b",
          "policy", "changed_a", "changed_b", "initial_sink_errors", "sink_errors",
          "flags", "reviews", "map_q", "map_delta")


def mixed_snapshot(clean, group_a, group_b, shift_a, shift_b):
    scores = np.array(clean.confidence, dtype=np.float64)
    shifted = scores.copy()
    for group, delta in ((group_a, shift_a), (group_b, shift_b)):
        shifted[group] = vector_sigmoid(vector_logit(scores[group]) + delta)
    selected = np.sort(np.concatenate((group_a, group_b)))
    if not np.array_equal(np.flatnonzero(scores != shifted), selected):
        raise ValueError("changed scores must match the two disjoint groups exactly")
    snapshot = replace(clean, confidence=tuple(shifted))
    if replace(snapshot, confidence=clean.confidence) != clean:
        raise ValueError("corruption changed hidden episode state")
    return snapshot


def review_cell(graph_seed, graph, snapshot, cell, layer, fraction, shifts, counts):
    rows = []
    for policy in POLICIES:
        diagnostics = {}
        if policy == "scope":
            audit, _, diagnostics = run_scope(graph, snapshot, P0)
        elif policy == "shrink":
            audit, _ = run_shrink(graph, snapshot, PI)
        else:
            audit = plain(graph, snapshot, "normal")
        trace = audit["trace"]
        if len(trace) != BUDGET:
            raise ValueError(f"review budget violated on {graph_seed}/{cell}/{policy}")
        rows.append((graph_seed, snapshot.seed, cell, layer, fraction, *shifts, policy,
                     *counts, audit["initial_sink_errors"], audit["final_sink_errors"],
                     sum(step["flagged"] for step in trace), len(trace),
                     diagnostics.get("map_q"), diagnostics.get("map_delta")))
    return rows


def evaluate_graph(graph_seed):
    graph = generate_graph("spike", graph_seed)
    episode_seed = graph_seed + EPISODE_OFFSET
    clean = sample_episode(graph, episode_seed, "normal")
    if graph.n != 80 or len(graph.sinks) != 20:
        raise ValueError("unexpected graph dimensions")
    rows = review_cell(graph_seed, graph, clean, "clean", "clean", 0, (0, 0), (0, 0))
    for layer, offset in LAYERS.items():
        pool = corruption_pool(graph, layer, clean)
        if len(pool) != 20 or len(set(graph.layers[i] for i in pool)) != 1:
            raise ValueError(f"unexpected {layer} layer in graph {graph_seed}")
        order = np.random.default_rng(episode_seed + offset).permutation(pool)
        for fraction in FRACTIONS:
            selected = order[:round(fraction * len(order))]
            group_a, group_b = selected[::2], selected[1::2]
            for shifts in PAIRS:
                snapshot = mixed_snapshot(clean, group_a, group_b, *shifts)
                rows.extend(review_cell(graph_seed, graph, snapshot, "within", layer,
                                        fraction, shifts, (len(group_a), len(group_b))))
    return rows


def make_manifest(csv_path):
    files = [Path(__file__), HERE / "PREREGISTER_SCOPE_WITHIN.md", HERE / "_env.py"]
    for name in ("evaluate_scope", "evaluate_shrink", "evaluate_scope_robust",
                 "evaluate_conditions", "evaluate_corruption", "evaluate_feedback"):
        files.append(HERE / (name + ".py"))
    for name in ("graphs", "environment", "policies"):
        files.append(ROLE3 / "dag_role3" / (name + ".py"))
    return {
        "status": "complete", "family": "spike", "nodes": 80, "sinks": 20,
        "budget": BUDGET, "p_catch": P_CATCH, "graph_seeds": list(SEEDS),
        "episode_seeds": [s + EPISODE_OFFSET for s in SEEDS],
        "episode_seed_offset": EPISODE_OFFSET, "policies": POLICIES,
        "cells": {"clean": 1, "within": 20, "layers": list(LAYERS),
                  "fractions": FRACTIONS, "shift_pairs": PAIRS},
        "permutation_seed_offsets": LAYERS,
        "selection": "Layer permutation prefix, alternating entries assigned to A and B.",
        "scope_p0": P0, "shrink_pi": PI, "scope_q_grid": Q_GRID,
        "scope_delta_grid": DELTAS.tolist(),
        "python": platform.python_version(), "numpy": np.__version__,
        "source_sha256": {p.relative_to(ROOT).as_posix(): sha256(p) for p in files},
        "episodes_sha256": sha256(csv_path),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=HERE / "results" / "scope-within-v1")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or args.workers < 1:
        parser.error("use a new output directory and a positive worker count")
    out.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=out.parent, prefix=".scope-within-") as temporary:
        stage = Path(temporary) / "result"
        stage.mkdir()
        csv_path = stage / "episodes.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(FIELDS)
            with ProcessPoolExecutor(args.workers) as pool:
                for i, rows in enumerate(pool.map(evaluate_graph, SEEDS), 1):
                    writer.writerows(rows)
                    if i % 10 == 0:
                        print(f"Evaluated {i}/{len(SEEDS)} graphs", flush=True)
        manifest = json.dumps(make_manifest(csv_path), ensure_ascii=False, indent=2)
        (stage / "manifest.json").write_text(manifest + "\n", encoding="utf-8")
        stage.rename(out)
    print(f"Completed {out}", flush=True)


if __name__ == "__main__":
    main()
