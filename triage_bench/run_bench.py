#!/usr/bin/env python3
"""Table 1: recall@k on the real review queue (1,048 candidates, 75/85 labels).

Usage:
    python3 triage_bench/run_bench.py [--data-dir ~/Documents/splsleep]

Writes only aggregate numbers to triage_bench/outputs/ and a figure to
triage_bench/figures/. The sleep data is read in place and never copied.
"""

from __future__ import annotations

import argparse
import json

import numpy as np

from bench import config
from bench.load import describe, load_queue, load_rows
from bench.participant import (FEATURES, build_features, overdispersion,
                               participant_auc, scores_for)
from bench.metrics import bootstrap_paired_diff, bootstrap_recall_ci, precision_at_k
from bench.policies import score_all, type_partition_scores


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default=None, help=f"default: ${config.DATA_DIR_ENV} or {config.DEFAULT_DATA_DIR}")
    parser.add_argument("--boot", type=int, default=1000)
    args = parser.parse_args()

    if args.data_dir:
        import os
        os.environ[config.DATA_DIR_ENV] = args.data_dir

    data = config.require_data()
    rows = load_rows(data)
    queue = load_queue(data, rows=rows)
    info = describe(queue)
    print("queue:", info)

    ks = [10, 25, 50, 100, 200, 400, 800]
    scores = score_all(queue)
    scores["type_partition"] = type_partition_scores(queue)
    pf = build_features(queue, rows)
    for name in FEATURES:
        scores[f"pid:{name}"] = scores_for(queue, pf, name)
    y = queue["y_broad"].to_numpy()

    curves = {}
    table = {}
    for name, s in scores.items():
        curve = {k: round(bootstrap_recall_ci(queue, s, k, n_boot=args.boot)[0], 4) for k in ks}
        curves[name] = curve
        point, lo, hi = bootstrap_recall_ci(queue, s, 100, n_boot=args.boot)
        table[name] = {
            "recall@100": round(point, 4), "lo95": round(lo, 4), "hi95": round(hi, 4),
            "precision@100": round(precision_at_k(s, y, 100), 4),
        }
        print(f"{name:18s} " + "  ".join(f"R@{k}={curve[k]:.3f}" for k in (50, 100, 200, 400)))

    delta = {}
    for k in (200, 400):
        d, lo, hi = bootstrap_paired_diff(queue, scores["pid:m1_density"], scores["m1_first"], k,
                                          n_boot=args.boot)
        delta[f"k{k}"] = {"diff": round(d, 4), "lo95": round(lo, 4), "hi95": round(hi, 4)}
    print("paired pid:m1_density - m1_first:", delta)

    disp = overdispersion(queue)
    pid_auc = participant_auc(queue, pf)
    print("participant clustering:", disp)
    print(pid_auc.to_string(index=False))

    config.OUT_DIR.mkdir(parents=True, exist_ok=True)
    (config.OUT_DIR / "participant.json").write_text(
        json.dumps({"overdispersion": disp,
                    "pid_auc": pid_auc.to_dict("records"),
                    "paired_vs_m1_first": delta}, indent=2) + "\n"
    )
    (config.OUT_DIR / "queue_summary.json").write_text(json.dumps(info, indent=2) + "\n")
    (config.OUT_DIR / "recall_at_k.json").write_text(
        json.dumps({"k": ks, "curves": curves, "at_100": table}, indent=2) + "\n"
    )

    lines = [
        "# Table 1 - recall@k on the real review queue",
        "",
        f"Candidates (AI FLAGs): **{info['candidates']}**",
        f"Human-confirmed errors in the queue: **{info['positives_broad']}** (broad), "
        f"{info['positives_narrow']} (narrow)",
        f"Queue precision: **{info['precision']:.1%}**",
        "",
        "| policy | R@50 | R@100 | R@200 | R@400 | P@100 | 95% CI R@100 |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    order = ["queue_order", "random", "rule_count", "m1_first", "type_partition",
             "m1_then_sol_gap", "oracle"]
    for name in order:
        if name not in curves:
            continue
        c = curves[name]
        t = table[name]
        lines.append(
            f"| {name} | {c[50]:.1%} | {c[100]:.1%} | {c[200]:.1%} | {c[400]:.1%} "
            f"| {t['precision@100']:.1%} | [{t['lo95']:.1%}, {t['hi95']:.1%}] |"
        )
    lines += [
        "",
        "## Participant-level policies",
        "",
        "Do errors cluster inside participants, and can a label-free feature rank them?",
        "",
        f"- participants in queue: **{disp['participants_in_queue']}** "
        f"({disp['participants_with_positive']} with at least one error)",
        f"- max errors carried by one participant: **{disp['max_positives_one_participant']}**",
        f"- variance/mean of errors per participant: **{disp['observed_vmr']}** "
        f"(label-shuffle null {disp['null_vmr_mean']}, p95 {disp['null_vmr_p95']}, "
        f"p = {disp['p_value']})",
        "",
        "| policy | R@50 | R@100 | R@200 | R@400 |",
        "|---|---:|---:|---:|---:|",
    ]
    for name in [f"pid:{f}" for f in FEATURES]:
        c = curves[name]
        lines.append(f"| {name} | {c[50]:.1%} | {c[100]:.1%} | {c[200]:.1%} | {c[400]:.1%} |")
    lines += [
        "",
        "Paired difference, `pid:m1_density` − `m1_first` (same participants, cluster bootstrap): "
        f"@200 {delta['k200']['diff']:+.1%} [{delta['k200']['lo95']:+.1%}, {delta['k200']['hi95']:+.1%}], "
        f"@400 {delta['k400']['diff']:+.1%} [{delta['k400']['lo95']:+.1%}, {delta['k400']['hi95']:+.1%}].",
        "",
        "| participant feature | AUC (has >=1 error) |",
        "|---|---:|",
    ]
    for _, row in pid_auc.iterrows():
        lines.append(f"| `{row['feature']}` | {row['auc']:.3f} |")
    lines += [
        "",
        "`pid:<feature>` = rank participants by that feature, then M1-bearing rows first inside.",
        f"{len(FEATURES)} features were tried; treat the best AUC as multiple-comparison weak.",
        "",
        "`queue_order` = the pipeline's own file order (no prioritisation).",
        "`oracle` needs the labels and is a ceiling, not a policy.",
        "CI = participant-clustered bootstrap, 1,000 resamples, k fixed at 100.",
        "",
        "Numbers are generated by `triage_bench/run_bench.py`; do not hand-edit.",
    ]
    (config.OUT_DIR / "table1.md").write_text("\n".join(lines) + "\n")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(6, 4))
        for name in ["queue_order", "random", "rule_count", "m1_first",
                     "type_partition", "pid:m1_density", "oracle"]:
            ax.plot(ks, [curves[name][k] for k in ks], marker="o", label=name)
        ax.set_xlabel("review budget k (items)")
        ax.set_ylabel("recall of human-confirmed errors")
        ax.set_title("Real review queue: recall@k")
        ax.grid(alpha=0.3)
        ax.legend()
        fig.tight_layout()
        config.FIG_DIR.mkdir(parents=True, exist_ok=True)
        fig.savefig(config.FIG_DIR / "recall_at_k.png", dpi=160)
    except Exception as exc:  # figure is optional
        print("figure skipped:", exc)


if __name__ == "__main__":
    main()
