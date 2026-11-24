"""Is the oracle gap the belief's values or the one-step horizon?

``marginal`` and ``oracle`` run the same rule, the same budget and the same
one-step horizon; only the source-error prior differs. That makes the gap equal
to the value of knowing the truth, which is not the same as the value a better
use of the *public* information could extract.

The public belief already ranks well (its AUC against the truth is about 0.96 in
a pilot), so ranking it better is not a lever worth pulling. What is left is the
*numbers*: the forward derivative in ``marginal_scores`` is fed probabilities, and
if those probabilities are miscalibrated the derivative can order actions wrongly
even when it orders nodes correctly.

So the reference damages calibration while preserving ranking:

    q_i(gamma) = sigmoid(gamma * logit(belief_i))

One strictly monotone map applied to every node leaves the per-graph AUC
identical, so any change in final errors comes from the values alone.
``gamma = 1`` must reproduce ``marginal`` exactly, per graph, or the script
aborts; ``gamma > 1`` pushes probabilities towards 0/1, ``gamma < 1`` towards 0.5.

Pre-registered in ``PREREGISTER_BELIEF_DECOMPOSITION.md``: block, grid, metric,
selection-free reporting of the whole curve and the verdict table.
"""
import argparse
import csv
import json
from pathlib import Path

import numpy as np

from dag_role3 import OversightEnv, generate_graph, sample_episode
from dag_role3.environment import initial_belief
from dag_role3.policies import marginal_scores, run_public_policy

BLOCK = (4800, 4999)
EPISODE_OFFSET = 20000
GAMMAS = (0.50, 0.75, 1.00, 1.25, 1.50, 2.00)
BOOTSTRAP = 10_000
BOOTSTRAP_SEED = 20261124
BUDGET = {"spike": 16, "modular": 50}
P_CATCH = 0.9


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -60.0, 60.0)))


def logit(p):
    p = np.clip(np.asarray(p, dtype=float), 1e-8, 1 - 1e-8)
    return np.log(p / (1 - p))


def auc(scores, labels):
    """Mann-Whitney AUC, ties in scores handled by average ranks.

    Returns ``None`` when only one class is present: that graph carries no
    ranking information, and filling a neutral 0.5 would fabricate a data point.
    """
    scores = np.asarray(scores, dtype=float)
    labels = np.asarray(labels, dtype=bool)
    positives, negatives = labels.sum(), (~labels).sum()
    if positives == 0 or negatives == 0:
        return None
    order = np.argsort(scores, kind="mergesort")
    ranks = np.empty(len(scores), dtype=float)
    ordered = scores[order]
    start = 0
    while start < len(scores):
        stop = start
        while stop + 1 < len(scores) and ordered[stop + 1] == ordered[start]:
            stop += 1
        ranks[order[start:stop + 1]] = (start + stop) / 2 + 1
        start = stop + 1
    return float((ranks[labels].sum() - positives * (positives + 1) / 2)
                 / (positives * negatives))


def calibrated(observation, gamma):
    """The same observation with the belief column pushed through one monotone map.

    The rule is untouched: only the column ``marginal_scores`` reads as its prior
    is replaced. ``gamma = 1`` returns the observation itself so the identity
    holds bit-for-bit rather than up to a sigmoid/logit round trip.
    """
    if gamma == 1.0:
        return observation
    k = observation["features"].shape[1] - 7
    augmented = dict(observation)
    features = observation["features"].copy()
    features[:, k + 2] = sigmoid(gamma * logit(features[:, k + 2]))
    augmented["features"] = features
    return augmented


def run_reference(graph, snapshot, gamma, budget):
    """The marginal greedy, with its prior's calibration perturbed."""
    env = OversightEnv(graph, snapshot, budget=budget, p_catch=P_CATCH)
    observation, done = env.observation(), env.done
    while not done:
        scores = marginal_scores(calibrated(observation, gamma))
        available = np.flatnonzero(observation["mask"])
        observation, _, done, _ = env.step(int(available[np.argmax(scores[available])]))
    return env.final_audit()["final_sink_errors"], env


def bootstrap(delta):
    delta = np.asarray(delta, dtype=float)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    draws = rng.integers(len(delta), size=(BOOTSTRAP, len(delta)))
    return tuple(float(x) for x in np.quantile(delta[draws].mean(axis=1),
                                               [0.025, 0.975]))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--families", nargs="+", default=["modular", "spike"])
    ap.add_argument("--start", type=int, default=BLOCK[0])
    ap.add_argument("--end", type=int, default=BLOCK[1])
    ap.add_argument("--out", type=Path, default=Path("outputs/belief-v1"))
    args = ap.parse_args()
    if args.start >= 90000:
        raise SystemExit("the 90000 block is spent; pick a fresh one")
    args.out.mkdir(parents=True, exist_ok=True)
    seeds = list(range(args.start, args.end + 1))

    rows = []
    for family in args.families:
        budget = BUDGET[family]
        for graph_seed in seeds:
            graph = generate_graph(family, graph_seed)
            snapshot = sample_episode(graph, EPISODE_OFFSET + graph_seed)
            truth = np.asarray(snapshot.source_errors, dtype=float)
            marginal, _ = run_public_policy(graph, snapshot, "marginal", budget,
                                            p_catch=P_CATCH)
            oracle, _ = run_public_policy(graph, snapshot, "oracle", budget,
                                          p_catch=P_CATCH)
            # The belief the policy starts from, so the AUC check is about the
            # information the episode begins with, not about post-review updates.
            belief0 = initial_belief(graph, snapshot.confidence)
            base_auc = auc(belief0, truth)
            row = {"family": family, "graph_seed": graph_seed,
                   "marginal": marginal, "oracle": oracle,
                   "auc_belief": base_auc}
            for gamma in GAMMAS:
                errors, _ = run_reference(graph, snapshot, gamma, budget)
                if gamma == 1.0 and errors != marginal:
                    raise SystemExit(
                        f"gamma=1 must reproduce marginal on seed {graph_seed}: "
                        f"{errors} != {marginal}")
                curved = auc(sigmoid(gamma * logit(belief0)), truth)
                if base_auc is not None and curved != base_auc:
                    raise SystemExit(
                        f"monotone map changed the AUC on seed {graph_seed}: "
                        f"{curved} != {base_auc}")
                row[f"gamma_{gamma}"] = errors
                row[f"auc_gamma_{gamma}"] = curved
            rows.append(row)

        subset = [r for r in rows if r["family"] == family]
        with open(args.out / f"belief_{family}.csv", "w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(subset[0]))
            writer.writeheader()
            writer.writerows(subset)

    summary = []
    for family in args.families:
        subset = [r for r in rows if r["family"] == family]
        gap = np.array([r["marginal"] - r["oracle"] for r in subset], dtype=float)
        usable = gap > 0
        curve = []
        for gamma in GAMMAS:
            delta = np.array([r["marginal"] - r[f"gamma_{gamma}"] for r in subset], float)
            recovery = delta[usable] / gap[usable]
            low, high = bootstrap(recovery)
            a = [r[f"auc_gamma_{gamma}"] for r in subset]
            a = [v for v in a if v is not None]
            curve.append({
                "gamma": gamma,
                "mean_errors": float(np.mean([r[f"gamma_{gamma}"] for r in subset])),
                "mean_auc": float(np.mean(a)) if a else None,
                "recovery": float(recovery.mean()),
                "recovery_ci": [low, high],
                "wins": int((delta > 0).sum()), "ties": int((delta == 0).sum()),
                "losses": int((delta < 0).sum()),
            })
        peak = max(curve, key=lambda c: c["recovery"])
        summary.append({
            "family": family, "graphs": len(subset),
            "marginal_mean": float(np.mean([r["marginal"] for r in subset])),
            "oracle_mean": float(np.mean([r["oracle"] for r in subset])),
            "gap_mean": float(gap.mean()),
            "graphs_with_gap": int(usable.sum()),
            "graph_recovery_mean": peak["recovery"],
            "recovery_ci": peak["recovery_ci"],
            "gamma_star": peak["gamma"],
            "mean_auc": peak["mean_auc"],
            "curve": curve,
        })
        print(f"{family:8s} marginal {summary[-1]['marginal_mean']:.3f}  "
              f"oracle {summary[-1]['oracle_mean']:.3f}  "
              f"peak gamma {peak['gamma']} -> {peak['mean_errors']:.3f}  "
              f"recovery {peak['recovery']:+.3f} "
              f"[{peak['recovery_ci'][0]:+.3f}, {peak['recovery_ci'][1]:+.3f}]  "
              f"W/T/L {peak['wins']}/{peak['ties']}/{peak['losses']}")

    with open(args.out / "belief_summary.csv", "w", newline="") as stream:
        flat = [{k: v for k, v in s.items() if k != "curve"} for s in summary]
        writer = csv.DictWriter(stream, fieldnames=list(flat[0]))
        writer.writeheader()
        writer.writerows(flat)
    (args.out / "manifest.json").write_text(json.dumps({
        "block": [args.start, args.end], "episode_offset": EPISODE_OFFSET,
        "gammas": list(GAMMAS), "knob": "logit temperature, ranking preserved",
        "bootstrap_draws": BOOTSTRAP, "bootstrap_seed": BOOTSTRAP_SEED,
        "budget": BUDGET, "p_catch": P_CATCH,
    }, indent=2))
    (args.out / "curve.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
