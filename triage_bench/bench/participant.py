"""Participant-level headroom.

The row-level result is a negative: inside the 885 M4-only flags nothing beats
noise. But positives are spread thin across participants (~1 error each), which
is exactly the pattern that makes row features useless and participant features
worth testing.

Two questions, both answerable from labels:

    1. Do errors cluster by participant at all?  (variance/mean of positives per
       participant vs a label-shuffle null -- a single test, no multiple
       comparisons.)
    2. If they do, can a feature that never sees a label rank participants?

A feature is computed only from rows and rule flags. The label columns are
already gone by the time `build_features` sees the frame.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import SEED


def build_features(queue: pd.DataFrame, rows: pd.DataFrame) -> pd.DataFrame:
    """Per-participant aggregates. No label column is read."""
    r = rows.copy()
    for col in ("sol_selfreport_minutes", "sol_computed_minutes", "tst_minutes",
                "tib_minutes", "waso_computed_minutes"):
        r[col] = pd.to_numeric(r[col], errors="coerce")

    bed = pd.to_datetime(r.get("bedtime_selfreport_ts"), errors="coerce")
    r["bed_hour"] = bed.dt.hour + bed.dt.minute / 60.0
    r["abs_sol_gap"] = (r["sol_selfreport_minutes"] - r["sol_computed_minutes"]).abs()
    ident = (r["tst_minutes"]
             - (r["tib_minutes"] - r["sol_computed_minutes"] - r["waso_computed_minutes"])).abs()
    r["tst_break"] = (ident > 30).astype(float)
    r.loc[ident.isna(), "tst_break"] = np.nan

    all_rows = r.groupby("pid").agg(
        n_rows=("row_id", "size"),
        mean_abs_sol_gap=("abs_sol_gap", "mean"),
        tst_break_rate=("tst_break", "mean"),
        sd_bed_hour=("bed_hour", "std"),
    )

    flags = queue.groupby("pid").agg(
        n_flags=("m1", "size"),
        n_m1=("m1", "sum"),
        mean_n_rules=("n_rules", "mean"),
    )
    feats = all_rows.join(flags, how="inner")
    feats["flag_density"] = feats["n_flags"] / feats["n_rows"]
    feats["m1_density"] = feats["n_m1"] / feats["n_rows"]
    return feats


FEATURES = [
    "flag_density",
    "m1_density",
    "mean_n_rules",
    "mean_abs_sol_gap",
    "tst_break_rate",
    "sd_bed_hour",
]


def overdispersion(queue: pd.DataFrame, label_col: str = "y_broad",
                   n_perm: int = 2000, seed: int = SEED) -> dict:
    """Variance/mean of positives per participant, against a label-shuffle null.

    Poisson errors would give VMR ~ 1. VMR >> 1 means errors cluster inside
    participants, which is the precondition for any participant-level policy.
    """
    per_pid = queue.groupby("pid")[label_col].sum()
    observed = float(per_pid.var(ddof=1) / per_pid.mean()) if per_pid.mean() > 0 else float("nan")

    y = queue[label_col].to_numpy()
    rng = np.random.default_rng(seed)
    null = []
    for _ in range(n_perm):
        perm = rng.permutation(y)
        s = pd.Series(perm).groupby(queue["pid"].to_numpy()).sum()
        m = s.mean()
        if m > 0:
            null.append(float(s.var(ddof=1) / m))
    null = np.asarray(null)
    p = float((1 + (null >= observed).sum()) / (1 + len(null)))
    return {
        "participants_in_queue": int(per_pid.size),
        "participants_with_positive": int((per_pid > 0).sum()),
        "max_positives_one_participant": int(per_pid.max()),
        "observed_vmr": round(observed, 3),
        "null_vmr_mean": round(float(null.mean()), 3),
        "null_vmr_p95": round(float(np.percentile(null, 95)), 3),
        "p_value": round(p, 4),
    }


def participant_auc(queue: pd.DataFrame, feats: pd.DataFrame,
                    label_col: str = "y_broad") -> pd.DataFrame:
    """Does a feature rank participants who have >=1 error above those who do not?"""
    has = queue.groupby("pid")[label_col].max().rename("has_error")
    frame = feats.join(has, how="inner")
    y = frame["has_error"].to_numpy(int)
    out = []
    for name in FEATURES:
        x = frame[name].to_numpy(float)
        ok = np.isfinite(x)
        auc = _auc(y[ok], x[ok])
        out.append({"feature": name, "auc": round(auc, 3), "n": int(ok.sum())})
    return pd.DataFrame(out).sort_values("auc", ascending=False).reset_index(drop=True)


def _auc(y: np.ndarray, x: np.ndarray) -> float:
    """Rank AUC with ties averaged (no sklearn import needed)."""
    if len(np.unique(y)) < 2:
        return float("nan")
    ranks = pd.Series(x).rank(method="average").to_numpy()
    n1 = y.sum()
    n0 = len(y) - n1
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def scores_for(queue: pd.DataFrame, feats: pd.DataFrame, name: str) -> np.ndarray:
    """Row score: participant rank first, M1-bearing rows first inside the participant."""
    values = queue["pid"].map(feats[name]).astype(float)
    ranks = values.rank(pct=True).fillna(0.0)
    return ranks.to_numpy() * 2.0 + queue["m1"].astype(float).to_numpy() * 0.5
