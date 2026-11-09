"""The only remaining headroom: can anything rank M4-only flags above noise?

885 of the 1,048 queue items are M4-only (window-illegal, no order violation) and
only 7 of them are human-confirmed errors -- 0.8% precision. The M1-bearing items
are already easy (42.7%). So the scientific question is whether context features
lift precision inside the M4-only block.

This module answers it honestly: grouped cross-validation by participant (a
participant never appears in both train and test), a permutation test on the CV
AUC, and top-k precision at the small k a curator could actually afford.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .config import SEED

# Feature allow-list. Nothing here is derived from a correction or a label.
NUMERIC = [
    "tst_minutes", "sol_computed_minutes", "se_percent", "tib_minutes",
    "sleepperiod_minutes", "waso_computed_minutes",
    "waso_avg_bout_selfreport_minutes", "sol_selfreport_minutes",
    "waso_selfreport_minutes", "num_waso_bouts_selfreport",
    "nap_selfreport_totalminutes", "exercise_light_minutes",
    "exercise_moderate_minutes", "exercise_vigorous_minutes",
    "exercise_strength_minutes", "caffeine_num", "alcohol_num",
    "nicotine_doses", "cannabis_doses", "day_num",
]
TIMESTAMPS = [
    "bedtime_selfreport_ts", "sleeponset_selfreport_ts",
    "awakening_selfreport_ts", "getup_selfreport_ts",
]


def _minutes_between(later: pd.Series, earlier: pd.Series) -> pd.Series:
    """Minutes from `earlier` to `later`, wrapping across midnight."""
    delta = (later - earlier).dt.total_seconds() / 60.0
    return delta.where(delta >= 0, delta + 24 * 60)


def build_features(queue: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, pd.Series, list[str]]:
    """Return (X, y, groups, feature_names) for the M4-only block."""
    block = queue.loc[queue["m4"] & ~queue["m1"]].copy()
    X = pd.DataFrame(index=block.index)
    for col in NUMERIC:
        X[col] = pd.to_numeric(block.get(col), errors="coerce")

    ts = {name: pd.to_datetime(block.get(name), errors="coerce") for name in TIMESTAMPS}
    bed, sleep, awake, getup = (ts[n] for n in TIMESTAMPS)
    X["bed_hour"] = bed.dt.hour + bed.dt.minute / 60.0
    X["bed_sleep_gap"] = _minutes_between(sleep, bed)
    X["sleep_awake_gap"] = _minutes_between(awake, sleep)
    X["awake_getup_gap"] = _minutes_between(getup, awake)

    X["sol_gap"] = X["sol_selfreport_minutes"] - X["sol_computed_minutes"]
    X["waso_gap"] = X["waso_selfreport_minutes"] - X["waso_computed_minutes"]
    # TST should equal TIB - SOL - WASO if the four timestamps are consistent.
    X["tst_identity_gap"] = X["tst_minutes"] - (
        X["tib_minutes"] - X["sol_computed_minutes"] - X["waso_computed_minutes"]
    )
    X["timeline_gap"] = X["sleep_awake_gap"] - (
        X["tst_minutes"] + X["waso_computed_minutes"]
    )

    features = [c for c in X.columns if X[c].notna().any()]
    X = X[features].fillna(X[features].median(numeric_only=True))
    return X, block["y_broad"].to_numpy(int), block["pid"], features


def _model() -> object:
    return make_pipeline(
        StandardScaler(),
        LogisticRegression(C=0.5, class_weight="balanced", max_iter=2000),
    )


def cv_scores(X: pd.DataFrame, y: np.ndarray, groups: pd.Series) -> np.ndarray:
    cv = GroupKFold(n_splits=min(5, groups.nunique()))
    return cross_val_predict(_model(), X, y, groups=groups, cv=cv,
                             method="predict_proba")[:, 1]


def _safe_auc(y: np.ndarray, s: np.ndarray) -> float:
    return float(roc_auc_score(y, s)) if len(np.unique(y)) == 2 else float("nan")


def permutation_p(X: pd.DataFrame, y: np.ndarray, groups: pd.Series,
                  observed: float, n_perm: int = 200, seed: int = SEED) -> float:
    rng = np.random.default_rng(seed)
    hits = 0
    for _ in range(n_perm):
        perm = rng.permutation(y)
        if _safe_auc(perm, cv_scores(X, perm, groups)) >= observed:
            hits += 1
    return (1 + hits) / (1 + n_perm)


def single_feature_auc(X: pd.DataFrame, y: np.ndarray) -> pd.DataFrame:
    rows = []
    for col in X.columns:
        auc = _safe_auc(y, X[col].to_numpy())
        rows.append({"feature": col, "auc": auc if auc >= 0.5 else 1 - auc,
                     "direction": "+" if auc >= 0.5 else "-"})
    return pd.DataFrame(rows).sort_values("auc", ascending=False).reset_index(drop=True)


def univariate_perm_p(X: pd.DataFrame, y: np.ndarray,
                      observed_max: float, n_perm: int = 200,
                      seed: int = SEED) -> float:
    """Family-wise p-value for the best single-feature AUC.

    Univariate AUCs with ~10 positives look impressive by chance; this shuffles
    the labels and records how often *any* feature reaches the observed maximum.
    """
    rng = np.random.default_rng(seed)
    hits = 0
    for _ in range(n_perm):
        perm = rng.permutation(y)
        best = 0.0
        for col in X.columns:
            auc = _safe_auc(perm, X[col].to_numpy())
            if np.isfinite(auc):
                best = max(best, auc, 1 - auc)
        if best >= observed_max:
            hits += 1
    return (1 + hits) / (1 + n_perm)


def topk_precision(scores: np.ndarray, y: np.ndarray, ks=(10, 25, 50, 100)) -> dict:
    order = np.argsort(-scores, kind="stable")
    out = {}
    for k in ks:
        idx = order[:k]
        out[f"p@{k}"] = float(y[idx].mean())
    return out
