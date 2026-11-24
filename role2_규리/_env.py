"""Locate the Role 3 environment and the shared experiment modules.

Preferred: install the environment once.

    python -m pip install -e "role3 improvement"

The in-repo directory is still appended, because Role 2 imports Role 3's entry
scripts (``run_benchmark``, ``train_gnn``), which are not installed. Appending
means an installed ``dag_role3`` still wins over the repo copy. Keep this the
only place that edits ``sys.path``.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
ROLE3 = ROOT / "role3 improvement"
EXPERIMENTS = ROOT / "experiments"


def ensure_role3() -> Path:
    """Make the Role 3 directory importable.

    Two different needs share one path: ``dag_role3`` (a package, which an
    installed ``dag-role3`` should satisfy) and the Role 3 entry scripts
    ``run_benchmark`` / ``train_gnn`` (which Role 2 imports directly and which
    are never installed). Appending keeps an installed package winning while
    still reaching the scripts.
    """
    if str(ROLE3) not in sys.path:
        sys.path.append(str(ROLE3))
    return ROLE3


def ensure_experiments() -> Path:
    """Make the shared helpers in ``experiments/`` importable."""
    if str(EXPERIMENTS) not in sys.path:
        sys.path.append(str(EXPERIMENTS))
    return EXPERIMENTS
