"""Gap D — fit the error model on *measured* confidence instead of inventing it.

Every result in this repo assumes the confidence score has a known error model:
`dag_role3.environment.initial_belief` hard-codes a symmetric Gaussian likelihood
(`mu_err=-1.5`, `mu_good=+1.5`, `sigma=1.2`) and a type-prior bias. That assumption is
Gap D in `CROSS_IMPLEMENTATION_VALIDATION.md` §7. This script replaces it with numbers
fitted on human-audited labels.

It cannot run on synthetic data. `dag_role3` emits confidence from the *same* Gaussian
the simulator assumes, so fitting on it would only return the constants it was generated
with — a tautology, not a calibration. The script therefore requires an explicit
`--human-audited` flag and refuses rows whose provenance column says otherwise.

Input CSV (one row per audited node in one record):

    record_id,node,node_type,confidence,is_error,audited_by

`confidence` is the observable score the pipeline emits (in the real sleep replay this
is `suspicion()` normalised to (0,1)); `is_error` is the human verdict, 1 = wrong value.
At least 200 audited rows are needed for a usable fit — the 75 corrections currently
available are enough to *report*, not to *deploy*.

Usage:

    python3 signal_calibration_real.py --csv audit_nodes.csv --human-audited \\
        --out results/calibration-v1

Outputs `calibration.json` (the fitted model in the form `initial_belief` consumes),
`calibration.md` (reliability table + metrics) and `manifest.json` (sha256, counts).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from pathlib import Path

SIGMA = 1.2  # kept fixed so the fit maps onto the environment's parametrisation
MIN_ROWS = 30
REQUIRED = ("record_id", "node", "node_type", "confidence", "is_error", "audited_by")
SYNTHETIC_NAMES = {"synthetic", "simulated", "dag_role3", "spike", "ticket"}


def logit(p: float) -> float:
    p = min(max(float(p), 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, x))))


def load(csv_path: Path, allow_synthetic: bool) -> list[dict]:
    with csv_path.open(newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(f"missing columns: {missing}")
        rows = []
        for r in reader:
            provenance = r["audited_by"].strip().lower()
            if not allow_synthetic and provenance in SYNTHETIC_NAMES:
                raise SystemExit(
                    f"row for {r['record_id']}/{r['node']} is audited by {provenance!r}; "
                    "Gap D needs human labels (pass --allow-synthetic only for a plumbing test)")
            rows.append({
                "record_id": r["record_id"], "node": r["node"], "type": r["node_type"],
                "confidence": float(r["confidence"]), "is_error": int(r["is_error"]),
            })
    if len(rows) < MIN_ROWS:
        raise SystemExit(f"{len(rows)} rows; a fit below {MIN_ROWS} is not reportable")
    return rows


def fit_logistic(xs: list[float], ys: list[int], l2: float = 1.0, iters: int = 40):
    """IRLS on logit(p) = a + b*z with a mild ridge. Two parameters, no sklearn."""
    a = b = 0.0
    for _ in range(iters):
        g_a = g_b = h_aa = h_ab = h_bb = 0.0
        for z, y in zip(xs, ys):
            p = sigmoid(a + b * z)
            w = max(1e-6, p * (1 - p))
            r = y - p
            g_a += r - l2 * a / max(1, len(xs))
            g_b += r * z - l2 * b / max(1, len(xs))
            h_aa += w
            h_ab += w * z
            h_bb += w * z * z
        det = h_aa * h_bb - h_ab * h_ab
        if abs(det) < 1e-12:
            break
        da = (h_bb * g_a - h_ab * g_b) / det
        db = (-h_ab * g_a + h_aa * g_b) / det
        a += da
        b += db
        if abs(da) + abs(db) < 1e-9:
            break
    return a, b


def metrics(xs, ys, a, b) -> dict:
    preds = [sigmoid(a + b * z) for z in xs]
    brier = sum((p - y) ** 2 for p, y in zip(preds, ys)) / len(ys)
    pos = [p for p, y in zip(preds, ys) if y == 1]
    neg = [p for p, y in zip(preds, ys) if y == 0]
    auc = None
    if pos and neg:
        wins = sum((p > q) + 0.5 * (p == q) for p in pos for q in neg)
        auc = wins / (len(pos) * len(neg))
    bins = [[] for _ in range(10)]
    for p, y in zip(preds, ys):
        bins[min(9, int(p * 10))].append((p, y))
    ece, table = 0.0, []
    for i, cell in enumerate(bins):
        if not cell:
            continue
        conf = sum(p for p, _ in cell) / len(cell)
        emp = sum(y for _, y in cell) / len(cell)
        ece += len(cell) / len(ys) * abs(conf - emp)
        table.append({"bin": f"{i/10:.1f}-{(i+1)/10:.1f}", "n": len(cell),
                      "mean_confidence": conf, "empirical_error_rate": emp})
    return {"n": len(ys), "positives": sum(ys), "brier": brier, "auc": auc,
            "ece": ece, "reliability": table, "predictions": preds}


def bootstrap(xs, ys, a, b, draws=2000, seed=0) -> dict:
    rng = random.Random(seed)
    n = len(ys)
    aucs, briers = [], []
    for _ in range(draws):
        idx = [rng.randrange(n) for _ in range(n)]
        sx = [xs[i] for i in idx]
        sy = [ys[i] for i in idx]
        if len(set(sy)) < 2:
            continue
        fa, fb = fit_logistic(sx, sy)
        m = metrics(sx, sy, fa, fb)
        briers.append(m["brier"])
        if m["auc"] is not None:
            aucs.append(m["auc"])
    def ci(v):
        if not v:
            return None
        v = sorted(v)
        return [v[int(0.025 * (len(v) - 1))], v[int(0.975 * (len(v) - 1))]]
    return {"brier": ci(briers), "auc": ci(aucs), "draws": len(briers)}


def fit(rows: list[dict]) -> dict:
    by_type: dict[str, list[dict]] = {}
    for r in rows:
        by_type.setdefault(r["type"], []).append(r)

    pooled_x = [logit(r["confidence"]) for r in rows]
    pooled_y = [r["is_error"] for r in rows]
    a, b = fit_logistic(pooled_x, pooled_y)
    out = {
        "sigma": SIGMA,
        "pooled": {"a": a, "b": b, "metrics": {k: v for k, v in metrics(pooled_x, pooled_y, a, b).items()
                                               if k != "predictions"},
                   "bootstrap": bootstrap(pooled_x, pooled_y, a, b)},
        "per_type": {},
    }
    for t, group in sorted(by_type.items()):
        xs = [logit(r["confidence"]) for r in group]
        ys = [r["is_error"] for r in group]
        ta, tb = fit_logistic(xs, ys) if len(set(ys)) > 1 else (a, b)
        out["per_type"][t] = {
            "n": len(group), "positives": sum(ys), "a": ta, "b": tb,
            "metrics": {k: v for k, v in metrics(xs, ys, ta, tb).items() if k != "predictions"},
            "note": "fell back to pooled fit" if len(set(ys)) <= 1 else "",
        }
    # Map the fitted slope onto the environment's symmetric-Gaussian parametrisation.
    # In the simulator confidence is P(correct), so logit P(error | z) has slope
    # b = -(mu_good - mu_err)/sigma^2; the separation therefore carries a minus sign.
    separation = -b * SIGMA ** 2
    out["environment_model"] = {
        "mu_err": -separation / 2, "mu_good": separation / 2, "sigma": SIGMA,
        "intercept": a, "fitted_slope_on_logit_confidence": b,
        "direction_ok": b < 0,
        "bias_coefficient": -0.4,
        "bias_note": "kept at the simulator's -0.4; the type-prior bias is not fitted here",
        "how_to_apply": "pass mu_err/mu_good/sigma into initial_belief instead of the "
                        "-1.5/+1.5/1.2 constants; keep the type-prior bias as fitted or 0",
    }
    if b >= 0:
        out["environment_model"]["warning"] = (
            "fitted slope is non-negative: the score rises with the error rate, so it is an "
            "error score, not a correctness score. Flip it before feeding the simulator.")
    return out


def report(result: dict, rows: list[dict], out: Path) -> None:
    lines = ["# Gap D — calibration fitted on human-audited confidence", ""]
    p = result["pooled"]
    lines += [
        f"Rows: **{p['metrics']['n']}** audited node reviews, "
        f"positives (wrong values): **{p['metrics']['positives']}**.",
        f"Records: {len({r['record_id'] for r in rows})}, node types: {len(result['per_type'])}.",
        "",
        "| metric | value | 95 % bootstrap |",
        "|---|---|---|",
        f"| Brier | {p['metrics']['brier']:.4f} | {p['bootstrap']['brier']} |",
        f"| AUC | {p['metrics']['auc'] if p['metrics']['auc'] is None else round(p['metrics']['auc'], 4)} "
        f"| {p['bootstrap']['auc']} |",
        f"| ECE (10 bins) | {p['metrics']['ece']:.4f} | — |",
        "",
        "## Reliability",
        "",
        "| bin | n | mean confidence | empirical error rate |",
        "|---|---:|---:|---:|",
    ]
    for row in p["metrics"]["reliability"]:
        lines.append(f"| {row['bin']} | {row['n']} | {row['mean_confidence']:.3f} "
                     f"| {row['empirical_error_rate']:.3f} |")
    lines += ["", "## What this replaces in the simulator", "",
              "```json", json.dumps(result["environment_model"], indent=2), "```", "",
              "The simulator's `initial_belief` uses `mu_err=-1.5`, `mu_good=+1.5`, "
              "`sigma=1.2`. Those three constants were chosen, not measured. The block "
              "above is the same three numbers fitted on real labels.", ""]
    if p["metrics"]["n"] < 200:
        lines += [f"**Caveat.** {p['metrics']['n']} rows is below the 200 needed for a "
                  "deployable calibration; treat this as a first measurement, not the "
                  "final error model.", ""]
    (out / "calibration.md").write_text("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", default="results/calibration-v1")
    ap.add_argument("--human-audited", action="store_true",
                    help="required: asserts the labels came from a person, not the simulator")
    ap.add_argument("--allow-synthetic", action="store_true",
                    help="plumbing test only; the fit is a tautology on simulated scores")
    args = ap.parse_args()
    if not args.human_audited and not args.allow_synthetic:
        raise SystemExit("pass --human-audited to confirm the labels are human verdicts")

    csv_path, out = Path(args.csv), Path(args.out)
    rows = load(csv_path, args.allow_synthetic)
    result = fit(rows)
    out.mkdir(parents=True, exist_ok=True)
    (out / "calibration.json").write_text(json.dumps(result, indent=2))
    report(result, rows, out)
    (out / "manifest.json").write_text(json.dumps({
        "csv": str(csv_path),
        "csv_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "rows": len(rows), "records": len({r["record_id"] for r in rows}),
        "allow_synthetic": args.allow_synthetic,
        "sigma_fixed": SIGMA,
    }, indent=2))
    print(f"{len(rows)} rows → {out}/calibration.md")


if __name__ == "__main__":
    main()
