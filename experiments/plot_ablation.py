#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ablation figure: normal / noise / oracle confidence for GNN+REINFORCE."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.dirname(os.path.abspath(__file__))

conds = ["noise\n(signal destroyed)", "normal\n(learned conf)", "oracle\n(true error revealed)"]
means = [3.78, 1.38, 0.72]
per = [[3.30, 5.20, 2.85], [1.30, 1.95, 0.90], [0.80, 0.70, 0.65]]
colors = ["#fdae61", "#2a7de1", "#1a9850"]

plt.figure(figsize=(7, 4.5))
bars = plt.bar(conds, means, color=colors, yerr=[[m - min(p) for m, p in zip(means, per)],
                                                 [max(p) - m for m, p in zip(means, per)]],
               capsize=5)
for b, v, p in zip(bars, means, per):
    plt.text(b.get_x() + b.get_width() / 2, v + 0.15,
             f"{v:.2f}\n" + "/".join(f"{x:.2f}" for x in p),
             ha="center", va="bottom", fontsize=8)
plt.axhline(2.30, color="#999999", ls="--", lw=1, label="confidence threshold (2.30)")
plt.axhline(5.90, color="#bbbbbb", ls=":", lw=1, label="no review (5.90)")
plt.ylabel("avg sink errors (lower = better)")
    # error bars are min-max across 3 seeds, not CI
plt.title("Ablation: the confidence signal is the bottleneck\n(GNN + REINFORCE, 3 seeds × 12k episodes)")
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(OUT, "ablation_conf.png"), dpi=130)
plt.close()
print("saved ablation_conf.png")
