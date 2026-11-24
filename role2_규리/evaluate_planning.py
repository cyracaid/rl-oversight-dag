"""Evaluate four public-observation review policies on paired v3 Spike graphs."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import csv
from dataclasses import replace
import json
import math
import os
from pathlib import Path
import platform
import sys

import numpy as np

HERE = Path(__file__).resolve()
from _env import ROLE3, ROOT, ensure_role3

ensure_role3()
from dag_role3 import OversightEnv, generate_graph, sample_episode
from dag_role3.policies import choose
from planning_policy import P_CATCH, WIDTH, PlanningPolicy


CONDITIONS = ("matched", "uniform", "shuffled")
POLICIES = ("hard", "mixture", "open_loop", "adaptive")
FIELDS = ("graph_seed", "episode_seed", "condition", "policy", "initial_sink_errors",
          "sink_errors", "flags", "reviews", "planning_steps", "greedy_disagreements",
          "loop_disagreements", "branch_disagreements")
TRACE_FIELDS = ("graph_seed", "episode_seed", "condition", "policy", "step", "action",
                "greedy_action", "open_loop_action", "flag_next", "miss_next",
                "flag_prob", "flagged", "log_odds")


def evaluate_episode(graph, snapshot, label, initial_probability, budget, epsilon, save_trace):
    normal, noise = (OversightEnv(graph, snapshot, budget, p_catch=P_CATCH, confidence_mode=mode)
                     for mode in ("normal", "noise"))
    normal_obs, noise_obs = normal.observation(), noise.observation()
    planner = None if label == "hard" else PlanningPolicy(normal_obs)
    log_odds = math.log(initial_probability / (1.0 - initial_probability))
    planning_steps = greedy_disagreements = loop_disagreements = branch_disagreements = 0
    trace = []
    for step in range(1, budget + 1):
        if planner is None:
            action = choose(normal_obs if log_odds >= 0 else noise_obs, "marginal")
        else:
            decision = planner.decide(normal_obs, noise_obs, log_odds, label)
            action = decision.action
            if label in ("open_loop", "adaptive") and step < budget and normal_obs["mask"].sum() >= 2:
                if min(decision.adaptive_action, decision.open_loop_action,
                       decision.flag_next, decision.miss_next) < 0:
                    raise ValueError("missing two-step diagnostic on an eligible review")
                planning_steps += 1
                greedy_disagreements += int(action != decision.greedy_action)
                loop_disagreements += int(decision.adaptive_action != decision.open_loop_action)
                branch_disagreements += int(decision.flag_next != decision.miss_next)

        # Same public, clipped reviewer likelihoods used by the existing feedback router.
        p_normal, p_noise = (min(1.0 - epsilon, max(epsilon, P_CATCH * float(obs["features"][action, -4])))
                             for obs in (normal_obs, noise_obs))
        normal_obs, _, _, normal_info = normal.step(action)
        noise_obs, _, _, noise_info = noise.step(action)
        flagged = normal_info["flagged"]
        if flagged != noise_info["flagged"]:
            raise ValueError("the two belief models received different reviewer outcomes")
        if save_trace:
            trace.append((step, action, decision.greedy_action, decision.open_loop_action,
                          decision.flag_next, decision.miss_next, decision.flag_prob,
                          int(flagged), log_odds))
        if flagged:
            log_odds += math.log(p_normal) - math.log(p_noise)
        else:
            log_odds += math.log1p(-p_normal) - math.log1p(-p_noise)

    audit = normal.final_audit()
    reviews = len(audit["trace"])
    if reviews != budget:
        raise ValueError("incorrect number of completed reviews")
    return (audit["initial_sink_errors"], audit["final_sink_errors"],
            sum(s["flagged"] for s in audit["trace"]), reviews, planning_steps,
            greedy_disagreements, loop_disagreements, branch_disagreements), trace


def graph_jobs(graph_seeds, gate, budget, epsilon, priors):
    # Generate conditions using the earlier experiment's exact pairing and shuffling.
    # These imports include training dependencies; only the coordinator needs them.
    from evaluate_conditions import paired_snapshots
    from shuffle_control import shuffle_within_type
    from signal_calibration import infer_signal_mode

    for index, seed in enumerate(graph_seeds):
        episode_seed = seed + 20000
        graph = generate_graph("spike", seed)
        snapshots = paired_snapshots(graph, episode_seed)
        normal, noise = snapshots["normal"], snapshots["noise"]
        shuffled = shuffle_within_type(normal, graph.types, episode_seed)
        conditions = [(label, snap.confidence, priors[infer_signal_mode(snap.confidence, gate)])
                      for label, snap in zip(CONDITIONS, (normal, noise, shuffled))]
        yield seed, episode_seed, conditions, budget, epsilon, index == 0


def evaluate_graph(job):
    seed, episode_seed, conditions, budget, epsilon, first_graph = job
    graph = generate_graph("spike", seed)
    # The same immutable hidden sample serves every condition. Only public scores vary.
    base = sample_episode(graph, episode_seed, "normal")
    if base.confidence != conditions[0][1]:
        raise ValueError(f"worker and coordinator sampled different episodes on graph {seed}")
    rows, traces = [], []
    initial_errors = None
    for condition, confidence, prior in conditions:
        snapshot = replace(base, confidence=confidence)
        for label in POLICIES:
            prefix = (seed, episode_seed, condition, label)
            outcome, trace = evaluate_episode(graph, snapshot, label, prior, budget, epsilon,
                                              first_graph and label == "adaptive")
            if initial_errors is None:
                initial_errors = outcome[0]
            if initial_errors != outcome[0]:
                raise ValueError(f"unpaired initial errors on graph {seed}")
            rows.append((*prefix, *outcome))
            traces.extend((*prefix, *row) for row in trace)
    return rows, traces


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="new output directory")
    parser.add_argument("--start", type=int, default=94000)
    parser.add_argument("--graphs", type=int, default=200)
    parser.add_argument("--jobs", type=int, default=min(4, os.cpu_count() or 1),
                        help="number of graph workers (1 runs without a process pool)")
    args = parser.parse_args()
    if args.graphs < 1 or args.start < 90000 or args.start + args.graphs > 100000:
        parser.error("choose a positive graph count within the v3 test range [90000, 100000)")
    if not 1 <= args.jobs <= (61 if os.name == "nt" else sys.maxsize):
        parser.error("choose a positive number of supported workers (up to 61 on Windows)")
    out = args.out.resolve()
    if out.exists():
        parser.error(f"output directory already exists: {out}")

    from evaluate_conditions import BUDGET, sha256
    from evaluate_feedback import EPSILON, INITIAL_PROBABILITY, P_CATCH as ROUTER_CATCH
    from signal_calibration import fit_signal_gate

    if P_CATCH != ROUTER_CATCH:
        raise ValueError("reviewer sensitivity differs between planner and feedback reference")
    seeds = list(range(args.start, args.start + args.graphs))
    gate = fit_signal_gate()
    sources = [HERE, *(HERE.with_name(name) for name in (
        "planning_policy.py", "evaluate_conditions.py", "evaluate_feedback.py",
        "signal_calibration.py", "shuffle_control.py", "두단계계획.md")),
        *(ROLE3 / "dag_role3" / name for name in (
            "__init__.py", "environment.py", "graphs.py", "policies.py"))]
    workers = min(args.jobs, len(seeds))
    manifest = {
        "family": "spike", "nodes": 80, "budget": BUDGET, "p_catch": P_CATCH, "particles": 0,
        "conditions": CONDITIONS, "policies": POLICIES, "graph_seeds": seeds,
        "episode_seeds": [s + 20000 for s in seeds], "signal_gate": gate,
        "protocol": {"belief": "v3 mean-field; normal and noise", "width": WIDTH, "horizon": 2,
                     "second_candidates": "all available nodes except the first candidate",
                     "normal_prior_given_gate": INITIAL_PROBABILITY, "hard_log_odds_threshold": 0,
                     "feedback_probability_clip": EPSILON, "shuffle_seed_offset": 173,
                     "planning_steps": "nonfinal reviews with at least two legal nodes, on each two-step policy's own trajectory",
                     "trace": "first graph, adaptive policy; predicted branches before actual reviewer feedback",
                     "primary": "shuffled, adaptive minus mixture final sink errors"},
        "source_sha256": {p.relative_to(ROOT).as_posix(): sha256(p) for p in sources},
        "python": platform.python_version(), "numpy": np.__version__, "jobs": workers,
    }
    out.mkdir(parents=True, exist_ok=False)
    episodes, trace = out / "episodes.csv", out / "trace.csv"
    pending_episodes, pending_trace = (p.with_suffix(".csv.partial") for p in (episodes, trace))
    jobs = graph_jobs(seeds, gate, BUDGET, EPSILON, INITIAL_PROBABILITY)
    with pending_episodes.open("w", encoding="utf-8", newline="") as es, pending_trace.open(
            "w", encoding="utf-8", newline="") as ts:
        ew, tw = csv.writer(es), csv.writer(ts)
        ew.writerow(FIELDS)
        tw.writerow(TRACE_FIELDS)
        pool = ProcessPoolExecutor(max_workers=workers) if workers > 1 else None
        try:
            results = pool.map(evaluate_graph, jobs) if pool else map(evaluate_graph, jobs)
            for index, (rows, traces) in enumerate(results, start=1):
                ew.writerows(rows)
                tw.writerows(traces)
                if index == 1 or index % 10 == 0 or index == len(seeds):
                    es.flush()
                    ts.flush()
                    print(f"Evaluated {index}/{len(seeds)} paired graphs", flush=True)
        finally:
            if pool:
                pool.shutdown(wait=True, cancel_futures=True)
    pending_episodes.replace(episodes)
    pending_trace.replace(trace)
    manifest.update(status="complete", episodes_sha256=sha256(episodes), trace_sha256=sha256(trace))
    receipt = out / "manifest.json.partial"
    receipt.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    receipt.replace(out / "manifest.json")
    print(f"Completed {out}", flush=True)


if __name__ == "__main__":
    main()
