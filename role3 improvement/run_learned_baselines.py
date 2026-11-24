"""Train the learned baselines on every family except spike, then evaluate all six.

Why this exists: the 2026-11-24 suite compares a learned scheduler against rules on
`spike` only. On the other five families the table is rule-versus-rule. This script
closes that asymmetry with the same budget the spike models used (GNN 1,000 episodes,
DQN 300 episodes, 3 training seeds, 30 validation episodes).

Frozen expectation, written before the run: `marginal` still wins. A learned policy
that beats `marginal` on a family is a headline change, not a bug — inspect it and
report it instead of rerunning until it goes away.

Usage (from `role3 improvement/`):

    python3 run_learned_baselines.py                 # train + evaluate + report, 4 workers
    python3 run_learned_baselines.py --jobs 6        # more parallelism
    python3 run_learned_baselines.py --eval-only     # reuse finished checkpoints
    python3 run_learned_baselines.py --dry-run       # print the plan

Outputs:

    outputs/learned/<family>/train_<seed>/{gnn_<family>_observed.pt,dqn_<family>.pt}
    outputs/learned/logs/<family>_s<seed>.log
    outputs/v3-learned/{benchmark_summary.csv,benchmark_role3.csv,manifest.json}
    outputs/v3-learned/learned_vs_marginal.{md,json}   (benchmark spec section 7)
"""
import argparse
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Small families first so partial results exist early.
FAMILIES = ("real", "ticket", "modular", "er", "ba")
SPIKE_CHECKPOINTS = tuple(
    Path("outputs/v3") / f"train_{seed}" / name
    for seed in (1, 2, 3)
    for name in ("gnn_spike_observed.pt", "dqn_spike.pt")
)
GNN_EPISODES, DQN_EPISODES, VALIDATION_EPISODES = 1000, 300, 30


def checkpoints(family, seed, out_root):
    folder = out_root / family / f"train_{seed}"
    return (folder / f"gnn_{family}_observed.pt", folder / f"dqn_{family}.pt")


def run_train(family, seed, out_root, logs, dry_run):
    folder = out_root / family / f"train_{seed}"
    gnn, dqn = checkpoints(family, seed, out_root)
    if gnn.exists() and dqn.exists():
        return family, seed, "cached"
    folder.mkdir(parents=True, exist_ok=True)
    log = logs / f"{family}_s{seed}.log"
    commands = [
        [sys.executable, "train_gnn.py", "--family", family,
         "--episodes", str(GNN_EPISODES), "--eval-seeds", str(VALIDATION_EPISODES),
         "--seed", str(seed), "--out", str(folder)],
        [sys.executable, "train_dqn.py", "--family", family,
         "--episodes", str(DQN_EPISODES), "--eval-seeds", str(VALIDATION_EPISODES),
         "--seed", str(seed), "--out", str(folder)],
    ]
    if dry_run:
        return family, seed, " | ".join(" ".join(c) for c in commands)
    started = time.time()
    with log.open("a") as stream:
        stream.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S')} {family} s{seed} ===\n")
        stream.flush()
        for command in commands:
            subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, check=True)
    return family, seed, f"{time.time() - started:.0f}s"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--families", nargs="+", choices=FAMILIES, default=list(FAMILIES))
    ap.add_argument("--seeds", nargs="+", type=int, default=[1, 2, 3])
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--out-root", type=Path, default=Path("outputs/learned"))
    ap.add_argument("--eval-out", type=Path, default=Path("outputs/v3-learned"))
    ap.add_argument("--eval-only", action="store_true")
    ap.add_argument("--skip-report", action="store_true",
                    help="do not run report_learned_baselines.py after evaluating")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.jobs < 1 or any(seed < 1 for seed in args.seeds):
        ap.error("jobs and seeds must be positive")
    if len(set(args.families)) != len(args.families):
        ap.error("duplicate family")

    logs = args.out_root / "logs"
    logs.mkdir(parents=True, exist_ok=True)

    if not args.eval_only:
        tasks = [(family, seed) for family in args.families for seed in args.seeds]
        print(f"training {len(tasks)} (family, seed) pairs with {args.jobs} workers", flush=True)
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            futures = [pool.submit(run_train, f, s, args.out_root, logs, args.dry_run)
                       for f, s in tasks]
            for future in as_completed(futures):
                family, seed, status = future.result()
                print(f"  {family:8s} s{seed}: {status}", flush=True)
        if args.dry_run:
            return

    missing = [str(path) for family in args.families for seed in args.seeds
               for path in checkpoints(family, seed, args.out_root) if not path.exists()]
    if missing:
        raise SystemExit("missing checkpoints:\n  " + "\n  ".join(missing))

    chosen = SPIKE_CHECKPOINTS + tuple(
        path for family in args.families for seed in args.seeds
        for path in checkpoints(family, seed, args.out_root))
    if args.dry_run:
        print("checkpoints:", *(str(path) for path in chosen), sep="\n  ")
        return

    args.eval_out.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, "run_benchmark.py", "--seeds", "100", "--start-seed", "90000",
               "--checkpoints", *map(str, chosen), "--out", str(args.eval_out)]
    print("evaluating:", " ".join(command), flush=True)
    subprocess.run(command, check=True)

    if not args.skip_report:
        report = [sys.executable, "report_learned_baselines.py",
                  "--csv", str(args.eval_out / "benchmark_role3.csv"),
                  "--out", str(args.eval_out / "learned_vs_marginal.md")]
        print("reporting:", " ".join(report), flush=True)
        subprocess.run(report, check=True)

    import csv
    summary = list(csv.DictReader(
        (args.eval_out / "benchmark_summary.csv").open(encoding="utf-8-sig")))
    learned = ("gnn_s1", "gnn_s2", "gnn_s3", "dqn_s1", "dqn_s2", "dqn_s3")
    print("\nfamily    marginal  best learned  best policy")
    for family in ("spike",) + tuple(args.families):
        block = [row for row in summary if row["family"] == family]
        by_name = {row["policy"]: float(row["mean_sink_errors"]) for row in block}
        best_learned = min((by_name[name] for name in learned if name in by_name), default=float("nan"))
        best = min(by_name, key=by_name.get)
        print(f"{family:8s}  {by_name['marginal']:8.2f}  {best_learned:12.2f}  {best}")


if __name__ == "__main__":
    main()
