"""Render the pre-registered two-level scope experiment from episodes.csv.

    python3 report_scope.py results/scope-v1

The verdict is computed from PREREGISTER_SCOPE_V2.md's frozen rules. Every
comparison goes through one comparator so that a reversed sign cannot hide in a
per-prediction branch (that mistake was made once in report_shrink.py), and the
whole grid is printed whichever way the verdict falls.
"""

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from _env import EXPERIMENTS, ensure_experiments


ensure_experiments()
from rl_boundary import paired_bootstrap

POLICIES = ("oracle", "trust", "prior", "gate", "shrink", "scope")
LOCALITY_NAMES = {
    "uniform": "전체 노드 무작위",
    "source": "source 층",
    "sink": "sink 층",
    "error_nodes": "실제 오류 노드",
}

# (label, locality, fraction, shift, reference, relation, bar)
PREDICTIONS = (
    ("p1_global_up3", "uniform", 1.0, 3.0, "trust", "<=", 0.20),
    ("p2_global_up2", "uniform", 1.0, 2.0, "trust", "<=", 0.20),
    ("p3_masking_guard", "error_nodes", 1.0, 3.0, "trust", "<=", 0.20),
    ("p4_clean_cost", "clean", 0.0, 0.0, "trust", "<=", 0.05),
    ("p5a_partial_50", "uniform", 0.5, -3.0, "trust", "<=", 0.10),
    ("p5b_partial_25", "uniform", 0.25, -3.0, "trust", "<=", 0.10),
)
GRID_MEAN_BAR = 0.10          # prediction 6: scope - shrink <= 0.10 on the 112-cell mean

HEADLINES = (
    ("uniform", 1.0, 3.0, "예측 1: 무해한 전역 +3 (shrink가 +0.72를 잃던 셀)"),
    ("uniform", 1.0, 2.0, "예측 2: 무해한 전역 +2"),
    ("error_nodes", 1.0, 3.0, "예측 3: 은폐형 +3 (shrink의 이득을 반납하는지)"),
    ("uniform", 1.0, -4.0, "예상 손실: 전역 −4 (shrink −0.88)"),
    ("uniform", 1.0, -3.0, "예상 손실: 전역 −3 (shrink −0.66)"),
    ("uniform", 0.5, -3.0, "예측 5: 부분 50 %·−3"),
    ("uniform", 0.25, -3.0, "예측 5: 부분 25 %·−3"),
    ("sink", 1.0, -3.0, "참고: sink 층 −3"),
    ("source", 1.0, -4.0, "참고: source 층 −4"),
)
DIAGNOSTIC_CELLS = (
    ("clean", 0.0, 0.0, "깨끗함"),
    ("uniform", 1.0, 3.0, "전역 +3"),
    ("uniform", 1.0, -4.0, "전역 −4"),
    ("uniform", 0.5, -3.0, "부분 50 %·−3"),
    ("uniform", 0.25, -3.0, "부분 25 %·−3"),
    ("error_nodes", 1.0, 3.0, "은폐형 +3"),
    ("source", 1.0, -4.0, "source −4"),
    ("sink", 1.0, -3.0, "sink −3"),
)


def holds(value, relation, bar):
    """The only place a comparison sign exists."""
    if relation == "<=":
        return bool(value <= bar)
    if relation == ">=":
        return bool(value >= bar)
    raise ValueError(f"unknown relation {relation!r}")


def load(run):
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8-sig"))
    episodes = run / "episodes.csv"
    if hashlib.sha256(episodes.read_bytes()).hexdigest() != manifest["episodes_sha256"]:
        raise ValueError("episodes.csv SHA-256 does not match the run manifest")
    graphs = manifest["graph_seeds"]
    final, initial, mode, shift, verdict_cells = {}, {}, {}, {}, {}
    with episodes.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            graph = int(row["graph_seed"])
            key = (row["locality"], float(row["fraction"]), float(row["shift"]), row["policy"])
            if int(row["reviews"]) != manifest["budget"]:
                raise ValueError(f"review budget violated: {key}")
            final.setdefault(key, {})[graph] = int(row["sink_errors"])
            initial.setdefault(graph, int(row["initial_sink_errors"]))
            mode.setdefault(key, {})[graph] = row["gate_mode"]
            shift.setdefault(key, {})[graph] = float(row["belief_shift"])
            if row["policy"] == "scope":
                verdict_cells.setdefault(key, {})[graph] = (
                    float(row["post_none"]), float(row["post_frac"]), float(row["post_global"]),
                    float(row["map_q"]), float(row["map_delta"]))
    cells = {}
    for key, values in final.items():
        if set(values) != set(graphs):
            raise ValueError(f"incomplete cell {key}")
        cells[key] = np.array([values[graph] for graph in graphs])
    if len(initial) != len(graphs):
        raise ValueError("incomplete initial-error map")
    oracle = cells[("clean", 0.0, 0.0, "oracle")]
    if not np.array_equal(cells[("clean", 0.0, 0.0, "trust")], oracle):
        raise ValueError("clean trust must reproduce oracle exactly")
    for locality, fraction, s in {(k[0], k[1], k[2]) for k in cells if k[0] != "clean"}:
        gate_cell = cells[(locality, fraction, s, "gate")]
        trust_cell = cells[(locality, fraction, s, "trust")]
        prior_cell = cells[(locality, fraction, s, "prior")]
        labels = mode[(locality, fraction, s, "gate")]
        for index, graph in enumerate(graphs):
            expected = prior_cell[index] if labels[graph] == "noise" else trust_cell[index]
            if gate_cell[index] != expected:
                raise ValueError(f"gate is not a pure selector on {locality}/{fraction}/{s}/{graph}")
    for key in list(cells):
        if key[0] != "clean":
            cells[(key[0], key[1], key[2], "oracle")] = oracle
    return manifest, cells, shift, verdict_cells, graphs


def gap(cells, key, policy, reference, draws=10000):
    return paired_bootstrap(cells[key + (policy,)][None, :], cells[key + (reference,)],
                            draws=draws, seed=20261112)


def fmt_gap(result):
    return f"{result['mean']:+.3f} [{result['low']:+.3f}, {result['high']:+.3f}]"


def build(manifest, cells, graphs):
    localities, fractions, shifts = manifest["localities"], manifest["fractions"], manifest["shifts"]
    grid = {}
    for locality in ["clean"] + list(localities):
        grid[locality] = {}
        for fraction in ([0.0] if locality == "clean" else fractions):
            grid[locality][fraction] = {}
            for s in ([0.0] if locality == "clean" else shifts):
                key = (locality, fraction, s)
                means = {policy: float(cells[key + (policy,)].mean()) for policy in POLICIES}
                grid[locality][fraction][s] = {
                    "means": means,
                    "scope_trust": means["scope"] - means["trust"],
                    "scope_shrink": means["scope"] - means["shrink"],
                    "shrink_trust": means["shrink"] - means["trust"],
                }
    total = len(localities) * len(fractions) * len(shifts)
    grid_mean = {policy: float(np.mean([grid[locality][fraction][s]["means"][policy]
                                        for locality in localities
                                        for fraction in fractions
                                        for s in shifts]))
                 for policy in ("trust", "gate", "shrink", "prior", "scope")}

    checks, values = {}, {}
    for name, locality, fraction, s, reference, relation, bar in PREDICTIONS:
        key = (locality, fraction, s)
        value = grid[locality][fraction][s][f"scope_{reference}"]
        values[name] = {"delta": value, "relation": relation, "bar": bar, "reference": reference,
                        "cell": key}
        checks[name] = holds(value, relation, bar)
    checks["p6_grid_mean"] = holds(grid_mean["scope"] - grid_mean["shrink"], "<=", GRID_MEAN_BAR)
    values["p6_grid_mean"] = {"delta": grid_mean["scope"] - grid_mean["shrink"], "relation": "<=",
                              "bar": GRID_MEAN_BAR, "reference": "shrink", "cell": "112-cell mean"}
    primary = all(checks[name] for name in ("p1_global_up3", "p2_global_up2"))
    secondary_failures = [name for name in
                          ("p3_masking_guard", "p4_clean_cost", "p5a_partial_50",
                           "p5b_partial_25", "p6_grid_mean") if not checks[name]]
    if primary and not secondary_failures:
        verdict = "성공"
    elif primary and len(secondary_failures) == 1:
        verdict = "부분 성공"
    else:
        verdict = "실패"

    better = sorted(((locality, fraction, s) for locality in localities
                     for fraction in fractions for s in shifts),
                    key=lambda k: grid[k[0]][k[1]][k[2]]["scope_trust"])
    return {"grid": grid, "grid_mean": grid_mean, "predictions": checks, "prediction_values": values,
            "verdict": verdict, "primary_holds": primary, "secondary_failures": secondary_failures,
            "total_cells": total,
            "cells_worse_than_trust": [k for k in better if grid[k[0]][k[1]][k[2]]["scope_trust"] > 0],
            "cells_better_than_trust": [k for k in better if grid[k[0]][k[1]][k[2]]["scope_trust"] < 0],
            "best_cells": better[:5], "worst_cells": list(reversed(better))[:5],
            "bootstrap": {"unit": "paired graph", "draws": 10000, "seed": 20261112,
                          "coverage": 0.95},
            "frozen": {"predictions": [list(p) for p in PREDICTIONS],
                       "grid_mean_bar": GRID_MEAN_BAR}}


def table(result, manifest, locality, column):
    shifts = manifest["shifts"]
    lines = ["| 오염 비율 | " + " | ".join(f"{s:+.1f}" for s in shifts) + " |",
             "|---:|" + "---:|" * len(shifts)]
    for fraction in manifest["fractions"]:
        lines.append(f"| {fraction:.0%} | " + " | ".join(
            f"{result['grid'][locality][fraction][s][column]:+.2f}" for s in shifts) + " |")
    return lines


def mean_of(verdict_cells, graphs, key, index):
    values = np.array([verdict_cells[key][graph][index] for graph in graphs], dtype=float)
    return float(values.mean())


def render(manifest, cells, verdict_cells, graphs, result):
    count = len(graphs)
    scope = manifest["scope"]
    fit = scope["fit"]
    grid = result["grid"]
    clean = grid["clean"][0.0][0.0]["means"]
    lines = [
        "# 범위 2층 모형: 전역 이동과 부분 이동을 한 우도로 구분하기", "",
        f"사전 등록(`PREREGISTER_SCOPE_V2.md`) 후 새 그래프 {count}개(seed {graphs[0]}–{graphs[-1]})에서 "
        f"손상 격자를 그대로 재실행했다. 예산 {manifest['budget']}회, 이동 격자 "
        f"{len(scope['delta_grid'])}개(±0.5–±4.0), 비율 격자 {len(scope['q_grid'])}개"
        f"(0.05–1.00), \"아무 일 없음\" 사전확률 "
        f"`p0 = {scope['p0']:.2f}` (보정 70000–70029의 {fit['graph_count']}개 그래프).", "",
        "`scope`는 정책을 바꾸지 않는다. 그래프마다 두 가설을 경쟁시킨다. "
        "**q = 0**: 아무 일도 없었다. **(q, δ)**: 80개 중 q 비율이 같은 δ만큼 움직였다. "
        "δ가 노드마다가 아니라 **그래프에 하나**라는 점이 `shrink`와 다르고, 비율 q를 자유롭게 "
        "두는 점이 전역 게이트와 다르다. 그 우도로 가중한 노드 사후확률을 `initial_belief` 대신 "
        "넣고, 그 뒤로는 `trust`와 같은 marginal 규칙·예산 16회다. 정답·간선 동전·검토자 난수는 "
        "쓰지 않는다.", "",
        "## 기준선", "",
        "| 정책 | 평균 잔여 오류 |", "|---|---:|",
    ]
    for policy in POLICIES:
        lines.append(f"| {policy} | {clean[policy]:.3f} |")

    lines.extend(["", "## 핵심 셀", "",
                  "값은 짝지은 그래프 부트스트랩 95% 구간이다. 대괄호 안이 구간.", "",
                  "| 셀 | scope − trust | scope − shrink | gate − trust |",
                  "|---|---:|---:|---:|"])
    for locality, fraction, s, label in HEADLINES:
        key = (locality, fraction, s)
        lines.append(
            f"| {label} | {fmt_gap(gap(cells, key, 'scope', 'trust'))} "
            f"| {fmt_gap(gap(cells, key, 'scope', 'shrink'))} "
            f"| {fmt_gap(gap(cells, key, 'gate', 'trust'))} |")

    lines.extend(["", "## 전 구간: scope − trust (양수 = 나쁨)", ""])
    for locality in manifest["localities"]:
        lines.append(f"**scope**, {LOCALITY_NAMES[locality]}")
        lines.append("")
        lines.extend(table(result, manifest, locality, "scope_trust"))
        lines.append("")
    lines.extend(["", "## 전 구간: scope − shrink (양수 = shrink보다 나쁨)", ""])
    for locality in manifest["localities"]:
        lines.append(f"**scope**, {LOCALITY_NAMES[locality]}")
        lines.append("")
        lines.extend(table(result, manifest, locality, "scope_shrink"))
        lines.append("")

    lines.extend(["", "## p0 적합 곡선", "",
                  "깨끗한 비용 상한 `+0.05`를 만족하는 p0 중에서 손상 격자 평균이 최소인 값을 골랐다.", "",
                  "| p0 | 깨끗한 셀 평균 | 깨끗한 비용 | 손상 격자 평균 | 허용 |",
                  "|---:|---:|---:|---:|:---:|"])
    for key, row in fit["grid"].items():
        chosen = abs(float(key) - scope["p0"]) < 1e-9
        lines.append(f"| {float(key):.2f}{' ←' if chosen else ''} | {row['clean_mean']:.3f} | "
                     f"{row['clean_cost']:+.3f} | {row['grid_mean']:.3f} | "
                     f"{'예' if row['admissible'] else '아니오'} |")

    lines.extend(["", "## 가설 선택 진단", "",
                  "각 셀에서 그래프별로 무엇이 선택됐는지의 평균이다. `post_none`은 \"아무 일 없음\" "
                  "사후확률, `post_frac`은 부분 이동, `post_global`은 q = 1, `map_q`/`map_delta`는 "
                  "최빈 셀의 비율과 이동 크기다. 정답을 쓰지 않지만 정책 입력도 아니다.", "",
                  "| 셀 | post_none | post_frac | post_global | map_q | map_delta |",
                  "|---|---:|---:|---:|---:|---:|"])
    for locality, fraction, s, label in DIAGNOSTIC_CELLS:
        key = (locality, fraction, s, "scope")
        lines.append(f"| {label} | {mean_of(verdict_cells, graphs, key, 0):.3f} "
                     f"| {mean_of(verdict_cells, graphs, key, 1):.3f} "
                     f"| {mean_of(verdict_cells, graphs, key, 2):.3f} "
                     f"| {mean_of(verdict_cells, graphs, key, 3):.2f} "
                     f"| {mean_of(verdict_cells, graphs, key, 4):+.2f} |")

    checks = result["predictions"]
    labels = {
        "p1_global_up3": "예측 1 (전역 +3 에서 scope − trust ≤ +0.20)",
        "p2_global_up2": "예측 2 (전역 +2 에서 scope − trust ≤ +0.20)",
        "p3_masking_guard": "예측 3 (은폐형 +3 에서 scope − trust ≤ +0.20)",
        "p4_clean_cost": "예측 4 (깨끗한 셀에서 scope − trust ≤ +0.05)",
        "p5a_partial_50": "예측 5a (부분 50 %·−3 에서 scope − trust ≤ +0.10)",
        "p5b_partial_25": "예측 5b (부분 25 %·−3 에서 scope − trust ≤ +0.10)",
        "p6_grid_mean": f"예측 6 (112셀 평균에서 scope − shrink ≤ +{GRID_MEAN_BAR:.2f})",
    }
    lines.extend(["", "## 예측 대조와 판정", ""])
    for name, text in labels.items():
        value = result["prediction_values"][name]["delta"]
        lines.append(f"- {text}: **{'성립' if checks[name] else '불성립'}** ({value:+.3f}).")
    lines.extend(["",
                  f"전 격자 {result['total_cells']}셀 중 scope가 trust보다 나쁜 셀은 "
                  f"{len(result['cells_worse_than_trust'])}개, 나은 셀은 "
                  f"{len(result['cells_better_than_trust'])}개다. 격자 평균은 "
                  f"trust {result['grid_mean']['trust']:.3f}, shrink {result['grid_mean']['shrink']:.3f}, "
                  f"scope {result['grid_mean']['scope']:.3f} (gate {result['grid_mean']['gate']:.3f}, "
                  f"prior {result['grid_mean']['prior']:.3f}). 사전 등록 판정: **{result['verdict']}**.", ""])

    if result["verdict"] == "성공":
        lines.extend([
            "여섯 예측이 모두 성립했다. 이 실험이 존재하는 이유인 무해한 전역 상향 이동이 "
            "사라졌고, 깨끗한 비용도 상한 안이며, 112셀 평균에서 shrink를 capacity 손해 없이 "
            "대체했다. 즉 **\"노드가 움직였나\"가 아니라 \"그래프가 움직였나\"를 물으면 전역 이동을 "
            "되돌릴 수 있다.**", "",
            "다만 이 성공은 shrink가 잘하던 셀을 포기해서 산 것이다. 아래 `scope − shrink` 표에서 "
            "양수인 칸이 그 값이다(양수 = shrink보다 나쁨).",
        ])
    elif result["verdict"] == "부분 성공":
        lines.extend([
            "전역 상향 이동은 고쳤지만 부수 손실이 하나 남았다. 어느 예측이 깨졌는지가 다음 설계를 정한다.",
        ])
    else:
        lines.extend([
            "전역 이동을 되돌리는 데 실패했다. 공유 (q, δ) 가설이 실제로는 선택되지 않았거나, "
            "선택됐더라도 노드 사후확률이 정책 순서를 되돌리지 못했다는 뜻이다. 아래 진단 표가 "
            "둘 중 어느 쪽인지 보여준다.",
        ])

    lines.extend(["", "## 예측 밖에서 드러난 것", ""])
    best = result["best_cells"][0]
    worst = result["worst_cells"][0]
    down4 = grid["uniform"][1.0][-4.0]
    down3 = grid["uniform"][1.0][-3.0]
    mask = grid["error_nodes"][1.0][3.0]
    lines.extend([
        f"가장 크게 이긴 셀은 {LOCALITY_NAMES[best[0]]} {best[1]:.0%} {best[2]:+.1f}"
        f"(scope − trust {grid[best[0]][best[1]][best[2]]['scope_trust']:+.2f}), 가장 크게 진 셀은 "
        f"{LOCALITY_NAMES[worst[0]]} {worst[1]:.0%} {worst[2]:+.1f}"
        f"(scope − trust {grid[worst[0]][worst[1]][worst[2]]['scope_trust']:+.2f})이다.", "",
        "사전 등록에 미리 적은 예상 손실은 두 종류였다. 실측은 이렇다.", "",
        "| 예상 손실 셀 | scope − trust | scope − shrink |",
        "|---|---:|---:|",
        f"| 전역 −3 (shrink {down3['shrink_trust']:+.2f}) | {down3['scope_trust']:+.2f} "
        f"| {down3['scope_shrink']:+.2f} |",
        f"| 전역 −4 (shrink {down4['shrink_trust']:+.2f}) | {down4['scope_trust']:+.2f} "
        f"| {down4['scope_shrink']:+.2f} |",
        f"| 은폐형 +3 (shrink {mask['shrink_trust']:+.2f}) | {mask['scope_trust']:+.2f} "
        f"| {mask['scope_shrink']:+.2f} |", "",
        "전역 하향 이동에서 모형은 δ를 되돌린다. 그러면 사후확률은 이동이 없었던 그래프에서 `trust`가 "
        "가졌을 값이 되고, 점수 순서는 그대로지만 크기가 달라지므로 검토 선택은 `trust`와 같지 않을 수 "
        "있다. `shrink`가 그 셀에서 벌던 이득은 원칙적으로 반납된다. 은폐형 +3은 점수만 보면 깨끗한 "
        "그래프와 구별되지 않으므로 `q = 0`이 선택되고, 역시 원래 사후확률로 돌아간다. 위 표의 "
        "`scope − shrink` 열이 실제 반납액이고, `scope − trust` 열이 그 셀에서 남은 손익이다.", "",
        "두 손실을 합쳐도 112셀 평균에서 순손해가 되지 않는지가 예측 6이었고, 그 값은 위에 있다.",
        "", "## 한계", "",
        "- δ 격자가 평가 격자와 같은 구간이다. 다른 손상 생성기에는 재적합이 필요하다.",
        "- 한 그래프에 δ가 하나라는 가정은 이 생성기의 성질이다. 두 locality가 동시에 손상되는 조건은 없다.",
        "- q 격자는 0.05 간격(≤ 0.30), 그 위는 성겁다. 참 비율이 0.35나 0.45면 이웃 셀로 흡수된다.",
        "- `p0` 곡선이 평평해 사전확률의 영향은 작다. 깨끗한 그래프에서 `post_none`이 1에 가깝지 "
        "않은 것은 80개 노드가 \"아무 일 없음\"에 대해 주는 증거가 생각보다 약하기 때문이다.",
        "- `oracle`은 정답을 쓰므로 비배포 상한이다. 단일 marginal 규칙, 단일 그래프 family.",
        "- 탐색적이지 않다: 설계는 보정 블록에서만 수정했고(3600 이전), 예측·판정 기준은 실행 전에 "
        "동결했으며, 판정은 그 기준으로만 계산했다.", "",
        "[그래프별 결과](episodes.csv) · [실행 설정](manifest.json) · [수치 요약](scope.json) · "
        "[사전 등록](../PREREGISTER_SCOPE_V2.md)", ""])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    run = parser.parse_args().run
    manifest, cells, _, verdict_cells, graphs = load(run)
    result = build(manifest, cells, graphs)
    result["source_sha256"] = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (run / "manifest.json", run / "episodes.csv", Path(__file__),
                     Path(__file__).with_name("PREREGISTER_SCOPE_V2.md"),
                     EXPERIMENTS / "rl_boundary.py")
    }
    (run / "scope.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                                    encoding="utf-8")
    (run / "scope.md").write_text(render(manifest, cells, verdict_cells, graphs, result),
                                   encoding="utf-8")
    print(run / "scope.md")


if __name__ == "__main__":
    main()
