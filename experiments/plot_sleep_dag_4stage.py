#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Draw the 21-node sleep-pipeline DAG as four stages (collect → preprocess → analyze → conclude).

Single source of truth: node names, layers, types and parents are imported from
experiments/real_pipeline_graph.py. Output: experiments/sleep_dag_4stage.{png,svg}

The point of the figure is the slide claim: every pipeline output is a node; the
conclusion layer has four sink nodes, and the reward counts only those.
"""
import importlib.util
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib.lines import Line2D

LANG = sys.argv[1] if len(sys.argv) > 1 else "ko"
if LANG not in ("ko", "en"):
    sys.exit("usage: plot_sleep_dag_4stage.py [ko|en]")

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("rpg", os.path.join(HERE, "real_pipeline_graph.py"))
rpg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rpg)

NODES, PARENTS, SINKS = rpg.NODES, rpg.PARENTS, rpg.SINKS
NAME2ID, LAYER, TYPE, TYPE_RATE = rpg.NAME2ID, rpg.LAYER, rpg.TYPE, rpg.TYPE_RATE

plt.rcParams["font.family"] = ["AppleGothic", "DejaVu Sans"]

COLOR = {
    "order_error": "#e74c3c",
    "awake_getup_diff_error": "#f39c12",
    "bed_sleep_diff_error": "#3498db",
    "sleep_awake_equal_error": "#9b59b6",
    "sleep_awake_24h_error": "#16a085",
    "metric_spike": "#7f8c8d",
}

L = {
    "ko": dict(
        stages=[
            ("① 수집  Collect", "원시 일기 필드 (8)"),
            ("② 전처리  Preprocess", "파생 차이값 (5)"),
            ("③ 분석  Analyze", "수면 지표 (4)"),
            ("④ 결론  Conclude", "타당성·품질 판정 (4 sinks)"),
        ],
        reward="보상 = 결론 sink 4개의 잔여 오류 수 × (−1)",
        footer=("노드 = 파이프라인 각 단계의 출력값 하나.  숫자 = 모델이 쓰는 base error 선행확률(실측 아님).\n"
                "굵은 테두리 = SINK(최종 결론).  결론 노드도 자체 오류를 가질 수 있다."),
        legend_title="오류 유형 (실제 수정 파일 기준)",
        title="수면 파이프라인 의존성 DAG (N=21): 검토 노드란 무엇인가",
        subtitle="실제 수정 75건 기준 유형 비중: order_error 76% · 나머지 5종",
        suffix="",
    ),
    "en": dict(
        stages=[
            ("① Collect", "8 raw diary fields"),
            ("② Preprocess", "5 derived gaps"),
            ("③ Analyze", "4 sleep metrics"),
            ("④ Conclude", "4 verdicts (sinks)"),
        ],
        reward="reward = −(residual errors at the 4 sink conclusions)",
        footer=("A node is one output value of one pipeline stage.  Number = model prior for base error (not measured).\n"
                "Thick border = SINK (final conclusion).  Conclusion nodes can carry their own error."),
        legend_title="Error type (from the manual-correction file)",
        title="Sleep-pipeline dependency DAG (N=21): what is a review node?",
        subtitle="Type shares among 75 real corrections: order_error 76% · five other types",
        suffix="_en",
    ),
}[LANG]
STAGES = L["stages"]

# ---- layout ---------------------------------------------------------------
by_layer = {k: [] for k in range(4)}
for i, (_, layer, _) in enumerate(NODES):
    by_layer[layer].append(i)

pos = {}
for layer, ids in by_layer.items():
    n = len(ids)
    for rank, i in enumerate(ids):
        y = (n - 1) / 2.0 - rank
        pos[i] = (layer * 3.0, y * 1.05)

fig, ax = plt.subplots(figsize=(15.5, 9.4))
ax.set_xlim(-1.7, 11.9)
ax.set_ylim(-6.4, 7.4)
ax.axis("off")

# stage headers
for layer, (title, sub) in enumerate(STAGES):
    ax.text(layer * 3.0, 5.18, title, ha="center", va="center",
            fontsize=13, fontweight="bold", color="#1b1b1b")
    ax.text(layer * 3.0, 4.74, sub, ha="center", va="center",
            fontsize=9.5, color="#5a5a5a")
    ax.plot([layer * 3.0 - 1.45, layer * 3.0 + 1.45], [4.38, 4.38],
            color="#c9cdd2", lw=1.2, zorder=0)

# edges first (behind boxes)
for child, ps in PARENTS.items():
    ci = NAME2ID[child]
    for p in ps:
        pi = NAME2ID[p]
        x0, y0 = pos[pi]
        x1, y1 = pos[ci]
        rad = 0.10 if abs(x1 - x0) > 3 or abs(x1 - x0) < 0.1 else 0.04
        ax.add_patch(FancyArrowPatch(
            (x0 + 0.62, y0), (x1 - 0.62, y1),
            connectionstyle=f"arc3,rad={rad}",
            arrowstyle="-|>,head_length=6,head_width=3.4",
            linewidth=1.15, color="#9aa0a6", alpha=0.55,
            shrinkA=0, shrinkB=0, zorder=1))

# node boxes
for i, (name, layer, typ) in enumerate(NODES):
    x, y = pos[i]
    w, h = 1.28, 0.74
    sink = i in SINKS
    ax.add_patch(FancyBboxPatch(
        (x - w / 2, y - h / 2), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.10",
        linewidth=2.4 if sink else 1.0,
        edgecolor="#111111" if sink else "#ffffff",
        facecolor=COLOR[typ], alpha=0.92, zorder=3))
    ax.text(x, y + 0.10, name, ha="center", va="center",
            fontsize=8.2, color="white", fontweight="bold", zorder=4)
    ax.text(x, y - 0.20, f"{TYPE_RATE[typ]:.2f}", ha="center", va="center",
            fontsize=7.4, color="white", alpha=0.95, zorder=4)
    if sink:
        ax.text(x + 0.70, y + 0.26, "SINK", ha="left", va="center",
                fontsize=7.6, fontweight="bold", color="#111111",
                zorder=5, clip_on=False)

# reward note
ax.annotate(L["reward"],
            xy=(9.0, -2.15), xytext=(3.35, -3.30),
            fontsize=10.5, color="#111111",
            arrowprops=dict(arrowstyle="-|>", color="#e74c3c", lw=1.6,
                            connectionstyle="arc3,rad=-0.15"))
ax.text(-1.65, -5.30,
        L["footer"],
        fontsize=9.3, color="#333333", va="top")

# legend
handles = [Line2D([0], [0], marker="s", linestyle="", markersize=9,
                  markerfacecolor=c, markeredgecolor="none", label=t)
           for t, c in COLOR.items()]
ax.legend(handles=handles, loc="lower right", ncol=3, frameon=False,
          fontsize=8.4, title=L["legend_title"], title_fontsize=8.8)

# title
ax.text(-1.65, 7.15,
        L["title"],
        fontsize=16, fontweight="bold", color="#111111", va="top")
ax.text(-1.65, 6.55,
        L["subtitle"],
        fontsize=10, color="#5a5a5a", va="top")

plt.tight_layout()
for ext in ("png", "svg"):
    out = os.path.join(HERE, f"sleep_dag_4stage{L['suffix']}.{ext}")
    plt.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    print("wrote", out)
