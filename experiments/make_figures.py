#!/usr/bin/env python3
"""Draw the three figures the paper argues with, from the committed artifacts.

Every plotted value is read from a committed JSON/CSV/MD, never typed here, and the
exact arrays are written to `figures/figure_data.json` so `experiments/test_figures.py`
can check the figures against the artifacts they claim to show.

Run: python3 experiments/make_figures.py
"""

import csv
import json
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "figures")

SPEC = os.path.join(ROOT, "BENCHMARK_SPEC.md")
BASELINE_CSV = os.path.join(ROOT, "role3 improvement", "outputs", "v3-baselines", "benchmark_summary.csv")
LEARNED = os.path.join(ROOT, "role3 improvement", "outputs", "v3-learned", "learned_vs_marginal.json")
CEILING = os.path.join(ROOT, "triage_bench", "outputs", "ceiling.json")
RANKING = os.path.join(ROOT, "runs", "real-confidence-ranking", "results.json")

INK, MUTED = "#1c2530", "#6a7683"
BLUE, ORANGE, TEAL = "#3b6ea5", "#c26f3a", "#4b8b7a"


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def family_sizes():
    """n per family, parsed from the frozen suite table in BENCHMARK_SPEC.md."""
    body = read(SPEC).split("| family | n | budget", 1)[1]
    sizes = {}
    for line in body.splitlines():
        if not line.startswith("|"):
            if sizes:
                break
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2 or not cells[1].isdigit():
            continue
        name = cells[0].strip("`")
        sizes[name] = int(cells[1])
    if len(sizes) < 6:
        raise SystemExit(f"parsed only {len(sizes)} families from BENCHMARK_SPEC.md §3.1")
    return sizes


def marginal_levels():
    levels = {}
    with open(BASELINE_CSV, encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["policy"] == "marginal":
                levels[row["family"]] = float(row["mean_sink_errors"])
    return levels


def styled():
    plt.rcParams.update({
        "font.size": 9,
        "font.family": "DejaVu Sans",
        "axes.edgecolor": MUTED,
        "axes.labelcolor": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": 200,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
        "savefig.facecolor": "white",
        "svg.fonttype": "none",
    })


def save(fig, name):
    path = os.path.join(OUT, name)
    fig.savefig(path, metadata={"Software": None})
    plt.close(fig)
    return os.path.basename(path)


# --------------------------------------------------------------------------- #
# Figure 1 — the gap grows with graph size
# --------------------------------------------------------------------------- #

LEARNER_STYLE = {"gnn": (BLUE, "GNN+REINFORCE"), "dqn": (ORANGE, "DQN")}
FAMILY_MARK = {"spike": "^", "modular": "o", "ba": "s", "er": "D", "real": "v", "ticket": "P"}


def figure_gap():
    sizes, levels = family_sizes(), marginal_levels()
    rows = [r for r in json.loads(read(LEARNED)) if r["learner"] in LEARNER_STYLE]
    groups = sorted({sizes[r["family"]] for r in rows})

    fig, axes = plt.subplots(1, 2, figsize=(9.8, 3.9))
    for ax, mode in zip(axes, ("absolute", "relative")):
        for n in groups:
            names = sorted({r["family"] for r in rows if sizes[r["family"]] == n})
            for i, name in enumerate(names):
                x = groups.index(n) + 0.20 * (i - (len(names) - 1) / 2)
                for r in (r for r in rows if r["family"] == name):
                    colour, _ = LEARNER_STYLE[r["learner"]]
                    base = levels[name]
                    delta = r["delta"] if mode == "absolute" else 100.0 * r["delta"] / base
                    lo, hi = r["lo"], r["hi"]
                    if mode == "relative":
                        lo, hi = 100.0 * lo / base, 100.0 * hi / base
                    ax.errorbar(x, delta, yerr=[[delta - lo], [hi - delta]],
                                fmt=FAMILY_MARK[name], color=colour, ecolor=colour,
                                elinewidth=0.9, capsize=2.2, markersize=5.5,
                                alpha=0.95 if r["learner"] == "gnn" else 0.55, zorder=3)
        ax.set_xticks(range(len(groups)))
        ax.set_xticklabels([f"N={g}" for g in groups])
        ax.set_xlim(-0.55, len(groups) - 0.45)
        ax.axhline(0, color=MUTED, linewidth=0.8, zorder=1)
        ax.grid(axis="y", color="#e6eaee", linewidth=0.8, zorder=0)
        ax.set_axisbelow(True)

    rel = [100.0 * r["delta"] / levels[r["family"]] for r in rows]
    by_n = {n: [100.0 * r["delta"] / levels[r["family"]] for r in rows
                if sizes[r["family"]] == n] for n in groups}
    axes[0].set_ylabel("extra sink errors per graph\n(learner − marginal)")
    axes[1].set_ylabel("% of the rule's own error level")
    axes[0].set_title("absolute gap grows with graph size", loc="left", fontsize=9, color=INK)
    axes[1].set_title("relative gap: larger at scale, but the ranges overlap", loc="left",
                      fontsize=9, color=INK)

    learners = [plt.Line2D([], [], color=c, linestyle="", marker="o", markersize=6, label=l)
                for c, l in LEARNER_STYLE.values()]
    families = [plt.Line2D([], [], color=MUTED, linestyle="", marker=FAMILY_MARK[f],
                           markersize=5, label=f) for f in sorted(FAMILY_MARK)]
    first = fig.legend(handles=learners, loc="lower center", ncol=2, frameon=False,
                       fontsize=8, bbox_to_anchor=(0.42, -0.02))
    fig.add_artist(first)
    fig.legend(handles=families, loc="lower center", ncol=6, frameon=False,
               fontsize=7.5, bbox_to_anchor=(0.42, -0.10))
    fig.subplots_adjust(bottom=0.26, wspace=0.30)

    data = {"groups": groups,
            "points": [{"family": r["family"], "learner": r["learner"],
                        "n": sizes[r["family"]], "delta": r["delta"],
                        "lo": r["lo"], "hi": r["hi"],
                        "marginal": levels[r["family"]],
                        "relative_pct": 100.0 * r["delta"] / levels[r["family"]]}
                       for r in rows],
            "relative_range_by_n": {str(n): [min(v), max(v)] for n, v in by_n.items()}}
    return save(fig, "fig1_gap_vs_graph_size.png"), data


# --------------------------------------------------------------------------- #
# Figure 2 — the queue has a ceiling, and most of it is the detector
# --------------------------------------------------------------------------- #


def figure_ceiling():
    d = json.loads(read(CEILING))
    ks = sorted(int(k) for k in d["ceiling_recall"])
    recall = [d["ceiling_recall"][str(k)] for k in ks]
    coverage = d["coverage"]["narrow_ceiling"]
    saturation = max(recall)
    plateaus_at = ks[recall.index(saturation)]
    leftover = 1.0 - saturation
    tail = next(g for g in d["type_table"] if g["g"] == "M4")

    fig, ax = plt.subplots(figsize=(6.8, 3.9))
    ax.step(ks, recall, where="post", color=BLUE, linewidth=1.8, zorder=3)
    ax.scatter(ks, recall, color=BLUE, s=22, zorder=4)
    ax.axhline(coverage, color=TEAL, linestyle=(0, (4, 2)), linewidth=1.1, zorder=2)
    ax.axvline(plateaus_at, color=MUTED, linestyle=(0, (1, 2)), linewidth=0.9, zorder=1)
    ax.annotate(f"detector coverage {coverage * 100:.1f} %: a row with no flag\n"
                "cannot be ranked at any budget",
                (8, coverage), textcoords="offset points", xytext=(0, 5),
                fontsize=7.5, color=TEAL, va="bottom", ha="left")
    ax.annotate(f"type-partition ceiling {saturation * 100:.1f} %",
                (plateaus_at, saturation), textcoords="offset points",
                xytext=(8, 4), fontsize=7.5, color=BLUE, va="bottom")
    ax.annotate(f"{leftover * 100:.1f} % of the corrections are left in\n"
                f"{tail['size']} rows at {tail['mean'] * 100:.1f} % base rate",
                (ks[-1], saturation), xytext=(ks[-1] - 30, saturation - 0.30),
                fontsize=7.5, color=MUTED, ha="right", va="top",
                arrowprops={"arrowstyle": "-", "color": MUTED, "linewidth": 0.8,
                            "shrinkA": 2, "shrinkB": 3})
    ax.set_xlabel("k — rows reviewed")
    ax.set_ylabel("recall bound given the flag types")
    ax.set_xlim(0, ks[-1] + 30)
    ax.set_ylim(0, 1.05)
    ax.set_xticks([50, 100, plateaus_at, 200, 400])
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0", "25 %", "50 %", "75 %", "100 %"])
    ax.grid(axis="y", color="#e6eaee", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.set_title("Where the review queue runs out of room", loc="left", fontsize=9)

    data = {"k": ks, "recall": recall, "coverage_ceiling": coverage,
            "saturation": saturation, "plateau_k": plateaus_at,
            "uncovered": leftover, "tail_group": tail["g"],
            "tail_size": tail["size"], "tail_base_rate": tail["mean"],
            "narrow_total": d["coverage"]["narrow_total"],
            "narrow_in_queue": d["coverage"]["narrow_in_queue"]}
    return save(fig, "fig2_queue_ceiling.png"), data


# --------------------------------------------------------------------------- #
# Figure 3 — the confidence signal scores consequences, not causes
# --------------------------------------------------------------------------- #


def figure_localisation():
    d = json.loads(read(RANKING))
    agg = d["observables"]["suspicion_binary"]
    groups = agg["by_node_group"]
    a = agg["aggregate"]
    chance = 0.5
    bars = [("all 14 nodes", a["auc_mean"], a["auc_ci95"], INK),
            ("4 validity sinks", groups["validity_sink"]["auc_pooled"], None, TEAL),
            ("6 derived nodes", groups["derived"]["auc_pooled"], None, BLUE),
            ("4 raw timestamps", groups["raw_leaf"]["auc_pooled"], None, ORANGE)]

    fig, ax = plt.subplots(figsize=(6.8, 3.2))
    ys = range(len(bars))[::-1]
    for y, (label, value, ci, colour) in zip(ys, bars):
        ax.barh(y, value - chance, left=chance, height=0.55, color=colour,
                alpha=0.85, zorder=3)
        right = value
        if ci:
            ax.errorbar(value, y, xerr=[[value - ci[0]], [ci[1] - value]],
                        color=colour, capsize=3, linewidth=1.0, zorder=4)
            right = ci[1]
        ax.text(right + 0.015, y, f"{value:.3f}", va="center", fontsize=8.5,
                color=INK if colour != ORANGE else ORANGE,
                fontweight="bold" if colour == ORANGE else "normal")
    ax.axvline(chance, color=MUTED, linewidth=0.9, zorder=2)
    ax.annotate("chance 0.50", (chance + 0.006, -0.88), ha="left", va="bottom",
                fontsize=7, color=MUTED)
    ax.set_yticks(list(ys))
    ax.set_yticklabels([b[0] for b in bars])
    ax.set_ylim(-0.95, len(bars) - 0.4)
    ax.set_xlim(chance - 0.02, 1.02)
    ax.set_xlabel("AUC: wrong node above correct node")
    ax.grid(axis="x", color="#e6eaee", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.set_title("The same flag scores 0.97 on sinks and 0.57 on the inputs a reviewer opens",
                 loc="left", fontsize=9)

    data = {"chance": chance,
            "bars": [{"label": label, "auc": value,
                      "ci": list(ci) if ci else None}
                     for label, value, ci, _ in bars],
            "hit1": a["by_target"]["source_leaf"]["hit1_expected"],
            "ties_records": a["ties"]["records_with_tied_max"]}
    return save(fig, "fig3_localisation_auc.png"), data


def main():
    os.makedirs(OUT, exist_ok=True)
    styled()
    payload = {}
    for key, fn in (("fig1", figure_gap), ("fig2", figure_ceiling), ("fig3", figure_localisation)):
        name, data = fn()
        payload[key] = {"file": name, **data}
        print(f"wrote figures/{name}")
    with open(os.path.join(OUT, "figure_data.json"), "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=1, ensure_ascii=False)
        handle.write("\n")
    print("wrote figures/figure_data.json")


if __name__ == "__main__":
    main()
