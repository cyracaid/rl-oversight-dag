"""Validate paired public-belief planning runs and report graph-level effects."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from report_conditions import format_gap, paired_bootstrap


CONDITIONS = {"shuffled": "유형 내 신뢰도 순열", "matched": "정상 신뢰도", "uniform": "균등 잡음"}
POLICIES = {"hard": "단일 모형 한 단계", "mixture": "혼합 한 단계",
            "open_loop": "고정 후속 검토", "adaptive": "조건부 후속 검토"}
CONTRASTS = (("adaptive", "mixture"), ("adaptive", "open_loop"),
             ("mixture", "hard"), ("adaptive", "hard"))
DECISION_COUNTS = ("planning_steps", "greedy_disagreements", "loop_disagreements", "branch_disagreements")


def csv_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def read_run(run):
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8-sig"))
    graphs, episodes = manifest["graph_seeds"], manifest["episode_seeds"]
    budget = manifest["budget"]
    protocol = manifest["protocol"]
    if (manifest["status"] != "complete" or manifest["family"] != "spike"
            or manifest["nodes"] != 80 or budget != 16 or manifest["p_catch"] != 0.9
            or manifest["particles"] != 0
            or protocol["width"] != 6 or protocol["horizon"] != 2
            or sorted(manifest["conditions"]) != sorted(CONDITIONS)
            or sorted(manifest["policies"]) != sorted(POLICIES)
            or not graphs or len(set(graphs)) != len(graphs)
            or episodes != [g + 20000 for g in graphs]):
        raise ValueError("Incomplete run or unexpected planning study configuration")
    for name in ("episodes", "trace"):
        digest = hashlib.sha256((run / f"{name}.csv").read_bytes()).hexdigest()
        if digest != manifest[f"{name}_sha256"]:
            raise ValueError(f"{name}.csv does not match its manifest digest")

    cells = {(cond, policy): {} for cond in CONDITIONS for policy in POLICIES}
    initial_by_graph = {}
    episode_for = dict(zip(graphs, episodes))
    for row in csv_rows(run / "episodes.csv"):
        condition, policy = row["condition"], row["policy"]
        cell = cells[condition, policy]
        graph = int(row["graph_seed"])
        initial, final, flags, reviews = (
            int(row[field]) for field in ("initial_sink_errors", "sink_errors", "flags", "reviews"))
        steps, greedy, loop, branch = (int(row[field]) for field in DECISION_COUNTS)
        expected_steps = budget - 1 if policy in ("adaptive", "open_loop") else 0
        if (graph in cell or episode_for.get(graph) != int(row["episode_seed"])
                or initial_by_graph.setdefault(graph, initial) != initial
                or not 0 <= final <= initial or not 0 <= flags <= reviews or reviews != budget
                or expected_steps != steps or any(not 0 <= k <= steps for k in (greedy, loop, branch))):
            raise ValueError(f"Invalid or unpaired trajectory for {condition}/{policy}/{graph}")
        cell[graph] = (final, flags, steps, greedy, loop, branch)
    if any(len(cell) != len(graphs) for cell in cells.values()):
        raise ValueError("Missing graph-policy-condition pairs")

    traces = {cond: [] for cond in CONDITIONS}
    for row in csv_rows(run / "trace.csv"):
        if (row["policy"] != "adaptive" or int(row["graph_seed"]) != graphs[0]
                or int(row["episode_seed"]) != episodes[0]):
            raise ValueError("Expected an adaptive trace of the first evaluation graph")
        traces[row["condition"]].append(row)
    for cond, trace in traces.items():
        trace.sort(key=lambda row: int(row["step"]))
        steps = [int(row["step"]) for row in trace]
        actions = [int(row["action"]) for row in trace]
        if (steps != list(range(1, budget + 1)) or len(set(actions)) != budget
                or any(not 0 <= a < manifest["nodes"] for a in actions)):
            raise ValueError(f"Invalid or incomplete action sequence in {cond} trace")
        counts = np.zeros(3, dtype=int)
        flags = 0
        for i, row in enumerate(trace):
            flag, miss, greedy, fixed = (int(row[field]) for field in
                                         ("flag_next", "miss_next", "greedy_action", "open_loop_action"))
            observed = int(row["flagged"])
            if observed not in (0, 1) or not 0 <= float(row["flag_prob"]) <= 1:
                raise ValueError(f"Invalid reviewer outcome in {cond} trace")
            flags += observed
            if i < budget - 1:
                if (any(not 0 <= node < manifest["nodes"] or node in actions[:i + 1]
                        for node in (flag, miss))
                        or any(not 0 <= node < manifest["nodes"] or node in actions[:i]
                               for node in (greedy, fixed))):
                    raise ValueError(f"Invalid public forecast in {cond} trace")
                counts += [actions[i] != greedy, actions[i] != fixed, flag != miss]
            elif greedy != actions[i] or (fixed, flag, miss) != (-1, -1, -1):
                raise ValueError(f"Expected a one-step decision on the last {cond} review")
        _, episode_flags, _, *episode_counts = cells[cond, "adaptive"][graphs[0]]
        if flags != episode_flags or list(counts) != episode_counts:
            raise ValueError(f"Trace does not reproduce {cond} episode diagnostics")

    arrays = {key: np.array([cell[g] for g in graphs]) for key, cell in cells.items()}
    return manifest, arrays, traces


def describe_example(trace):
    for current, following in zip(trace, trace[1:]):
        if current["flag_next"] == current["miss_next"]:
            continue
        outcome = "오류가 발견됐고" if int(current["flagged"]) else "오류가 발견되지 않았고"
        return (f"첫 평가 그래프(시드 {current['graph_seed']})의 순열 조건에서 두 예상 후보가 처음 갈린 "
                f"시점은 {current['step']}번째 검토였다. 정책은 {current['action']}번 노드를 선택했고, "
                f"오류를 발견하면 다음 후보를 {current['flag_next']}번, 발견하지 못하면 "
                f"{current['miss_next']}번으로 예상했다. 실제로는 {outcome} 재계획 뒤 다음에 검토한 "
                f"노드는 {following['action']}번이었다.")
    return (f"첫 평가 그래프(시드 {trace[0]['graph_seed']})의 순열 조건에서는 발견과 미발견을 "
            "가정했을 때 두 번째 검토 후보가 모든 시점에서 같았다.")


def summarize(run):
    manifest, data, traces = read_run(run)
    effects = {}
    for cond in CONDITIONS:
        for candidate, reference in CONTRASTS:
            a, b = data[cond, candidate][:, 0], data[cond, reference][:, 0]
            gap = paired_bootstrap(a[None, :], b, draws=10000, seed=20261112)
            counts = tuple(int(np.count_nonzero(mask)) for mask in (a < b, a == b, a > b))
            effects[cond, candidate, reference] = gap, counts

    main, wins = effects["shuffled", "adaptive", "mixture"]
    if main["high"] < 0:
        reading = "이 합성 조건에서는 조건부 후속 검토가 오류를 더 적게 남겼다."
    elif main["low"] > 0:
        reading = "이 합성 조건에서는 혼합 한 단계가 오류를 더 적게 남겼다."
    else:
        reading = "구간에 0이 포함되어 다음 검토까지 계획하면 오류를 줄이는지 판정하기 어렵다."
    n = len(manifest["graph_seeds"])
    lines = [
        "# 다음 검토 결과까지 내다보면 결론 오류가 줄어드는가", "",
        f"사전에 정한 유형 내 신뢰도 순열 조건에서 조건부 후속 검토와 혼합 한 단계의 차이는 "
        f"그래프당 **{format_gap(main)}개**였다(평균 차이와 95% 구간). {reading} "
        f"같은 {n}개 그래프 중 조건부 후속 검토가 오류를 적게 남긴 경우는 {wins[0]}개, "
        f"같은 경우는 {wins[1]}개, 더 많이 남긴 경우는 {wins[2]}개였다.", "",
        f"같은 합성 Spike 그래프 {n}개에서 각 정책이 80개 노드 중 16개를 검토했다. "
        "각 그래프의 숨은 오류, 전파 여부, 리뷰어의 발견 난수는 조건과 정책이 공유했다. "
        "정책은 공개 신뢰도, 그래프, 지금까지의 검토 결과로 다음 노드를 골랐다.", "",
        "## 16회 검토 후 그래프당 남은 결론 오류", "",
        "| 신뢰도 조건 | 단일 모형 한 단계 | 혼합 한 단계 | 고정 후속 검토 | 조건부 후속 검토 |",
        "|---|---:|---:|---:|---:|",
    ]
    for cond, label in CONDITIONS.items():
        means = " | ".join(f"{data[cond, p][:, 0].mean():.3f}" for p in POLICIES)
        lines.append(f"| {label} | {means} |")
    lines.extend([
        "", "평균이 낮을수록 좋다. 단일 모형은 신뢰도가 오류와 관련된다는 모형과 잡음이라는 모형 중 "
        "현재 가능성이 더 높은 쪽의 하류 영향 점수로 다음 노드를 고른다. 혼합 한 단계는 같은 두 점수를 "
        "현재 모형 확률로 가중 평균한다. 두 단계 정책은 이 점수 상위 6개를 첫 후보로 두고, 다음 검토에서 "
        "얻을 점수까지 합산한다. 고정 후속 검토는 두 결과에 공통인 다음 후보를 가정한다. "
        "조건부 후속 검토는 발견·미발견 각각의 다음 후보를 고른다. 두 정책 모두 실제 관측 후 매번 다시 계획한다.", "",
        "## 같은 그래프에서의 정책 차이", "",
        "| 조건 | 비교(앞 정책 − 뒤 정책) | 평균 차이 [95% 구간] | 앞 정책이 적음 / 같음 / 많음 |",
        "|---|---|---:|---:|",
    ])
    for cond, label in CONDITIONS.items():
        for candidate, reference in CONTRASTS:
            gap, (fewer, equal, more) = effects[cond, candidate, reference]
            lines.append(f"| {label} | {POLICIES[candidate]} − {POLICIES[reference]} | {format_gap(gap)} "
                         f"| {fewer} / {equal} / {more} |")
    lines.extend([
        "", "각 구간은 그래프별 차이를 짝지어 10,000번 재표집한 백분위 구간이다(난수 시드 20261112). "
        "음수는 앞 정책이 오류를 적게 남겼다는 뜻이다. 사전에 지정한 순열 조건의 조건부 후속 검토 − "
        "혼합 한 단계가 주 비교이며, 나머지 구간은 다중비교 보정 없이 제시한 보조 분석이다.", "",
        "## 실제 선택과 가상 후속 선택", "",
        "조건부 후속 검토가 방문한 상태에서 다시 계산한 선택을 비교했다. 마지막 검토에는 후속 검토가 "
        "없으므로 분모는 각 그래프의 첫 15회다. 첫 두 열은 지금 고르는 노드, 마지막 열은 지금 선택한 "
        "노드에서 발견과 미발견을 각각 가정했을 때 다음에 고를 노드가 달랐던 횟수다.", "",
        "| 조건 | 혼합 한 단계와 현재 선택이 다름 | 고정 후속 검토와 현재 선택이 다름 | 발견·미발견의 다음 후보가 다름 |",
        "|---|---:|---:|---:|",
    ])
    for cond, label in CONDITIONS.items():
        total, *counts = data[cond, "adaptive"][:, 2:].sum(axis=0)
        rates = " | ".join(f"{count}/{total} ({count / total:.1%})" for count in counts)
        lines.append(f"| {label} | {rates} |")
    lines.extend([
        "", describe_example(traces["shuffled"]), "",
        "후속 검토 점수는 모형이 예측한 하류 오류 감소의 근사치다. 첫 후보를 6개로 제한했고, "
        "실험 범위는 이 합성 그래프 구조와 검토 예산이다.", "",
        "[그래프별 원자료](episodes.csv) · [첫 그래프의 검토 기록](trace.csv) · [실행 설정과 해시](manifest.json)", "",
    ])
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path, help="completed planning evaluation directory")
    run = parser.parse_args().run
    path = run / "planning.md"
    path.write_text(summarize(run), encoding="utf-8")
    print(path)
