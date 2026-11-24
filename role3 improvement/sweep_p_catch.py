"""Sweep the reviewer hit rate p_catch on held-out graph seeds.

Pre-registered in ``PREREGISTER_P_CATCH.md``. Graph seeds 4000-4199 were not used
by any earlier experiment; the reporting block 90000-90099 is spent and is not
touched here.

Every policy in a row sees the same graph, the same episode snapshot and the same
reviewer uniforms. Only ``p_catch`` changes, so the cells are paired by
construction and the differences are within-episode differences.
"""
import argparse
import hashlib
import json
import platform
from pathlib import Path

import numpy as np

from dag_role3 import generate_graph, sample_episode
from dag_role3.policies import run_public_policy
from run_benchmark import interval, load_policy, save

GRID = (0.60, 0.75, 0.90, 1.00)
BUDGET = {"spike": 16, "real": 8}
SPIKE_CHECKPOINTS = [Path(f"outputs/v3/train_{seed}/gnn_spike_observed.pt")
                     for seed in (1, 2, 3)]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--families", nargs="+", default=["spike", "real"])
    ap.add_argument("--p-catch", nargs="+", type=float, default=list(GRID))
    ap.add_argument("--seeds", type=int, default=200)
    ap.add_argument("--start-seed", type=int, default=4000)
    ap.add_argument("--out", type=Path, default=Path("outputs/p-catch-v1"))
    args = ap.parse_args()
    if args.seeds < 1 or len(set(args.families)) != len(args.families):
        ap.error("need positive seeds and distinct families")
    if any(not 0 < p <= 1 for p in args.p_catch):
        ap.error("p_catch must lie in (0, 1]")
    if len(set(args.p_catch)) != len(args.p_catch):
        ap.error("duplicate p_catch values")
    if args.start_seed < 4000 or args.start_seed + args.seeds > 90000:
        ap.error("this sweep owns graph seeds [4000, 90000) only")

    learners = {}
    for path in SPIKE_CHECKPOINTS:
        if not path.exists():
            ap.error(f"missing checkpoint {path}; run train_gnn.py first")
        family, name, act = load_policy(path)
        if family != "spike":
            ap.error(f"{path} is not a spike checkpoint")
        learners[name] = act

    args.out.mkdir(parents=True, exist_ok=True)
    rules = ("confidence", "marginal", "oracle")
    rows, summary = [], []
    for family in args.families:
        policies = {name: name for name in rules}
        if family == "spike":
            policies |= learners
        scores = {(p, name): [] for p in args.p_catch for name in policies}
        for seed in range(args.start_seed, args.start_seed + args.seeds):
            graph = generate_graph(family, seed)
            episode_seed = 20000 + seed
            snapshot = sample_episode(graph, episode_seed)
            budget = BUDGET[family]
            for p_catch in args.p_catch:
                for name in policies:
                    errors, _ = run_public_policy(graph, snapshot, name, budget,
                                                  p_catch=p_catch)
                    scores[p_catch, name].append(errors)
                    rows.append(dict(family=family, graph_seed=seed,
                                     episode_seed=episode_seed, n=graph.n,
                                     budget=budget, p_catch=p_catch, policy=name,
                                     sink_errors=errors,
                                     sink_error_rate=errors / len(graph.sinks)))
        for p_catch in args.p_catch:
            for name in policies:
                errors = scores[p_catch, name]
                delta = np.subtract(scores[p_catch, "confidence"], errors)
                lo, hi = interval(delta)
                summary.append(dict(
                    family=family, p_catch=p_catch, policy=name,
                    n_episodes=len(errors), mean_sink_errors=float(np.mean(errors)),
                    zero_error_rate=float(np.mean(np.asarray(errors) == 0)),
                    gain_vs_confidence=float(delta.mean()),
                    paired_lo=lo, paired_hi=hi,
                    wins=int(np.sum(delta > 0)), ties=int(np.sum(delta == 0)),
                    losses=int(np.sum(delta < 0))))
        print(family, "complete", flush=True)

    manifest = {
        "python": platform.python_version(), "numpy": np.__version__,
        "families": list(args.families), "p_catch_grid": list(args.p_catch),
        "test_start": args.start_seed, "episodes_per_cell": args.seeds,
        "preregistration": "PREREGISTER_P_CATCH.md",
        "bootstrap_replicates": 2000, "bootstrap_seed": 411,
        "checkpoints": {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in SPIKE_CHECKPOINTS},
        "source_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sorted(Path("dag_role3").glob("*.py"))},
    }
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    save(args.out / "p_catch_episodes.csv", rows)
    save(args.out / "p_catch_summary.csv", summary)


if __name__ == "__main__":
    main()
