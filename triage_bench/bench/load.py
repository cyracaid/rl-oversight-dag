"""Load the real review queue and join it to human labels.

Three tables, one key: (pid, day_num, row_id).

    candidates  audit_m1_m7_decision.csv      13,990 rows -> 1,048 FLAGs
    labels      manual_error_correction_updated.csv  75 rows (72 unique keys)
    rows        output/cleaned_data_final.csv 13,990 rows, features only

Label definitions (both are reported, never mixed):

    narrow  the 72 unique keys of the manual correction file (what README calls 75)
    broad   cleaned_data_final.human_review == "corrected" (85 rows)

Label-derived columns are dropped from every feature frame: they would leak.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .config import FILES, RULES

KEYS = ["pid", "day_num", "row_id"]

# Anything carrying the answer, or provenance of the answer.
LABEL_COLUMNS = [
    "has_correction",
    "is_error",
    "error_type",
    "is_unusual",
    "unusual_type",
    "record_status",
    "flag_severity",
    "human_review",
    "correction_type",
    "decision",
    "corrected",
    "manually_corrected",
    "review_resolution",
    "resolved_at",
    "resolved_by",
    "StartDate",
]


def _normalise_keys(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for key in KEYS:
        df[key] = pd.to_numeric(df[key], errors="coerce").fillna(-1).astype("int64")
    return df


def load_rows(data_dir: Path) -> pd.DataFrame:
    """All 13,990 rows, keys normalised, label-derived columns dropped."""
    rows = _normalise_keys(pd.read_csv(data_dir / FILES["rows"]))
    keep = [c for c in rows.columns if c not in LABEL_COLUMNS]
    return rows[list(dict.fromkeys(keep))].copy()


def load_queue(data_dir: Path, rows: pd.DataFrame | None = None) -> pd.DataFrame:
    """Return the review queue: one row per AI FLAG, with rule flags and labels."""
    audit = _normalise_keys(pd.read_csv(data_dir / FILES["candidates"]))
    labels = _normalise_keys(pd.read_csv(data_dir / FILES["labels"]))
    raw = _normalise_keys(pd.read_csv(data_dir / FILES["rows"]))

    label_keys = raw[KEYS + ["human_review"]].copy()

    for rule in RULES:
        audit[rule] = audit[rule].astype(str).str.upper().eq("TRUE")

    queue = audit.loc[audit["decision"].astype(str).str.upper() == "FLAG"].copy()
    queue["queue_pos"] = np.arange(len(queue))  # file order = pipeline default order

    narrow = set(map(tuple, labels[KEYS].drop_duplicates().itertuples(index=False, name=None)))
    broad = set(
        map(tuple, label_keys.loc[label_keys["human_review"] == "corrected", KEYS]
            .drop_duplicates().itertuples(index=False, name=None))
    )
    keys = list(queue[KEYS].itertuples(index=False, name=None))
    queue["y_narrow"] = np.array([k in narrow for k in keys], dtype=int)
    queue["y_broad"] = np.array([k in broad for k in keys], dtype=int)

    # Features: the cleaned row fields, minus every label-derived column.
    features = rows if rows is not None else load_rows(data_dir)
    merged = queue.merge(features, on=KEYS, how="left", validate="one_to_one")

    merged["n_rules"] = merged[RULES].sum(axis=1)
    merged["m1"] = merged["M1_order_violation"]
    merged["m4"] = merged["M4_window_illegal"]
    return merged


def describe(queue: pd.DataFrame) -> dict:
    """Aggregate counts only -- never row-level output."""
    y = queue["y_broad"]
    pos = queue.loc[y == 1, ["m1", "m4"]]
    return {
        "candidates": int(len(queue)),
        "positives_narrow": int(queue["y_narrow"].sum()),
        "positives_broad": int(y.sum()),
        "precision": float(y.mean()),
        "positives_m1_only": int((pos["m1"] & ~pos["m4"]).sum()),
        "positives_m4_only": int((~pos["m1"] & pos["m4"]).sum()),
        "positives_both": int((pos["m1"] & pos["m4"]).sum()),
    }
