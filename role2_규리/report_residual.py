"""Analyze paired terminal errors and policy decisions for the residual actor."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from report_conditions import EXPERIMENTS, format_gap, paired_bootstrap


CONDITIONS = {"shuffled": "유형 내 점수 순열", "matched": "정상 점수", "uniform": "균등 잡음"}
VARIANTS = ("residual", "feature_only")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_paired_data(run):
    directory = run / "eval"
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    raw = directory / "episodes.csv"
    if manifest["status"] != "complete" or sha256(raw) != manifest["episodes_sha256"]:
        raise ValueError("Incomplete run or invalid episode data digest")
    graphs, episodes, names = (manifest[key] for key in ("graph_seeds", "episode_seeds", "policies"))
    budget = manifest["budget"]
    if (not graphs or len(set(graphs)) != len(graphs) or len(episodes) != len(graphs)
            or len(set(episodes)) != len(graphs) or len(set(names)) != len(names)
            or budget != 16 or set(manifest["conditions"]) != set(CONDITIONS)):
        raise ValueError("Invalid evaluation design or duplicate IDs")
    groups = {
        group: sorted((n for n in names if n.startswith(group + "_s")),
                      key=lambda n: int(n.rsplit("_s", 1)[1]))
        for group in ("old", *VARIANTS)
    }
    seeds = [n.rsplit("_s", 1)[1] for n in groups["residual"]]
    if (not seeds or not groups["old"] or groups["feature_only"] != [f"feature_only_s{s}" for s in seeds]
            or set(names) != {"marginal", *groups["old"], *groups["residual"], *groups["feature_only"]}):
        raise ValueError("Inconsistent learned policies or unpaired training seeds")
    groups["marginal"] = ["marginal"]
    selected = {p: int(manifest["checkpoints"][p]["selected_episode"])
                for group in VARIANTS for p in groups[group]}
    episode_for = dict(zip(graphs, episodes))
    cells = {(cond, p): {} for cond in CONDITIONS for p in names}
    initial_by_graph = {}
    with raw.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            cond, policy = row["condition"], row["policy"]
            cell = cells[cond, policy]
            g = int(row["graph_seed"])
            initial, final, flags, steps, changed = (
                int(row[k]) for k in ("initial_sink_errors", "sink_errors", "flags", "reviews", "disagreements"))
            if (g in cell or episode_for[g] != int(row["episode_seed"]) or steps != budget
                    or not 0 <= final <= initial or initial_by_graph.setdefault(g, initial) != initial
                    or not 0 <= flags <= steps or not 0 <= changed <= steps):
                raise ValueError(f"Duplicate or inconsistent paired outcome: {cond}/{policy}/{g}")
            cell[g] = (final, flags, changed)
    if any(len(cell) != len(graphs) for cell in cells.values()):
        raise ValueError("Missing policy/episode pairs")
    arrays = {key: np.array([cell[g] for g in graphs]) for key, cell in cells.items()}
    for (cond, name), data in arrays.items():
        unchanged = data[:, 2] == 0
        if (name == "marginal" or (name.startswith("residual_s") and selected[name] == 0)) and not unchanged.all():
            raise ValueError(f"Uncorrected rule disagrees with itself: {cond}/{name}")
        if not np.array_equal(data[unchanged, :2], arrays[cond, "marginal"][unchanged, :2]):
            raise ValueError(f"Identical decisions produced different outcomes: {cond}/{name}")
    return manifest, arrays, groups, selected


def contrast_summary(data, groups, budget):
    # data[group] has axes for training seed, graph and metric (errors, flags, disagreements).
    errors = {group: rows[:, :, 0] for group, rows in data.items()}
    base = errors["marginal"][0]
    differences = errors["residual"] - errors["feature_only"]
    against_rule = errors["residual"] - base
    return {
        "means": {group: float(vals.mean()) for group, vals in errors.items()},
        "disagreement_rates": {group: float(rows[:, :, 2].mean() / budget) for group, rows in data.items()},
        "flag_rates": {group: float(rows[:, :, 1].mean() / budget) for group, rows in data.items()},
        "residual_minus_marginal": paired_bootstrap(errors["residual"], base),
        "residual_minus_feature_only": paired_bootstrap(differences, np.zeros_like(base)),
        "residual_vs_marginal_counts": {
            "fewer": int((against_rule < 0).sum()), "equal": int((against_rule == 0).sum()),
            "more": int((against_rule > 0).sum()),
        },
        "by_seed": {
            p: {"mean_sink_errors": float(vals[:, 0].mean()),
                "vs_marginal": float((vals[:, 0] - base).mean()),
                "disagreement_rate": float(vals[:, 2].mean() / budget)}
            for group in VARIANTS for p, vals in zip(groups[group], data[group])
        },
    }


def analyze(run):
    manifest, cells, groups, selected = read_paired_data(run)
    data = {c: {k: np.stack([cells[c, p] for p in names]) for k, names in groups.items()} for c in CONDITIONS}
    budget = manifest["budget"]
    conditions = {c: contrast_summary(samples, groups, budget) for c, samples in data.items()}
    # Preserve the same graph and training seed across all three regimes in each draw.
    average = {k: np.mean([samples[k] for samples in data.values()], axis=0) for k in groups}
    sources = [run / "eval" / "manifest.json", run / "eval" / "episodes.csv", Path(__file__),
               Path(__file__).with_name("report_conditions.py"), Path(__file__).with_name("잔차학습계획.md"),
               EXPERIMENTS / "rl_boundary.py"]
    return {
        "graphs": len(manifest["graph_seeds"]), "budget": budget, "policies": groups,
        "selected_episodes": selected, "conditions": conditions,
        "equal_weight": contrast_summary(average, groups, budget),
        "primary_shuffled_residual_minus_marginal": conditions["shuffled"]["residual_minus_marginal"],
        "bootstrap": {"draws": 10000, "seed": 20261112, "coverage": 0.95},
        "sha256": {p.name: sha256(p) for p in sources},
    }


def markdown(result):
    primary = result["primary_shuffled_residual_minus_marginal"]
    groups = result["policies"]
    selected = result["selected_episodes"]
    initial_count = sum(selected[name] == 0 for name in groups["residual"])
    if initial_count == len(groups["residual"]):
        reading = "모든 시드에서 보정값이 0인 초기 상태가 선택되어 기존 규칙과 같은 행동을 했다."
    elif primary["high"] < 0:
        reading = "이 합성 조건에서는 잔차 정책이 기존 규칙보다 결론 오류를 적게 남겼다."
    elif primary["low"] > 0:
        reading = "이 합성 조건에서는 기존 규칙이 잔차 정책보다 결론 오류를 적게 남겼다."
    else:
        reading = "95% 구간이 0을 포함해 어느 쪽이 더 적은 오류를 남기는지 판정하기 어렵다."
    lines = ["# 하류 영향 점수에 학습 보정을 더한 검토 정책", "",
             f"사전에 정한 유형 내 점수 순열 조건에서 잔차 정책의 평균 결론 오류에서 기존 하류 영향 규칙"
             f"(`marginal`)의 평균을 뺀 차이는 **{format_gap(primary)}개**였다. {reading}", "",
             f"합성 그래프 {result['graphs']}개에 각각 검토 {result['budget']}회를 배정했다. "
             "잔차 정책은 정규화한 하류 영향 점수에 GNN 출력을 더한다. 특징 전용 GNN은 같은 점수를 "
             "입력 특징으로 받고 GNN 출력만으로 순위를 정한다. 두 정책은 같은 학습 시드·사례·예산으로 비교했다.", "",
             "| 조건 | 하류 영향 규칙 | 잔차 정책 | 특징 전용 GNN | 기존 GNN | 잔차 − 규칙 [95% 구간] | 잔차 − 특징 전용 [95% 구간] |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    summaries = [(label, result["conditions"][key]) for key, label in CONDITIONS.items()]
    summaries.append(("세 조건 동일 가중", result["equal_weight"]))
    for label, summary in summaries:
        m = summary["means"]
        lines.append(f"| {label} | {m['marginal']:.3f} | {m['residual']:.3f} | {m['feature_only']:.3f} | "
                     f"{m['old']:.3f} | {format_gap(summary['residual_minus_marginal'])} | "
                     f"{format_gap(summary['residual_minus_feature_only'])} |")
    lines.extend(["", "각 평균은 그래프당 남은 결론 오류 수이며 낮을수록 좋다. 음의 차이는 잔차 정책에 유리하다. "
                  "기존 GNN의 값은 학습 이력이 다른 v3 체크포인트의 참고 평균이다. "
                  "차이의 95% 구간은 같은 그래프에서 구한 차이를 유지하고 학습 시드와 그래프를 독립적으로 "
                  "10,000번 재표집했다. 두 새 정책은 같은 학습 시드끼리 짝지었다. 세 조건 평균은 같은 그래프에 "
                  "속한 세 결과를 함께 재표집했다.", "",
                  "## 학습한 보정이 실제 결정을 바꾼 정도", "",
                  f"잔차 정책의 {len(groups['residual'])}개 학습 시드 중 {initial_count}개에서 검증이 "
                  "0회차를 선택했다. 잔차 정책의 0회차는 하류 영향 규칙을 그대로 재현한다. "
                  "아래 비율은 각 정책이 실제 방문한 상태에서 하류 영향 규칙과 다른 노드를 고른 검토의 비율이다.", "",
                  "| 조건 | 잔차 정책의 다른 선택 | 특징 전용 GNN의 다른 선택 |",
                  "|---|---:|---:|"])
    for label, summary in summaries:
        rates = summary["disagreement_rates"]
        lines.append(f"| {label} | {rates['residual']:.1%} | {rates['feature_only']:.1%} |")
    lines.extend(["", "| 학습 시드 | 잔차 선택 회차 | 특징 전용 선택 회차 | 순열에서 시드별 잔차 − 규칙 |",
                  "|---:|---:|---:|---:|"])
    for residual, feature in zip(groups["residual"], groups["feature_only"]):
        gap = result["conditions"]["shuffled"]["by_seed"][residual]["vs_marginal"]
        lines.append(f"| {residual.rsplit('_s', 1)[1]} | {selected[residual]} | {selected[feature]} | {gap:+.3f} |")
    counts = result["conditions"]["shuffled"]["residual_vs_marginal_counts"]
    lines.extend(["", f"순열 조건에서 잔차 정책이 규칙보다 오류를 적게 남긴 시드·그래프 조합은 "
                  f"{counts['fewer']}건, 같은 조합은 {counts['equal']}건, 더 많이 남긴 조합은 "
                  f"{counts['more']}건이었다. 동일 그래프가 여러 학습 시드에 등장하므로 구간 추정은 위의 "
                  "짝지은 재표집을 사용했다.",
                  "", "[조건별 효과 그림](residual_effect.png) · [짝지은 원자료](eval/episodes.csv) · [실행 설정과 체크포인트 해시](eval/manifest.json) · "
                  "[조건별 시드 수치와 분석 코드 해시](residual.json)", ""])
    return "\n".join(lines)


def plot(result, path):
    from matplotlib.figure import Figure
    from matplotlib.ticker import MaxNLocator

    figure = Figure(figsize=(9, 3.5), layout="constrained")
    axes = figure.subplots(1, 2, sharey=True)
    labels = ["Within-type shuffle", "Calibrated scores", "Uniform noise"]
    contrasts = (("residual_minus_marginal", "Residual minus marginal rule", "#1e6175"),
                 ("residual_minus_feature_only", "Residual minus feature-only GNN", "#8b4b21"))
    for axis, (key, title, color) in zip(axes, contrasts):
        estimates = [result["conditions"][c][key] for c in CONDITIONS]
        lo = [g["low"] for g in estimates]
        hi = [g["high"] for g in estimates]
        left, right = min(0, *lo), max(0, *hi)
        padding = 0.09 * max(0.10, right - left)
        axis.set_xlim(left - padding, right + padding)
        axis.axvline(0, color="0.55", linestyle="--", linewidth=1)
        axis.hlines(range(len(labels)), lo, hi, color=color, linewidth=2.2)
        axis.scatter([g["mean"] for g in estimates], range(len(labels)), color=color, s=40, zorder=3)
        axis.set_title(title, fontsize=11)
        axis.set_yticks(range(len(labels)), labels)
        axis.set_ylim(2.65, -0.65)
        axis.spines[["top", "right"]].set_visible(False)
        axis.xaxis.set_major_locator(MaxNLocator(nbins=5))
    figure.suptitle("Residual policy contrasts with paired 95% bootstrap intervals", fontsize=14)
    figure.supxlabel("Difference in remaining conclusion errors per graph\nNegative values favor the residual policy  ·  Horizontal scales differ by panel", fontsize=10)
    figure.savefig(path, dpi=180)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    run_dir = parser.parse_args().run
    result = analyze(run_dir)
    report = markdown(result)
    plot(result, run_dir / "residual_effect.png")
    (run_dir / "residual.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (run_dir / "residual.md").write_text(report, encoding="utf-8")
    print(run_dir / "residual.md")
