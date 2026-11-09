#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scale-500 results figure: three graph families × five policies."""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.dirname(os.path.abspath(__file__))

families = ["modular", "scale-free (BA)", "sparse (ER)"]
policies = ["No review", "Random", "Conf threshold", "Hub", "Greedy (1−1/e)"]
means = {
    "modular": [24.00, 22.60, 8.60, 19.00, 2.00],
    "scale-free (BA)": [80.60, 79.20, 29.80, 53.80, 3.80],
    "sparse (ER)": [42.60, 42.00, 16.40, 34.60, 8.20],
}
colors = ["#999999", "#bbbbbb", "#fdae61", "#abdda4", "#1a9850"]

x = np.arange(len(families))
width = 0.15

plt.figure(figsize=(9, 5))
for j, pol in enumerate(policies):
    vals = [means[fam][j] for fam in families]
    bars = plt.bar(x + (j - 2) * width, vals, width, label=pol, color=colors[j], alpha=0.9)
    for b, v in zip(bars, vals):
        plt.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v:.1f}",
                 ha="center", va="bottom", fontsize=7)

plt.xticks(x, families, fontsize=10)
plt.ylabel("avg sink errors (lower = better)")
plt.title(f"Scaled experiments: N=500, budget=50 (10%), λ=0.8, Zipf types, 5 seeds")
plt.legend(title="policy")
plt.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(OUT, "scale500.png"), dpi=130)
plt.close()
print("saved scale500.png")
