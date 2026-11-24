"""Post-hoc diagnostic for the contrastive pilot: does a node's own error rate explain
the latent error RDM?

Not part of the pre-registered analysis in ``PREREGISTER_CONTRASTIVE.md`` and it carries
no verdict. It exists to answer one question the pilot's tables cannot: on ``real`` the
supervised encoder reached a Spearman of only 0.046 while on ``ticket`` it reached 0.554.
If a one-dimensional "this node's error rate" representation reproduces most of the truth
RDM on ``ticket`` but not on ``real``, then ``real``'s error structure is not a function
of node marginals — i.e. it is relational, which is the pilot's working interpretation.

    python3 diagnose_contrastive_rdm.py --out outputs/contrastive-v1/diagnostic.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

from dag_role3 import contrastive as C

EVAL_START, EVAL_COUNT = 5120, 40
FAMILIES = ("real", "ticket", "spike")


def diagnose(family: str) -> dict:
    ds = C.build_dataset(family, tuple(range(EVAL_START, EVAL_START + EVAL_COUNT)))
    labels = ds.labels.numpy()
    rates = labels.mean(0)
    truth = labels.T
    hamming = np.abs(truth[:, None, :] - truth[None, :, :]).mean(-1)
    iu = np.triu_indices(len(rates), k=1)
    rate_gap = np.abs(rates[:, None] - rates[None, :])
    rho = float(spearmanr(rate_gap[iu], hamming[iu]).statistic)
    with np.errstate(invalid="ignore", divide="ignore"):
        corr = np.corrcoef(truth)
    np.fill_diagonal(corr, 0.0)
    pairs = np.abs(corr[iu])
    return {
        "family": family,
        "n_nodes": int(ds.graph.n),
        "episodes": EVAL_COUNT,
        "mean_errors_per_episode": float(labels.sum(1).mean()),
        "error_rate_min": float(rates.min()),
        "error_rate_max": float(rates.max()),
        "distinct_rates": int(len(np.unique(np.round(rates, 3)))),
        "rates_only_rdm_spearman": rho,
        "max_abs_error_cooccurrence_corr": float(np.nanmax(pairs)),
        "mean_abs_error_cooccurrence_corr": float(np.nanmean(pairs)),
        "truth_rdm_sd": float(hamming[iu].std()),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="outputs/contrastive-v1/diagnostic.json")
    args = parser.parse_args(argv)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = [diagnose(f) for f in FAMILIES]
    payload = {
        "purpose": "post-hoc diagnostic, no verdict; see PREREGISTER_CONTRASTIVE.md C1",
        "eval_seeds": [EVAL_START, EVAL_COUNT],
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "families": rows,
    }
    out.write_text(json.dumps(payload, indent=2) + "\n")
    for row in rows:
        print(f"{row['family']:>7}: rates-only RDM rho {row['rates_only_rdm_spearman']:+.3f}, "
              f"mean errors/episode {row['mean_errors_per_episode']:.2f}, "
              f"truth RDM sd {row['truth_rdm_sd']:.3f}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
