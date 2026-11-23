"""Summarize a paired evaluation of frozen policies with and without review feedback."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re

import numpy as np

from report_conditions import EXPERIMENTS, format_gap, paired_bootstrap


CONDITIONS = {"shuffled": "신뢰도 순열", "matched": "정상 신뢰도", "uniform": "균등 잡음"}
APPROACHES = ("fixed", "feedback")


def read_run(run):
    manifest_path = run / "manifest.json"
    episodes = run / "episodes.csv"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if manifest["status"] != "complete" or hashlib.sha256(episodes.read_bytes()).hexdigest() != manifest["episodes_sha256"]:
        raise ValueError("Incomplete run or invalid episodes.csv digest")
    graphs = manifest["graph_seeds"]
    episode_ids = manifest["episode_seeds"]
    policies = manifest["policies"]
    if (not graphs or len(set(graphs)) != len(graphs) or len(episode_ids) != len(graphs)
            or len(set(episode_ids)) != len(graphs) or set(manifest["conditions"]) != set(CONDITIONS)
            or len(set(policies)) != len(policies) or "marginal" not in policies):
        raise ValueError("Invalid graph, episode, condition or policy manifest")
    learned = [p for p in policies if re.fullmatch(r"gnn_s[1-9]\d*", p)]
    if not learned or len(learned) + 1 != len(policies):
        raise ValueError("Expected marginal and observed GNN checkpoint policies")
    learned.sort(key=lambda name: int(name.split("_s")[1]))
    expected_episode = dict(zip(graphs, episode_ids))
    cells = {(c, a, p): {} for c in CONDITIONS for a in APPROACHES for p in policies}
    initial_by_graph = {}
    with episodes.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            cell = cells[row["condition"], row["approach"], row["policy"]]
            graph = int(row["graph_seed"])
            initial, final, flags, reviews, switched, noise_actions = (int(row[key]) for key in
                ("initial_sink_errors", "sink_errors", "flags", "reviews", "switched", "noise_actions"))
            if (graph in cell or int(row["episode_seed"]) != expected_episode[graph]
                    or initial_by_graph.setdefault(graph, initial) != initial or not 0 <= final <= initial
                    or reviews != manifest["budget"] or not 0 <= flags <= reviews
                    or not 0 <= noise_actions <= reviews or switched not in (0, 1)):
                raise ValueError(f"Unpaired or invalid outcome for graph {graph}")
            if row["approach"] == "fixed" and switched:
                raise ValueError(f"Fixed approach reported switching on graph {graph}")
            cell[graph] = (final, flags, initial - final, switched, noise_actions)
    if any(len(cell) != len(graphs) for cell in cells.values()):
        raise ValueError("Missing paired policy results")
    return manifest, learned, {key: np.asarray([cell[g] for g in graphs]) for key, cell in cells.items()}


def summarize(run):
    manifest, learned, cells = read_run(run)
    n_graphs = len(manifest["graph_seeds"])
    budget = manifest["budget"]
    conditions = {}
    for condition in CONDITIONS:
        summary = {}
        for group, labels in (("gnn", learned), ("marginal", ["marginal"])):
            metrics = {}
            errors = {}
            for approach in APPROACHES:
                data = np.stack([cells[condition, approach, label] for label in labels])
                final, flags, saved, switches, noise_actions = data.transpose(2, 0, 1)
                errors[approach] = final
                metrics[approach] = {
                    "mean_errors": float(final.mean()), "flag_rate": float(flags.mean() / budget),
                    "saved_per_review": float(saved.mean() / budget),
                    "noise_action_rate": float(noise_actions.mean() / budget),
                    "switching_trajectories": int(switches.sum()), "trajectories": int(switches.size),
                    "switch_rate": float(switches.mean()),
                    "graphs_switched_by_any_seed": int(switches.any(axis=0).sum()),
                    "switched_graphs_by_policy": {p: int(s.sum()) for p, s in zip(labels, switches)},
                }
            delta = errors["feedback"] - errors["fixed"]
            metrics["feedback_minus_fixed"] = paired_bootstrap(delta, np.zeros(n_graphs))
            metrics["by_policy"] = {
                p: {"fixed": float(errors["fixed"][i].mean()), "feedback": float(errors["feedback"][i].mean()),
                    "feedback_minus_fixed": float(delta[i].mean())}
                for i, p in enumerate(labels)
            }
            summary[group] = metrics
        gnn = np.stack([cells[condition, "feedback", p][:, 0] for p in learned])
        summary["gnn_minus_marginal_feedback"] = paired_bootstrap(gnn, cells[condition, "feedback", "marginal"][:, 0])
        conditions[condition] = summary

    sources = [run / "manifest.json", run / "episodes.csv", Path(__file__),
               Path(__file__).with_name("report_conditions.py"), EXPERIMENTS / "rl_boundary.py"]
    return {
        "graphs": n_graphs, "budget": budget, "policies": learned, "conditions": conditions,
        "primary_shuffled_gnn_feedback_minus_fixed": conditions["shuffled"]["gnn"]["feedback_minus_fixed"],
        "bootstrap": {"draws": 10000, "seed": 20261112, "coverage": 0.95},
        "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
    }


def markdown(result):
    primary = result["primary_shuffled_gnn_feedback_minus_fixed"]
    if primary["high"] < 0:
        reading = "이 합성 조건에서 피드백 방식의 잔여 오류가 더 적었다."
    elif primary["low"] > 0:
        reading = "이 합성 조건에서 고정 방식의 잔여 오류가 더 적었다."
    else:
        reading = "95% 구간이 0을 포함해 이 비교로는 개선을 확인하기 어렵다."
    lines = [
        "# 검토 관측을 반영한 GNN의 결론 오류", "",
        f"사전에 정한 주 비교에서 신뢰도를 노드 간에 섞었을 때 GNN의 잔여 결론 오류 차이는 "
        f"그래프당 **{format_gap(primary)}개**였다. 차이는 피드백 방식에서 고정 방식을 뺀 값이고 "
        f"음수면 피드백 방식이 남긴 오류가 더 적다. {reading}", "",
        f"학습이 끝난 GNN {len(result['policies'])}개를 고정하고 같은 합성 그래프 {result['graphs']}개에서 "
        f"각 정책에 {result['budget']}회의 검토를 배정했다. 두 방식은 공개 신뢰도의 평균으로 정한 "
        "같은 모형에서 출발한다. 고정 방식은 그 모형을 유지하고 피드백 방식은 검토 관측으로 모형을 갱신한다. "
        "각 학습 시드에 같은 가중치를 주었다. "
        "95% 구간은 같은 시드와 그래프에서 차이를 먼저 구한 뒤 시드와 그래프를 독립적으로 10,000번 "
        "재표집한 값이다. marginal은 그래프만 재표집했다. 나머지 조건과 정책 비교는 보조 분석이다.", "",
        "| 조건 | 정책 | 고정 평균 | 피드백 평균 | 피드백 − 고정 [95% 구간] | 시드별 차이 |",
        "|---|---|---:|---:|---:|---|",
    ]
    for condition, scores in result["conditions"].items():
        for group in ("gnn", "marginal"):
            m = scores[group]
            point_gaps = ", ".join(f"{p.split('_')[-1]} {s['feedback_minus_fixed']:+.3f}"
                                   for p, s in m["by_policy"].items()) if group == "gnn" else "—"
            lines.append(f"| {CONDITIONS[condition]} | {group} | {m['fixed']['mean_errors']:.3f} "
                         f"| {m['feedback']['mean_errors']:.3f} | {format_gap(m['feedback_minus_fixed'])} | {point_gaps} |")
    lines.extend(["", "## 같은 피드백을 적용한 GNN과 marginal의 차이", ""])
    for condition, scores in result["conditions"].items():
        lines.append(f"- {CONDITIONS[condition]}에서 GNN − marginal은 "
                     f"{format_gap(scores['gnn_minus_marginal_feedback'])}개다.")
    lines.extend(["", "## 오류 발견과 정책 전환", "",
                  "발견율과 줄인 결론 오류는 검토 1회당 값이다. 전환 횟수는 최초 신호 모형과 다른 모형으로 "
                  "한 번이라도 행동한 시드·그래프 조합 수다. 맨 오른쪽 열은 시드가 공유한 그래프를 한 번씩 센다.", "",
                  "| 조건 | 정책 | 방식 | 오류 발견율 | 줄인 결론 오류 | 전환한 조합 수와 비율 | 전환이 발생한 그래프 |",
                  "|---|---|---|---:|---:|---:|---:|"])
    for condition, scores in result["conditions"].items():
        for group in ("gnn", "marginal"):
            for approach in APPROACHES:
                m = scores[group][approach]
                lines.append(f"| {CONDITIONS[condition]} | {group} | {approach} | {m['flag_rate']:.1%} "
                             f"| {m['saved_per_review']:.3f} | {m['switching_trajectories']}/{m['trajectories']} "
                             f"({m['switch_rate']:.1%}) | {m['graphs_switched_by_any_seed']}/{result['graphs']} |")
    lines.extend(["", "[조건별 효과 그림](feedback_effect.png) · [짝지은 원자료](episodes.csv) · [실행 설정](manifest.json) · [전체 비교](feedback.json)", ""])
    return "\n".join(lines)


def plot_effect(result, path):
    from matplotlib.figure import Figure

    figure = Figure(figsize=(8, 3.5), layout="constrained")
    axis = figure.subplots()
    conditions = ("shuffled", "matched", "uniform")
    axis.axvline(0, color="0.45", linewidth=1, linestyle="--")
    for group, label, color, offset in (("gnn", "Observed GNN", "#275b99", -0.13),
                                         ("marginal", "Marginal rule", "#b4581c", 0.13)):
        gaps = [result["conditions"][c][group]["feedback_minus_fixed"] for c in conditions]
        y = np.arange(len(conditions)) + offset
        axis.hlines(y, [g["low"] for g in gaps], [g["high"] for g in gaps], color=color, linewidth=2)
        axis.scatter([g["mean"] for g in gaps], y, color=color, label=label, zorder=3)
    axis.set_yticks(range(3), ["Shuffled within type", "Calibrated scores", "Uniform noise"])
    axis.set_ylim(2.5, -0.5)
    axis.set_xlabel("Change in remaining conclusion errors per graph (feedback minus fixed)")
    axis.set_title(f"Review feedback at a budget of {result['budget']} nodes")
    axis.spines[["top", "right"]].set_visible(False)
    axis.legend(loc="lower left", frameon=False, title="Paired 95% bootstrap intervals")
    figure.savefig(path, dpi=180)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    run_dir = parser.parse_args().run
    result = summarize(run_dir)
    report = markdown(result)
    plot_effect(result, run_dir / "feedback_effect.png")
    (run_dir / "feedback.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (run_dir / "feedback.md").write_text(report, encoding="utf-8")
    print(run_dir / "feedback.md")
