"""Replay the first shuffled-case disagreement, selected without terminal scores."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import torch

from evaluate_conditions import ROOT, sha256
from evaluate_feedback import run_feedback
from evaluate_residual import marginal
from train_residual import GainActor, make_case, marginal_scores


@torch.inference_mode()
def write_trace(run):
    evaluation = run / "eval"
    meta = json.loads((evaluation / "manifest.json").read_text(encoding="utf-8"))
    episodes = evaluation / "episodes.csv"
    if meta["status"] != "complete" or sha256(episodes) != meta["episodes_sha256"]:
        raise ValueError("incomplete run or changed episodes.csv")
    with episodes.open(encoding="utf-8", newline="") as stream:
        shuffled = [r for r in csv.DictReader(stream) if r["condition"] == "shuffled"]
    residuals = sorted((r for r in shuffled if r["policy"].startswith("residual_s")),
                       key=lambda r: (int(r["policy"].split("_s")[1]), int(r["graph_seed"])))
    row = next((r for r in residuals if int(r["disagreements"]) > 0), residuals[0])
    base_row = next(r for r in shuffled if r["policy"] == "marginal" and r["graph_seed"] == row["graph_seed"])
    record = meta["checkpoints"][row["policy"]]
    path = ROOT / record["path"]
    if sha256(path) != record["sha256"]:
        raise ValueError(f"changed checkpoint: {path}")
    torch.set_num_threads(1)
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    model = GainActor("residual").eval()
    model.load_state_dict(checkpoint["state_dict"])
    graph, snapshot, mode = make_case(int(row["graph_seed"]), "shuffled", meta["signal_gate"])
    if snapshot.seed != int(row["episode_seed"]):
        raise ValueError("episode seed differs from recorded evaluation")
    actions, rule_actions, states, rule_states = [], [], [], []

    def learned(obs):
        states.append(obs)
        action = model.greedy(obs)
        actions.append(action)
        return action

    def rule(obs):
        rule_states.append(obs)
        action = marginal(obs)
        rule_actions.append(action)
        return action

    for act, expected in ((learned, row), (rule, base_row)):
        initial, final, flags, reviews, _, _ = run_feedback(graph, snapshot, mode, act)
        if (initial, final, flags, reviews) != tuple(int(expected[k]) for k in
                ("initial_sink_errors", "sink_errors", "flags", "reviews")):
            raise ValueError("replay outcomes do not match episodes.csv")
    diffs = [i for i, obs in enumerate(states) if actions[i] != marginal(obs)]
    if len(diffs) != int(row["disagreements"]):
        raise ValueError("replay disagreement count differs from episodes.csv")
    step = diffs[0] if diffs else 0
    obs = states[step]
    if (actions[:step] != rule_actions[:step] or marginal(obs) != rule_actions[step]
            or not np.array_equal(obs["features"], rule_states[step]["features"])):
        raise ValueError("policies did not share the public history through the illustrated decision")
    gains = marginal_scores(obs)
    maximum = gains[obs["mask"]].max()
    if maximum > 0:
        gains = gains / maximum
    scores, _ = model(obs)
    heading = "첫 선택 차이" if diffs else "동일한 첫 선택"
    selection = ("선택 차이가 있는 시드·그래프 중 번호가 가장 작은 조합을 사용했다." if diffs else
                 "모든 잔차 정책이 규칙과 같은 행동을 골라 번호가 가장 작은 시드·그래프의 첫 선택을 사용했다.")
    lines = [f"# 유형 내 점수 섞기에서의 {heading}", "", selection,
             f"학습 시드 {record['train_seed']}, 그래프 {row['graph_seed']}, 에피소드 {snapshot.seed}에서 "
             f"{step + 1}번째 검토 직전 남은 예산은 {obs['budget_left']}회였다. "
             f"여기까지 완료한 {step}회의 검토 이력은 두 정책에서 같았다.", "",
             "| 선택한 정책 | 노드 ID | 유형 | 원천 오류 추정확률 | 직접 자식 수 | 도달 가능한 결론 수 | "
             "정규화 marginal | 학습 보정량 | 보정 후 점수 |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for label, node in (("잔차 GNN", actions[step]), ("marginal", rule_actions[step])):
        gain, score = float(gains[node]), float(scores[node])
        lines.append(f"| {label} | {node} | {graph.types[node]} | {obs['features'][node, -5]:.4f} | "
                     f"{len(graph.children[node])} | {graph.sink_reach[node]} | {gain:.6f} | "
                     f"{score - gain:+.6f} | {score:.6f} |")
    lines += ["", "정규화 marginal은 현재 검토 가능한 노드의 최대 하류 영향 점수를 1로 맞춘 값이다. "
              "마지막 두 열은 각 후보에 잔차 GNN을 적용했을 때의 값이다. marginal 규칙은 정규화 marginal로 순위를 정한다.",
              "", f"16회 검토가 끝난 뒤 잔여 결론 오류는 잔차 GNN {row['sink_errors']}개, "
              f"marginal {base_row['sink_errors']}개였다. 최종 오류 수에는 이후의 검토 순서도 반영된다.",
              "", "[에피소드별 원자료](eval/episodes.csv) · [전체 정책 비교](residual.md)", ""]
    (run / "decision.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    write_trace(parser.parse_args().run)
