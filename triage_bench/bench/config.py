"""Configuration and the data-boundary guard for triage_bench.

Red line (repo Core Principle 1): the sleep data never enters this repository.
Every script reads it from an external directory, and this module refuses to run
if the data directory resolves inside the repo. Only aggregate numbers are
written to ``triage_bench/outputs/``.
"""

from __future__ import annotations

import os
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BENCH_DIR.parent
OUT_DIR = BENCH_DIR / "outputs"
FIG_DIR = BENCH_DIR / "figures"

# Where the three input files live, relative to the data directory.
FILES = {
    "candidates": "audit_m1_m7_decision.csv",           # 13,990 row-level AI verdicts
    "labels": "manual_error_correction_updated.csv",    # 75 manual corrections
    "rows": "output/cleaned_data_final.csv",            # cleaned fields (features)
}

DEFAULT_DATA_DIR = Path.home() / "Documents" / "splsleep"
DATA_DIR_ENV = "SPLSLEEP_DATA_DIR"

SEED = 20261109
RULES = [
    "M1_order_violation",
    "M2_clock_shape",
    "M3_self_deviation",
    "M4_window_illegal",
    "M5_silent_worsening",
    "M6_cross_day_jump",
]


def data_dir() -> Path:
    """Resolve the external data directory (never inside the repo)."""
    raw = os.environ.get(DATA_DIR_ENV)
    root = Path(raw).expanduser().resolve() if raw else DEFAULT_DATA_DIR.resolve()
    return root


def assert_outside_repo(path: Path) -> Path:
    """Fail closed if the data directory is inside the git repository."""
    path = path.resolve()
    try:
        path.relative_to(REPO_ROOT)
    except ValueError:
        return path
    raise SystemExit(
        f"REFUSING TO RUN: data dir {path} is inside the repo {REPO_ROOT}. "
        "Real sleep data must stay outside the repository "
        f"(set {DATA_DIR_ENV} to an external path)."
    )


def require_data() -> Path:
    """Return the data dir, or exit cleanly when it is absent.

    Exiting 0 keeps `python3 triage_bench/run_bench.py` safe on a fresh clone
    where nobody has the restricted data -- same contract as verify_clustering.py.
    """
    root = assert_outside_repo(data_dir())
    missing = [rel for rel in FILES.values() if not (root / rel).is_file()]
    if missing:
        print(f"data missing in {root}: {missing}")
        print("skipping triage_bench (this is expected on a machine without the data).")
        raise SystemExit(0)
    return root
