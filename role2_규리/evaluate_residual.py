"""Evaluate structural residual and feature-only actors with the same review feedback."""

import argparse
import csv
import json
from pathlib import Path
import platform

import numpy as np
import torch

from evaluate_conditions import (BUDGET, ROLE3, ROOT, choose, fit_signal_gate, generate_graph,
                                 infer_signal_mode, load_policy, paired_snapshots, sha256)
from evaluate_feedback import EPSILON, INITIAL_PROBABILITY, P_CATCH, run_feedback
from shuffle_control import shuffle_within_type
from train_residual import load_actor


CONDITIONS = ("matched", "uniform", "shuffled")
VARIANTS = ("feature_only", "residual")
FIELDS = ("graph_seed", "episode_seed", "condition", "policy", "sink_errors",
          "initial_sink_errors", "flags", "reviews", "disagreements")


def marginal(obs):
    return choose(obs, "marginal")


def evaluate_actor(graph, snapshot, mode, actor):
    disagreements = 0

    def select_action(obs):
        nonlocal disagreements
        action = actor(obs)
        if actor is not marginal:
            disagreements += int(action != marginal(obs))
        return action

    initial, final, flags, reviews, _, _ = run_feedback(graph, snapshot, mode, select_action)
    return initial, final, flags, reviews, disagreements


def checkpoint_receipt(path, seed, meta):
    return {
        "path": path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path),
        "train_seed": seed, "sha256": sha256(path), "episodes": meta["episodes"],
        "selected_episode": meta["selected_episode"],
    }


def load_policies(run_dir, seeds, test_graphs):
    actors = {"marginal": marginal}
    checkpoints = {}
    for seed in (1, 2, 3):
        label = f"old_s{seed}"
        path = ROLE3 / "outputs" / "v3" / f"train_{seed}" / "gnn_spike_observed.pt"
        family, model_name, actor = load_policy(path)
        if family != "spike" or model_name != f"gnn_s{seed}":
            raise ValueError(f"unexpected archived Spike checkpoint: {path}")
        meta = torch.load(path, map_location="cpu", weights_only=True)
        actors[label] = actor
        checkpoints[label] = checkpoint_receipt(path, seed, meta)
    for seed in seeds:
        folder = run_dir / "train" / f"seed-{seed}"
        config_path = folder / "config.json"
        log_path = folder / "training.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        history = json.loads(log_path.read_text(encoding="utf-8"))
        for start, count in ((config["train_start"], config["episodes"]),
                             (config["validation_start"], config["validation_graphs"])):
            if not test_graphs.isdisjoint(range(start, start + count)):
                raise ValueError(f"training or validation graphs overlap evaluation: {folder}")
        for variant in VARIANTS:
            label = f"{variant}_s{seed}"
            path = folder / f"{variant}.pt"
            meta = torch.load(path, map_location="cpu", weights_only=True)
            if meta["train_seed"] != seed or meta["variant"] != variant:
                raise ValueError(f"checkpoint seed or variant differs from expected: {path}")
            if not 0 <= meta["selected_episode"] <= meta["episodes"]:
                raise ValueError(f"invalid validation-selected checkpoint: {path}")
            actors[label] = load_actor(path)
            receipt = checkpoint_receipt(path, seed, meta)
            if (history[variant]["checkpoint_sha256"] != receipt["sha256"]
                    or history[variant]["selected_episode"] != receipt["selected_episode"]
                    or config["train_seed"] != seed or config["episodes"] != receipt["episodes"]):
                raise ValueError(f"checkpoint disagrees with completed training record: {path}")
            receipt.update(training_config_sha256=sha256(config_path), training_log_sha256=sha256(log_path))
            checkpoints[label] = receipt
    return actors, checkpoints


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True, help="directory containing train/seed-N/")
    parser.add_argument("--seeds", nargs="+", type=int, default=[1, 2, 3, 4, 5])
    parser.add_argument("--start", type=int, default=93000)
    parser.add_argument("--graphs", type=int, default=200)
    parser.add_argument("--out", type=Path, help="new evaluation directory (default: RUN/eval)")
    args = parser.parse_args()
    if len(args.seeds) != len(set(args.seeds)) or min(args.seeds) < 1:
        parser.error("use distinct positive training seeds")
    # Earlier development graphs occupy 90000+, 91000+, 92000+ and smoke seeds 99994+.
    # The v3 test interval ends at 99999. New training uses 3M+ and validation 74000+.
    if args.graphs < 1 or args.start < 93000 or args.start + args.graphs > 99994:
        parser.error("choose a positive graph count in the unused range [93000,99994)")

    torch.set_num_threads(1)
    run = args.run.resolve()
    out = (args.out or run / "eval").resolve()
    if out.exists():
        parser.error(f"output directory already exists: {out}")
    graph_seeds = list(range(args.start, args.start + args.graphs))
    episode_seeds = [seed + 20000 for seed in graph_seeds]
    actors, checkpoints = load_policies(run, args.seeds, set(graph_seeds))
    gate = fit_signal_gate()
    here = Path(__file__).resolve()
    sources = [here, here.with_name("train_residual.py"), here.with_name("evaluate_feedback.py"),
               here.with_name("evaluate_conditions.py"), here.with_name("signal_calibration.py"),
               here.with_name("shuffle_control.py"), ROLE3 / "run_benchmark.py",
               *sorted((ROLE3 / "dag_role3").glob("*.py"))]
    manifest = {
        "family": "spike", "nodes": 80, "budget": BUDGET, "p_catch": P_CATCH,
        "conditions": CONDITIONS, "policies": list(actors), "checkpoints": checkpoints,
        "train_seeds": args.seeds, "graph_seeds": graph_seeds, "episode_seeds": episode_seeds,
        "signal_gate": gate, "protocol": {
            "belief": "v3 mean-field", "normal_prior_given_gate": INITIAL_PROBABILITY,
            "feedback_probability_clip": EPSILON, "shuffle_seed_offset": 173,
            "disagreements": "chosen action differs from marginal on the policy's own public observation",
        },
        "source_sha256": {p.relative_to(ROOT).as_posix(): sha256(p) for p in sources},
        "python": platform.python_version(), "torch": str(torch.__version__), "numpy": np.__version__,
    }
    out.mkdir(parents=True, exist_ok=False)
    pending = out / "episodes.csv.partial"
    with pending.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(FIELDS)
        for index, (gs, es) in enumerate(zip(graph_seeds, episode_seeds), start=1):
            graph = generate_graph("spike", gs)
            snapshots = paired_snapshots(graph, es)
            cases = {"matched": snapshots["normal"], "uniform": snapshots["noise"],
                     "shuffled": shuffle_within_type(snapshots["normal"], graph.types, es)}
            initial_errors = None
            for condition, snapshot in cases.items():
                mode = infer_signal_mode(snapshot.confidence, gate)
                for label, actor in actors.items():
                    initial, final, flags, reviews, disagreements = evaluate_actor(graph, snapshot, mode, actor)
                    if initial_errors is None:
                        initial_errors = initial
                    if initial != initial_errors or reviews != BUDGET:
                        raise ValueError(f"unpaired underlying graph or review budget for {gs}, {label}")
                    writer.writerow((gs, es, condition, label, final, initial, flags, reviews, disagreements))
            if index % 25 == 0 or index == args.graphs:
                print(f"Evaluated {index}/{args.graphs} graphs", flush=True)
    episodes = out / "episodes.csv"
    pending.replace(episodes)
    manifest.update(status="complete", episodes_sha256=sha256(episodes))
    receipt = out / "manifest.json.partial"
    receipt.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    receipt.replace(out / "manifest.json")
    print(f"Completed {out}", flush=True)


if __name__ == "__main__":
    main()
