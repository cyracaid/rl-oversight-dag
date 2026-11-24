"""Paired comparison of learned baselines against the marginal rule.

`run_benchmark.py` reports every policy against `confidence`. The benchmark spec
(`BENCHMARK_SPEC.md` §7) requires the learned policies to be compared against
`marginal`, with a paired interval and win/tie/loss counts. This script reads the
episode-level CSV and produces that table.

Usage (from `role3 improvement/`, after `run_learned_baselines.py`):

    python3 report_learned_baselines.py
    python3 report_learned_baselines.py --csv outputs/v3-baselines/benchmark_role3.csv
    python3 report_learned_baselines.py --csv outputs/v3/benchmark_role3.csv --out /tmp/old.md

Delta convention: `learned - marginal` in residual sink errors. Negative means the
learned policy is better. Intervals are paired graph-level bootstraps, so the graph
difficulty cancels.
"""
import argparse
import csv
import json
from pathlib import Path

import numpy as np

SEEDS = (1, 2, 3)
BOOTSTRAP = 10_000
BOOTSTRAP_SEED = 20261124


def load(path):
    rows = list(csv.DictReader(path.open(encoding="utf-8-sig")))
    scores = {}
    for row in rows:
        key = (row["family"], row["policy"])
        scores.setdefault(key, {})[int(row["graph_seed"])] = float(row["sink_errors"])
    return scores


def aligned(scores, family, policy):
    common = sorted(set(scores[(family, "marginal")]) & set(scores[(family, policy)]))
    return (np.array([scores[(family, "marginal")][g] for g in common]),
            np.array([scores[(family, policy)][g] for g in common]))


def paired(marginal, learned, rng):
    delta = learned - marginal
    draws = delta[rng.integers(len(delta), size=(BOOTSTRAP, len(delta)))].mean(axis=1)
    lo, hi = np.quantile(draws, [.025, .975])
    return (delta.mean(), lo, hi,
            int(np.sum(delta < 0)), int(np.sum(delta == 0)), int(np.sum(delta > 0)))


def seed_mean(scores, family, prefix):
    """Average the three training seeds per graph, as in the role 2 tables."""
    usable = [f"{prefix}_s{seed}" for seed in SEEDS if (family, f"{prefix}_s{seed}") in scores]
    if not usable:
        return None
    graphs = sorted(set.intersection(*(set(scores[(family, name)]) for name in usable)))
    stacked = np.array([[scores[(family, name)][g] for name in usable] for g in graphs])
    return graphs, stacked.mean(axis=1), usable


def report(csv_path, out_path):
    scores = load(csv_path)
    families = sorted({family for family, _ in scores})
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    lines = [
        "# Learned baselines vs the marginal rule",
        "",
        f"Source: `{csv_path}`. Delta = learned − marginal in residual sink errors; negative is better.",
        f"Intervals: paired graph bootstrap, {BOOTSTRAP:,} draws, seed {BOOTSTRAP_SEED}.",
        "",
        "| family | marginal | GNN (3-seed mean) | Δ vs marginal [95% CI] | W/T/L | DQN (3-seed mean) | Δ vs marginal [95% CI] | W/T/L |",
        "|---|---:|---:|---|---|---:|---|---|",
    ]
    detail = ["", "## Per training seed", "",
              "| family | policy | mean | Δ vs marginal | 95% CI | W/T/L |", "|---|---|---:|---:|---|---|"]
    records = []
    for family in families:
        if (family, "marginal") not in scores:
            continue
        marginal_all = list(scores[(family, "marginal")].values())
        cells = ["—", "—", "—", "—", "—", "—"]
        offset = 0
        for prefix in ("gnn", "dqn"):
            block = seed_mean(scores, family, prefix)
            if block is None:
                offset += 3
                continue
            graphs, mean_learned, names = block
            marginal = np.array([scores[(family, "marginal")][g] for g in graphs])
            d, lo, hi, w, t, l = paired(marginal, mean_learned, rng)
            cells[offset:offset + 3] = [f"{mean_learned.mean():.3f}",
                                        f"{d:+.3f} [{lo:+.3f}, {hi:+.3f}]",
                                        f"{w}/{t}/{l}"]
            records.append(dict(family=family, learner=prefix, delta=float(d), lo=float(lo),
                                hi=float(hi), wins=w, ties=t, losses=l, seeds=names))
            offset += 3
        lines.append("| " + " | ".join([family, f"{np.mean(marginal_all):.3f}", *cells]) + " |")
        for prefix in ("gnn", "dqn"):
            for seed in SEEDS:
                name = f"{prefix}_s{seed}"
                if (family, name) not in scores:
                    continue
                marginal, learned = aligned(scores, family, name)
                d, lo, hi, w, t, l = paired(marginal, learned, rng)
                detail.append(f"| {family} | `{name}` | {learned.mean():.3f} | {d:+.3f} | "
                              f"[{lo:+.3f}, {hi:+.3f}] | {w}/{t}/{l} |")
                records.append(dict(family=family, learner=name, delta=float(d), lo=float(lo),
                                    hi=float(hi), wins=w, ties=t, losses=l))
    lines += detail
    lines += ["",
              "Negative Δ means the learned policy leaves fewer conclusion errors than the rule.",
              "An interval that spans zero is not a win, even when the mean is negative.",
              "Raw means are not comparable across families (different n, budgets and sink sets)."]
    out_path.write_text("\n".join(lines) + "\n")
    json_path = out_path.with_suffix(".json")
    json_path.write_text(json.dumps(records, indent=2) + "\n")
    print("\n".join(lines[:9]))
    print(f"\nwrote {out_path} and {json_path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", type=Path, default=Path("outputs/v3-learned/benchmark_role3.csv"))
    ap.add_argument("--out", type=Path, default=Path("outputs/v3-learned/learned_vs_marginal.md"))
    args = ap.parse_args()
    if not args.csv.exists():
        log = Path("outputs/learned/run.log")
        hint = (f"training still running — watch `tail -f {log}`" if log.exists()
                else "run run_learned_baselines.py first")
        raise SystemExit(f"missing {args.csv}\n{hint}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    report(args.csv, args.out)


if __name__ == "__main__":
    main()
