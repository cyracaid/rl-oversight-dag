"""Report paired terminal-error contrasts for a completed Role 2 diagnostic run."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import sys

import numpy as np

EXPERIMENTS = Path(__file__).resolve().parents[1] / "experiments"
sys.path.insert(0, str(EXPERIMENTS))
from rl_boundary import paired_bootstrap


CONDITIONS = ("matched", "noise_unrecognized", "noise_known")
CONTROLS = ("confidence", "type_prior", "marginal", "adaptive_marginal")
COMPARATORS = ("marginal", "type_prior", "adaptive_marginal")
MODEL_LABEL = re.compile(r"(gnn(?:_static)?)_s([1-9]\d*)")
CONDITION_NAMES = {
    "matched": "정상 신뢰도",
    "noise_unrecognized": "노이즈를 정상 신호로 해석",
    "noise_known": "노이즈를 알고 유형 사전확률 사용",
}


def load_episodes(path, manifest):
    graphs = manifest["graph_seeds"]
    policies = manifest["policies"]
    episode_ids = manifest["episode_seeds"]
    if (manifest["status"] != "complete" or set(manifest["conditions"]) != set(CONDITIONS)
            or not graphs or len(graphs) != len(set(graphs)) or len(graphs) != len(episode_ids)
            or len(set(episode_ids)) != len(episode_ids) or len(set(policies)) != len(policies)
            or not set(CONTROLS).issubset(policies)):
        raise ValueError("Incomplete run or inconsistent policy, graph, episode or condition manifest")
    expected_episode = dict(zip(graphs, episode_ids))
    cells = {(condition, policy): {} for condition in CONDITIONS for policy in policies}
    initial_errors = {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            policy = row["policy"]
            cell = cells[(row["condition"], policy)]
            graph = int(row["graph_seed"])
            if graph in cell or expected_episode[graph] != int(row["episode_seed"]):
                raise ValueError(f"Duplicate or unpaired graph in {policy}: {graph}")
            initial, final, flags, reviews = (int(row[key]) for key in
                                             ("initial_sink_errors", "sink_errors", "flags", "reviews"))
            assumed = row["assumed_mode"]
            if (assumed not in ("normal", "noise") or not 0 <= final <= initial or not 0 <= flags <= reviews
                    or reviews != (0 if policy == "none" else manifest["budget"])
                    or initial_errors.setdefault(graph, initial) != initial):
                raise ValueError(f"Inconsistent initial or final outcome, flags or budget on graph {graph}")
            cell[graph] = (final, initial - final, flags, reviews, int(assumed == "noise"))
    if any(len(cell) != len(graphs) for cell in cells.values()):
        raise ValueError("Missing episodes in the paired policy comparison")
    if cells["noise_unrecognized", "adaptive_marginal"] != cells["noise_known", "adaptive_marginal"]:
        raise ValueError("Adaptive policy changed outcomes or inferred signal model on identical noise graphs")
    return {key: np.array([cell[g] for g in graphs]) for key, cell in cells.items()}


def make_comparison(run):
    manifest_path = run / "manifest.json"
    episodes_path = run / "episodes.csv"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    episodes_hash = hashlib.sha256(episodes_path.read_bytes()).hexdigest()
    if episodes_hash != manifest["episodes_sha256"]:
        raise ValueError("episodes.csv SHA-256 does not match the run manifest")
    cells = load_episodes(episodes_path, manifest)
    groups = {}
    for label in manifest["policies"]:
        match = MODEL_LABEL.fullmatch(label)
        if match:
            groups.setdefault(match[1], []).append(label)
    if not groups:
        raise ValueError("No learned GNN checkpoint in the experiment")
    for labels in groups.values():
        labels.sort(key=lambda label: int(MODEL_LABEL.fullmatch(label)[2]))
    policy_groups = {p: [p] for p in manifest["policies"] if not MODEL_LABEL.fullmatch(p)}
    policy_groups.update(groups)
    conditions = {}
    for condition in CONDITIONS:
        summary = {}
        for name, labels in policy_groups.items():
            # Rows are training seeds with the same graph order in every row.
            data = np.stack([cells[condition, label] for label in labels])
            errors, saved, flags, reviews, assumed_noise = data.transpose(2, 0, 1)
            total_reviews = reviews.sum()
            metrics = {
                "mean_sink_errors": float(errors.mean()),
                "flag_rate": float(flags.sum() / total_reviews) if total_reviews else None,
                "saved_per_review": float(saved.sum() / total_reviews) if total_reviews else None,
            }
            if name in groups:
                seed_scores = {label: {"mean_sink_errors": float(row.mean())} for label, row in zip(labels, errors)}
                for control in COMPARATORS:
                    reference = cells[condition, control][:, 0]
                    metrics["vs_" + control] = paired_bootstrap(errors, reference)
                    for label, row in zip(labels, errors):
                        seed_scores[label]["vs_" + control] = float((row - reference).mean())
                metrics["seeds"] = seed_scores
            if name == "adaptive_marginal":
                metrics["vs_marginal"] = paired_bootstrap(errors, cells[condition, "marginal"][:, 0])
                metrics["inferred_noise_graphs"] = int(assumed_noise.sum())
                metrics["inferred_normal_graphs"] = int(assumed_noise.size - assumed_noise.sum())
            summary[name] = metrics
        conditions[condition] = summary

    corrected_reference = cells["noise_known", "marginal"][:, 0]
    noise_comparison = {}
    for name, labels in groups.items():
        errors = np.stack([cells["noise_unrecognized", label][:, 0] for label in labels])
        noise_comparison[name] = paired_bootstrap(errors, corrected_reference)
    return {
        "graphs": len(manifest["graph_seeds"]), "review_budget": manifest["budget"],
        "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in (manifest_path, episodes_path, Path(__file__), EXPERIMENTS / "rl_boundary.py")},
        "bootstrap": {"draws": 10000, "seed": 20261112, "coverage": 0.95},
        "conditions": conditions, "uncorrected_gnn_vs_corrected_marginal": noise_comparison,
    }


def format_gap(gap):
    return f"{gap['mean']:+.3f} [{gap['low']:+.3f}, {gap['high']:+.3f}]"


def render_report(result):
    lines = [
        "# 신뢰도 조건에 따른 검토 정책 비교", "",
        f"합성 Spike 그래프 {result['graphs']}개에서 정책마다 최대 {result['review_budget']}개 노드를 "
        "검토했다. 주 지표는 검토 후 결론 노드에 남은 오류 수이며 낮을수록 좋다. "
        "GNN 평균은 각 학습 시드에 같은 가중치를 준 값이다. gnn은 검토 결과까지 입력받는 observed 모델이다.", "",
        "| 신뢰도 조건 | 정책 | 평균 잔여 오류 | 검토 중 오류 발견율 | 검토 1회당 줄인 결론 오류 |",
        "|---|---|---:|---:|---:|",
    ]
    for condition, scores in result["conditions"].items():
        for name, metrics in scores.items():
            rate = metrics["flag_rate"]
            saved = metrics["saved_per_review"]
            lines.append(f"| {CONDITION_NAMES[condition]} | {name} | {metrics['mean_sink_errors']:.3f} "
                         f"| {format(rate, '.1%') if rate is not None else '—'} "
                         f"| {format(saved, '.3f') if saved is not None else '—'} |")
    lines.extend([
        "", "## 같은 그래프에서의 정책 차이", "",
        "차이는 GNN의 평균 잔여 오류에서 각 기준선의 평균을 뺀 값이다. 음수면 GNN의 잔여 오류가 더 적다. "
        "대괄호는 학습 시드와 그래프를 각각 재표집하되 정책 사이의 그래프 짝을 유지한 "
        "10,000회 부트스트랩의 95% 구간이다. 학습 시드가 하나면 그래프에 의한 변동만 반영한다. "
        "각 구간은 개별 비교에 해당한다.", "",
        "| 신뢰도 조건 | GNN | 시드별 평균 잔여 오류 | marginal 대비 차이 | type_prior 대비 차이 | adaptive_marginal 대비 차이 |",
        "|---|---|---|---:|---:|---:|",
    ])
    for condition, scores in result["conditions"].items():
        for name, metrics in scores.items():
            if "seeds" in metrics:
                means = ", ".join(f"{label.rsplit('_', 1)[1]} {values['mean_sink_errors']:.3f}"
                                  for label, values in metrics["seeds"].items())
                lines.append(f"| {CONDITION_NAMES[condition]} | {name} | {means} "
                             f"| {format_gap(metrics['vs_marginal'])} | {format_gap(metrics['vs_type_prior'])} "
                             f"| {format_gap(metrics['vs_adaptive_marginal'])} |")
    lines.extend(["", "## 관측한 신뢰도로 사전확률을 선택한 정책", "",
                  "adaptive_marginal은 그래프의 공개 신뢰도로 신호 모형을 선택한 뒤 marginal로 검토 순서를 "
                  "정한다. 아래 차이는 adaptive_marginal에서 해당 조건의 marginal을 뺀 잔여 오류다. "
                  "같은 그래프의 차이를 재표집해 95% 구간을 구했다.", "",
                  "| 신뢰도 조건 | 정상으로 판정한 그래프 | 노이즈로 판정한 그래프 | 잔여 오류 차이 [95% 구간] |",
                  "|---|---:|---:|---:|"])
    for condition, scores in result["conditions"].items():
        adaptive = scores["adaptive_marginal"]
        lines.append(f"| {CONDITION_NAMES[condition]} | {adaptive['inferred_normal_graphs']} "
                     f"| {adaptive['inferred_noise_graphs']} | {format_gap(adaptive['vs_marginal'])} |")
    lines.extend(["", "## 같은 노이즈에서 비교 기준을 바꾼 결과", "",
                  "노이즈를 정상 신호로 해석한 GNN의 결과를 고정하고, 동일 그래프에서 "
                  "노이즈임을 알고 유형 사전확률을 사용한 marginal과 비교했다.", ""])
    for name, gap in result["uncorrected_gnn_vs_corrected_marginal"].items():
        lines.append(f"- {name}의 잔여 오류 차이는 {format_gap(gap)}개다.")
    lines.extend(["", "이 개발 실험은 신뢰도의 생성 방식과 정책에 주어진 가정을 바꾼 합성 비교다. "
                  "검토 중 발견율은 선택한 노드에서 오류를 발견한 비율이며, 검토 1회당 줄인 결론 오류는 "
                  "초기 오류와 최종 오류의 차이를 실제 검토 횟수로 나눈 값이다. "
                  "노이즈를 안다는 가정은 실제 운영에서 별도 검증이 필요하다.", "",
                  "[그래프별 결과](episodes.csv) · [실행 설정과 출처](manifest.json) · [비교 수치](comparison.json)", ""])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path, help="completed diagnostic run directory")
    run = parser.parse_args().run
    result = make_comparison(run)
    (run / "comparison.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (run / "comparison.md").write_text(render_report(result), encoding="utf-8")
    print(run / "comparison.md")


if __name__ == "__main__":
    main()
