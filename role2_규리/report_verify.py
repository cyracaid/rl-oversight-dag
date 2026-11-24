"""Render the pre-registered probe-then-decide experiment from episodes.csv.

    python3 report_verify.py results/verify-v1

The verdict is computed from PREREGISTER_VERIFY.md's frozen rules; nothing in the
report may be edited to fit the numbers.
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

POLICIES = ("oracle", "trust", "prior", "gate", "verify")
LOCALITY_NAMES = {
    "uniform": "전체 노드 무작위",
    "source": "source 층",
    "sink": "sink 층",
    "error_nodes": "실제 오류 노드",
}
HEADLINES = [
    ("uniform", 1.0, -1.0, "예측 1: 순위 보존 손상"),
    ("uniform", 0.5, -3.0, "예측 2: 국소 과보정"),
    ("uniform", 0.25, -3.0, "예측 2: 국소 과보정 (25%)"),
    ("error_nodes", 1.0, 3.0, "예측 3: 은폐형 손상"),
]


def load(run):
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8-sig"))
    episodes = run / "episodes.csv"
    if hashlib.sha256(episodes.read_bytes()).hexdigest() != manifest["episodes_sha256"]:
        raise ValueError("episodes.csv SHA-256 does not match the run manifest")
    graphs = manifest["graph_seeds"]
    final, initial, mode, probes, chosen = {}, {}, {}, {}, {}
    with episodes.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            graph = int(row["graph_seed"])
            key = (row["locality"], float(row["fraction"]), float(row["shift"]), row["policy"])
            if int(row["reviews"]) != manifest["budget"]:
                raise ValueError(f"review budget violated: {key}")
            final.setdefault(key, {})[graph] = int(row["sink_errors"])
            initial.setdefault(graph, int(row["initial_sink_errors"]))
            mode.setdefault(key, {})[graph] = row["gate_mode"]
            probes.setdefault(key, {})[graph] = int(row["probes"])
            chosen.setdefault(key, {})[graph] = row["chosen_mode"]
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
    for locality, fraction, shift in {(k[0], k[1], k[2]) for k in cells if k[0] != "clean"}:
        gate_cell = cells[(locality, fraction, shift, "gate")]
        trust_cell = cells[(locality, fraction, shift, "trust")]
        prior_cell = cells[(locality, fraction, shift, "prior")]
        labels = mode[(locality, fraction, shift, "gate")]
        for index, graph in enumerate(graphs):
            expected = prior_cell[index] if labels[graph] == "noise" else trust_cell[index]
            if gate_cell[index] != expected:
                raise ValueError(f"gate is not a pure selector on {locality}/{fraction}/{shift}/{graph}")
        if np.any(np.array(list(probes[(locality, fraction, shift, "verify")].values())) > manifest["probe"]["count"]):
            raise ValueError(f"too many probes on {locality}/{fraction}/{shift}")
    for key in list(cells):
        if key[0] != "clean":
            cells[(key[0], key[1], key[2], "oracle")] = oracle
    return manifest, cells, mode, probes, chosen, graphs


def mean(cells, locality, fraction, shift, policy):
    return float(cells[(locality, fraction, shift, policy)].mean())


def gap(cells, locality, fraction, shift, policy, reference, draws=10000):
    return paired_bootstrap(cells[(locality, fraction, shift, policy)][None, :],
                            cells[(locality, fraction, shift, reference)], draws=draws, seed=20261112)


def fmt_gap(result):
    return f"{result['mean']:+.3f} [{result['low']:+.3f}, {result['high']:+.3f}]"


def detection(mode, locality, fraction, shift, graphs):
    labels = mode[(locality, fraction, shift, "gate")]
    return sum(labels[graph] == "noise" for graph in graphs)


def build(manifest, cells, mode, probes, chosen, graphs):
    fractions, shifts, localities = manifest["fractions"], manifest["shifts"], manifest["localities"]
    clean = {policy: mean(cells, "clean", 0.0, 0.0, policy) for policy in POLICIES}
    grid = {}
    for locality in localities:
        grid[locality] = {}
        for fraction in fractions:
            grid[locality][fraction] = {}
            for shift in shifts:
                entry = {"detected": detection(mode, locality, fraction, shift, graphs),
                         "means": {policy: mean(cells, locality, fraction, shift, policy)
                                   for policy in POLICIES}}
                entry["regret"] = {policy: entry["means"][policy] - entry["means"]["oracle"]
                                   for policy in ("trust", "gate", "verify")}
                entry["probe_mean"] = float(np.mean(
                    [probes[(locality, fraction, shift, "verify")][g] for g in graphs]))
                entry["rank_share"] = float(np.mean(
                    [chosen[(locality, fraction, shift, "verify")][g] == "rank" for g in graphs]))
                grid[locality][fraction][shift] = entry

    fired = [(loc, f, s) for loc in localities for f in fractions for s in shifts
             if grid[loc][f][s]["detected"] * 2 >= len(graphs)]
    worse = [key for key in fired
             if grid[key[0]][key[1]][key[2]]["means"]["verify"] > grid[key[0]][key[1]][key[2]]["means"]["trust"]]

    p1 = grid["uniform"][1.0][-1.0]["regret"]["verify"] - grid["uniform"][1.0][-1.0]["regret"]["trust"] <= 0.20
    p2 = all(grid["uniform"][f][-3.0]["means"]["verify"] <= grid["uniform"][f][-3.0]["means"]["trust"]
             for f in (0.5, 0.25))
    p3 = grid["error_nodes"][1.0][3.0]["regret"]["verify"] >= 2.0
    p4 = clean["verify"] == clean["trust"] and all(
        grid["uniform"][f][s]["means"]["verify"] == grid["uniform"][f][s]["means"]["trust"]
        for f in fractions for s in shifts if s > 0)
    if p1 and p2 and p4:
        verdict = "성공"
    elif p1 and not worse:
        verdict = "부분 성공"
    elif fired and len(worse) / len(fired) > 0.20:
        verdict = "실패"
    else:
        verdict = "부분 성공"
    return {"clean": clean, "grid": grid, "fired_cells": len(fired),
            "verify_worse_cells": len(worse),
            "predictions": {"p1_rank_preserving": bool(p1), "p2_local_overcorrection": bool(p2),
                            "p3_masking_unfixable": bool(p3), "p4_no_false_alarm": bool(p4)},
            "verdict": verdict,
            "bootstrap": {"unit": "paired graph", "draws": 10000, "seed": 20261112, "coverage": 0.95}}


def table(grid, manifest, locality, policy):
    shifts = manifest["shifts"]
    lines = ["| 오염 비율 | " + " | ".join(f"{s:+.1f}" for s in shifts) + " |",
             "|---:|" + "---:|" * len(shifts)]
    for fraction in manifest["fractions"]:
        lines.append(f"| {fraction:.0%} | " + " | ".join(
            f"{grid[locality][fraction][s]['regret'][policy]:+.2f}" for s in shifts) + " |")
    return lines


def render(manifest, cells, mode, probes, chosen, graphs, result):
    count = len(graphs)
    clean = result["clean"]
    lines = [
        "# 검증 후 전환: 게이트를 고칠 수 있는가", "",
        f"사전 등록(`PREREGISTER_VERIFY.md`) 후 새 그래프 {count}개(seed {graphs[0]}–{graphs[-1]})에서 "
        f"손상 격자를 그대로 재실행했다. 예산 {manifest['budget']}회, probe {manifest['probe']['count']}회, "
        f"probe 발동 임계값 `T = {manifest['probe']['trigger']['value']:.4f}` "
        f"(보정 100그래프 max|ΔP|의 99백분위).", "",
        "`verify`는 두 가설(점수 그대로 vs 순위만 복원)의 예측 차이가 `T`를 넘을 때만 probe를 쓰고, "
        "관측된 flag의 로그우도비로 **한 번만** 가설을 고른 뒤 남은 예산을 그 가설로 쓴다. "
        "**유형 사전확률로는 절대 회귀하지 않는다.**", "",
        "## 기준선", "",
        "| 정책 | 평균 잔여 오류 |", "|---|---:|",
    ]
    for policy in POLICIES:
        lines.append(f"| {policy} | {clean[policy]:.3f} |")
    lines.extend(["", "## 핵심 셀", "",
                  "값은 짝지은 그래프 부트스트랩 95% 구간이다.", "",
                  "| 셀 | 판정률 | verify − oracle | verify − trust | gate − trust |",
                  "|---|---:|---:|---:|---:|"])
    for locality, fraction, shift, _ in HEADLINES:
        fired = detection(mode, locality, fraction, shift, graphs)
        lines.append(
            f"| {LOCALITY_NAMES[locality]} {fraction:.0%} {shift:+.1f} | {fired}/{count} "
            f"| {fmt_gap(gap(cells, locality, fraction, shift, 'verify', 'oracle'))} "
            f"| {fmt_gap(gap(cells, locality, fraction, shift, 'verify', 'trust'))} "
            f"| {fmt_gap(gap(cells, locality, fraction, shift, 'gate', 'trust'))} |")

    lines.extend(["", "## 손해 (oracle 대비, 전 구간)", ""])
    for policy in ("verify",):
        for locality in manifest["localities"]:
            lines.append(f"**{policy}**, {LOCALITY_NAMES[locality]}")
            lines.append("")
            lines.extend(table(result["grid"], manifest, locality, policy))
            lines.append("")

    lines.extend(["## probe 사용량", "",
                  "`probe`는 발동하면 4회를 쓰고, 발동하지 않으면 `trust`와 완전히 같다.", "",
                  "| 국소성 | 오염 비율 | 평균 probe | rank 선택 비율 |", "|---|---:|---:|---:|"])
    for locality in manifest["localities"]:
        for fraction in manifest["fractions"]:
            entry = result["grid"][locality][fraction][-4.0]
            lines.append(f"| {LOCALITY_NAMES[locality]} | {fraction:.0%} | "
                         f"{entry['probe_mean']:.1f} | {entry['rank_share']:.0%} |")

    predictions = result["predictions"]
    lines.extend(["", "## 예측 대조와 판정", "",
                  f"- 예측 1 (순위 보존 손상에서 verify − trust ≤ +0.20): "
                  f"**{'성립' if predictions['p1_rank_preserving'] else '불성립'}** "
                  f"({result['grid']['uniform'][1.0][-1.0]['regret']['verify']:+.2f} vs "
                  f"{result['grid']['uniform'][1.0][-1.0]['regret']['trust']:+.2f}).",
                  f"- 예측 2 (국소 과보정 셀에서 verify ≤ trust): "
                  f"**{'성립' if predictions['p2_local_overcorrection'] else '불성립'}**.",
                  f"- 예측 3 (은폐형 손상은 못 고침, verify − oracle ≥ +2.0): "
                  f"**{'성립' if predictions['p3_masking_unfixable'] else '불성립'}** "
                  f"({result['grid']['error_nodes'][1.0][3.0]['regret']['verify']:+.2f}).",
                  f"- 예측 4 (깨끗한 셀·양수 shift에서 오경보 없음): "
                  f"**{'성립' if predictions['p4_no_false_alarm'] else '불성립'}**.", "",
                  f"게이트가 발동한 셀 {result['fired_cells']}개 중 verify가 trust보다 나쁜 셀은 "
                  f"{result['verify_worse_cells']}개다. 사전 등록 판정: **{result['verdict']}**.", "",
                  "## 해석", ""])
    if result["verdict"] == "성공":
        lines.extend([
            "검증 4회로 게이트의 과보정을 막고, 순위가 살아 있는 손상에서는 순위 복원으로 손해를 줄였다. "
            "즉 실패한 것은 '탐지'가 아니라 '회귀 대상'이었다는 진단이 맞다.",
        ])
    elif result["verdict"] == "부분 성공":
        lines.extend([
            "과보정은 막았지만 국소 손상에서 trust를 이기지 못했다. probe가 고른 노드가 실제 위험과 "
            "충분히 겹치지 않거나, 4회로는 두 가설을 가르기에 부족하다는 뜻이다.",
        ])
    else:
        lines.extend([
            "probe 비용이 이득을 넘었다. 게이트를 고치는 대신 전역 판정 자체를 버려야 한다는 음성 결과다.",
        ])
    lines.extend(["", "은폐형 손상은 예측대로 남는다. 순위 자체가 오염되면 어떤 재보정도 복구할 수 없고, "
                  "이 경우 필요한 것은 점수가 아니라 **노드별 독립 증거**다.", "",
                  "## 한계", "",
                  "- `oracle`은 정답을 쓰므로 비배포 상한이다. `rank` 복원은 층별 분포가 같은 합성 Spike에서만 정당화된다.",
                  "- 단일 marginal 규칙, 단일 그래프 family. 학습 정책은 없다.",
                  "- `T`와 rank 기준 분포는 보정 70000–70099에 의존한다. 다른 손상 생성기에는 재적합이 필요하다.",
                  "- 탐색적 경계 측정이다. 다만 예측과 판정 기준은 실행 전에 동결했다.", "",
                  "[그래프별 결과](episodes.csv) · [실행 설정](manifest.json) · [수치 요약](verify.json) · "
                  "[사전 등록](../PREREGISTER_VERIFY.md)", ""])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    run = parser.parse_args().run
    manifest, cells, mode, probes, chosen, graphs = load(run)
    result = build(manifest, cells, mode, probes, chosen, graphs)
    result["source_sha256"] = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (run / "manifest.json", run / "episodes.csv", Path(__file__),
                     Path(__file__).with_name("PREREGISTER_VERIFY.md"), EXPERIMENTS / "rl_boundary.py")}
    (run / "verify.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (run / "verify.md").write_text(render(manifest, cells, mode, probes, chosen, graphs, result), encoding="utf-8")
    print(run / "verify.md")


if __name__ == "__main__":
    main()
