"""Evaluate confidence policies with nested, type-balanced partial score shuffles."""

import argparse
import csv
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from functools import partial
import json
from pathlib import Path
import platform

import numpy as np

from evaluate_conditions import (BUDGET, ROLE3, ROOT, choose, evaluate_policy, fit_signal_gate,
                                 generate_graph, infer_signal_mode, sample_episode, sha256)
from evaluate_feedback import P_CATCH, run_feedback
from shuffle_control import shuffle_within_type


APPROACHES = ("trust", "ignore", "feedback")
FIELDS = ("graph_seed", "episode_seed", "shuffled_type_count", "shuffled_types", "changed_nodes",
          "nodes", "gate", "approach", "initial_sink_errors", "sink_errors", "flags", "reviews",
          "noise_actions", "actions")


def partial_cases(graph, graph_seed, episode_seed):
    """Build the evaluator's cases. Only the resulting public scores reach a policy."""
    original = sample_episode(graph, episode_seed, "normal")
    shuffled = shuffle_within_type(original, graph.types, episode_seed)
    types = np.asarray(graph.types)
    type_ids = np.unique(types)
    if len(type_ids) != 5:
        raise ValueError("expected five Spike types")
    offset = graph_seed % len(type_ids)
    block_seed = graph_seed - offset + 420001
    order = np.roll(np.random.default_rng(block_seed).permutation(type_ids), -offset)
    for k in range(6):
        selected = tuple(int(t) for t in order[:k])
        scores = tuple(np.where(np.isin(types, selected), shuffled.confidence, original.confidence))
        if (k == 0 and scores != original.confidence) or (k == 5 and scores != shuffled.confidence):
            raise ValueError("partial shuffling endpoints disagree with the original experiment")
        changes = int(np.count_nonzero(np.asarray(scores) != original.confidence))
        yield k, selected, changes, replace(original, confidence=scores)


def evaluate_case(graph, snapshot, gate):
    outputs = {}
    initial_mode = infer_signal_mode(snapshot.confidence, gate)
    for name in APPROACHES:
        actions = []

        def record_choice(obs):
            action = choose(obs, name="marginal")
            actions.append(action)
            return action

        if name == "feedback":
            initial, final, flags, reviews, noise_actions, _ = run_feedback(
                graph, snapshot, initial_mode, record_choice)
        else:
            assumed_mode = "normal" if name == "trust" else "noise"
            final, initial, flags, reviews = evaluate_policy(graph, snapshot, assumed_mode, record_choice)
            noise_actions = reviews if assumed_mode == "noise" else 0
        if reviews != BUDGET or len(set(actions)) != BUDGET or not 0 <= final <= initial <= len(graph.sinks):
            raise ValueError("inconsistent budget, unique action count or sink errors")
        outputs[name] = (initial, final, flags, reviews, noise_actions, tuple(actions))
    return outputs


def evaluate_graph(graph_seed, gate):
    graph = generate_graph("spike", graph_seed)
    if graph.n != 80 or len(graph.sinks) != 20:
        raise ValueError("unexpected graph dimensions")
    episode_seed = graph_seed + 20000
    records = []
    ignore_reference = None
    initial_gate = None
    for k, selected, changes, snapshot in partial_cases(graph, graph_seed, episode_seed):
        mode = infer_signal_mode(snapshot.confidence, gate)
        results = evaluate_case(graph, snapshot, gate)
        if k == 0:
            ignore_reference = results["ignore"]
            initial_gate = mode
        if results["ignore"] != ignore_reference or mode != initial_gate:
            raise ValueError(f"blind trajectory or score gate changed on graph {graph_seed}")
        for name, (initial, final, flags, reviews, noise_actions, actions) in results.items():
            if initial != ignore_reference[0]:
                raise ValueError(f"unpaired initial errors on graph {graph_seed}")
            records.append((graph_seed, episode_seed, k, " ".join(map(str, selected)), changes,
                            graph.n, mode, name, initial, final, flags, reviews, noise_actions,
                            " ".join(map(str, actions))))
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--start", type=int, default=95000)
    parser.add_argument("--graphs", type=int, default=200)
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    if args.start % 5 or args.graphs <= 0 or args.graphs % 5 or args.workers < 1:
        parser.error("choose complete, aligned five-graph blocks and at least one worker")
    args.out.mkdir(parents=True, exist_ok=False)
    seeds = range(args.start, args.start + args.graphs)
    gate = fit_signal_gate()
    evaluate = partial(evaluate_graph, gate=gate)
    pending = args.out / "episodes.csv.partial"
    with pending.open("w", newline="", encoding="utf-8") as stream, ProcessPoolExecutor(args.workers) as pool:
        writer = csv.writer(stream)
        writer.writerow(FIELDS)
        batches = pool.map(evaluate, seeds) if args.workers > 1 else map(evaluate, seeds)
        for n, batch in enumerate(batches, 1):
            writer.writerows(batch)
            if n % 25 == 0 or n == args.graphs:
                stream.flush()
                print(f"Completed {n}/{args.graphs} paired graphs", flush=True)
    episodes = args.out / "episodes.csv"
    pending.replace(episodes)
    here = Path(__file__).resolve()
    sources = [here, here.with_name("부분손상실행안.md"), here.with_name("shuffle_control.py"),
               here.with_name("evaluate_conditions.py"), here.with_name("evaluate_feedback.py"),
               here.with_name("signal_calibration.py"), ROLE3 / "dag_role3" / "policies.py",
               ROLE3 / "dag_role3" / "graphs.py", ROLE3 / "dag_role3" / "environment.py"]
    manifest = {
        "status": "complete", "graph_start": args.start, "graphs": args.graphs, "nodes": 80,
        "sink_nodes": 20, "budget": BUDGET, "p_catch": P_CATCH, "episode_seed_offset": 20000,
        "conditions": list(range(6)), "approaches": APPROACHES, "signal_gate": gate,
        "primary_condition": 2, "bootstrap": {"unit": "paired graph", "draws": 10000, "seed": 20261112},
        "type_order": "default_rng(graph_seed - graph_seed % 5 + 420001), rotate left by graph_seed % 5",
        "score_permutation": "shuffle_within_type, episode_seed + 173, prefix of type order",
        "python": platform.python_version(), "numpy": np.__version__, "episodes_sha256": sha256(episodes),
        "source_sha256": {p.relative_to(ROOT).as_posix(): sha256(p) for p in sources},
    }
    receipt = args.out / "manifest.json.partial"
    receipt.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    receipt.replace(args.out / "manifest.json")


if __name__ == "__main__":
    main()
