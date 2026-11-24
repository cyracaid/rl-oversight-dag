"""Evaluate frozen Spike policies under paired changes in confidence quality."""

import argparse
import csv
from functools import partial
import hashlib
import json
from pathlib import Path
import platform

import numpy as np
import torch

from _env import ROLE3, ROOT, ensure_role3

ensure_role3()
from dag_role3 import OversightEnv, generate_graph, sample_episode
from dag_role3.graphs import SPIKE_RATES
from dag_role3.policies import choose
from run_benchmark import load_policy
from signal_calibration import fit_signal_gate, infer_signal_mode


CONDITIONS = {
    "matched": {"signal_mode": "normal", "assumed_mode": "normal"},
    "noise_unrecognized": {"signal_mode": "noise", "assumed_mode": "normal"},
    "noise_known": {"signal_mode": "noise", "assumed_mode": "noise"},
}
BUDGET = 16
FIELDS = ("graph_seed", "episode_seed", "condition", "policy", "assumed_mode", "sink_errors",
          "initial_sink_errors", "flags", "reviews")


def type_prior(obs):
    available = np.flatnonzero(obs["mask"])
    types = obs["features"][available, :len(SPIKE_RATES)].argmax(axis=1)
    # np.argmax selects the first maximum, breaking equal prior risks by node ID.
    return int(available[np.argmax(np.asarray(SPIKE_RATES)[types])])


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def paired_snapshots(graph, episode_seed):
    normal = sample_episode(graph, episode_seed, "normal")
    noise = sample_episode(graph, episode_seed, "noise")
    for field in ("source_errors", "edge_coins", "edge_probs", "review_uniforms"):
        if getattr(normal, field) != getattr(noise, field):
            raise RuntimeError(f"unpaired {field} for episode {episode_seed}")
    return {"normal": normal, "noise": noise}


def evaluate_policy(graph, snapshot, assumed_mode, act):
    env = OversightEnv(graph, snapshot, BUDGET, p_catch=0.9, confidence_mode=assumed_mode)
    obs = env.observation()
    while not env.done:
        obs, _, _, _ = env.step(act(obs))
    audit = env.final_audit()
    return (audit["final_sink_errors"], audit["initial_sink_errors"],
            sum(step["flagged"] for step in audit["trace"]), len(audit["trace"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="new output directory")
    parser.add_argument("--start", type=int, default=91000, help="first evaluation graph seed")
    parser.add_argument("--graphs", type=int, default=200, help="number of paired graphs")
    parser.add_argument("--checkpoints", type=Path, nargs="+", default=[
        ROLE3 / "outputs" / "v3" / f"train_{seed}" / "gnn_spike_observed.pt"
        for seed in (1, 2, 3)
    ])
    args = parser.parse_args()
    if args.graphs < 1 or args.start < 90000 or args.start + args.graphs > 100000:
        parser.error("select a positive graph count within the test range [90000, 100000)")

    marginal = partial(choose, name="marginal")
    policies = {"confidence": partial(choose, name="confidence"),
                "marginal": marginal, "type_prior": type_prior, "adaptive_marginal": marginal}
    checkpoints = {}
    for path in args.checkpoints:
        path = path.resolve()
        if not path.is_file():
            parser.error(f"missing checkpoint: {path}")
        family, name, act = load_policy(path)
        if family != "spike" or not name.startswith("gnn"):
            parser.error(f"expected a Spike GNN checkpoint: {path}")
        if name in policies:
            parser.error(f"duplicate policy variant and training seed: {name}")
        policies[name] = act
        checkpoints[name] = {
            "path": path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path),
            "sha256": sha256(path), "train_seed": int(name.rsplit("_s", 1)[1]),
        }
    out = args.out.resolve()
    try:
        out.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error(f"output directory already exists: {out}")

    graph_seeds = list(range(args.start, args.start + args.graphs))
    episode_seeds = [seed + 20000 for seed in graph_seeds]
    signal_gate = fit_signal_gate()
    sources = [Path(__file__).resolve(), Path(__file__).with_name("signal_calibration.py").resolve(),
               ROLE3 / "run_benchmark.py",
               *sorted((ROLE3 / "dag_role3").glob("*.py"))]
    manifest = {
        "family": "spike", "budget": BUDGET, "nodes": 80, "p_catch": 0.9, "particles": 0,
        "graph_seeds": graph_seeds, "episode_seeds": episode_seeds,
        "conditions": CONDITIONS, "policies": list(policies), "checkpoints": checkpoints,
        "signal_gate": signal_gate,
        "source_sha256": {p.relative_to(ROOT).as_posix(): sha256(p) for p in sources},
        "python": platform.python_version(), "numpy": np.__version__, "torch": str(torch.__version__),
    }
    pending = out / "episodes.csv.partial"
    with pending.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(FIELDS)
        for index, (graph_seed, episode_seed) in enumerate(zip(graph_seeds, episode_seeds), start=1):
            graph = generate_graph("spike", graph_seed)
            snapshots = paired_snapshots(graph, episode_seed)
            inferred = {mode: infer_signal_mode(snap.confidence, signal_gate)
                        for mode, snap in snapshots.items()}
            for condition, modes in CONDITIONS.items():
                snapshot = snapshots[modes["signal_mode"]]
                for name, act in policies.items():
                    assumed_mode = modes["assumed_mode"]
                    if name == "adaptive_marginal":
                        assumed_mode = inferred[modes["signal_mode"]]
                    outcome = evaluate_policy(graph, snapshot, assumed_mode, act)
                    writer.writerow((graph_seed, episode_seed, condition, name, assumed_mode, *outcome))
            if index % 25 == 0 or index == args.graphs:
                print(f"Evaluated {index}/{args.graphs} graphs", flush=True)
    pending.replace(out / "episodes.csv")
    manifest.update(status="complete", episodes_sha256=sha256(out / "episodes.csv"))
    receipt = out / "manifest.json.partial"
    receipt.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    receipt.replace(out / "manifest.json")
    print(f"Completed {out}", flush=True)


if __name__ == "__main__":
    main()
