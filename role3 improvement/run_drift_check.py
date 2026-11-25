"""Boundary test for the construct mapping: does forbidding the loop matter?

Pre-registered in ``PREREGISTER_DRIFT.md`` (block 5600-5699). Two arms, one policy,
one episode per arm:

* ``open``   the shipped layer: the receipt describes the review log and nothing
  feeds back. This is the arm in ``outputs/supervisor-v1/``.
* ``closed`` the prohibited mapping from ``AUDIT_POLICY.md`` v1: an unreviewed
  source still feeding a ``partial`` sink is read as "the reviewers found nothing
  here", so its belief is multiplied by ``1 - p_catch``, compounding per decision.

The arms differ in one function call. Everything else — graph, snapshot, budget,
tie-breaking, reviewer, episode offset — is shared, so the difference is the loop
and not the experiment.
"""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

from dag_role3 import generate_graph, sample_episode
from dag_role3.audit_policy import frozen_policy_v1
from dag_role3.drift import downweight, frontier_sources, optimistic_features, sink_depth
from dag_role3.environment import OversightEnv
from dag_role3.policies import marginal_scores
from dag_role3.supervisor import coverage_truth, receipt, score, sink_truth

BLOCK = (5730, 5829)
EPISODE_OFFSET = 20000
BUDGET = {"spike": 16, "modular": 50, "real": 8, "ticket": 8}
P_CATCH = 0.9
ARMS = ("open", "closed")
BOOTSTRAP_DRAWS = 10000
BOOTSTRAP_SEED = 20261124


def run(graph, snapshot, arm, budget):
    """One episode. Returns actions, env, review log, and the compounding weights."""
    env = OversightEnv(graph, snapshot, budget=budget, p_catch=P_CATCH)
    obs, done, actions, reviewed = env.observation(), env.done, [], []
    weights: dict[int, float] = {}
    while not done:
        if arm == "closed":
            truth = coverage_truth(graph, reviewed)
            downweight(weights, frontier_sources(graph, reviewed, truth=truth), P_CATCH)
            framed = dict(obs, features=optimistic_features(obs, weights))
            values = marginal_scores(framed)
        else:
            values = marginal_scores(obs)
        available = np.flatnonzero(obs["mask"])
        action = int(available[np.argmax(values[available])])
        actions.append(action)
        obs, _, done, _ = env.step(action)
        reviewed.append(action)
    return actions, env, reviewed, weights


def paired(a, b, seed=BOOTSTRAP_SEED, draws=BOOTSTRAP_DRAWS):
    """Paired mean difference a-b with a percentile interval. a and b are paired."""
    d = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(draws, len(d)))
    means = d[idx].mean(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    return {"delta": float(d.mean()), "lo": float(lo), "hi": float(hi),
            "n": int(len(d)), "wins": int((d > 0).sum()), "losses": int((d < 0).sum())}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--families", nargs="+", default=list(BUDGET))
    ap.add_argument("--start", type=int, default=BLOCK[0])
    ap.add_argument("--end", type=int, default=BLOCK[1])
    ap.add_argument("--out", type=Path, default=Path("outputs/drift-v1"))
    args = ap.parse_args()
    if args.start >= 90000 or 5400 <= args.start <= 5729:
        raise SystemExit("pick a block that is neither spent nor the supervisor/pilot block")
    args.out.mkdir(parents=True, exist_ok=True)
    seeds = list(range(args.start, args.end + 1))

    graphs, sinks = [], []
    for family in args.families:
        budget = BUDGET[family]
        for graph_seed in seeds:
            graph = generate_graph(family, graph_seed)
            snapshot = sample_episode(graph, EPISODE_OFFSET + graph_seed)
            depth = sink_depth(graph)
            per_arm, arm_rows = {}, {}
            for arm in ARMS:
                actions, env, reviewed, weights = run(graph, snapshot, arm, budget)
                truth = sink_truth(graph, env)
                statement = receipt(graph, reviewed, claim="honest")
                scored = score(graph, reviewed, statement, truth)
                errors = int(sum(env._effective[i] for i in graph.sinks))
                if errors != sum(1 for v in truth.values() if v):
                    raise RuntimeError("sink truth and environment disagree")
                per_arm[arm] = {"errors": errors, "scored": scored, "truth": truth,
                                "weights": weights, "actions": actions}
                arm_rows[arm] = {
                    "family": family, "graph_seed": graph_seed, "arm": arm,
                    "nodes": graph.n, "sinks": len(graph.sinks),
                    "errors": errors,
                    "false_inspection": scored["false_inspection"],
                    "declared_gap": scored["declared_gap"],
                    "uninspected_errors": scored["uninspected_errors"],
                    "inspected": scored["status_counts"].get("inspected", 0),
                    "partial": scored["status_counts"].get("partial", 0),
                    "untouched": scored["status_counts"].get("untouched", 0),
                    "drifted_sources": len(weights),
                    "min_weight": min(weights.values()) if weights else 1.0,
                }
                for sink in graph.sinks:
                    status = statement["status"][int(sink)]
                    sinks.append({
                        "family": family, "graph_seed": graph_seed, "arm": arm,
                        "sink": int(sink), "depth": depth[int(sink)],
                        "status": status, "wrong": bool(truth[int(sink)]),
                        "declared": status in ("partial", "untouched"),
                    })
            same = per_arm["open"]["actions"] == per_arm["closed"]["actions"]
            for arm in ARMS:
                arm_rows[arm]["identical_actions"] = same
                graphs.append(arm_rows[arm])
            if graph_seed % 20 == 0:
                print(f"  {family} {graph_seed} done", flush=True)

    with open(args.out / "drift_episodes.csv", "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(graphs[0]))
        writer.writeheader()
        writer.writerows(graphs)
    with open(args.out / "drift_sinks.csv", "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(sinks[0]))
        writer.writeheader()
        writer.writerows(sinks)

    by_key = {(g["family"], g["arm"], g["graph_seed"]): g for g in graphs}
    summary, deltas = [], []
    for family in args.families:
        cell = {}
        for arm in ARMS:
            rows = [g for g in graphs if g["family"] == family and g["arm"] == arm]
            wrong = sum(r["errors"] for r in rows)
            false_insp = sum(r["false_inspection"] for r in rows)
            declared = sum(r["declared_gap"] for r in rows)
            denom = false_insp + declared
            cell[arm] = {
                "graphs": len(rows),
                "mean_errors": float(np.mean([r["errors"] for r in rows])),
                "wrong_sinks": wrong,
                "false_inspection": false_insp,
                "declared_gap": declared,
                "declared_share": (declared / denom) if denom else None,
                "untouched": sum(r["untouched"] for r in rows),
                "inspected": sum(r["inspected"] for r in rows),
                "drifted_sources": sum(r["drifted_sources"] for r in rows),
                "identical_actions": sum(1 for r in rows if r["identical_actions"]),
            }
        summary.append({"family": family, **{f"{arm}": cell[arm] for arm in ARMS}})
        for metric in ("errors", "false_inspection", "declared_gap", "untouched"):
            closed = [by_key[(family, "closed", s)][metric] for s in seeds]
            open_ = [by_key[(family, "open", s)][metric] for s in seeds]
            deltas.append({"family": family, "metric": metric, **paired(closed, open_)})
        print(f"{family:8s} errors open {cell['open']['mean_errors']:.3f} "
              f"closed {cell['closed']['mean_errors']:.3f} | undone {cell['open']['untouched']} "
              f"-> {cell['closed']['untouched']}", flush=True)

    depth_rows = []
    for family in args.families:
        depths = sorted({s["depth"] for s in sinks if s["family"] == family})
        for depth in depths:
            row = {"family": family, "depth": depth}
            for arm in ARMS:
                sel = [s for s in sinks if s["family"] == family and s["arm"] == arm
                       and s["depth"] == depth]
                inspected = sum(1 for s in sel if s["status"] == "inspected")
                false_insp = sum(1 for s in sel if s["status"] == "inspected" and s["wrong"])
                row[f"{arm}_sinks"] = len(sel)
                row[f"{arm}_inspected"] = inspected
                row[f"{arm}_false_inspected"] = false_insp
                row[f"{arm}_declared_errors"] = sum(
                    1 for s in sel if s["declared"] and s["wrong"])
                row[f"{arm}_rate"] = (false_insp / inspected) if inspected else None
            depth_rows.append(row)

    payload = {"block": [args.start, args.end], "episode_offset": EPISODE_OFFSET,
               "p_catch": P_CATCH, "arms": list(ARMS),
               "policy": frozen_policy_v1().fingerprint(),
               "bootstrap": {"draws": BOOTSTRAP_DRAWS, "seed": BOOTSTRAP_SEED},
               "summary": summary, "paired": deltas, "depth": depth_rows}
    (args.out / "summary.json").write_text(json.dumps(payload, indent=2))
    (args.out / "manifest.json").write_text(json.dumps({
        "block": [args.start, args.end], "episode_offset": EPISODE_OFFSET,
        "p_catch": P_CATCH, "budget": {f: BUDGET[f] for f in args.families},
        "families": args.families, "arms": list(ARMS),
        "policy": frozen_policy_v1().fingerprint(),
        "python": sys.version.split()[0], "numpy": np.__version__,
        "sha256": {name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
                   for name in ("dag_role3/environment.py", "dag_role3/supervisor.py",
                                "dag_role3/drift.py", "run_drift_check.py")},
    }, indent=2) + "\n")
    for row in deltas:
        if row["metric"] == "errors":
            print(f"{row['family']:8s} dErrors {row['delta']:+.3f} "
                  f"[{row['lo']:+.3f}, {row['hi']:+.3f}]", flush=True)


if __name__ == "__main__":
    main()
