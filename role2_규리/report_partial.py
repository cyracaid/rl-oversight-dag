"""Verify paired trajectories and report the prespecified partial-corruption comparisons."""

import argparse
from collections import Counter
import csv
import json
from pathlib import Path

import numpy as np

from evaluate_partial import APPROACHES, ROOT, sha256
from report_conditions import format_gap, paired_bootstrap


LABEL = {"trust": "계속 신뢰", "ignore": "계속 무시", "feedback": "검토하면서 갱신"}


def summarize(run):
    manifest_path = run / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    episodes = run / "episodes.csv"
    if manifest["status"] != "complete" or manifest["episodes_sha256"] != sha256(episodes):
        raise ValueError("incomplete or modified raw results")
    for name, digest in manifest["source_sha256"].items():
        if sha256(ROOT / name) != digest:
            raise ValueError(f"source changed since collection: {name}")
    seeds = range(manifest["graph_start"], manifest["graph_start"] + manifest["graphs"])
    counts = manifest["conditions"]
    rows = {}
    with episodes.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            g, k = int(row["graph_seed"]), int(row["shuffled_type_count"])
            key = g, k, row["approach"]
            if g not in seeds or k not in counts or key[2] not in APPROACHES or key in rows:
                raise ValueError(f"duplicate or unexpected cell: {key}")
            actions = [int(a) for a in row["actions"].split()]
            if (len(actions) != int(row["reviews"]) or len(set(actions)) != manifest["budget"]
                    or min(actions) < 0 or max(actions) >= manifest["nodes"]
                    or int(row["episode_seed"]) != g + manifest["episode_seed_offset"]
                    or not 0 <= int(row["sink_errors"]) <= int(row["initial_sink_errors"]) <= manifest["sink_nodes"]):
                raise ValueError(f"invalid episode: {key}")
            rows[key] = row
    if len(rows) != len(seeds) * len(counts) * len(APPROACHES):
        raise ValueError("missing policy or graph")

    result = {}
    triggers = []
    for k in counts:
        frequencies = Counter()
        for g in seeds:
            r = rows[g, k, "trust"]
            picked = tuple(int(t) for t in r["shuffled_types"].split())
            if len(picked) != k or len(set(picked)) != k or any(t not in range(5) for t in picked):
                raise ValueError(f"invalid type set: {g}, {k}")
            if k and picked[:-1] != tuple(map(int, rows[g, k - 1, "trust"]["shuffled_types"].split())):
                raise ValueError("non-nested partial corruption")
            frequencies.update(picked)
            for a in APPROACHES:
                if rows[g, k, a]["initial_sink_errors"] != rows[g, 0, "trust"]["initial_sink_errors"]:
                    raise ValueError("unpaired initial truth")
                for field in ("shuffled_types", "changed_nodes", "gate", "nodes"):
                    if rows[g, k, a][field] != r[field]:
                        raise ValueError("unpaired treatment")
            for field in ("actions", "flags", "sink_errors"):
                if rows[g, k, "ignore"][field] != rows[g, 0, "ignore"][field]:
                    raise ValueError("confidence-blind trajectory changed")
        if any(frequencies[t] != len(seeds) * k // 5 for t in range(5)):
            raise ValueError("unbalanced type exposure")

        errors = {a: np.array([int(rows[g, k, a]["sink_errors"]) for g in seeds]) for a in APPROACHES}
        gaps = {a: paired_bootstrap(errors["feedback"][None, :], errors[a]) for a in ("trust", "ignore")}
        for a in gaps:
            if 1 <= k <= 4 and gaps[a]["low"] > 0:
                triggers.append({"count": k, "baseline": a})
        result[k] = {
            "changed_fraction": float(np.mean([int(rows[g, k, "trust"]["changed_nodes"]) /
                                               manifest["nodes"] for g in seeds])),
            "type_appearances": [frequencies[t] for t in range(5)],
            "mean_final_errors": {a: float(errors[a].mean()) for a in APPROACHES},
            "feedback_minus_fixed": gaps,
            "feedback_noise_fraction": float(np.mean([int(rows[g, k, "feedback"]["noise_actions"]) /
                                                      manifest["budget"] for g in seeds])),
        }
    return {"graphs": len(seeds), "rows": len(rows), "conditions": result, "followup_triggers": triggers,
            "source_sha256": {p.relative_to(ROOT).as_posix(): sha256(p) for p in (
                manifest_path.resolve(), Path(__file__).resolve(), ROOT / "experiments" / "rl_boundary.py")}}


def write_report(run):
    result = summarize(run)
    summary = result["conditions"]
    primary = summary[2]
    wins = [LABEL[a] for a, gap in primary["feedback_minus_fixed"].items() if gap["high"] < 0]
    if len(wins) == 2:
        conclusion = "두 고정 정책 모두에 비해 갱신 정책의 잔여 오류가 줄었다."
    elif wins:
        conclusion = f"갱신으로 ‘{wins[0]}’ 정책 대비 오류가 줄었다. 두 고정 정책 모두를 앞선다는 기준은 충족하지 못했다."
    else:
        conclusion = "두 고정 정책 각각과 비교했을 때 갱신으로 오류가 줄었다고 판단할 근거가 부족했다."
    lines = [
        "# 일부 유형의 신뢰도 점수만 뒤섞였을 때", "",
        f"**주 비교.** 5개 유형 중 2개에서만 점수를 섞었을 때 {conclusion}",
        "", f"합성 작업 흐름 {result['graphs']}개에서 사람의 검토를 모의했다. 한 흐름의 항목 80개 중 16개만 "
        "확인한 뒤, 최종 결론 20개 중 여전히 틀린 개수를 셌다. 표의 오류 수는 흐름당 평균으로, 작을수록 좋다.",
        "", "‘계속 신뢰’는 컴퓨터의 항목별 점수를 매번 반영한다. ‘계속 무시’는 유형별 기본 오류 확률을 쓴다. "
        "‘검토하면서 갱신’은 실제로 오류가 발견됐는지에 따라 둘 중 무엇을 다음 선택에 쓸지 정한다. "
        "세 정책 모두 한 오류가 최종 결론에 얼마나 영향을 주는지도 고려한다.",
        "", "| 점수를 섞은 유형 수 | 실제 점수가 바뀐 항목 | 계속 신뢰 | 계속 무시 | 검토하면서 갱신 |",
        "|---:|---:|---:|---:|---:|",
    ]
    for k, row in summary.items():
        means = row["mean_final_errors"]
        lines.append(f"| {k}/5 | {row['changed_fraction']:.1%} | {means['trust']:.3f} | "
                     f"{means['ignore']:.3f} | {means['feedback']:.3f} |")
    lines.extend(["", "### 같은 흐름에서의 차이", "",
                  "각 열은 갱신 정책의 최종 오류에서 비교 정책의 최종 오류를 뺀 값이다. 음수면 갱신 쪽에 "
                  "오류가 덜 남았다. 대괄호는 같은 그래프끼리 짝지어 10,000회 재표집한 개별 95% 구간이다. "
                  "2개 손상만 사전에 정한 주 비교이고 나머지는 손상이 늘어나는 경향을 읽기 위한 것이다.", "",
                  "| 섞은 유형 수 | 갱신 − 계속 신뢰 [95% 구간] | 갱신 − 계속 무시 [95% 구간] | "
                  "갱신이 점수를 무시한 검토 비율 |", "|---:|---:|---:|---:|"])
    for k, row in summary.items():
        gaps = row["feedback_minus_fixed"]
        lines.append(f"| {k}/5 | {format_gap(gaps['trust'])} | {format_gap(gaps['ignore'])} | "
                     f"{row['feedback_noise_fraction']:.1%} |")
    signs = [np.sign(row["mean_final_errors"]["trust"] - row["mean_final_errors"]["ignore"])
             for row in summary.values()]
    cross = [f"{k}개와 {k + 1}개" for k in range(5) if signs[k] != signs[k + 1]]
    if cross:
        lines.extend(["", "두 고정 정책의 평균 오류 순위가 바뀐 구간은 " + ", ".join(cross) +
                      " 사이다. 정책은 실제로 몇 개 유형이 섞였는지 볼 수 없으며 이 경계는 이 실험에서 관측한 값이다."])
    if result["followup_triggers"]:
        triggers = ", ".join(f"{cell['count']}개 손상 때 ‘{LABEL[cell['baseline']]}’" for cell in result["followup_triggers"])
        lines.extend(["", f"일부 유형이 손상된 조건에서 그래프 전체를 한 번에 갱신한 정책보다 오류가 적었던 고정 정책은 {triggers}였다 "
                      "(짝지은 구간 전체가 0 위). 사전에 정한 유형별 갱신 후보의 독립 평가 조건에 해당한다."])
    else:
        lines.extend(["", "일부 유형이 손상된 조건에서 갱신이 고정 정책보다 더 많은 오류를 남긴다고 판정한 비교는 없었다. "
                      "유형별 갱신 후보의 조건부 독립 평가 기준에는 도달하지 않았다."])
    lines.extend(["", "### 재현과 점검", "",
                  f"{result['rows']:,}개 실행 모두 16개의 서로 다른 항목을 검토했고 같은 그래프에서는 초기 오류가 같았다. "
                  "0개와 5개 입력은 기존 정상·전체 순열 입력과 각각 일치했다. 계속 무시 정책은 같은 그래프의 여섯 "
                  "조건 모두에서 16개 선택 순서와 최종 오류가 일치했다. 유형별 점수의 분포는 유지되고 값의 위치만 바뀌었다.",
                  "", "저장소 루트에서 새 출력 폴더를 지정해 재실행할 수 있다.", "", "```powershell",
                  "python 'role2_규리/evaluate_partial.py' --out 'role2_규리/runs/partial-repeat' --workers 2",
                  "python 'role2_규리/report_partial.py' 'role2_규리/runs/partial-repeat'",
                  "```", "", "[실행 전 고정한 조건](../../부분손상실행안.md) · [그래프별 검토 순서와 결과](episodes.csv) · "
                  "[실행 환경과 해시](manifest.json) · [비교 수치](partial.json)", ""])
    (run / "partial.md").write_text("\n".join(lines), encoding="utf-8")
    (run / "partial.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    write_report(parser.parse_args().run)
