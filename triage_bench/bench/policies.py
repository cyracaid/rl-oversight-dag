"""Ranking policies for the review queue.

Every policy returns a score where larger means "review this sooner". No policy
may read a label column; the oracle exists only to measure the ceiling.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import SEED


def _sol_selfreport_gap(queue: pd.DataFrame) -> pd.Series:
    """|self-reported SOL - computed SOL| -- a feature M4 is nominally about."""
    return (queue["sol_selfreport_minutes"] - queue["sol_computed_minutes"]).abs()


POLICIES = {
    # The pipeline's own order, as a proxy for "no prioritisation at all".
    "queue_order": lambda q: -q["queue_pos"].to_numpy(float),
    # Structural rules the AI already has; a deliberately dumb severity score.
    "rule_count": lambda q: q["n_rules"].to_numpy(float),
    # One-line rule: anything M1-bearing first, everything else after.
    "m1_first": lambda q: q["m1"].astype(float).to_numpy(),
    # M1 first, then M4-only ordered by the self-report/computed inconsistency.
    "m1_then_sol_gap": lambda q: (
        q["m1"].astype(float) * 10.0 + np.clip(_sol_selfreport_gap(q).fillna(0), 0, 9) / 10.0
    ).to_numpy(float),
    # Ceiling: only reachable with the labels in hand.
    "oracle": lambda q: q["y_broad"].to_numpy(float),
}

RANDOM_NAME = "random"


def random_scores(queue: pd.DataFrame, seed: int = SEED) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.random(len(queue))


def score_all(queue: pd.DataFrame) -> dict[str, np.ndarray]:
    scores = {name: fn(queue) for name, fn in POLICIES.items()}
    scores[RANDOM_NAME] = random_scores(queue)
    return scores
