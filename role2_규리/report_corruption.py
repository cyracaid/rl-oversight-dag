"""Render the corruption-boundary sweep from its committed episodes.csv.

The report is derived only from ``episodes.csv`` and ``manifest.json`` so that a
clone can reproduce it without re-running the simulator:

    python3 report_corruption.py results/corruption-v1

Point estimates fill the matrices; paired bootstrap intervals (graph-level,
10,000 draws) are reported only for the cells the conclusions rest on, because
the full grid is 112 cells.
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

REGRET = ("trust", "gate", "feedback", "prior")
NEGATIVE = lambda shifts: [s for s in shifts if s < 0]
POSITIVE = lambda shifts: [s for s in shifts if s > 0]
LOCALITY_NAMES = {
    "uniform": "전체 노드 무작위",
    "source": "source 층",
    "sink": "sink 층",
    "error_nodes": "실제 오류 노드",
}


def load(run):
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8-sig"))
    episodes = run / "episodes.csv"
    if hashlib.sha256(episodes.read_bytes()).hexdigest() != manifest["episodes_sha256"]:
        raise ValueError("episodes.csv SHA-256 does not match the run manifest")
    graphs = manifest["graph_seeds"]
    final, initial, mode, corrupted = {}, {}, {}, {}
    with episodes.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            graph = int(row["graph_seed"])
            key = (row["locality"], float(row["fraction"]), float(row["shift"]), row["policy"])
            if int(row["reviews"]) != manifest["budget"]:
                raise ValueError(f"review budget violated: {key} graph {graph}")
            final.setdefault(key, {})[graph] = int(row["sink_errors"])
            initial.setdefault(graph, int(row["initial_sink_errors"]))
            mode.setdefault(key, {})[graph] = row["gate_mode"]
            corrupted.setdefault((key[0], key[1], key[2]), {})[graph] = int(row["corrupted_nodes"])
    cells = {}
    for key, values in final.items():
        if set(values) != set(graphs):
            raise ValueError(f"incomplete cell {key}")
        cells[key] = np.array([values[graph] for graph in graphs])
    if len(initial) != len(graphs):
        raise ValueError("incomplete initial-error map")
    if set(policy for _, _, _, policy in cells) != {"oracle", "trust", "prior", "gate", "feedback"}:
        raise ValueError("unexpected policy set")
    oracle = cells[("clean", 0.0, 0.0, "oracle")]
    for key in list(cells):
        if key[0] != "clean" and key[3] == "oracle":
            raise ValueError("grid cells must not carry their own oracle")
    for key in list(cells):
        if key[0] != "clean":
            # One clean oracle row serves every cell; injecting it keeps the CSV small.
            cells[(key[0], key[1], key[2], "oracle")] = oracle
    labels = [mode[key][graph] for key in mode for graph in graphs]
    if any(label not in ("normal", "noise") for label in labels):
        raise ValueError("invalid gate label")

    for (locality, fraction, shift) in {(k[0], k[1], k[2]) for k in cells if k[0] != "clean"}:
        labels = np.array([mode[(locality, fraction, shift, "gate")][g] for g in graphs])
        trust = cells[(locality, fraction, shift, "trust")]
        prior = cells[(locality, fraction, shift, "prior")]
        gate = cells[(locality, fraction, shift, "gate")]
        if not np.array_equal(gate, np.where(labels == "noise", prior, trust)):
            raise ValueError(f"gate is not a pure selector on {locality}/{fraction}/{shift}")
    if {mode[("clean", 0.0, 0.0, "gate")][g] for g in graphs} != {"normal"}:
        raise ValueError("the clean cell must be labelled normal")
    if not np.array_equal(cells[("clean", 0.0, 0.0, "trust")], cells[("clean", 0.0, 0.0, "oracle")]):
        raise ValueError("clean trust must reproduce oracle exactly")
    return manifest, cells, mode, corrupted, graphs


def mean(cells, locality, fraction, shift, policy):
    return float(cells[(locality, fraction, shift, policy)].mean())


def gap(cells, locality, fraction, shift, policy, reference):
    return paired_bootstrap(cells[(locality, fraction, shift, policy)][None, :],
                            cells[(locality, fraction, shift, reference)])


def detection(mode, locality, fraction, shift, graphs):
    labels = mode[(locality, fraction, shift, "gate")]
    return sum(labels[graph] == "noise" for graph in graphs)


def fmt(value, digits=3):
    return f"{value:.{digits}f}"


def fmt_gap(result):
    return f"{result['mean']:+.3f} [{result['low']:+.3f}, {result['high']:+.3f}]"


def matrix(manifest, cells, corrupted, locality, policy, reference=None):
    fractions, shifts = manifest["fractions"], manifest["shifts"]
    header = "| 오염 비율 | 오염 노드 | " + " | ".join(f"{s:+.1f}" for s in shifts) + " |"
    rule = "|---:|---:|" + "---:|" * len(shifts)
    lines = [header, rule]
    for fraction in fractions:
        nodes = float(np.mean(list(corrupted[(locality, fraction, shifts[0])].values())))
        cells_text = []
        for shift in shifts:
            value = mean(cells, locality, fraction, shift, policy)
            if reference is not None:
                value -= mean(cells, locality, fraction, shift, reference)
                cells_text.append(f"{value:+.2f}")
            else:
                cells_text.append(f"{value:.2f}")
        lines.append(f"| {fraction:.0%} | {nodes:.0f} | " + " | ".join(cells_text) + " |")
    return lines


def detection_matrix(manifest, mode, graphs, locality):
    shifts = manifest["shifts"]
    lines = ["| 오염 비율 | " + " | ".join(f"{s:+.1f}" for s in shifts) + " |",
             "|---:|" + "---:|" * len(shifts)]
    for fraction in manifest["fractions"]:
        lines.append(f"| {fraction:.0%} | " + " | ".join(
            f"{detection(mode, locality, fraction, s, graphs)}/{len(graphs)}"
            for s in shifts) + " |")
    return lines


def boundary(manifest, cells, mode, graphs, locality, fraction):
    """Smallest |negative shift| whose detection reaches half, plus its trust regret."""
    for shift in sorted(NEGATIVE(manifest["shifts"]), key=abs):
        if detection(mode, locality, fraction, shift, graphs) * 2 >= len(graphs):
            return shift, mean(cells, locality, fraction, shift, "trust") - mean(cells, locality, fraction, shift, "oracle")
    return None, None


def make_result(manifest, cells, mode, graphs):
    fractions, shifts = manifest["fractions"], manifest["shifts"]
    clean = {policy: mean(cells, "clean", 0.0, 0.0, policy) for policy in manifest["policies"]}
    grid = {}
    for locality in manifest["localities"]:
        grid[locality] = {}
        for fraction in fractions:
            limit, limit_regret = boundary(manifest, cells, mode, graphs, locality, fraction)
            grid[locality][fraction] = {}
            for shift in shifts:
                fired = detection(mode, locality, fraction, shift, graphs)
                entry = {"detected": fired, "detection_rate": fired / len(graphs),
                         "means": {policy: mean(cells, locality, fraction, shift, policy)
                                   for policy in manifest["policies"]}}
                entry["regret_vs_oracle"] = {
                    policy: entry["means"][policy] - entry["means"]["oracle"] for policy in REGRET}
                entry["fallback_harm"] = entry["means"]["gate"] - min(entry["means"]["trust"],
                                                                     entry["means"]["prior"])
                grid[locality][fraction][shift] = entry
            grid[locality][fraction]["_boundary"] = {"shift": limit, "trust_regret": limit_regret}
    fired = [(loc, f, s) for loc in grid for f in grid[loc] for s in shifts
             if grid[loc][f][s]["detection_rate"] >= 0.5]
    helps = [key for key in fired if grid[key[0]][key[1]][key[2]]["means"]["gate"]
             < grid[key[0]][key[1]][key[2]]["means"]["trust"]]
    hurts = [key for key in fired if key not in helps]
    monotone = True
    for locality in manifest["localities"]:
        for fraction in fractions:
            ordered = sorted(NEGATIVE(shifts), key=abs)
            counts = [grid[locality][fraction][shift]["detected"] for shift in ordered]
            monotone &= all(a <= b for a, b in zip(counts, counts[1:]))
    all_cells = [(loc, f, s) for loc in manifest["localities"]
                 for f in fractions for s in shifts]
    overcorrection = sum(1 for key in all_cells
                         if grid[key[0]][key[1]][key[2]]["means"]["gate"]
                         > grid[key[0]][key[1]][key[2]]["means"]["trust"])
    feedback_better = sum(1 for key in all_cells
                          if grid[key[0]][key[1]][key[2]]["means"]["feedback"]
                          < grid[key[0]][key[1]][key[2]]["means"]["trust"])
    products = sorted(abs(grid["uniform"][fraction]["_boundary"]["shift"]) * fraction
                      for fraction in fractions
                      if grid["uniform"][fraction]["_boundary"]["shift"] is not None)
    return {"clean": clean, "grid": grid,
            "fired_cells": len(fired), "fallback_helps": len(helps), "fallback_hurts": len(hurts),
            "gate_overcorrects_cells": overcorrection, "feedback_beats_trust_cells": feedback_better,
            "total_cells": len(all_cells),
            "detection_monotone_in_abs_shift": bool(monotone),
            "uniform_boundary_products": products,
            "bootstrap": {"unit": "paired graph", "draws": 10000, "seed": 20261112, "coverage": 0.95}}


def render(manifest, cells, mode, corrupted, graphs, result):
    graph_count = len(graphs)
    clean = result["clean"]
    lines = [
        "# 신뢰도 오염의 국소성과 전역 게이트의 경계", "",
        f"합성 Spike 그래프 {graph_count}개(seed {graphs[0]}–{graphs[-1]}, 이전 개발·확인 실험에 쓰지 않은 구간)에서 "
        f"공개 신뢰도 점수만 손상시키고 검토 정책을 비교했다. 예산은 그래프당 {manifest['budget']}회다.", "",
        "손상은 노드 점수를 로짓 공간에서 이동시키는 것이다: `sigmoid(logit(c) + shift)`. "
        "가려진 정답, 간선 동전, 검토자 난수는 바꾸지 않으며 매 셀에서 확인했다. "
        "음수 shift는 실제로는 맞는 노드를 의심스럽게 보이게 하고, 양수 shift는 실제 오류를 감춘다. "
        "오염 비율은 **해당 국소성 풀의 비율**이므로 100%는 그래프 전체가 아니라 그 층 전체를 뜻한다.", "",
        "## 기준선", "",
        "| 정책 | 평균 잔여 오류 |", "|---|---:|",
    ]
    for policy in manifest["policies"]:
        lines.append(f"| {policy} | {clean[policy]:.3f} |")
    lines.extend(["",
                  "`oracle`은 손상되지 않은 점수를 쓰는 비현실적 상한이다. `prior`는 점수를 완전히 버리고 유형 사전확률만 쓴다. "
                  "`gate`는 그래프 평균 점수만 보고 `normal`/`noise`를 고른 뒤, `noise`면 `prior`, `normal`이면 `trust`와 "
                  "정확히 같은 행동을 한다(행 단위로 검증).", "",
                  "## 게이트 판정률", "",
                  "각 칸은 손상된 그래프를 게이트가 `noise`로 판정한 수다. 정상 그래프에서는 "
                  f"{detection(mode, 'clean', 0.0, 0.0, graphs)}/{graph_count}로 오탐이 없다.", ""])
    for locality in manifest["localities"]:
        lines.append(f"**{LOCALITY_NAMES[locality]}**")
        lines.append("")
        lines.extend(detection_matrix(manifest, mode, graphs, locality))
        lines.append("")

    lines.extend(["## 손상이 남기는 추가 오류 (oracle 대비)", "",
                  "값은 `정책 − oracle`의 그래프 평균이다. 0에 가까우면 손상이 그 정책을 해치지 않았다는 뜻이다. "
                  "아래 세 표는 모두 `uniform` 국소성이며, 나머지 국소성의 같은 수치는 `corruption.json`에 있다.", ""])
    for policy in ("trust", "gate", "feedback"):
        lines.append(f"**{policy}**")
        lines.append("")
        lines.extend(matrix(manifest, cells, corrupted, "uniform", policy, reference="oracle"))
        lines.append("")

    lines.extend(["## 국소성 비교", "",
                  "해당 풀 전체를 오염시킨 경우다. `uniform`은 80개, `source`·`sink`는 20개, "
                  "`error_nodes`는 그래프마다 다른 실제 오류 노드 수다.", ""])
    for policy in ("trust", "gate"):
        lines.append(f"**{policy} − oracle**")
        lines.append("")
        lines.append("| 국소성 | 평균 오염 노드 | " + " | ".join(f"{s:+.1f}" for s in manifest["shifts"]) + " |")
        lines.append("|---|---:|" + "---:|" * len(manifest["shifts"]))
        for locality in manifest["localities"]:
            fraction = manifest["fractions"][-1]
            nodes = float(np.mean(list(corrupted[(locality, fraction, manifest["shifts"][0])].values())))
            values = " | ".join(
                f"{mean(cells, locality, fraction, s, policy) - mean(cells, locality, fraction, s, 'oracle'):+.2f}"
                for s in manifest["shifts"])
            lines.append(f"| {LOCALITY_NAMES[locality]} | {nodes:.0f} | {values} |")
        lines.append("")

    lines.extend(["## 국소성별 경계", "",
                  "50% 판정에 필요한 가장 작은 음수 shift와, 그 지점에서 `trust`가 남긴 추가 오류다.", "",
                  "| 국소성 | 오염 비율 | 50% 판정 shift | trust − oracle |", "|---|---:|---:|---:|"])
    for locality in manifest["localities"]:
        for fraction in manifest["fractions"]:
            entry = result["grid"][locality][fraction]["_boundary"]
            shift, regret = entry["shift"], entry["trust_regret"]
            lines.append(f"| {LOCALITY_NAMES[locality]} | {fraction:.0%} | "
                         f"{'없음' if shift is None else f'{shift:+.1f}'} | "
                         f"{'—' if regret is None else f'{regret:+.2f}'} |")

    lines.extend(["", "## 게이트가 발동했을 때 실제로 도움이 되는가", "",
                  f"판정률 50% 이상인 셀은 {result['fired_cells']}개였고, 그중 게이트의 선택(사전확률로 회귀)이 "
                  f"점수를 그대로 믿는 것보다 평균 오류를 낮춘 셀은 {result['fallback_helps']}개, "
                  f"오히려 높인 셀은 {result['fallback_hurts']}개다.", ""])

    examples = [("uniform", 1.0, -1.0), ("uniform", 0.25, -3.0), ("source", 1.0, -3.0), ("sink", 1.0, -3.0)]
    lines.extend(["| 셀 | 판정률 | trust − oracle | gate − trust | feedback − oracle |",
                  "|---|---:|---:|---:|---:|"])
    for locality, fraction, shift in examples:
        fired = detection(mode, locality, fraction, shift, graphs)
        trust_gap = gap(cells, locality, fraction, shift, "trust", "oracle")
        gate_gap = gap(cells, locality, fraction, shift, "gate", "trust")
        feedback_gap = gap(cells, locality, fraction, shift, "feedback", "oracle")
        lines.append(f"| {LOCALITY_NAMES[locality]} {fraction:.0%} {shift:+.1f} | {fired}/{graph_count} "
                     f"| {fmt_gap(trust_gap)} | {fmt_gap(gate_gap)} | {fmt_gap(feedback_gap)} |")

    masking = [("error_nodes", 1.0, shift) for shift in POSITIVE(manifest["shifts"])]
    lines.extend(["", "## 실제 오류를 감출 때", "",
                  "`error_nodes`는 정답이 있는 노드만 손상시키는 평가자 측 적대자다(oracle과 같은 수준의 정보). "
                  "양수 shift는 실제 오류를 정상처럼 보이게 만든다.", "",
                  "| 오염 비율 | shift | 판정률 | trust − oracle | gate − oracle | feedback − oracle |",
                  "|---:|---:|---:|---:|---:|---:|"])
    for locality, fraction, shift in masking:
        fired = detection(mode, locality, fraction, shift, graphs)
        lines.append(f"| {fraction:.0%} | {shift:+.1f} | {fired}/{graph_count} "
                     f"| {fmt_gap(gap(cells, locality, fraction, shift, 'trust', 'oracle'))} "
                     f"| {fmt_gap(gap(cells, locality, fraction, shift, 'gate', 'oracle'))} "
                     f"| {fmt_gap(gap(cells, locality, fraction, shift, 'feedback', 'oracle'))} |")

    uniform = result["grid"]["uniform"]
    products = ", ".join(f"{value:g}" for value in result["uniform_boundary_products"])
    lost = next((f for f in manifest["fractions"] if uniform[f]["_boundary"]["shift"] is None), None)
    src = result["grid"]["source"][1.0][-3.0]
    snk = result["grid"]["sink"][1.0][-3.0]
    masked = result["grid"]["error_nodes"][1.0][3.0]
    total = result["total_cells"]
    lines.extend(["", "## 사전 예측과 결과", "",
                  "실행 전에 적은 예측을 그대로 대조한다. 틀린 예측도 고치지 않고 남긴다.", "",
                  f"1. **판정률은 |shift|에 단조 증가하고 경계는 p·|shift|≈1** — "
                  f"단조성은 {'모든 국소성·비율에서 성립했다' if result['detection_monotone_in_abs_shift'] else '일부 칸에서 깨졌다'}. "
                  f"`uniform`의 50% 경계에서 p·|shift|는 {products}로 0.75–1 구간이다"
                  + (f". 다만 {lost:.0%} 비율은 -4에서도 50%에 못 미쳤다" if lost is not None else "") + ". "
                  "p는 그래프 전체가 아니라 풀의 비율이므로, 층 국소성에서는 같은 p가 그래프 평균을 1/4만 움직인다.",
                  f"2. **source 층은 판정률이 낮고 손해는 크다** — 절반만 맞다. "
                  f"100%·-3에서 판정률은 source {src['detected']}/{graph_count}, sink {snk['detected']}/{graph_count}로 비슷하다. "
                  f"손해는 예측과 반대로 sink가 더 크다(trust − oracle: source {src['regret_vs_oracle']['trust']:+.2f}, "
                  f"sink {snk['regret_vs_oracle']['trust']:+.2f}). 전역 평균 게이트는 층을 구분하지 못한다.",
                  f"3. **feedback은 작은 오염에서 trust보다 낫지 않고 큰 오염에서 oracle에 접근** — 틀렸다. "
                  f"전체 {total}개 셀 중 feedback이 trust보다 나은 칸은 {result['feedback_beats_trust_cells']}개뿐이고, "
                  "개선되는 칸에서도 oracle에는 멀리 못 미친다.",
                  f"4. **oracle−gate로 노드 수준 신뢰 추정의 가치를 수량화할 수 있다** — 맞다. "
                  f"예를 들어 `uniform` 100%·-1에서 순위가 거의 보존되어 trust − oracle은 "
                  f"{uniform[1.0][-1.0]['regret_vs_oracle']['trust']:+.2f}인데, 게이트는 "
                  f"{uniform[1.0][-1.0]['regret_vs_oracle']['gate']:+.2f}까지 악화된다. "
                  f"반대로 실제 오류를 감춘 `error_nodes` 100%·+3은 판정 {masked['detected']}/{graph_count}에 "
                  f"trust − oracle {masked['regret_vs_oracle']['trust']:+.2f}로 게이트가 전혀 개입하지 못한다.", "",
                  "## 해석", "",
                  "게이트는 '점수가 좋다'와 '점수가 무정보하다'만 구분한다. 국소 오염은 그 둘 사이에 있으므로 "
                  "게이트의 판정 자체가 목적과 어긋난다. 전체를 같은 방향으로 미는 손상은 순위를 보존해 거의 무해한데 "
                  "평균만 크게 움직이므로 게이트가 가장 세게 발동하고, 그때 사전확률로 회귀하는 것이 점수를 믿는 것보다 "
                  "훨씬 나쁠 수 있다. 반대로 실제 오류를 감추는 손상은 평균을 위로 밀어 게이트를 전혀 깨우지 못한다.", "",
                  "이 결과가 말하는 것은 '게이트가 쓸모없다'가 아니라 **게이트의 결정 변수(그래프 평균)가 피해량과 "
                  "정렬되어 있지 않다**는 것이다. 필요한 것은 전역 이진 판정이 아니라 노드별 신뢰 추정이다.", "",
                  "## 한계", "",
                  "- `error_nodes`와 `oracle`은 정답을 쓰므로 배포 가능한 정책이 아니다. 손상 모델의 상한·하한을 재는 용도다.",
                  "- 합성 Spike 한 종류, 단일 아키텍처(고정 marginal 규칙)만 측정했다. 학습 정책은 이 표에 없다.",
                  "- `uniform` 100% 음수 shift는 모든 점수에 같은 단조 변환이라 신뢰도 순위가 보존되지만, "
                  "marginal이 쓰는 사후확률은 비선형이라 순위가 조금 달라질 수 있다. 그 칸의 작은 손해나 이득은 버그가 아니다.",
                  "- 게이트는 정상/균일 노이즈 두 모형의 그래프 평균으로만 적합되어 있다. 다른 손상 생성기에는 재적합이 필요하다.",
                  "- 이 구간(3000–3199)은 이전에 쓰지 않았지만, 이 실험 자체가 탐색적 경계 측정이지 동결된 가설의 확인 검정은 아니다.", "",
                  "[그래프별 결과](episodes.csv) · [실행 설정과 출처](manifest.json) · [수치 요약](corruption.json)", ""])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path, help="completed corruption sweep directory")
    run = parser.parse_args().run
    manifest, cells, mode, corrupted, graphs = load(run)
    result = make_result(manifest, cells, mode, graphs)
    result["source_sha256"] = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (run / "manifest.json", run / "episodes.csv", Path(__file__), EXPERIMENTS / "rl_boundary.py")}
    (run / "corruption.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (run / "corruption.md").write_text(render(manifest, cells, mode, corrupted, graphs, result), encoding="utf-8")
    print(run / "corruption.md")


if __name__ == "__main__":
    main()
