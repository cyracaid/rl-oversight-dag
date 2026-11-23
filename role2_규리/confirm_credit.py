"""Test the five frozen reward-to-go GNNs against three rules on independent shuffled graphs."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import csv
import json
from pathlib import Path

import numpy as np
import torch

from evaluate_conditions import BUDGET, ROOT, evaluate_policy, sha256
from evaluate_feedback import EPSILON, INITIAL_PROBABILITY, fit_signal_gate, run_feedback
from evaluate_planning import evaluate_episode
from evaluate_residual import marginal
from report_conditions import format_gap, paired_bootstrap
from train_credit import HERE, RUN, load_actor, make_case, write_json


GRAPHS = range(98000, 98200)
RULES = ("ignore", "feedback", "two_step")
LABELS = {"ignore": "처음부터 점수 무시", "feedback": "발견 결과로 점수 사용 여부 갱신",
          "two_step": "두 검토를 앞서 계산"}
SEEDS = range(1, 6)


def evaluate_chunk(args):
    chunk, paths, gate = args
    torch.set_num_threads(1)
    actors = [load_actor(path) for path in paths]
    rows = []
    for gs in chunk:
        graph, snap, mode = case = make_case(gs, "shuffled", gate)
        final, initial, flags, reviews = evaluate_policy(graph, snap, "noise", marginal)
        outcomes = [("ignore", "", (initial, final, flags, reviews)),
                    ("feedback", "", run_feedback(*case, marginal)[:4])]
        planner, _ = evaluate_episode(graph, snap, "adaptive", INITIAL_PROBABILITY[mode], BUDGET, EPSILON, False)
        outcomes.append(("two_step", "", planner[:4]))
        for seed, actor in zip(SEEDS, actors):
            outcomes.append(("future", seed, run_feedback(*case, actor)[:4]))
        for label, seed, (start, end, flags, reviews) in outcomes:
            if (start != initial or reviews != BUDGET or not 0 <= end <= start <= 20
                    or not 0 <= flags <= reviews):
                raise ValueError(f"unpaired outcomes in confirmation graph {gs}")
            rows.append((gs, snap.seed, label, seed, start, end, flags, reviews))
    return rows


def main(run, jobs):
    directory = run / "confirmation"
    graph_ids = list(GRAPHS)
    paths = [run / f"seed-{s}/future.pt" for s in SEEDS]
    inputs = [Path(__file__).resolve(), directory / "protocol.md",
              *(HERE / name for name in ["evaluate_planning.py", "evaluate_feedback.py", "planning_policy.py",
                                         "train_credit.py", "train_residual.py", "report_conditions.py"]),
              ROOT / "experiments/rl_boundary.py", *paths]
    for path in paths:
        config = json.loads(path.with_name("config.json").read_text(encoding="utf-8"))
        source_config = ROOT / config["control"]["path"]
        frozen = json.loads(source_config.with_name("config.json").read_text(encoding="utf-8"))
        for name, digest in frozen["source_sha256"].items():
            if sha256(ROOT / name) != digest:
                raise ValueError(f"training source changed: {name}")
        if sha256(path) != json.loads(path.with_name("complete.json").read_text(encoding="utf-8"))[path.name]:
            raise ValueError("candidate weights changed")
    manifest = {"condition": "shuffled", "budget": BUDGET, "graphs": graph_ids, "training_seeds": list(SEEDS),
                "rules": RULES, "source_and_candidate_sha256": {p.relative_to(ROOT).as_posix(): sha256(p) for p in inputs},
                "bootstrap": {"coverage": 0.95, "draws": 10000, "seed": 20261112}}
    gate = fit_signal_gate()
    chunks = [graph_ids[i:i+10] for i in range(0, len(graph_ids), 10)]
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        groups = pool.map(evaluate_chunk, ((chunk, paths, gate) for chunk in chunks))
        rows = [row for group in groups for row in group]
    if len(rows) != len(GRAPHS) * (len(RULES) + len(SEEDS)):
        raise ValueError("missing paired outcomes")
    data = {(label, str(seed), g): end for g, _, label, seed, _, end, _, _ in rows}
    errors = np.array([[data["future", str(s), g] for g in GRAPHS] for s in SEEDS])
    rules = {r: np.array([data[r, "", g] for g in GRAPHS]) for r in RULES}
    means = {"future": float(errors.mean()), **{name: float(x.mean()) for name, x in rules.items()}}
    gaps = {r: paired_bootstrap(errors, scores) for r, scores in rules.items()}
    path = directory / "episodes.csv"
    pending = path.with_suffix(".csv.partial")
    with pending.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["graph_seed", "episode_seed", "policy", "train_seed", "initial_sink_errors", "sink_errors",
                         "flags", "reviews"])
        writer.writerows(rows)
    pending.replace(path)
    manifest.update(episodes_sha256=sha256(path), means=means, future_minus_rule=gaps,
                    by_seed_future=errors.mean(axis=1).tolist(), all_upper_below_zero=all(x["high"] < 0 for x in gaps.values()))
    write_json(directory / "manifest.json", manifest)
    statement = ("세 규칙 모두보다 결론 오류를 적게 남겼다." if manifest["all_upper_below_zero"] else
                 "세 규칙 모두보다 잘했다는 판정 기준을 충족하지 못했다.")
    lines = ["# 새 그래프 200개에서 규칙과 비교한 결과", "",
             f"행동별 보상을 학습한 GNN은 검토 16회 후 결론 20개 중 평균 **{means['future']:.3f}개**의 오류를 남겼다. "
             + statement, "", "| 비교 규칙 | 규칙의 평균 잔여 오류 | GNN − 규칙 [95% 구간] |", "|---|---:|---:|"]
    for r in RULES:
        lines.append(f"| {LABELS[r]} | {means[r]:.3f} | {format_gap(gaps[r])} |")
    lines += ["", "모든 유형에서 점수를 섞은 새 그래프 98000–98199만 사용했다. 음수는 GNN이 오류를 더 적게 "
              "남겼다는 뜻이다. 범위는 5개 학습 시드와 200개 평가 그래프를 따로 재표집한 짝지은 95% 구간이다. "
              "후보 정책과 조건은 앞선 보상 비교 결과를 본 뒤 정했고 이 200개 그래프를 열기 전에 고정했다.",
              "", "저장소 루트에서 `python 'role2_규리/confirm_credit.py'`로 재실행할 수 있다.", "",
              "[실행 전 조건](protocol.md) · [그래프별 원자료](episodes.csv) · [가중치 해시와 구간 추정](manifest.json)", ""]
    (directory / "confirmation.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"means": means, "future_minus_rule": gaps}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=RUN)
    parser.add_argument("--jobs", type=int, default=4, choices=range(1, 17))
    args = parser.parse_args()
    main(args.run.resolve(), args.jobs)
