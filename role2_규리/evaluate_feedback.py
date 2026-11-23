"""Compare fixed and flag-updated confidence assumptions on paired Spike graphs."""

import argparse
import csv
from functools import partial
import json
import math
from pathlib import Path
import platform
import re

import numpy as np
import torch

from evaluate_conditions import (BUDGET, ROLE3, ROOT, OversightEnv, choose, evaluate_policy,
                                fit_signal_gate, generate_graph, infer_signal_mode, load_policy,
                                paired_snapshots, sha256)
from shuffle_control import shuffle_within_type


P_CATCH = 0.9
EPSILON = 1e-6
INITIAL_PROBABILITY = {"normal": 0.8, "noise": 0.2}
FIELDS = ("graph_seed", "episode_seed", "condition", "policy", "approach", "initial_sink_errors",
          "sink_errors", "flags", "reviews", "noise_actions", "switched")


def flag_probability(obs, action):
    # The final seven public features include P(effective error) in position four.
    effective = float(obs["features"][action, -4])
    return min(1.0 - EPSILON, max(EPSILON, P_CATCH * effective))


def run_feedback(graph, snapshot, initial_mode, policy):
    normal = OversightEnv(graph, snapshot, BUDGET, p_catch=P_CATCH, confidence_mode="normal")
    noise = OversightEnv(graph, snapshot, BUDGET, p_catch=P_CATCH, confidence_mode="noise")
    normal_obs, noise_obs = normal.observation(), noise.observation()
    p = INITIAL_PROBABILITY[initial_mode]
    log_odds = math.log(p / (1.0 - p))
    noise_actions, switched = 0, False

    while not normal.done:
        mode = "normal" if log_odds >= 0 else "noise"
        action = policy(normal_obs if mode == "normal" else noise_obs)
        p_normal = flag_probability(normal_obs, action)
        p_noise = flag_probability(noise_obs, action)
        normal_obs, _, _, normal_info = normal.step(action)
        noise_obs, _, _, noise_info = noise.step(action)
        flagged = normal_info["flagged"]
        if flagged != noise_info["flagged"]:
            raise ValueError("belief models received different reviewer feedback")
        if flagged:
            log_odds += math.log(p_normal) - math.log(p_noise)
        else:
            log_odds += math.log1p(-p_normal) - math.log1p(-p_noise)
        noise_actions += int(mode == "noise")
        switched |= mode != initial_mode

    audit = normal.final_audit()
    return (audit["initial_sink_errors"], audit["final_sink_errors"],
            sum(step["flagged"] for step in audit["trace"]), len(audit["trace"]),
            noise_actions, int(switched))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path, help="new directory for this run")
    parser.add_argument("--start", type=int, default=92000)
    parser.add_argument("--graphs", type=int, default=200)
    parser.add_argument("--checkpoints", type=Path, nargs="+", default=[
        ROLE3 / "outputs" / "v3" / f"train_{seed}" / "gnn_spike_observed.pt"
        for seed in (1, 2, 3)
    ], help="observed-state Spike GNN checkpoints from distinct training seeds")
    args = parser.parse_args()
    if args.graphs < 1 or args.start < 90000 or args.start + args.graphs > 100000:
        parser.error("choose a positive number of graphs within [90000, 100000)")

    policies = {"marginal": partial(choose, name="marginal")}
    checkpoints = {}
    for path in args.checkpoints:
        path = path.resolve()
        if not path.is_file():
            parser.error(f"missing checkpoint: {path}")
        family, label, act = load_policy(path)
        match = re.fullmatch(r"gnn_s([1-9]\d*)", label)
        if family != "spike" or match is None or label in policies:
            parser.error(f"expected distinct observed-state Spike GNN checkpoints, got {label}: {path}")
        policies[label] = act
        checkpoints[label] = {
            "train_seed": int(match.group(1)), "sha256": sha256(path),
            "path": path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path),
        }
    out = args.out.resolve()
    try:
        out.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error(f"output directory already exists: {out}")

    graph_seeds = list(range(args.start, args.start + args.graphs))
    episode_seeds = [seed + 20000 for seed in graph_seeds]
    gate = fit_signal_gate()
    here = Path(__file__).resolve()
    sources = [here, here.with_name("evaluate_conditions.py"), here.with_name("signal_calibration.py"),
               here.with_name("shuffle_control.py"), ROLE3 / "run_benchmark.py",
               *sorted((ROLE3 / "dag_role3").glob("*.py"))]
    manifest = {
        "family": "spike", "nodes": 80, "budget": BUDGET, "p_catch": P_CATCH, "particles": 0,
        "graph_seeds": graph_seeds, "episode_seeds": episode_seeds,
        "conditions": ["matched", "uniform", "shuffled"], "approaches": ["fixed", "feedback"],
        "policies": list(policies), "checkpoints": checkpoints, "signal_gate": gate,
        "protocol": {"normal_prior_given_gate": INITIAL_PROBABILITY, "clip_probability": EPSILON,
                     "decision": "P(normal) >= 0.5 selects normal, before each action",
                     "update": "log odds += log P(flag outcome | normal) - log P(flag outcome | noise)",
                     "flag_probability": "p_catch * modeled effective error probability of selected node",
                     "shuffle": "within-type, numpy.default_rng(episode_seed + 173)"},
        "source_sha256": {p.relative_to(ROOT).as_posix(): sha256(p) for p in sources},
        "python": platform.python_version(), "numpy": np.__version__, "torch": str(torch.__version__),
    }
    pending = out / "episodes.csv.partial"
    with pending.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(FIELDS)
        for i, (gseed, eseed) in enumerate(zip(graph_seeds, episode_seeds), start=1):
            graph = generate_graph("spike", gseed)
            snapshots = paired_snapshots(graph, eseed)
            cases = {"matched": snapshots["normal"], "uniform": snapshots["noise"],
                     "shuffled": shuffle_within_type(snapshots["normal"], graph.types, eseed)}
            for condition, snapshot in cases.items():
                initial_mode = infer_signal_mode(snapshot.confidence, gate)
                for name, act in policies.items():
                    final, initial, flags, reviews = evaluate_policy(graph, snapshot, initial_mode, act)
                    noise_actions = reviews if initial_mode == "noise" else 0
                    prefix = (gseed, eseed, condition, name)
                    writer.writerow((*prefix, "fixed", initial, final, flags, reviews, noise_actions, 0))
                    outcome = run_feedback(graph, snapshot, initial_mode, act)
                    if outcome[0] != initial or outcome[3] != reviews:
                        raise ValueError(f"inconsistent initial error or budget on graph {gseed}")
                    writer.writerow((*prefix, "feedback", *outcome))
            if i % 25 == 0 or i == args.graphs:
                print(f"Evaluated {i}/{args.graphs} graphs", flush=True)
    episodes_path = out / "episodes.csv"
    pending.replace(episodes_path)
    manifest.update(status="complete", episodes_sha256=sha256(episodes_path))
    receipt = out / "manifest.json.partial"
    receipt.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    receipt.replace(out / "manifest.json")
    print(f"Completed {out}", flush=True)


if __name__ == "__main__":
    main()
