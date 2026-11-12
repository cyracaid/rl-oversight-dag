"""Rebuild the distributed training and evaluation results on CPU."""
import subprocess
import sys
from pathlib import Path


def run(*args):
    subprocess.run([sys.executable, *map(str, args)], check=True)


if __name__ == "__main__":
    checkpoints = []
    for seed in (1, 2, 3):
        out = Path("outputs") / f"train_{seed}"
        run("train_gnn.py", "--seed", seed, "--out", out)
        run("train_dqn.py", "--seed", seed, "--out", out)
        checkpoints.extend([out/"dqn_spike.pt", out/"gnn_spike_observed.pt"])
    run("run_benchmark.py", "--checkpoints", *checkpoints)
    run("compare_beliefs.py")
    run("run_demo.py", "--family", "real", "--policy", "structural")
    run("run_demo.py", "--family", "real", "--policy", "marginal", "--particles", 1024,
        "--out", "outputs/particle_demo")
