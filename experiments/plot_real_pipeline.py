#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Real sleep-pipeline DAG results figure.

Every number is read from `real_pipeline_table.md`, which
`real_pipeline_graph.py` writes, so the figure cannot drift from the
experiment. Run the experiment first, then this script.
"""
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.dirname(os.path.abspath(__file__))
TABLE = os.path.join(OUT, "real_pipeline_table.md")

ORDER = ["no review", "random", "hub (children)", "conf threshold"]
LABELS = {"no review": "No review", "random": "Random",
          "hub (children)": "Hub", "conf threshold": "Conf threshold"}

header = ""
rows = {}
with open(TABLE, encoding="utf-8") as fh:
    for line in fh:
        line = line.rstrip("\n")
        if line and not header:
            header = line
        ikey = line.strip().strip("|").split("|")
        if len(ikey) != 2:
            continue
        key, val = ikey[0].strip(), ikey[1].strip()
        if key in LABELS:
            rows[key] = float(val)

missing = [k for k in ORDER if k not in rows]
if missing:
    raise SystemExit(f"{TABLE} is missing {missing}; run real_pipeline_graph.py first")

policies = [LABELS[k] for k in ORDER]
vals = [rows[k] for k in ORDER]
colors = ["#999999", "#bbbbbb", "#abdda4", "#1a9850"]

plt.figure(figsize=(6.5, 4))
bars = plt.bar(policies, vals, color=colors)
for b, v in zip(bars, vals):
    plt.text(b.get_x() + b.get_width() / 2, v + 0.06, f"{v:.2f}",
             ha="center", va="bottom", fontsize=10)
plt.ylabel("avg sink errors (lower = better)")
plt.ylim(0, max(vals) * 1.22)
plt.title(f"{header.replace('Real sleep-pipeline DAG ', 'Real sleep-pipeline DAG\n')}\n"
          "calibrated threshold nearly clears conclusion errors")
plt.tight_layout()
plt.savefig(os.path.join(OUT, "real_pipeline.png"), dpi=130)
plt.close()
print("saved real_pipeline.png from", os.path.basename(TABLE), vals)
