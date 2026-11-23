"""Verify the paired review-budget experiment and summarize reward-to-go versus terminal-only learning."""

import argparse
import csv
import json
from pathlib import Path
from statistics import mean

import numpy as np
from matplotlib.figure import Figure

from evaluate_conditions import ROOT, sha256
from report_conditions import EXPERIMENTS, format_gap, paired_bootstrap
from train_credit import ARCHIVE, CONDITIONS, EPISODES, EVAL_GRAPHS, RUN, weights_for, write_json


SEEDS = range(1, 6)
ARMS = ("terminal", "future")
LABELS = {"matched": "정상 점수", "uniform": "균등 잡음", "shuffled": "모든 유형 안에서 점수를 섞음"}


def verified_inputs(run):
    rows, histories, files = {}, {}, {}
    for seed in SEEDS:
        folder = run / f"seed-{seed}"
        receipt_path = folder / "complete.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if set(receipt) != {"training.json", "config.json", "episodes.csv", "future.pt"}:
            raise ValueError("incomplete seed receipt")
        for name, digest in receipt.items():
            if sha256(folder / name) != digest:
                raise ValueError(f"changed seed-{seed}/{name}")
        files[receipt_path] = sha256(receipt_path)
        config = json.loads((folder / "config.json").read_text(encoding="utf-8"))
        old = config["control"]
        for name, digest in config["inputs"].items():
            if sha256(ROOT / name) != digest:
                raise ValueError(f"changed experiment input: {name}")
        checkpoint = ROOT / old["path"]
        archive_log = checkpoint.with_name("training.json")
        if old["training_log_sha256"] != sha256(archive_log) or old["sha256"] != sha256(checkpoint):
            raise ValueError("changed archived training log or checkpoint")
        histories[seed, "terminal"] = json.loads(archive_log.read_text(encoding="utf-8"))["feature_only"]
        histories[seed, "future"] = json.loads((folder / "training.json").read_text(encoding="utf-8"))
        for arm in ARMS:
            h = histories[seed, arm]
            if len(h["training"]) != EPISODES or [r["episode"] for r in h["validation"]] != [0, 192, 384]:
                raise ValueError(f"incomplete training or validation for {seed}/{arm}")
            if min(h["validation"], key=lambda r: r["mean_sink_errors"])["episode"] != h["selected_episode"]:
                raise ValueError("incorrect validation selection")
        for a, b in zip(histories[seed, "terminal"]["training"], histories[seed, "future"]["training"]):
            if any(a[k] != b[k] for k in ("episode", "condition", "graph_seed", "baseline_sink_errors")):
                raise ValueError("training cases differ between arms")
            terminal, future = weights_for(b["actor_errors"], b["rule_errors"])
            if b["terminal_advantage"] != terminal or b["step_advantages"] != future.tolist():
                raise ValueError("incorrect per-step advantage in B's training trace")
        with (folder / "episodes.csv").open(encoding="utf-8", newline="") as stream:
            for r in csv.DictReader(stream):
                g = int(r["graph_seed"])
                outcome = tuple(int(r[k]) for k in ("initial_sink_errors", "sink_errors", "flags", "reviews"))
                name, cond = r["policy"], r["condition"]
                sid = None if name == "marginal" else seed
                key = cond, name, sid, g
                if (key in rows or g not in EVAL_GRAPHS or cond not in CONDITIONS or name not in (*ARMS, "marginal")
                        or r["train_seed"] != ("" if sid is None else str(seed))
                        or int(r["episode_seed"]) != g + 20000 or (name == "marginal" and seed != 1)
                        or not 0 <= outcome[1] <= outcome[0] <= 20 or not 0 <= outcome[2] <= outcome[3] == 16):
                    raise ValueError(f"duplicate or invalid row {key}")
                rows[key] = outcome
    expected = len(EVAL_GRAPHS) * len(CONDITIONS) * (1 + len(ARMS) * len(SEEDS))
    if len(rows) != expected:
        raise ValueError("evaluation matrix is incomplete")
    for g in EVAL_GRAPHS:
        starts = {rows[c, a, s, g][0] for c in CONDITIONS for a in (*ARMS, "marginal")
                  for s in (SEEDS if a != "marginal" else [None])}
        if len(starts) != 1:
            raise ValueError(f"initial outcomes unpaired on graph {g}")
    return rows, histories, files


def curves(run, histories):
    fields = ["phase", "arm", "train_seed", "from_episode", "through_episode", "sink_errors"]
    rows = []
    for (seed, arm), log in histories.items():
        for j in range(0, EPISODES, 48):
            vals = [r["sink_errors"] for r in log["training"][j:j + 48]]
            rows.append(("training", arm, seed, j + 1, j + 48, mean(vals)))
        for row in log["validation"]:
            rows.append(("validation", arm, seed, row["episode"], row["episode"], row["mean_sink_errors"]))
    path = run / "curves.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(fields)
        writer.writerows(rows)
    fig = Figure(figsize=(10, 4.4), layout="constrained")
    axes = fig.subplots(1, 2)
    for ax, phase, title in zip(axes, ["training", "validation"],
                                ["Training · sampled choices", "Validation · highest-ranked choice"]):
        for arm, label, color in (("terminal", "A · terminal reward", "#416494"),
                                  ("future", "B · reward-to-go", "#a54b28")):
            steps = sorted({r[4] for r in rows if r[:2] == (phase, arm)})
            values = [mean(r[-1] for r in rows if r[:2] == (phase, arm) and r[4] == t) for t in steps]
            ax.plot(steps, values, marker="o", color=color, label=label)
        ax.set_title(title, fontsize=11)
        ax.set_xlabel("Training episodes")
        ax.set_ylabel("Remaining conclusion errors")
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(frameon=False, fontsize=9)
    fig.suptitle("Learning curves averaged across five paired training seeds")
    fig.savefig(run / "curves.png", dpi=160)


def analyze(run):
    rows, histories, files = verified_inputs(run)
    curves(run, histories)
    summary = {}
    for c in CONDITIONS:
        data = {a: np.array([[rows[c, a, s, g][1] for g in EVAL_GRAPHS] for s in SEEDS]) for a in ARMS}
        base = np.array([rows[c, "marginal", None, g][1] for g in EVAL_GRAPHS])
        delta = data["future"] - data["terminal"]
        summary[c] = {"means": {a: float(m.mean()) for a, m in data.items()}, "rule": float(base.mean()),
                      "future_minus_terminal": paired_bootstrap(delta, np.zeros_like(base)),
                      "vs_rule": {a: paired_bootstrap(m, base) for a, m in data.items()},
                      "by_seed": {a: m.mean(axis=1).tolist() for a, m in data.items()},
                      "worst_seed_mean_errors": {a: float(m.mean(axis=1).max()) for a, m in data.items()}}
    selected = {a: [histories[s, a]["selected_episode"] for s in SEEDS] for a in ARMS}
    files.update({path: sha256(path) for path in [Path(__file__).resolve(), EXPERIMENTS / "rl_boundary.py",
                  run / "protocol.md", run / "curves.csv", run / "curves.png"]})
    return {"conditions": summary, "selected_episodes": selected, "evaluation_rows": len(rows),
            "train_seeds": list(SEEDS), "graph_range_inclusive": [EVAL_GRAPHS.start, EVAL_GRAPHS.stop - 1],
            "bootstrap": {"draws": 10000, "seed": 20261112, "coverage": 0.95},
            "sha256": {path.relative_to(ROOT).as_posix(): digest for path, digest in files.items()}}


def describe_diagnostic(run):
    diag = json.loads((run / "diagnostic.json").read_text(encoding="utf-8"))
    if (diag["updates"] != 0 or diag["episodes_per_seed"] != 24
            or diag["source_sha256"] != sha256(Path(__file__).with_name("credit_diagnostic.py"))
            or diag["training_source_sha256"] != sha256(Path(__file__).with_name("train_credit.py"))):
        raise ValueError("diagnostic sources or sample size differ from protocol")
    pairs = [diag["seeds"][str(s)] for s in SEEDS]
    drops = [1 - pair["future"]["covariance_trace"] / pair["terminal"]["covariance_trace"] for pair in pairs]
    zeros = {arm: sum(p[arm]["zero_gradients"] for p in pairs) for arm in ARMS}
    better_cosine = sum(pair["future"]["mean_pairwise_cosine_nonzero"] > pair["terminal"]["mean_pairwise_cosine_nonzero"]
                        for pair in pairs)
    return (f"학습 전 다섯 모델에서 각각 같은 24개 경로의 보상만 바꿔 봤다. "
            f"B의 기울기 변동(표본 공분산 대각합)이 더 작은 시드는 {sum(d > 0 for d in drops)}/5개였고 "
            f"감소율은 시드에 따라 {min(drops):.1%}–{max(drops):.1%}였다. 업데이트 신호가 완전히 0인 경로는 "
            f"전체 120개 중 A {zeros['terminal']}개, B {zeros['future']}개였다. 0이 아닌 경로끼리 업데이트 방향의 "
            f"평균 코사인 유사도가 높아진 시드는 {better_cosine}/5개였다. 이 진단은 초기 상태 120개 경로에 해당한다. "
            "[시드별 변동·방향·0인 횟수](diagnostic.json)")


def report(run, result, diagnostic_note):
    summaries = result["conditions"]
    primary = summaries["shuffled"]
    gap = primary["future_minus_terminal"]
    interpretation = ("이 학습량에서 행동별 보상이 오류를 줄였다는 기준을 충족했다." if gap["high"] < 0 else
                      "이 학습량에서는 종료 보상이 오류를 더 적게 남겼다." if gap["low"] > 0 else
                      "95% 구간에 0이 들어가서 이 학습량에서 행동별 보상이 더 나았는지는 확정하기 어렵다.")
    lines = ["# 어떤 검토에 보상을 주느냐에 따른 GNN의 성능", "",
             f"점수를 유형 안에서 전부 섞은 주 비교에서 A는 최종 결론 20개 중 평균 "
             f"**{primary['means']['terminal']:.3f}개**, B는 **{primary['means']['future']:.3f}개**를 "
             f"틀린 채 남겼다. B에서 A를 뺀 차이는 **{format_gap(gap)}개**다. {interpretation}", "",
             "한 그래프에서 사람이 검토할 수 있는 항목은 80개 중 16개다. A는 16회를 다 끝냈을 때의 "
             "결과를 모든 선택에 동일하게 반영한다. B는 각 선택을 하기 전부터 마지막까지 개선된 수만 "
             "그 선택에 반영한다. 두 방식 모두 같은 사례에서 기준 규칙이 달성한 개선량을 뺀다. "
             "예를 들어 첫 5회에 해결한 오류는 B에서 여섯 번째 선택의 보상에 들어가지 않는다.", "",
             "| 공개 점수 조건 | A 종료 보상 | B 행동별 보상 | 하류 영향 규칙 | B − A [95% 구간] | B − 규칙 [95% 구간] |",
             "|---|---:|---:|---:|---:|---:|"]
    for c in ("shuffled", "matched", "uniform"):
        q = summaries[c]
        lines.append(f"| {LABELS[c]} | {q['means']['terminal']:.3f} | {q['means']['future']:.3f} | "
                     f"{q['rule']:.3f} | {format_gap(q['future_minus_terminal'])} | "
                     f"{format_gap(q['vs_rule']['future'])} |")
    lines += ["", "작을수록 검토 이후에 잘못 남은 결론이 적다. 하류 영향 규칙은 검토 결과로 점수를 믿을지 "
              "갱신하면서 여러 결론에 영향을 미칠 수 있는 항목을 우선 확인한다. "
              "그래프 200개와 학습 시드 5개를 각각 재표집해 95% 구간을 구했다. "
              "같은 시드와 그래프에서 두 정책의 결과는 항상 짝으로 묶었다.", "",
              "## 시드별 결과와 학습 경과", "",
              "| 학습 시드 | A 선택 회차 | B 선택 회차 | 전체 순열 A 오류 | 전체 순열 B 오류 |",
              "|---:|---:|---:|---:|---:|"]
    for i, s in enumerate(SEEDS):
        lines.append(f"| {s} | {result['selected_episodes']['terminal'][i]} | {result['selected_episodes']['future'][i]} | "
                     f"{primary['by_seed']['terminal'][i]:.3f} | {primary['by_seed']['future'][i]:.3f} |")
    worst = primary["worst_seed_mean_errors"]
    lines += ["", f"순열에서 오류가 가장 많이 남은 시드의 평균은 A {worst['terminal']:.3f}개와 "
              f"B {worst['future']:.3f}개였다. 학습 곡선은 시드마다 48회씩 묶은 평균, 검증 곡선은 "
              "0·192·384회차에 고정 그래프 24개의 세 조건을 평가한 값이다. [곡선 그림](curves.png) · "
              "[시드별 곡선 원자료](curves.csv)", "", "## 초기 정책의 기울기 변동", "", diagnostic_note, "",
              "## 재현", "", "A의 기존 체크포인트·훈련 설정·실행 환경·학습 로그 해시를 확인했다. B는 시드 "
              "1–5 각각에 대해 384개 사례(조건별 128개)를 같은 순서·초기 가중치로 다시 학습했다. "
              "각 사례의 기준 규칙 결과, 첫 학습 사례 결과, 0회차 검증 점수가 일치했다. "
              "두 방식 모두 같은 검증 기준으로 가중치를 결정한 다음 새 그래프 96000–96199에서 평가했다. "
              "시뮬레이터의 단계별 정답은 전체 행동이 끝난 뒤에만 학습 보상을 계산하는 데 사용했다.", "",
              "저장소 루트에서 훈련 명령을 시드 1–5에 각각 실행한다. 기존 완료 파일을 사용하면 "
              "저장된 입력과 가중치를 확인한다. 별도 재실행에는 새 폴더에 [실행 전 조건](protocol.md)을 "
              "복사하고 세 명령의 출력 경로를 같은 폴더에 맞춘다.", "",
              "```powershell", "1..5 | ForEach-Object { python 'role2_규리/train_credit.py' --seed $_ }",
              "python 'role2_규리/credit_diagnostic.py'",
              "python 'role2_규리/report_credit.py'", "```", "",
              "원자료는 각 폴더의 `episodes.csv`, B의 16회 보상 경로는 `training.json`에 있다. "
              "[시드 1](seed-1/episodes.csv) · [시드 2](seed-2/episodes.csv) · [시드 3](seed-3/episodes.csv) · "
              "[시드 4](seed-4/episodes.csv) · [시드 5](seed-5/episodes.csv) · [수치와 검증 해시](summary.json)", ""]
    confirmation = run / "confirmation" / "confirmation.md"
    if confirmation.is_file():
        lines.extend(["[새 그래프 200개에서 후보를 고정해 세 규칙과 비교한 결과](confirmation/confirmation.md)", ""])
    (run / "credit.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=RUN)
    args = parser.parse_args()
    run = args.run.resolve()
    result = analyze(run)
    diagnostic = run / "diagnostic.json"
    result["sha256"][diagnostic.relative_to(ROOT).as_posix()] = sha256(diagnostic)
    report(run, result, describe_diagnostic(run))
    write_json(run / "summary.json", result)
