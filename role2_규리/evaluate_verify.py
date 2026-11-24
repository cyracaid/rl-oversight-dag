"""Pre-registered probe-then-decide experiment (see PREREGISTER_VERIFY.md).

Reuses the corruption grid and the corruption model from ``evaluate_corruption``
but adds one deployable policy, ``verify``:

    if the two hypotheses (scores-as-is vs rank-restored scores) do not disagree
    by more than a calibrated threshold, behave exactly like ``trust``;
    otherwise spend 4 reviews on the most-disagreeing nodes, then commit once to
    the hypothesis the flag outcomes favour and finish the budget with it.

The fallback is *rank restoration*, never the global type prior: the boundary
sweep showed that the prior is ~3x worse than the clean oracle, so a false alarm
that falls back to it costs more than the corruption it was reacting to.
"""

import argparse
import csv
from dataclasses import replace
from functools import partial
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import platform

import numpy as np

from _env import ROLE3, ROOT, ensure_role3

ensure_role3()
from dag_role3 import OversightEnv, generate_graph, sample_episode
from dag_role3.policies import choose
from evaluate_conditions import BUDGET, sha256
from evaluate_corruption import (FRACTIONS, LOCALITIES, SHIFTS, corrupt_snapshot)
from signal_calibration import fit_signal_gate, infer_signal_mode


PROBES = 4
P_CATCH = 0.9
EPSILON = 1e-6
CALIBRATION_START = 70000
CALIBRATION_COUNT = 100
THRESHOLD_QUANTILE = 0.99
FIELDS = ("graph_seed", "episode_seed", "locality", "fraction", "shift", "policy",
          "gate_mode", "chosen_mode", "probes", "llr", "corrupted_nodes", "changed_nodes",
          "initial_sink_errors", "sink_errors", "flags", "reviews")


def flag_risk(observation):
    """Predicted P(a review flags this node) under the observation's own model."""
    return P_CATCH * observation["features"][:, -4].astype(np.float64)


def fit_rank_reference():
    """Pooled clean confidence values on the calibration block (no truth used)."""
    values = []
    for seed in range(CALIBRATION_START, CALIBRATION_START + CALIBRATION_COUNT):
        graph = generate_graph("spike", seed)
        sample = sample_episode(graph, seed + 20000, "normal")
        values.extend(sample.confidence)
    return np.sort(np.asarray(values, dtype=np.float64))


def restore_confidence(confidence, reference):
    """Replace each score by the reference value at the same within-graph rank."""
    values = np.asarray(confidence, dtype=np.float64)
    order = np.argsort(values, kind="stable")
    ranks = np.empty(len(values), dtype=np.float64)
    ranks[order] = np.arange(len(values))
    quantiles = (ranks + 0.5) / len(values)
    return np.quantile(reference, quantiles)


def fit_probe_threshold(reference):
    """Calibrate the probe trigger on clean graphs: 99th percentile of max |dP|."""
    spreads = []
    for seed in range(CALIBRATION_START, CALIBRATION_START + CALIBRATION_COUNT):
        graph = generate_graph("spike", seed)
        clean = sample_episode(graph, seed + 20000, "normal")
        restored = replace(clean, confidence=tuple(restore_confidence(clean.confidence, reference)))
        normal = OversightEnv(graph, clean, BUDGET, p_catch=P_CATCH, confidence_mode="normal")
        rank = OversightEnv(graph, restored, BUDGET, p_catch=P_CATCH, confidence_mode="normal")
        spread = np.abs(flag_risk(normal.observation()) - flag_risk(rank.observation()))
        spreads.append(float(spread.max()))
    spreads = np.asarray(spreads)
    return {
        "quantile": THRESHOLD_QUANTILE, "value": float(np.quantile(spreads, THRESHOLD_QUANTILE)),
        "clean_max_dP": {"min": float(spreads.min()), "median": float(np.median(spreads)),
                         "p99": float(np.quantile(spreads, 0.99)), "max": float(spreads.max())},
        "graph_start": CALIBRATION_START, "graph_count": CALIBRATION_COUNT,
        "episode_seed_offset": 20000,
    }


def finish(env, observation, action_policy):
    while not env.done:
        observation, _, _, _ = env.step(action_policy(observation))
    return env.final_audit()


def run_verify(graph, snapshot, reference, threshold):
    """Probe then commit once; the committed hypothesis is normal or rank, never prior."""
    restored = replace(snapshot, confidence=tuple(restore_confidence(snapshot.confidence, reference)))
    normal = OversightEnv(graph, snapshot, BUDGET, p_catch=P_CATCH, confidence_mode="normal")
    rank = OversightEnv(graph, restored, BUDGET, p_catch=P_CATCH, confidence_mode="normal")
    normal_obs, rank_obs = normal.observation(), rank.observation()
    normal_risk, rank_risk = flag_risk(normal_obs), flag_risk(rank_obs)
    available = np.flatnonzero(normal_obs["mask"])
    trigger = float(np.abs(normal_risk[available] - rank_risk[available]).max()) > threshold

    probes, llr = 0, 0.0
    while trigger and probes < PROBES and not normal.done:
        available = np.flatnonzero(normal_obs["mask"])
        disagreement = np.abs(normal_risk[available] - rank_risk[available])
        action = int(available[np.argmax(disagreement)])
        p_normal = float(np.clip(normal_risk[action], EPSILON, 1 - EPSILON))
        p_rank = float(np.clip(rank_risk[action], EPSILON, 1 - EPSILON))
        normal_obs, _, _, normal_info = normal.step(action)
        rank_obs, _, _, rank_info = rank.step(action)
        if normal_info["flagged"] != rank_info["flagged"]:
            raise ValueError("paired hypotheses saw different reviewer feedback")
        if normal_info["flagged"]:
            llr += np.log(p_normal) - np.log(p_rank)
        else:
            llr += np.log1p(-p_normal) - np.log1p(-p_rank)
        probes += 1
        normal_risk, rank_risk = flag_risk(normal_obs), flag_risk(rank_obs)

    chosen = "rank" if llr < 0 else "normal"
    env, observation = (rank, rank_obs) if chosen == "rank" else (normal, normal_obs)
    audit = finish(env, observation, partial(choose, name="marginal"))
    return audit, probes, float(llr), chosen, trigger


def evaluate_graph(graph_seed, gate, reference, threshold):
    graph = generate_graph("spike", graph_seed)
    if graph.n != 80 or len(graph.sinks) != 20:
        raise ValueError("unexpected graph dimensions")
    episode_seed = graph_seed + 20000
    clean = sample_episode(graph, episode_seed, "normal")
    clean_mode = infer_signal_mode(clean.confidence, gate)
    if clean_mode != "normal":
        raise ValueError(f"clean graph {graph_seed} misclassified as {clean_mode}")
    rows = []
    initial_reference = None

    def emit(locality, fraction, shift, snapshot, corrupted_nodes, changed_nodes):
        nonlocal initial_reference
        if locality == "clean":
            policies = ("oracle", "trust", "prior", "gate", "verify")
        else:
            policies = ("trust", "prior", "gate", "verify")
        mode = clean_mode if locality == "clean" else infer_signal_mode(snapshot.confidence, gate)
        outcome = {}
        for name in policies:
            probes, llr, chosen = 0, 0.0, mode
            if name == "verify":
                audit, probes, llr, chosen, _ = run_verify(graph, snapshot, reference, threshold["value"])
            else:
                if name == "prior":
                    chosen = "noise"
                    confidence_mode = "noise"
                elif name == "gate":
                    confidence_mode = mode
                else:
                    confidence_mode = "normal"
                env = OversightEnv(graph, snapshot, BUDGET, p_catch=P_CATCH,
                                   confidence_mode=confidence_mode)
                audit = finish(env, env.observation(), partial(choose, name="marginal"))
            if initial_reference is None:
                initial_reference = audit["initial_sink_errors"]
            elif audit["initial_sink_errors"] != initial_reference:
                raise ValueError(f"unpaired initial errors on graph {graph_seed}")
            if len(audit["trace"]) != BUDGET:
                raise ValueError(f"review budget violated on {graph_seed}/{locality}/{fraction}/{shift}/{name}")
            outcome[name] = audit["final_sink_errors"]
            rows.append((graph_seed, episode_seed, locality, fraction, shift, name, mode, chosen,
                         probes, round(llr, 6), corrupted_nodes, changed_nodes,
                         audit["initial_sink_errors"], audit["final_sink_errors"],
                         sum(step["flagged"] for step in audit["trace"]), len(audit["trace"])))
        if locality != "clean":
            selected = outcome["prior"] if mode == "noise" else outcome["trust"]
            if outcome["gate"] != selected:
                raise ValueError(f"gate is not a pure selector on {graph_seed}/{locality}/{fraction}/{shift}")

    emit("clean", 0.0, 0.0, clean, 0, 0)
    for locality in LOCALITIES:
        for fraction in FRACTIONS:
            for shift in SHIFTS:
                corrupted, (selected, changed) = corrupt_snapshot(
                    graph, clean, episode_seed, locality, fraction, shift)
                for field in ("source_errors", "edge_coins", "edge_probs", "review_uniforms"):
                    if getattr(corrupted, field) != getattr(clean, field):
                        raise ValueError(f"corruption changed hidden field {field}")
                if changed == 0 and locality != "error_nodes":
                    raise ValueError(f"corruption had no effect on {graph_seed}/{locality}/{fraction}/{shift}")
                emit(locality, fraction, shift, corrupted, len(selected), changed)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="new output directory")
    parser.add_argument("--start", type=int, default=3200,
                        help="first graph seed; 3200-3399 is fresh (corruption-v1 used 3000-3199)")
    parser.add_argument("--graphs", type=int, default=200)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if (args.start < 3200 or args.start + args.graphs > 70000
            or args.graphs < 1 or args.workers < 1):
        parser.error("graph seeds must stay in the fresh range [3200, 70000); "
                     "70000-70099 is calibration and 90000+ is development/test")
    out = args.out.resolve()
    try:
        out.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error(f"output directory already exists: {out}")

    gate = fit_signal_gate()
    reference = fit_rank_reference()
    threshold = fit_probe_threshold(reference)
    print(f"probe threshold (p{THRESHOLD_QUANTILE:.2f} of clean max|dP|) = {threshold['value']:.4f}",
          flush=True)

    graph_seeds = list(range(args.start, args.start + args.graphs))
    evaluate = partial(evaluate_graph, gate=gate, reference=reference, threshold=threshold)
    pending = out / "episodes.csv.partial"
    with pending.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(FIELDS)
        if args.workers > 1:
            with ProcessPoolExecutor(args.workers) as pool:
                for index, rows in enumerate(pool.map(evaluate, graph_seeds), start=1):
                    writer.writerows(rows)
                    if index % 25 == 0 or index == args.graphs:
                        stream.flush()
                        print(f"Evaluated {index}/{args.graphs} graphs", flush=True)
        else:
            for index, graph_seed in enumerate(graph_seeds, start=1):
                writer.writerows(evaluate(graph_seed))
                if index % 25 == 0 or index == args.graphs:
                    stream.flush()
                    print(f"Evaluated {index}/{args.graphs} graphs", flush=True)
    pending.replace(out / "episodes.csv")

    here = Path(__file__).resolve()
    sources = [here, here.with_name("evaluate_corruption.py"), here.with_name("evaluate_conditions.py"),
               here.with_name("evaluate_feedback.py"), here.with_name("signal_calibration.py"),
               ROLE3 / "dag_role3" / "policies.py", ROLE3 / "dag_role3" / "environment.py",
               ROLE3 / "dag_role3" / "graphs.py"]
    manifest = {
        "status": "complete", "family": "spike", "nodes": 80, "sinks": 20, "budget": BUDGET,
        "p_catch": P_CATCH, "particles": 0, "graph_seeds": graph_seeds,
        "episode_seeds": [seed + 20000 for seed in graph_seeds],
        "localities": list(LOCALITIES), "fractions": list(FRACTIONS), "shifts": list(SHIFTS),
        "policies": ["oracle", "trust", "prior", "gate", "verify"], "signal_gate": gate,
        "corruption": "sigmoid(logit(c) + shift) on a deterministic subset of the locality pool",
        "selection_seed_offset": 991,
        "fraction_meaning": "fraction of the locality pool, not of all nodes",
        "probe": {"count": PROBES, "trigger": threshold,
                  "decision": "log-likelihood ratio of the probed flags, normal vs rank",
                  "commit": "once, after the probes; never falls back to the type prior",
                  "rank_reference": "pooled clean confidences on 70000-70099, within-graph rank restored"},
        "preregistration": "PREREGISTER_VERIFY.md",
        "python": platform.python_version(), "numpy": np.__version__,
        "episodes_sha256": sha256(out / "episodes.csv"),
        "source_sha256": {p.relative_to(ROOT).as_posix(): sha256(p) for p in sources},
    }
    receipt = out / "manifest.json.partial"
    receipt.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    receipt.replace(out / "manifest.json")
    print(f"Completed {out}", flush=True)


if __name__ == "__main__":
    main()
