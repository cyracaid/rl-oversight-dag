"""Train and compare Role 2 policies on the Role 3 v3 Spike environment."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys


ROLE2 = Path(__file__).resolve().parent
ROLE3 = ROLE2.parent / "role3 improvement"
VARIANTS = ("static", "observed")
FAMILY = "spike"
PROFILES = {
    "smoke": {
        "train_seeds": (1,),
        "episodes": 2,
        "validation_graphs": 2,
        "validation_every": 1,
        "test_start": 99997,
        "test_graphs": 3,
    },
    "full": {
        "train_seeds": (1, 2, 3, 4, 5),
        "episodes": 20000,
        "validation_graphs": 30,
        "validation_every": 100,
        "test_start": 90000,
        "test_graphs": 200,
    },
}


def run_script(directory, script, *args):
    command = [sys.executable, "-B", "-u", "-X", "utf8", script, *map(str, args)]
    try:
        subprocess.run(command, cwd=directory, check=True)
    except subprocess.CalledProcessError as error:
        raise SystemExit(f"{script} failed (exit {error.returncode})") from None


def assess(out, *options):
    run_script(ROLE2, "evaluate_conditions.py", "--out", out, *options)
    run_script(ROLE2, "report_conditions.py", out)
    run_script(ROLE2, "shuffle_control.py", out)


def assess_feedback(out, *options):
    run_script(ROLE2, "evaluate_feedback.py", "--out", out, *options)
    run_script(ROLE2, "report_feedback.py", out)


def run_residual_study(out, jobs):
    out.mkdir(parents=True, exist_ok=False)

    def train_seed(seed):
        run_script(ROLE2, "train_residual.py", "--seed", seed, "--out", out / "train" / f"seed-{seed}")

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        list(pool.map(train_seed, range(1, 6)))
    run_script(ROLE2, "evaluate_residual.py", "--run", out, "--out", out / "eval")
    run_script(ROLE2, "report_residual.py", out)
    run_script(ROLE2, "trace_residual.py", out)
    print(f"Report: {out / 'residual.md'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=(*PROFILES, "assess", "feedback", "residual", "planning"),
                        default="smoke", help="planning evaluates two-review policies, residual trains "
                             "the anchored GNN, assess and feedback evaluate frozen models, "
                             "smoke and full train the original variants")
    parser.add_argument("--jobs", type=int, choices=range(1, 6), default=1,
                        help="parallel training seeds for residual or graph workers for planning (default: 1)")
    parser.add_argument("--out", type=Path, help="new run directory (default: role2_규리/runs)")
    args = parser.parse_args()

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = (args.out or ROLE2 / "runs" / f"{args.profile}-{timestamp}").resolve()
    if args.profile == "planning":
        run_script(ROLE2, "evaluate_planning.py", "--out", out, "--jobs", args.jobs)
        run_script(ROLE2, "report_planning.py", out)
        print(f"Report: {out / 'planning.md'}")
        return
    for script in ("train_gnn.py", "run_benchmark.py"):
        if not (ROLE3 / script).is_file():
            parser.error(f"missing Role 3 script: {ROLE3 / script}")
    if args.profile == "residual":
        if out.exists():
            parser.error(f"run directory already exists: {out}")
        run_residual_study(out, args.jobs)
        return
    if args.profile == "assess":
        assess(out)
        print(f"Report: {out / 'comparison.md'}")
        return
    if args.profile == "feedback":
        assess_feedback(out)
        print(f"Report: {out / 'feedback.md'}")
        return

    try:
        out.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error(f"run directory already exists: {out}")

    settings = PROFILES[args.profile]
    config = {"profile": args.profile, "family": FAMILY, "variants": VARIANTS, **settings}
    (out / "config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(f"Run directory: {out}", flush=True)

    checkpoints = []
    for seed in settings["train_seeds"]:
        for variant in VARIANTS:
            train_dir = out / "train" / variant / f"seed-{seed}"
            print(f"Training {variant}, seed {seed}", flush=True)
            run_script(
                ROLE3, "train_gnn.py", "--family", FAMILY, "--variant", variant, "--seed", seed,
                "--episodes", settings["episodes"], "--eval-seeds", settings["validation_graphs"],
                "--validation-every", settings["validation_every"], "--out", train_dir,
            )
            checkpoints.append(train_dir / f"gnn_{FAMILY}_{variant}.pt")

    run_script(
        ROLE3, "run_benchmark.py", "--families", FAMILY, "--start-seed", settings["test_start"],
        "--seeds", settings["test_graphs"], "--checkpoints", *checkpoints, "--out", out / "eval",
    )

    condition_start = settings["test_start"] if args.profile == "smoke" else 91000
    assess(out / "conditions", "--checkpoints", *checkpoints, "--start", condition_start,
           "--graphs", settings["test_graphs"])
    observed = [path for path in checkpoints if path.name.endswith("_observed.pt")]
    feedback_start = 99994 if args.profile == "smoke" else 92000
    assess_feedback(out / "feedback", "--checkpoints", *observed, "--start", feedback_start,
                    "--graphs", settings["test_graphs"])
    print(f"Finished. Reports: {out / 'conditions' / 'comparison.md'}, {out / 'feedback' / 'feedback.md'}")


if __name__ == "__main__":
    main()
