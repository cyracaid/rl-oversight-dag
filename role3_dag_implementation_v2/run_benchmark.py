"""Compare public policies on matched, held-out episodes."""
import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from dag_role3 import generate_graph, sample_episode
from dag_role3.policies import run_public_policy

RULES = ("none", "random", "confidence", "hub", "structural", "marginal")
FAMILIES = ("spike", "modular", "ba", "er", "real")


def load_policy(path):
    import torch
    from dag_role3.models import GNNScorer, GraphDQN, torch_obs, masked_action
    torch.set_num_threads(1)
    ckpt = torch.load(path, map_location="cpu", weights_only=True)
    dim = ckpt["input_dim"]
    family = ckpt["family"]
    k = len(generate_graph(family).rates)
    is_gnn = "self_layer.weight" in ckpt["state_dict"]
    static = is_gnn and dim == k + 2
    if dim != k + (2 if static else 7):
        raise ValueError(f"Incompatible feature dimensions in {path}")
    net = GNNScorer(dim) if is_gnn else GraphDQN(dim)
    net.load_state_dict(ckpt["state_dict"])
    net.eval()
    @torch.inference_mode()
    def act(obs):
        x, edges, mask = torch_obs(obs, static=static)
        return masked_action(net(x, edges), mask)[0]
    name = ("gnn_static" if static else "gnn" if is_gnn else "dqn")
    return family, f"{name}_s{ckpt['seed']}", act


def interval(xs):
    # Resample complete paired episodes, with a fixed Monte Carlo seed.
    xs = np.asarray(xs, dtype=float)
    if len(xs) < 2:
        return "", ""
    rng = np.random.default_rng(411)
    means = [xs[rng.integers(len(xs), size=(100, len(xs)))].mean(axis=1)
             for _ in range(20)]
    return tuple(np.quantile(np.concatenate(means), [.025, .975]))


def save(path, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--families", nargs="+", choices=FAMILIES, default=FAMILIES)
    ap.add_argument("--seeds", type=int, default=50)
    ap.add_argument("--start-seed", type=int, default=80000)
    ap.add_argument("--checkpoints", nargs="+", type=Path, default=[])
    ap.add_argument("--out", type=Path, default=Path("outputs"))
    args = ap.parse_args()
    if args.seeds < 1 or len(set(args.families)) != len(args.families):
        ap.error("need positive seeds and distinct families")
    learners = {f: {} for f in args.families}
    for path in args.checkpoints:
        family, name, act = load_policy(path)
        if family not in learners or name in learners[family]:
            ap.error(f"Unexpected family or duplicate model: {path}")
        learners[family][name] = act
    args.out.mkdir(parents=True, exist_ok=True)
    rows, summary = [], []
    for family in args.families:
        policies = dict(zip(RULES, RULES)) | learners[family]
        scores = {key: [] for key in policies}
        for seed in range(args.start_seed, args.start_seed + args.seeds):
            graph = generate_graph(family, seed)
            episode_seed = 20000 + seed
            snapshot = sample_episode(graph, episode_seed)
            budget = {"spike": 16, "real": 8}.get(family, 50)
            for name, policy in policies.items():
                errors, actions = run_public_policy(graph, snapshot, policy, budget)
                scores[name].append(errors)
                rows.append(dict(family=family, graph_seed=seed, episode_seed=episode_seed,
                                 n=graph.n, edges=graph.edge_count, sinks=len(graph.sinks),
                                 budget=budget, policy=name, sink_errors=errors,
                                 actions=" ".join(map(str, actions))))
        for name, errors in scores.items():
            delta = np.subtract(scores["confidence"], errors)
            lo, hi = interval(delta)
            summary.append(dict(family=family, policy=name, n_episodes=len(errors),
                                mean_sink_errors=np.mean(errors),
                                mean_saved_vs_none=np.mean(np.subtract(scores["none"], errors)),
                                gain_vs_confidence=delta.mean(), paired_lo=lo, paired_hi=hi,
                                wins=sum(delta>0), ties=sum(delta==0), losses=sum(delta<0)))
        print(family, "complete", flush=True)
    save(args.out/"benchmark_role3.csv", rows)
    save(args.out/"benchmark_summary.csv", summary)
    fig, axes = plt.subplots(1, len(args.families), figsize=(3.8*len(args.families), 5), squeeze=False)
    for ax, family in zip(axes[0], args.families):
        block = [r for r in summary if r["family"] == family]
        ax.barh([r["policy"] for r in block], [r["mean_sink_errors"] for r in block])
        ax.invert_yaxis()
        ax.set_title(f"{family} (n={args.seeds})")
        ax.set_xlabel("Mean remaining conclusion errors")
    fig.tight_layout()
    fig.savefig(args.out/"benchmark_summary.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    main()
