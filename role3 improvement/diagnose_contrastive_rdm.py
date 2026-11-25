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

    # The estimator above uses rates estimated from the same 40 episodes, which is
    # biased upward. The honest baseline is the family's own generating model: the
    # simulator draws each source error independently from the node's type rate, so an
    # independent sample from those exact rates is the null this statistic lives under.
    true_rates = np.array([ds.graph.rates[t] for t in ds.graph.types])
    gap_true = np.abs(true_rates[:, None] - true_rates[None, :])
    obs_rho = float(spearmanr(gap_true[iu], hamming[iu]).statistic)
    rng = np.random.default_rng(1)
    draws = []
    for _ in range(200):
        sample = (rng.random(labels.shape) < true_rates).astype(float)
        sim_ham = np.abs(sample.T[:, None, :] - sample.T[None, :, :]).mean(-1)
        draws.append(spearmanr(gap_true[iu], sim_ham[iu]).statistic)
    draws = np.asarray(draws)
    null = {
        "observed_rho_against_true_rates": obs_rho,
        "independence_mean": float(draws.mean()),
        "independence_ci": [float(np.percentile(draws, 2.5)),
                            float(np.percentile(draws, 97.5))],
        "draws": 200,
        "distinct_true_rates": int(len(np.unique(true_rates))),
    }
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
        "independence_null": null,
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
        null = row["independence_null"]
        print(f"{row['family']:>7}: rho vs true rates {null['observed_rho_against_true_rates']:+.3f}, "
              f"independence null {null['independence_mean']:+.3f} "
              f"[{null['independence_ci'][0]:+.3f}, {null['independence_ci'][1]:+.3f}], "
              f"{null['distinct_true_rates']} distinct rates")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
