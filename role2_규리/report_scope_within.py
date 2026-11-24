"""Report the paired within-layer delta experiment from its episode CSV."""

import argparse
import csv
import hashlib
import json
from itertools import product
from pathlib import Path

import numpy as np


POLICIES = ("trust", "shrink", "scope")
COMPARISONS = (("scope", "shrink"), ("scope", "trust"), ("shrink", "trust"))
LAYERS = {"source": "원천층", "sink": "결론층"}
SHIFT_PAIRS = ((-3, 3), (-4, 2), (-2, 4), (-4, -2), (2, 4))
CLEAN = ("clean", 0.0, 0, 0)
MIXED = [(layer, fraction, a, b) for layer, fraction, (a, b)
         in product(LAYERS, (0.5, 1.0), SHIFT_PAIRS)]
DRAWS = 10_000
BOOTSTRAP_SEED = 411


def read_episodes(run):
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    seeds = manifest["graph_seeds"]
    if (manifest["status"] != "complete" or seeds != list(range(4600, 4700))
            or manifest["budget"] != 16 or manifest["p_catch"] != 0.9
            or manifest["family"] != "spike" or manifest["nodes"] != 80 or manifest["sinks"] != 20):
        raise ValueError("Run settings or graph seeds differ from the registered design.")
    graph_index = {seed: index for index, seed in enumerate(seeds)}
    episode_file = run / "episodes.csv"
    if hashlib.sha256(episode_file.read_bytes()).hexdigest() != manifest["episodes_sha256"]:
        raise ValueError("episodes.csv does not match the manifest hash.")

    shape = (len(seeds), len(POLICIES))
    data = {cell: np.full(shape, -1, dtype=int) for cell in [CLEAN, *MIXED]}
    initial_by_seed = {}
    with episode_file.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            seed = int(row["graph_seed"])
            index = graph_index[seed]
            policy = POLICIES.index(row["policy"])
            cell = (row["layer"], float(row["fraction"]), float(row["shift_a"]),
                    float(row["shift_b"]))
            counts = data[cell]
            if counts[index, policy] != -1:
                raise ValueError(f"Duplicate result for {seed}, {cell}, {row['policy']}.")
            if row["cell"] != ("clean" if cell == CLEAN else "within"):
                raise ValueError(f"Cell label disagrees with its factors: {cell}.")
            # Each layer contains 20 nodes. Two groups receive half the selected nodes each.
            per_group = int(10 * cell[1])
            if int(row["changed_a"]) != per_group or int(row["changed_b"]) != per_group:
                raise ValueError(f"Unequal or incomplete delta assignment for {seed}, {cell}.")
            episode = int(row["episode_seed"])
            initial = int(row["initial_sink_errors"])
            final = int(row["sink_errors"])
            if (int(row["reviews"]) != manifest["budget"] or episode != seed + 20000
                    or initial_by_seed.setdefault(seed, initial) != initial
                    or not 0 <= final <= initial <= 20):
                raise ValueError(f"Invalid review budget, episode or sink count for {seed}, {cell}.")
            counts[index, policy] = final
    for cell, counts in data.items():
        if (counts < 0).any():
            raise ValueError(f"Incomplete graph/policy pairs for {cell}.")
    return manifest, data


def summarize(cells, sample_indices):
    # Sum over conditions within each graph before resampling that graph as one unit.
    totals = np.sum(cells, axis=0)
    means = totals.mean(axis=0) / len(cells)
    result = {"means": dict(zip(POLICIES, means.tolist())), "differences": {}}
    for policy, reference in COMPARISONS:
        differences = totals[:, POLICIES.index(policy)] - totals[:, POLICIES.index(reference)]
        samples = differences[sample_indices].mean(axis=1) / len(cells)
        low, high = np.quantile(samples, [0.025, 0.975])
        result["differences"][f"{policy}-{reference}"] = {
            "mean": float(differences.mean() / len(cells)), "low": float(low), "high": float(high),
        }
    return result


def analyze(manifest, data):
    count = len(manifest["graph_seeds"])
    samples = np.random.default_rng(BOOTSTRAP_SEED).integers(count, size=(DRAWS, count))
    aggregate = summarize([data[cell] for cell in MIXED], samples)
    primary = aggregate["differences"]["scope-shrink"]
    if primary["high"] < 0:
        verdict = "scope_lower"
    elif primary["low"] > 0:
        verdict = "shrink_lower"
    else:
        verdict = "inconclusive"
    table = []
    for layer, fraction, a, b in MIXED:
        table.append({"layer": layer, "fraction": fraction, "shift_a": a, "shift_b": b,
                      **summarize([data[(layer, fraction, a, b)]], samples)})
    return {
        "graphs": count, "first_seed": manifest["graph_seeds"][0],
        "last_seed": manifest["graph_seeds"][-1], "budget": manifest["budget"],
        "episodes_sha256": manifest["episodes_sha256"],
        "bootstrap": {"unit": "graph", "draws": DRAWS, "seed": BOOTSTRAP_SEED,
                      "interval": "95% percentile", "mixed_cell_weight": 1 / len(MIXED)},
        "verdict": verdict, "mixed": aggregate, "cells": table,
        "clean": summarize([data[CLEAN]], samples),
    }


def interval(stats, digits=3):
    return (f"{stats['mean']:+.{digits}f} "
            f"[{stats['low']:+.{digits}f}, {stats['high']:+.{digits}f}]")


def render(result):
    conclusion = {
        "scope_lower": "그래프별로 보정한 scope가 평균적으로 결론 오류를 더 적게 남겼다.",
        "shrink_lower": "노드별로 보정한 shrink가 평균적으로 결론 오류를 더 적게 남겼다.",
        "inconclusive": "신뢰구간이 0을 포함해 두 보정법 중 어느 쪽이 평균적으로 앞서는지 판단하기 어렵다.",
    }[result["verdict"]]
    primary = result["mixed"]["differences"]["scope-shrink"]
    lines = [
        "# 한 층 안에 두 가지 신뢰도 이동량을 섞었을 때", "",
        f"20개 혼합 조건에서 그래프당 잔여 결론 오류의 평균 차이(scope − shrink)는 "
        f"**{primary['mean']:+.4f}개**였다(짝지은 95% 구간 {primary['low']:+.4f}~{primary['high']:+.4f}). "
        + conclusion, "",
        f"합성 Spike 그래프 {result['graphs']}개(시드 {result['first_seed']}–{result['last_seed']})에 "
        f"검토 예산 {result['budget']}회를 적용했다. 각 그래프에서 원천층과 결론층을 차례로 시험했다. "
        "그 층의 20개 노드 중 절반 또는 전체를 두 집단에 균등 배정했다. "
        "두 집단의 공개 신뢰도에 로그 오즈 단위로 서로 다른 δ를 더했다. "
        "각 그래프의 실제 오류, 전파 결과, 검토자 난수는 모든 정책과 조건이 공유한다.", "",
        "trust는 주어진 신뢰도 점수를 사용한다. shrink는 노드별로 점수 이동 가능성을 추정하고, "
        "scope는 이동한 노드들이 하나의 δ를 공유한다고 가정한다. 세 정책 모두 이 점수로 "
        "같은 하류 영향 규칙을 적용한다.", "",
        "## 전체 평균과 정상 신호 대조", "",
        "각 정책 열의 값은 검토 후 결론 노드 20개에 남은 평균 오류 수다. 차이가 음수이면 "
        "앞 정책에 남은 오류가 적다. 대괄호는 짝지은 95% 구간이다.", "",
        "| 조건 | trust | shrink | scope | scope − shrink | scope − trust | shrink − trust |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for label, stats in (("혼합 20조건 평균", result["mixed"]), ("정상 신호", result["clean"])):
        values = [f"{stats['means'][p]:.4f}" for p in POLICIES]
        values += [interval(stats["differences"][f"{a}-{b}"], 4) for a, b in COMPARISONS]
        lines.append("| " + " | ".join([label] + values) + " |")
    lines += [
        "", "각 그래프에서 20조건의 정책 차이를 같은 비중으로 평균 냈다. 그래프를 복원추출해 "
        "그 평균의 95% 백분위 구간을 구했다(10,000회, 시드 411). 혼합 조건의 scope − shrink를 "
        "주 비교로 사용했고, trust 대비 차이와 정상 신호 결과를 함께 표시했다.", "",
        "## 층과 이동량에 따른 차이", "",
        "비율은 해당 층에서 이동시킨 노드의 비율이다. 50%에서는 5개씩, 100%에서는 "
        "10개씩 δ₁과 δ₂를 적용했다. 아래 20개 구간은 조건별 탐색 결과이며 다중 비교 보정을 적용하지 않았다.", "",
        "| 층 | 비율 | δ₁ | δ₂ | trust | shrink | scope | scope − shrink [95% 구간] |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["cells"]:
        means = row["means"]
        lines.append(f"| {LAYERS[row['layer']]} | {row['fraction']:.0%} | {row['shift_a']:+d} | "
                     f"{row['shift_b']:+d} | {means['trust']:.2f} | {means['shrink']:.2f} | "
                     f"{means['scope']:.2f} | {interval(row['differences']['scope-shrink'])} |")
    extremes = sorted(result["cells"], key=lambda row: row["differences"]["scope-shrink"]["mean"])
    descriptions = []
    for row in (extremes[0], extremes[-1]):
        diff = row["differences"]["scope-shrink"]["mean"]
        descriptions.append(f"{LAYERS[row['layer']]} {row['fraction']:.0%}에서 "
                            f"({row['shift_a']:+d}, {row['shift_b']:+d})일 때 {diff:+.3f}개")
    lines += ["", "20조건에서 scope − shrink의 최솟값과 최댓값을 보인 예는 각각 "
              + ", ".join(descriptions) + "였다.", "",
              "이 측정의 적용 범위는 Spike의 두 층, 지정한 다섯 δ 조합, 검토 적중률 90%다. "
              "20조건 평균은 이 격자에 같은 비중을 준 값이며, 실제 자료에서의 발생 빈도는 별도 측정이 필요하다.",
              "", "[사전 계획](../../PREREGISTER_SCOPE_WITHIN.md) · [그래프별 원자료](episodes.csv) · "
              "[실행 설정](manifest.json) · [전체 차이와 구간](summary.json)", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path, help="directory with episodes.csv and manifest.json")
    run = parser.parse_args().run
    manifest, data = read_episodes(run)
    result = analyze(manifest, data)
    (run / "summary.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    (run / "report.md").write_text(render(result), encoding="utf-8")
    print(run / "report.md")


if __name__ == "__main__":
    main()
