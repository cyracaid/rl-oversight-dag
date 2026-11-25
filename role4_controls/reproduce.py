"""One-command teammate reproduction of everything in role4_controls/.

Reruns every script into a temporary folder and compares each output byte-for-byte with the committed
file. The committed results are never touched.

    python3 reproduce.py               # v1 + diagnostics (~6 min, one core)
    python3 reproduce.py --full        # + v2, ten rewire draws (~20-40 min; use --jobs)
    python3 reproduce.py --full --jobs 4

Exit code 0 = every file identical. Report the printed table either way.
"""
from __future__ import annotations

import argparse
import filecmp
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable


def run(cmd):
    t = time.time()
    print("$", " ".join(str(c) for c in cmd), flush=True)
    done = subprocess.run([PY, *map(str, cmd)], cwd=HERE)
    if done.returncode != 0:
        print(f"FAILED (exit {done.returncode}) — stop here and report this output", file=sys.stderr)
        sys.exit(done.returncode)
    print(f"  ok, {time.time() - t:.0f}s", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--full", action="store_true", help="also rerun v2 (ten rewire draws)")
    ap.add_argument("--jobs", type=int, default=1, help="processes for v2")
    args = ap.parse_args()

    import networkx
    import numpy
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=HERE,
                            capture_output=True, text=True).stdout.strip() or "unknown"
    print(f"commit {commit} | Python {platform.python_version()} | numpy {numpy.__version__} | "
          f"networkx {networkx.__version__} | {platform.system()} {platform.machine()}\n")

    tmp = Path(tempfile.mkdtemp(prefix="role4_repro_"))
    pairs = []

    run(["run_controls.py", "--selftest"])
    run(["run_controls.py", "--out", tmp / "v1"])
    for name in ("controls.csv", "controls_summary.csv", "benchmark_worst_of_n.csv"):
        pairs.append((f"results/{name}", tmp / "v1" / name))

    run(["diagnostics.py", "--controls", tmp / "v1" / "controls.csv", "--out", tmp / "diagnostics.csv"])
    pairs.append(("results/diagnostics.csv", tmp / "diagnostics.csv"))

    if args.full:
        run(["run_controls_v2.py", "--selftest"])
        run(["run_controls_v2.py", "--jobs", args.jobs, "--out", tmp / "v2"])
        for name in ("controls_v2.csv", "controls_v2_summary.csv"):
            pairs.append((f"results/v2/{name}", tmp / "v2" / name))

    print("\n| committed file | identical |\n|---|---|")
    ok = True
    for committed, fresh in pairs:
        same = filecmp.cmp(HERE / committed, fresh, shallow=False)
        ok &= same
        print(f"| {committed} | {'yes' if same else '**NO**'} |")
    scope = "v1 + diagnostics + v2" if args.full else "v1 + diagnostics (add --full for v2)"
    print(f"\n{'PASS' if ok else 'FAIL'}: {scope}. Fresh outputs in {tmp}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
