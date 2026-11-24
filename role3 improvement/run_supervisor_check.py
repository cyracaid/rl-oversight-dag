"""Run the supervisor axis: the same review log, three ways of describing it.

Pre-registered in ``PREREGISTER_SUPERVISOR.md`` (block 5400-5599). Numbers here
are counts, not deltas: this experiment does not compare policies, it compares
statements about one policy's episode.

P1 is checked by construction, not asserted: the policy is run twice, once with
a receipt recomputed after every step and once without, and the action lists are
compared.
"""
import argparse
import csv
import hashlib
import json
import random
import sys
from pathlib import Path

import numpy as np

from dag_role3 import generate_graph, sample_episode
from dag_role3.environment import OversightEnv
from dag_role3.policies import choose, marginal_scores
from dag_role3.supervisor import receipt, score, sink_truth

BLOCK = (5400, 5599)
EPISODE_OFFSET = 20000
BUDGET = {"spike": 16, "modular": 50, "real": 8, "ticket": 8}
P_CATCH = 0.9
POLICIES = ("marginal", "oracle")
CLAIMS = ("honest", "overclaim")


def run(graph, snapshot, policy, budget, with_receipts=False):
    """One episode. ``with_receipts`` recomputes a statement after every step."""
    env = OversightEnv(graph, snapshot, budget=budget, p_catch=P_CATCH)
    rng = random.Random(snapshot.seed + 981)
    obs, done, actions = env.observation(), env.done, []
    reviewed = []
    while not done:
        if policy == "oracle":
            values = marginal_scores(obs, base_override=env._base)
            available = np.flatnonzero(obs["mask"])
            action = int(available[np.argmax(values[available])])
        else:
            action = choose(obs, policy, rng)
        actions.append(action)
        obs, _, done, _ = env.step(action)
        reviewed.append(action)
        if with_receipts:
            receipt(graph, reviewed)          # must not touch env or rng
    return actions, env, reviewed


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--families", nargs="+", default=list(BUDGET))
    ap.add_argument("--start", type=int, default=BLOCK[0])
    ap.add_argument("--end", type=int, default=BLOCK[1])
    ap.add_argument("--out", type=Path, default=Path("outputs/supervisor-v1"))
    args = ap.parse_args()
    if args.start >= 90000:
        raise SystemExit("the 90000 block is spent; pick a fresh one")
    args.out.mkdir(parents=True, exist_ok=True)
    seeds = list(range(args.start, args.end + 1))

    rows, mismatches = [], []
    for family in args.families:
        budget = BUDGET[family]
        for graph_seed in seeds:
            graph = generate_graph(family, graph_seed)
            snapshot = sample_episode(graph, EPISODE_OFFSET + graph_seed)
            for policy in POLICIES:
                plain, env, reviewed = run(graph, snapshot, policy, budget)
                loud, _, _ = run(graph, snapshot, policy, budget, with_receipts=True)
                if plain != loud:
                    mismatches.append({"family": family, "graph_seed": graph_seed,
                                       "policy": policy})
                errors = int(sum(env._effective[i] for i in graph.sinks))
                truth = sink_truth(graph, env)
                wrong = sum(1 for v in truth.values() if v)
                if errors != wrong:
                    raise RuntimeError("sink truth and environment disagree")
                base = {"family": family, "policy": policy,
                        "graph_seed": graph_seed, "nodes": graph.n,
                        "sinks": len(graph.sinks), "errors": errors,
                        "wrong_sinks": wrong}
                for claim in CLAIMS:
                    statement = receipt(graph, reviewed, claim=claim)
                    scored = score(graph, reviewed, statement, truth)
                    row = dict(base, claim=claim)
                    row["inspected"] = scored["status_counts"].get("inspected", 0)
                    row["partial"] = scored["status_counts"].get("partial", 0)
                    row["untouched"] = scored["status_counts"].get("untouched", 0)
                    row["false_inspection"] = scored["false_inspection"]
                    row["declared_gap"] = scored["declared_gap"]
                    row["uninspected_errors"] = scored["uninspected_errors"]
                    row["fidelity"] = scored["fidelity"]
                    row["judged"] = scored["judged"]
                    rows.append(row)
                rows.append(dict(base, claim="silent", inspected="", partial="",
                                 untouched="", false_inspection="", declared_gap="",
                                 uninspected_errors="", fidelity="", judged=""))
            if graph_seed % 20 == 0:
                print(f"  {family} {graph_seed} done", flush=True)

    with open(args.out / "supervisor_episodes.csv", "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    summary = []
    for family in args.families:
        for policy in POLICIES:
            honest = [r for r in rows if r["family"] == family
                      and r["policy"] == policy and r["claim"] == "honest"]
            over = [r for r in rows if r["family"] == family
                    and r["policy"] == policy and r["claim"] == "overclaim"]
            wrong = sum(r["wrong_sinks"] for r in honest)
            false_insp = sum(r["false_inspection"] for r in honest)
            declared = sum(r["declared_gap"] for r in honest)
            denom = false_insp + declared
            summary.append({
                "family": family, "policy": policy,
                "graphs": len(honest),
                "mean_errors": float(np.mean([r["errors"] for r in honest])),
                "wrong_sinks": wrong,
                "false_inspection": false_insp,
                "declared_gap": declared,
                "declared_share": (declared / denom) if denom else None,
                "fidelity_min": min(float(r["fidelity"]) for r in honest),
                "judged_min": min(float(r["judged"]) for r in honest),
                "overclaim_false_inspection": sum(r["false_inspection"] for r in over),
                "overclaim_false_equals_wrong": all(
                    r["false_inspection"] == r["wrong_sinks"] for r in over),
                "status_counts": {
                    "inspected": sum(r["inspected"] for r in honest),
                    "partial": sum(r["partial"] for r in honest),
                    "untouched": sum(r["untouched"] for r in honest),
                },
            })
            entry = summary[-1]
            print(f"{family:8s} {policy:8s} errors {entry['mean_errors']:.3f} "
                  f"wrong {wrong:4d} declared {declared:4d} "
                  f"false {false_insp:4d} share "
                  f"{entry['declared_share'] if entry['declared_share'] is None else round(entry['declared_share'], 3)}",
                  flush=True)

    payload = {"block": list(BLOCK), "episode_offset": EPISODE_OFFSET,
               "p_catch": P_CATCH, "p1_mismatches": mismatches,
               "p1_holds": not mismatches, "rows": summary}
    with open(args.out / "summary.json", "w") as stream:
        json.dump(payload, stream, indent=2)
    with open(args.out / "manifest.json", "w") as stream:
        json.dump({"block": list(BLOCK), "episode_offset": EPISODE_OFFSET,
                   "p_catch": P_CATCH,
                   "budget": {f: BUDGET[f] for f in args.families},
                   "families": args.families, "policies": list(POLICIES),
                   "claims": [*CLAIMS, "silent"],
                   "python": sys.version.split()[0], "numpy": np.__version__,
                   "sha256": {name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
                              for name in ("dag_role3/environment.py",
                                           "dag_role3/supervisor.py",
                                           "run_supervisor_check.py")}},
                  stream, indent=2)
    print(f"P1 mismatches: {len(mismatches)}")


if __name__ == "__main__":
    main()
