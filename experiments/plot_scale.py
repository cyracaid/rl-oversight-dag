#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scale-500 results figure, read from scale500_table.md (written by graph_scale.py)."""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.dirname(os.path.abspath(__file__))
FAMILY_LABEL = {"modular": "modular", "ba": "scale-free (BA)", "er": "sparse (ER)"}
COLORS = ["#999999", "#bbbbbb", "#fdae61", "#abdda4", "#1a9850", "#d7d7d7"]


def read_table(path):
    rows = [l.strip() for l in open(path) if l.startswith("|")]
    header = [c.strip() for c in rows[0].strip("|").split("|")]
    data = {}
    for line in rows[2:]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        data[cells[0]] = [float(c) for c in cells[1:]]
    title = open(path).readline().strip()
    return header[1:], data, title


policies, means, title = read_table(os.path.join(OUT, "scale500_table.md"))
families = list(means)
x = np.arange(len(families))
width = 0.8 / len(policies)

plt.figure(figsize=(10, 5))
for j, pol in enumerate(policies):
    vals = [means[f][j] for f in families]
    hatch = "//" if "oracle" in pol else None
    bars = plt.bar(x + (j - (len(policies) - 1) / 2) * width, vals, width, label=pol,
                   color=COLORS[j % len(COLORS)], hatch=hatch, edgecolor="#555555", lw=0.3)
    for b, v in zip(bars, vals):
        plt.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v:.1f}",
                 ha="center", va="bottom", fontsize=7)

plt.xticks(x, [FAMILY_LABEL.get(f, f) for f in families], fontsize=10)
plt.ylabel("avg sink errors (lower = better)")
plt.title(f"Scaled experiments: {title}")
plt.legend(title="policy", fontsize=8)
plt.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(OUT, "scale500.png"), dpi=130)
plt.close()
print("saved scale500.png")
