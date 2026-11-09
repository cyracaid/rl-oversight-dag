#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Real sleep-pipeline DAG results figure."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.dirname(os.path.abspath(__file__))

policies = ["No review", "Random", "Hub", "Conf threshold"]
vals = [2.12, 1.88, 1.75, 0.50]
colors = ["#999999", "#bbbbbb", "#abdda4", "#1a9850"]

plt.figure(figsize=(6.5, 4))
bars = plt.bar(policies, vals, color=colors)
for b, v in zip(bars, vals):
    plt.text(b.get_x() + b.get_width() / 2, v + 0.06, f"{v:.2f}",
             ha="center", va="bottom", fontsize=10)
plt.ylabel("avg sink errors (lower = better)")
plt.title("Real sleep-pipeline DAG (N=21, budget=8, 8 seeds)\n"
          "calibrated threshold nearly clears conclusion errors")
plt.tight_layout()
plt.savefig(os.path.join(OUT, "real_pipeline.png"), dpi=130)
plt.close()
print("saved real_pipeline.png")
