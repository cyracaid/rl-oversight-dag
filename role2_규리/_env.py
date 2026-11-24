"""Locate the Role 3 environment and the shared experiment modules.

Preferred: install the environment once, then nothing here touches ``sys.path``.

    python -m pip install -e "role3 improvement"

Without an install a fresh checkout must still work, so the in-repo directory is
appended as a fallback. Keep this the only place that edits ``sys.path``.
"""
from __future__ import annotations

from importlib.util import find_spec
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
ROLE3 = ROOT / "role3 improvement"
EXPERIMENTS = ROOT / "experiments"


def _usable(module: str) -> bool:
    return find_spec(module) is not None


def ensure_role3() -> Path:
    """Make ``dag_role3`` importable; an installed package wins over the repo copy."""
    if not _usable("dag_role3") and str(ROLE3) not in sys.path:
        sys.path.insert(0, str(ROLE3))
    return ROLE3


def ensure_experiments() -> Path:
    """Make the shared helpers in ``experiments/`` importable."""
    if not _usable("rl_boundary") and str(EXPERIMENTS) not in sys.path:
        sys.path.insert(0, str(EXPERIMENTS))
    return EXPERIMENTS
