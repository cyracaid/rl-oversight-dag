"""Evaluate the PPO checkpoints on the pre-registered fresh block.

Block: graph seeds 4200-4399, episode seed 20000 + graph seed, family spike,
budget 16. Those graphs were not read by any earlier experiment, and the spent
90000 block is refused here as it is elsewhere.

Reporting is paired: every policy and ``marginal`` see the identical episode, so
only the per-episode difference is resampled. Wins, ties and losses are reported
next to the mean because a mean can be carried by one heavy episode.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from dag_role3 import generate_graph, sample_episode
from dag_role3.policies import run_public_policy
from run_benchmark import load_policy

BLOCK = (4200, 4399)
EPISODE_OFFSET = 20000
BOOTSTRAP = 10_000
BOOTSTRAP_SEED = 20261124


def block(start, end):
    if start >= 90000:
        raise SystemExit("the 90000 block is spent; pick a fresh one")
    return list(range(start, end + 1))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bootstrap_paired(delta):
    """95% interval for the mean of paired differences."""
    delta = np.asarray(delta, dtype=float)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    draws = rng.integers(len(delta), size=(BOOTSTRAP, len(delta)))
    means = delta[draws].mean(axis=1)
    return tuple(float(x) for x in np.quantile(means, [0.025, 0.975]))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--checkpoints", nargs="+", type=Path, required=True)
    ap.add_argument("--family", default="spike")
    ap.add_argument("--budget", type=int, default=16)
    ap.add_argument("--start", type=int, default=BLOCK[0])
    ap.add_argument("--end", type=int, default=BLOCK[1])
    ap.add_argument("--out", type=Path, default=Path("outputs/ppo-v1"))
    args = ap.parse_args()
    if args.start >= 90000:
        raise SystemExit("the 90000 block is spent; pick a fresh one")
    seeds = block(args.start, args.end)
    args.out.mkdir(parents=True, exist_ok=True)

    learners = []
    for path in args.checkpoints:
        family, name, act = load_policy(path)
        if family != args.family:
            raise SystemExit(f"{path} is a {family} checkpoint, not {args.family}")
        learners.append((name, act, str(path)))

    rows = []
    for graph_seed in seeds:
        graph = generate_graph(args.family, graph_seed)
        snapshot = sample_episode(graph, EPISODE_OFFSET + graph_seed)
        reference, _ = run_public_policy(graph, snapshot, "marginal", args.budget)
        row = {"graph_seed": graph_seed, "marginal": reference}
        for name, act, _ in learners:
            errors, _ = run_public_policy(graph, snapshot, act, args.budget)
            row[name] = errors
        rows.append(row)

    with open(args.out / "ppo_episodes.csv", "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    summary = []
    for name, _, path in learners:
        ours = np.asarray([r[name] for r in rows], dtype=float)
        theirs = np.asarray([r["marginal"] for r in rows], dtype=float)
        delta = ours - theirs
        low, high = bootstrap_paired(delta)
        summary.append({
            "policy": name, "checkpoint": path,
            "mean_sink_errors": float(ours.mean()),
            "marginal_mean": float(theirs.mean()),
            "delta_vs_marginal": float(delta.mean()),
            "ci_low": low, "ci_high": high,
            "wins": int((delta < 0).sum()), "ties": int((delta == 0).sum()),
            "losses": int((delta > 0).sum()),
            "separated": bool(low > 0 or high < 0),
        })
    with open(args.out / "ppo_summary.csv", "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    (args.out / "manifest.json").write_text(json.dumps({
        "block": [args.start, args.end], "episode_offset": EPISODE_OFFSET,
        "family": args.family, "budget": args.budget,
        "bootstrap_draws": BOOTSTRAP, "bootstrap_seed": BOOTSTRAP_SEED,
        "checkpoints": [{"policy": n, "path": p, "sha256": digest(p)}
                        for n, _, p in learners],
        "trainer_sha256": digest(Path(__file__).with_name("train_ppo.py")),
        "reference": "marginal",
    }, indent=2))

    for row in summary:
        direction = ("learned wins" if row["separated"] and row["delta_vs_marginal"] < 0
                     else "learned loses" if row["separated"] else "not separated")
        print(f"{row['policy']:10s} mean {row['mean_sink_errors']:.3f}  "
              f"marginal {row['marginal_mean']:.3f}  "
              f"delta {row['delta_vs_marginal']:+.3f} "
              f"[{row['ci_low']:+.3f}, {row['ci_high']:+.3f}]  "
              f"W/T/L {row['wins']}/{row['ties']}/{row['losses']}  {direction}")


if __name__ == "__main__":
    main()
