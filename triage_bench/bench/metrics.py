"""recall@k / precision@k with a participant-clustered bootstrap CI.

The unit of independence is the participant, not the row: one participant
contributes many days, and their diary errors are correlated. So the bootstrap
resamples pids with replacement and re-ranks the pooled candidate set at a
fixed k.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import SEED


def order_index(scores: np.ndarray) -> np.ndarray:
    """Descending order, deterministic tie-break by position."""
    return np.argsort(-np.asarray(scores, dtype=float), kind="stable")


def recall_at_k(scores: np.ndarray, y: np.ndarray, k: int) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    idx = order_index(scores)[:k]
    hits = float(np.asarray(y)[idx].sum())
    total = float(np.asarray(y).sum())
    return hits / total if total else float("nan")


def precision_at_k(scores: np.ndarray, y: np.ndarray, k: int) -> float:
    idx = order_index(scores)[:k]
    return float(np.asarray(y)[idx].mean()) if k else float("nan")


def bootstrap_recall_ci(
    queue: pd.DataFrame,
    scores: np.ndarray,
    k: int,
    label_col: str = "y_broad",
    n_boot: int = 1000,
    seed: int = SEED,
) -> tuple[float, float, float]:
    """Return (point, lo95, hi95) for recall@k under a pid-clustered bootstrap."""
    y = queue[label_col].to_numpy()
    point = recall_at_k(scores, y, k)

    pids = queue["pid"].to_numpy()
    unique = np.unique(pids)
    by_pid = {p: np.where(pids == p)[0] for p in unique}
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        chosen = rng.choice(unique, size=len(unique), replace=True)
        rows = np.concatenate([by_pid[p] for p in chosen])
        val = recall_at_k(scores[rows], y[rows], k)
        if np.isfinite(val):
            vals.append(val)

    if not vals:
        return point, float("nan"), float("nan")
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return point, float(lo), float(hi)
