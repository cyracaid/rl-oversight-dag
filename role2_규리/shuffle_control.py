"""Run the within-type confidence permutation on a completed Role 2 evaluation."""

import argparse
from dataclasses import replace
from functools import partial
import json
from pathlib import Path

import numpy as np

from evaluate_conditions import (ROOT, choose, evaluate_policy, generate_graph, infer_signal_mode,
                                load_policy, sample_episode, sha256)
from report_conditions import load_episodes, paired_bootstrap


def shuffle_within_type(snapshot, types, episode_seed):
    """Permute public scores inside fixed node types without changing the episode truth."""
    rng = np.random.default_rng(episode_seed + 173)
    original = np.array(snapshot.confidence)
    scores = original.copy()
    types = np.asarray(types)
    for node_type in np.unique(types):
        ids = np.flatnonzero(types == node_type)
        scores[ids] = rng.permutation(original[ids])
        if not np.array_equal(np.sort(scores[ids]), np.sort(original[ids])):
            raise ValueError(f"changed confidence multiset for type {node_type}")
    return replace(snapshot, confidence=tuple(scores))


def measure(run):
    manifest_path = run / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    episodes = run / "episodes.csv"
    if sha256(episodes) != manifest["episodes_sha256"]:
        raise ValueError("episode CSV differs from completed evaluation")
    cells = load_episodes(episodes, manifest)
    for name, digest in manifest["source_sha256"].items():
        if sha256(ROOT / name) != digest:
            raise ValueError(f"source differs from completed evaluation: {name}")
    observed = {}
    for name, checkpoint in manifest["checkpoints"].items():
        if name.startswith("gnn_s") and name.removeprefix("gnn_s").isdigit():
            path = ROOT / checkpoint["path"]
            if sha256(path) != checkpoint["sha256"]:
                raise ValueError(f"checkpoint changed: {name}")
            family, label, act = load_policy(path)
            if family != "spike" or name != label:
                raise ValueError(f"checkpoint does not match manifest: {name}")
            observed[name] = act
    if not observed:
        raise ValueError("an observed Spike GNN checkpoint is required")

    policies = {"confidence": partial(choose, name="confidence"),
                "marginal": partial(choose, name="marginal"),
                "prior_marginal": partial(choose, name="marginal"), **observed}
    names = [*policies, "adaptive_marginal"]
    matched = {name: cells["matched", name][:, 0].tolist() for name in names if name != "prior_marginal"}
    matched["prior_marginal"] = []
    shuffled = {name: [] for name in names}
    modes = []
    gate = manifest["signal_gate"]
    for index, (gseed, eseed) in enumerate(zip(manifest["graph_seeds"], manifest["episode_seeds"])):
        graph = generate_graph("spike", gseed)
        original = sample_episode(graph, eseed, "normal")
        permuted = shuffle_within_type(original, graph.types, eseed)
        inferred = infer_signal_mode(permuted.confidence, gate)
        recorded = "noise" if cells["matched", "adaptive_marginal"][index, 4] else "normal"
        if infer_signal_mode(original.confidence, gate) != inferred or inferred != recorded:
            raise ValueError(f"preserved scores changed the gate decision on graph {gseed}")
        modes.append(inferred)
        initial = int(cells["matched", "confidence"][index, :2].sum())
        for name, policy in policies.items():
            assumed = "noise" if name == "prior_marginal" else "normal"
            final, before, _, reviews = evaluate_policy(graph, permuted, assumed, policy)
            if before != initial or reviews != manifest["budget"]:
                raise ValueError(f"unpaired trial on graph {gseed}")
            shuffled[name].append(final)
        # Both branches were evaluated above; select using the public scores only.
        branch = "prior_marginal" if inferred == "noise" else "marginal"
        shuffled["adaptive_marginal"].append(shuffled[branch][-1])
        fallback, _, _, _ = evaluate_policy(graph, original, "noise", policies["prior_marginal"])
        matched["prior_marginal"].append(fallback)
        if fallback != shuffled["prior_marginal"][-1]:
            raise ValueError(f"confidence-blind reference changed on graph {gseed}")
        if (index + 1) % 50 == 0:
            print(f"Permuted {index + 1} graphs", flush=True)

    summaries = {}
    for name in names:
        errors = np.array(shuffled[name])
        summaries[name] = {
            "matched_mean": float(np.mean(matched[name])), "shuffled_mean": float(errors.mean()),
            "shuffled_minus_matched": paired_bootstrap(errors[None, :], matched[name]),
        }
    contrast = paired_bootstrap(np.array(shuffled["adaptive_marginal"])[None, :],
                                shuffled["prior_marginal"])
    sources = [Path(__file__).resolve(), Path(__file__).with_name("report_conditions.py").resolve(),
               ROOT / "experiments" / "rl_boundary.py"]
    return {
        "manifest_sha256": sha256(manifest_path), "episodes_sha256": manifest["episodes_sha256"],
        "source_sha256": {p.relative_to(ROOT).as_posix(): sha256(p) for p in sources},
        "checkpoints": {label: manifest["checkpoints"][label] for label in observed},
        "seed_rule": "numpy.default_rng(episode_seed + 173); ascending type and node IDs",
        "bootstrap": {"draws": 10000, "seed": 20261112, "unit": "paired graph"},
        "budget": manifest["budget"], "graph_seeds": manifest["graph_seeds"],
        "episode_seeds": manifest["episode_seeds"], "signal_gate": gate, "inferred_modes": modes,
        "unchanged_modes": len(modes), "normal_modes": modes.count("normal"),
        "matched_sink_errors": matched, "shuffled_sink_errors": shuffled, "summaries": summaries,
        "adaptive_minus_prior_marginal": contrast,
    }


def write_report(run, result):
    c = result["adaptive_minus_prior_marginal"]
    lines = [
        "# 같은 유형 안에서 신뢰도 순서를 섞은 대조 실험", "",
        f"기본 실험의 정상 신호 그래프 {len(result['graph_seeds'])}개에서 같은 노드 유형 안의 "
        "신뢰도 값을 한 번씩 재배정했다. 모든 유형의 신뢰도 값과 빈도를 그대로 보존했다. "
        "동일한 초기 오류·전파·검토자 난수를 유지하고 정책마다 16회 검토 후 결론 오류를 셌다.", "",
        f"신호 모형 선택은 {result['unchanged_modes']}개 그래프 모두에서 같았고, "
        f"그중 {result['normal_modes']}개를 정상으로 분류했다. 평균 신뢰도가 같아도 "
        "어느 노드에 점수가 붙는지에 따라 정책 성능이 달라질 수 있다.", "",
        "| 정책 | 원래 평균 오류 | 재배정 후 평균 오류 | 변화량 [95% 구간] |",
        "|---|---:|---:|---:|",
    ]
    for name, row in result["summaries"].items():
        gap = row["shuffled_minus_matched"]
        lines.append(f"| {name} | {row['matched_mean']:.3f} | {row['shuffled_mean']:.3f} | "
                     f"{gap['mean']:+.3f} [{gap['low']:+.3f}, {gap['high']:+.3f}] |")
    lines += ["", "재배정 후 자동 선택 규칙의 평균 잔여 오류에서 신뢰도를 배제하고 유형 사전확률과 "
              f"하류 영향을 쓰는 규칙의 값을 빼면 **{c['mean']:+.3f}**였다 "
              f"(짝지은 그래프 95% 구간 [{c['low']:+.3f}, {c['high']:+.3f}]).", "",
              "구간은 체크포인트를 고정해 그래프 단위로 계산했다. 각 그래프에서 유형별로 한 번 "
              "재배정했으므로 일부 원래 대응과 우연한 연관성이 남을 수 있다. 이는 기존 개발 "
              "그래프에 적용한 후속 대조 실험이다.", ""]
    outputs = {"shuffle_control.md": "\n".join(lines),
               "shuffle_control.json": json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n"}
    for name, text in outputs.items():
        pending = run / (name + ".partial")
        pending.write_text(text, encoding="utf-8")
        pending.replace(run / name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path, help="completed confidence evaluation directory")
    args = parser.parse_args()
    write_report(args.run, measure(args.run))
