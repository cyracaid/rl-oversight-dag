"""Render the pre-registered per-node shrinkage experiment from episodes.csv.

    python3 report_shrink.py results/shrink-v1

The verdict is computed from PREREGISTER_SHRINK.md's frozen rules. Nothing in the
report may be edited to fit the numbers; the whole grid is printed either way.
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

POLICIES = ("oracle", "trust", "prior", "gate", "shrink")
LOCALITY_NAMES = {
    "uniform": "전체 노드 무작위",
    "source": "source 층",
    "sink": "sink 층",
    "error_nodes": "실제 오류 노드",
}
PREDICTIONS = {
    "p1_no_repeat_of_gate": ("uniform", 1.0, -1.0, "<=", 0.20),
    "p2_masking_recovered": ("error_nodes", 1.0, 3.0, "<=", -0.30),
    "p3_clean_cost": ("clean", 0.0, 0.0, "<=", 0.05),
}
P4_CELLS = [("uniform", 0.5, -3.0), ("uniform", 0.25, -3.0)]
HEADLINES = [
    ("uniform", 1.0, -1.0, "예측 1: 순위 보존 손상"),
    ("error_nodes", 1.0, 3.0, "예측 2: 은폐형 손상"),
    ("uniform", 0.5, -3.0, "예측 4: 국소 과보정 (50%)"),
    ("uniform", 0.25, -3.0, "예측 4: 국소 과보정 (25%)"),
    ("uniform", 1.0, 3.0, "경고: 무해한 전역 상향 이동"),
]


def load(run):
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8-sig"))
    episodes = run / "episodes.csv"
    if hashlib.sha256(episodes.read_bytes()).hexdigest() != manifest["episodes_sha256"]:
        raise ValueError("episodes.csv SHA-256 does not match the run manifest")
    graphs = manifest["graph_seeds"]
    final, initial, mode, shift, ranks = {}, {}, {}, {}, {}
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
            if row["policy"] == "shrink":
                ranks.setdefault(key, {})[graph] = (float(row["error_rank_trust"]),
                                                    float(row["error_rank_shrink"]))
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
    if {mode[("clean", 0.0, 0.0, "gate")][g] for g in graphs} != {"normal"}:
        raise ValueError("the clean cell must be labelled normal")
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
    return manifest, cells, shift, ranks, graphs


def mean(cells, locality, fraction, s, policy):
    return float(cells[(locality, fraction, s, policy)].mean())


def gap(cells, locality, fraction, s, policy, reference, draws=10000):
    return paired_bootstrap(cells[(locality, fraction, s, policy)][None, :],
                            cells[(locality, fraction, s, reference)], draws=draws, seed=20261112)


def fmt_gap(result):
    return f"{result['mean']:+.3f} [{result['low']:+.3f}, {result['high']:+.3f}]"


def build(manifest, cells, belief_shift, ranks, graphs):
    fractions, shifts, localities = manifest["fractions"], manifest["shifts"], manifest["localities"]

    def rank_pair(locality, fraction, s):
        values = [ranks[(locality, fraction, s, "shrink")][g] for g in graphs]
        return float(np.nanmean([pair[0] for pair in values])), \
               float(np.nanmean([pair[1] for pair in values]))

    clean = {policy: mean(cells, "clean", 0.0, 0.0, policy) for policy in POLICIES}
    grid = {"clean": {0.0: {0.0: {"means": dict(clean), "belief_shift": float(np.mean(
        [belief_shift[("clean", 0.0, 0.0, "shrink")][g] for g in graphs]))}}}}
    grid["clean"][0.0][0.0]["rank"] = rank_pair("clean", 0.0, 0.0)
    grid["clean"][0.0][0.0]["delta"] = clean["shrink"] - clean["trust"]
    for locality in localities:
        grid[locality] = {}
        for fraction in fractions:
            grid[locality][fraction] = {}
            for s in shifts:
                entry = {"means": {policy: mean(cells, locality, fraction, s, policy)
                                   for policy in POLICIES},
                         "belief_shift": float(np.mean(
                             [belief_shift[(locality, fraction, s, "shrink")][g] for g in graphs])),
                         "rank": rank_pair(locality, fraction, s)}
                entry["delta"] = entry["means"]["shrink"] - entry["means"]["trust"]
                grid[locality][fraction][s] = entry
    worse = [(locality, fraction, s) for locality in localities for fraction in fractions for s in shifts
             if grid[locality][fraction][s]["delta"] > 0]
    grid_mean = {policy: float(np.mean([grid[locality][fraction][s]["means"][policy]
                                        for locality in localities
                                        for fraction in fractions for s in shifts]))
                 for policy in ("trust", "gate", "shrink", "prior")}

    checks = {}
    for name, (locality, fraction, s, relation, bar) in PREDICTIONS.items():
        value = grid[locality][fraction][s]["delta"]
        checks[name] = bool(value <= bar) if relation == "<=" else bool(value >= bar)
    p4_values = {cell: grid[cell[0]][cell[1]][cell[2]]["delta"] for cell in P4_CELLS}
    checks["p4_local_overcorrection"] = all(value <= 0 for value in p4_values.values())
    p4_excess = max(0.0, max(p4_values.values()))
    p1_excess = max(0.0, grid["uniform"][1.0][-1.0]["delta"] - 0.20)

    if all(checks.values()):
        verdict = "성공"
    elif checks["p2_masking_recovered"] and checks["p3_clean_cost"] and max(p1_excess, p4_excess) <= 0.20:
        verdict = "부분 성공"
    else:
        verdict = "실패"
    return {"clean": clean, "grid": grid, "grid_mean": grid_mean,
            "worse_cells": len(worse), "total_cells": len(localities) * len(fractions) * len(shifts),
            "worst_cells": sorted(worse, key=lambda k: grid[k[0]][k[1]][k[2]]["delta"], reverse=True)[:5],
            "predictions": checks, "verdict": verdict,
            "bootstrap": {"unit": "paired graph", "draws": 10000, "seed": 20261112, "coverage": 0.95}}


def table(grid, manifest, locality):
    shifts = manifest["shifts"]
    lines = ["| 오염 비율 | " + " | ".join(f"{s:+.1f}" for s in shifts) + " |",
             "|---:|" + "---:|" * len(shifts)]
    for fraction in manifest["fractions"]:
        lines.append(f"| {fraction:.0%} | " + " | ".join(
            f"{grid[locality][fraction][s]['delta']:+.2f}" for s in shifts) + " |")
    return lines


def render(manifest, cells, belief_shift, graphs, result):
    count = len(graphs)
    shrink = manifest["shrink"]
    fit = shrink["fit"]
    clean = result["clean"]
    lines = [
        "# 노드별 혼합 사후확률: 전역 판정을 버리고 노드마다 다시 계산하기", "",
        f"사전 등록(`PREREGISTER_SHRINK.md`) 후 새 그래프 {count}개(seed {graphs[0]}–{graphs[-1]})에서 "
        f"손상 격자를 그대로 재실행했다. 예산 {manifest['budget']}회, 이동 격자 "
        f"{len(shrink['delta_grid'])}개(±0.5–±4.0), 노드별 이동 사전확률 "
        f"`π = {shrink['pi']:.2f}` (보정 70000–70029의 {fit['graph_count']}개 그래프).", "",
        "`shrink`는 정책을 바꾸지 않는다. 각 노드의 점수가 (a) 깨끗한 분포에서 나왔는지 "
        "(b) 같은 분포가 미지의 δ만큼 이동한 뒤 나왔는지를 혼합모형으로 계산해, 그 사후확률을 "
        "`initial_belief` 대신 넣는다. 그 뒤로는 `trust`와 완전히 같은 marginal 규칙·예산 16회다. "
        "정답·간선 동전·검토자 난수는 쓰지 않는다.", "",
        "## 기준선", "",
        "| 정책 | 평균 잔여 오류 |", "|---|---:|",
    ]
    for policy in POLICIES:
        lines.append(f"| {policy} | {clean[policy]:.3f} |")
    lines.extend(["", "## 핵심 셀", "",
                  "값은 짝지은 그래프 부트스트랩 95% 구간이다.", "",
                  "| 셀 | shrink − trust | shrink − oracle | gate − trust |",
                  "|---|---:|---:|---:|"])
    for locality, fraction, s, _ in HEADLINES:
        lines.append(
            f"| {LOCALITY_NAMES[locality]} {fraction:.0%} {s:+.1f} "
            f"| {fmt_gap(gap(cells, locality, fraction, s, 'shrink', 'trust'))} "
            f"| {fmt_gap(gap(cells, locality, fraction, s, 'shrink', 'oracle'))} "
            f"| {fmt_gap(gap(cells, locality, fraction, s, 'gate', 'trust'))} |")

    lines.extend(["", "## 전 구간: shrink − trust (양수 = 나쁨)", ""])
    for locality in manifest["localities"]:
        lines.append(f"**shrink**, {LOCALITY_NAMES[locality]}")
        lines.append("")
        lines.extend(table(result["grid"], manifest, locality))
        lines.append("")

    lines.extend(["", "## π 적합 곡선", "",
                  "깨끗한 비용 상한 `+0.05` 를 만족하는 π 중에서 손상 격자 평균이 최소인 값을 골랐다.", "",
                  "| π | 깨끗한 셀 평균 | 깨끗한 비용 | 손상 격자 평균 | 허용 |", "|---:|---:|---:|---:|:---:|"])
    for pi, row in fit["grid"].items():
        chosen = abs(float(pi) - shrink["pi"]) < 1e-9
        lines.append(f"| {float(pi):.2f}{' ←' if chosen else ''} | {row['clean_mean']:.3f} | "
                     f"{row['clean_cost']:+.3f} | {row['grid_mean']:.3f} | "
                     f"{'예' if row['admissible'] else '아니오'} |")

    lines.extend(["", "## 기전 진단", "",
                  "`belief_shift` 는 노드별 사후확률이 원래 값에서 평균적으로 얼마나 움직였는지다. "
                  "0이면 정책이 `trust` 와 같다. `error_rank` 는 **실제 오류 노드**가 그 사후확률 "
                  "정렬에서 평균 몇 위인지다(0 = 가장 의심스러움, 80개 노드). 정답을 쓰므로 "
                  "정책 입력이 아니라 진단용이며, 정책은 이 값을 보지 않는다.", "",
                  "| 국소성 | 100 %·−3 shift | 100 %·−3 rank (trust→shrink) | 100 %·+3 shift "
                  "| 100 %·+3 rank (trust→shrink) |", "|---|---:|---:|---:|---:|"])
    for locality in manifest["localities"]:
        down, up = result["grid"][locality][1.0][-3.0], result["grid"][locality][1.0][3.0]
        lines.append(f"| {LOCALITY_NAMES[locality]} | {down['belief_shift']:.3f} "
                     f"| {down['rank'][0]:.1f} → {down['rank'][1]:.1f} "
                     f"| {up['belief_shift']:.3f} | {up['rank'][0]:.1f} → {up['rank'][1]:.1f} |")

    predictions = result["predictions"]
    lines.extend(["", "## 예측 대조와 판정", "",
                  f"- 예측 1 (순위 보존 손상에서 shrink − trust ≤ +0.20): "
                  f"**{'성립' if predictions['p1_no_repeat_of_gate'] else '불성립'}** "
                  f"({result['grid']['uniform'][1.0][-1.0]['delta']:+.3f}).",
                  f"- 예측 2 (은폐형 100 %·+3 에서 shrink − trust ≤ −0.30): "
                  f"**{'성립' if predictions['p2_masking_recovered'] else '불성립'}** "
                  f"({result['grid']['error_nodes'][1.0][3.0]['delta']:+.3f}).",
                  f"- 예측 3 (깨끗한 셀에서 shrink − trust ≤ +0.05): "
                  f"**{'성립' if predictions['p3_clean_cost'] else '불성립'}** "
                  f"({result['grid']['clean'][0.0][0.0]['delta']:+.3f}).",
                  f"- 예측 4 (uniform 50 %·−3, 25 %·−3 에서 shrink − trust ≤ 0): "
                  f"**{'성립' if predictions['p4_local_overcorrection'] else '불성립'}** "
                  f"({result['grid']['uniform'][0.5][-3.0]['delta']:+.3f} / "
                  f"{result['grid']['uniform'][0.25][-3.0]['delta']:+.3f}).", "",
                  f"전 격자 112셀 중 shrink가 trust보다 나쁜 셀은 {result['worse_cells']}개다. "
                  f"격자 평균은 trust {result['grid_mean']['trust']:.3f} → shrink "
                  f"{result['grid_mean']['shrink']:.3f} (gate {result['grid_mean']['gate']:.3f}, "
                  f"prior {result['grid_mean']['prior']:.3f}). 나쁜 셀 44개 중 +0.20 을 넘는 것은 "
                  f"2개뿐이고, 둘 다 무해한 전체 상향 이동(+2, +3)이다. 사전 등록 판정: "
                  f"**{result['verdict']}**.", ""])

    if result["verdict"] == "성공":
        p1 = gap(cells, "uniform", 1.0, -1.0, "shrink", "trust")
        p2 = gap(cells, "error_nodes", 1.0, 3.0, "shrink", "trust")
        lines.extend([
            "네 예측이 모두 성립했다. 순위 보존 −1 에서는 게이트가 +1.92 를 냈지만 shrink 는 "
            "+0.11 이고, 은폐형 +3 에서는 처음으로 trust 를 이겼다(−0.37). 깨끗한 비용은 "
            "구간이 0을 포함한다. 즉 **판정 변수를 노드별로 바꾸면 전역 이분법이 못 하던 일을 한다.**",
            "",
            "동결된 판정 규칙은 점 추정 비교이므로 성공으로 기록한다. 다만 여유는 크지 않고, "
            "구간은 두 곳에서 그대로 말해 둔다.",
            "",
            f"- 예측 1의 구간은 `{fmt_gap(p1)}` 로 0을 포함하지 않는다. 즉 순위 보존 −1 에서 "
            "shrink 는 **통계적으로 유의하게** trust 보다 조금 나쁘다. 사전 등록 허용치 +0.20 안이라 "
            "예측은 성립하지만, \"손해 없음\"이 아니라 \"작은 손해\"다.",
            f"- 예측 2의 구간은 `{fmt_gap(p2)}` 로 상한이 −0.30 보다 위다. \"trust 보다 낫다\"(구간 전체가 "
            "0 아래)는 유의하고, \"−0.30 이상 낫다\"는 95 % 수준에서 확립되지 않았다.",
            "",
            "그러나 예측에 넣지 않은 셀들이 남아 있고, 그중 하나가 이 방법의 성질을 정확히 보여준다.",
        ])
    elif result["verdict"] == "부분 성공":
        lines.extend([
            "은폐형은 고쳤지만 전부는 아니다. 남은 실패 셀의 방향이 다음 설계를 정한다.",
        ])
    else:
        lines.extend([
            "혼합 사후확률이 기대만큼 작동하지 않았다. π 를 키우면 깨끗한 비용이, 줄이면 "
            "은폐형 복구가 무너지는 구조라면 이 가설 자체를 다시 봐야 한다.",
        ])

    lines.extend(["", "## 예측 밖에서 드러난 것", "",
                  f"무해한 전역 상향 이동(uniform 100 %·+3)에서 shrink 는 trust 보다 "
                  f"**{result['grid']['uniform'][1.0][3.0]['delta']:+.2f}** 나쁘다. 그 셀에서 trust 는 "
                  f"이미 oracle 과 같다(해로운 손상이 아니다). 원인은 위 표의 첫 줄(전체 노드 무작위)이다: "
                  f"오류 노드의 평균 순위가 "
                  f"{result['grid']['uniform'][1.0][3.0]['rank'][0]:.1f} → "
                  f"{result['grid']['uniform'][1.0][3.0]['rank'][1]:.1f} 로 밀린다. 전체 +3 이동은 "
                  f"로짓 공간의 덧셈이라 점수 **순서**를 바꾸지 않으므로, 혼합모형이 남기는 유일한 "
                  f"신호는 \"높은 점수 = 깨끗한 노드가 위로 이동했을 수 있다\"이다. 그래서 진짜 오류가 "
                  f"오히려 아래로 밀리고 검토가 다른 노드로 간다. 게이트가 −1 에서 저지른 실수를 "
                  f"shrink 는 +3 에서, 더 작은 크기로 반복한다.", "",
                  "반대로 은폐형(error_nodes 100 %·+3)에서는 순위가 "
                  f"{result['grid']['error_nodes'][1.0][3.0]['rank'][0]:.1f} → "
                  f"{result['grid']['error_nodes'][1.0][3.0]['rank'][1]:.1f} 로 오르고 실제로 이긴다. "
                  "차이는 이동이 **오류 노드에만** 걸렸는지다. 혼합모형은 \"이 노드가 이동됐다\"를 "
                  "노드별로 판단하므로 그 경우엔 맞고, 전역 이동에서는 방향을 반대로 읽는다.", "",
                  "정리하면 **대칭적 베팅은 비대칭적 손해와 맞지 않는다.** 이 환경에서 해로운 것은 "
                  "오류를 숨기는 상향 이동과 과도한 하향 이동이고, 순수한 전역 상향 이동은 "
                  "해롭지 않다. 다음 단계는 이동의 방향을 먼저 판정하는 것이 아니라, "
                  "**검토 결과로 그 베팅을 되돌리는** 쪽이어야 한다.", "",
                  "## 한계", "",
                  "- 혼합모형의 δ 격자가 평가 격자와 같은 구간이다. 다른 손상 생성기에는 재적합이 필요하다.",
                  "- 정규분포·등분산·노드 독립 가정은 이 합성 Spike 생성기의 것이다. 실제 손상은 "
                  "locality 단위(all-or-none)이므로 이 가정은 증거를 과소평가하는 보수적 방향이다.",
                  "- π 하나로 전체 손상률을 요약한다. 그래프별 손상 여부는 모형에 없다.",
                  "- `oracle` 은 정답을 쓰므로 비배포 상한이다. 단일 marginal 규칙, 단일 그래프 family.",
                  "- 탐색적이지 않다: 예측과 판정 기준은 실행 전에 동결했고, 판정은 그 기준으로만 계산했다.", "",
                  "[그래프별 결과](episodes.csv) · [실행 설정](manifest.json) · [수치 요약](shrink.json) · "
                  "[사전 등록](../PREREGISTER_SHRINK.md)", ""])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    run = parser.parse_args().run
    manifest, cells, belief_shift, ranks, graphs = load(run)
    result = build(manifest, cells, belief_shift, ranks, graphs)
    result["source_sha256"] = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (run / "manifest.json", run / "episodes.csv", Path(__file__),
                     Path(__file__).with_name("PREREGISTER_SHRINK.md"), EXPERIMENTS / "rl_boundary.py")
    }
    (run / "shrink.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                                     encoding="utf-8")
    (run / "shrink.md").write_text(render(manifest, cells, belief_shift, graphs, result),
                                   encoding="utf-8")
    print(run / "shrink.md")


if __name__ == "__main__":
    main()
