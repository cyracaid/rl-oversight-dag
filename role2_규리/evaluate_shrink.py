"""Pre-registered per-node shrinkage experiment (see PREREGISTER_SHRINK.md).

`verify` failed because a single global statistic cannot tell "the scores moved"
from "the scores are harmful". This experiment replaces the decision variable
itself: each node's source-error posterior is recomputed under a two-component
mixture — the score came from the clean distribution, or the same distribution
shifted by an unknown delta. Only public data enters: the scores, the node types
and their base rates, and the clean-distribution constants that
``dag_role3.environment.initial_belief`` already assumes.

The policy is unchanged (marginal, budget 16). Only its input posterior changes,
node by node, continuously, and in both directions.
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
from evaluate_corruption import (FRACTIONS, LOCALITIES, SHIFTS, corrupt_snapshot,
                                 vector_logit)
from evaluate_feedback import P_CATCH
from signal_calibration import fit_signal_gate, infer_signal_mode


SIGMA = 1.2
MU_ERR = -1.5
MU_GOOD = 1.5
DELTAS = np.array([d * s for d in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0) for s in (-1, 1)])
PIS = tuple(round(0.05 * i, 2) for i in range(13))
CALIBRATION_START = 70000
CALIBRATION_COUNT = 30
CLEAN_COST_LIMIT = 0.05
EPISODE_OFFSET = 20000
POLICIES = ("oracle", "trust", "prior", "gate", "shrink")
CELL_POLICIES = ("trust", "prior", "gate", "shrink")
FIELDS = ("graph_seed", "episode_seed", "locality", "fraction", "shift", "policy",
          "gate_mode", "pi", "belief_shift", "corrupted_nodes", "changed_nodes",
          "initial_sink_errors", "sink_errors", "flags", "reviews",
          "error_rank_trust", "error_rank_shrink")


def gaussian(values, mean):
    return np.exp(-0.5 * ((values - mean) / SIGMA) ** 2) / (SIGMA * np.sqrt(2 * np.pi))


def node_rates(graph):
    return np.array([float(graph.rates[graph.types[i]]) for i in range(graph.n)])


def mixture_belief(graph, snapshot, pi):
    """P(node carries a source error | score), hedging over an unknown shift.

    The clean term is exactly the likelihood ``initial_belief`` uses. The shifted
    term adds a uniform prior over the shift grid, so a score that is extreme in
    the clean model is also credited to the opposite state moved by +-3.
    """
    z = vector_logit(snapshot.confidence)
    rates = node_rates(graph)
    bias = -0.4 * (rates - 0.15)
    honest_err = gaussian(z, MU_ERR + bias)
    honest_good = gaussian(z, MU_GOOD + bias)
    shifted = z[:, None] - DELTAS[None, :]
    moved_err = gaussian(shifted, (MU_ERR + bias)[:, None]).mean(axis=1)
    moved_good = gaussian(shifted, (MU_GOOD + bias)[:, None]).mean(axis=1)
    joint_err = rates * ((1 - pi) * honest_err + pi * moved_err)
    joint_good = (1 - rates) * ((1 - pi) * honest_good + pi * moved_good)
    total = joint_err + joint_good
    return np.divide(joint_err, total, out=np.zeros_like(total), where=total > 0)


def error_rank(belief, errors):
    """Mean 0-based rank of the truly erroneous nodes, 0 = most suspicious.

    Diagnostic only. The policy never sees ``errors``.
    """
    if not errors.any():
        return float("nan")
    order = np.argsort(np.argsort(-np.asarray(belief, dtype=np.float64)))
    return float(order[errors].mean())


def finish(env, observation):
    while not env.done:
        observation, _, _, _ = env.step(partial(choose, name="marginal")(observation))
    return env.final_audit()


def run_shrink(graph, snapshot, pi):
    """Marginal policy with a per-node mixture posterior in place of initial_belief."""
    env = OversightEnv(graph, snapshot, BUDGET, p_catch=P_CATCH, confidence_mode="normal")
    baseline = np.array(env._belief_base, dtype=np.float64)
    belief = mixture_belief(graph, snapshot, pi)
    # step() updates _belief_base in place, so measure the override before the episode runs.
    belief_shift = float(np.abs(belief - baseline).mean())
    env._belief_base = belief
    observed = env.observation()["features"][:, len(graph.rates) + 2]
    if not np.allclose(observed, belief.astype(np.float32), atol=1e-6):
        raise ValueError("belief override did not reach the observation")
    audit = finish(env, env.observation())
    return audit, belief_shift


def plain(graph, snapshot, mode):
    env = OversightEnv(graph, snapshot, BUDGET, p_catch=P_CATCH, confidence_mode=mode)
    return finish(env, env.observation())


def calibration_graph(graph_seed, pis):
    """Clean cost and full-grid cost of every pi on one calibration graph."""
    graph = generate_graph("spike", graph_seed)
    episode_seed = graph_seed + EPISODE_OFFSET
    clean = sample_episode(graph, episode_seed, "normal")
    row = {"trust_clean": plain(graph, clean, "normal")["final_sink_errors"],
           "clean": {}, "grid": {pi: [] for pi in pis}}
    for pi in pis:
        audit, _ = run_shrink(graph, clean, pi)
        row["clean"][pi] = audit["final_sink_errors"]
    for locality in LOCALITIES:
        for fraction in FRACTIONS:
            for shift in SHIFTS:
                corrupted, _ = corrupt_snapshot(graph, clean, episode_seed, locality, fraction, shift)
                for pi in pis:
                    audit, _ = run_shrink(graph, corrupted, pi)
                    row["grid"][pi].append(audit["final_sink_errors"])
    return row


def fit_shrink_pi(workers):
    pis = PIS
    seeds = list(range(CALIBRATION_START, CALIBRATION_START + CALIBRATION_COUNT))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(partial(calibration_graph, pis=pis), seeds))
    trust_clean = float(np.mean([row["trust_clean"] for row in rows]))
    table = {}
    for pi in pis:
        clean = float(np.mean([row["clean"][pi] for row in rows]))
        grid = float(np.mean([value for row in rows for value in row["grid"][pi]]))
        table[pi] = {"clean_mean": clean, "clean_cost": clean - trust_clean, "grid_mean": grid,
                     "admissible": clean - trust_clean <= CLEAN_COST_LIMIT}
    admissible = [pi for pi in pis if table[pi]["admissible"] or pi == 0.0]
    chosen = min(admissible, key=lambda pi: (table[pi]["grid_mean"], pi))
    return chosen, {"trust_clean_mean": trust_clean, "grid": table, "admissible": admissible,
                    "graph_start": CALIBRATION_START, "graph_count": CALIBRATION_COUNT,
                    "episode_seed_offset": EPISODE_OFFSET, "clean_cost_limit": CLEAN_COST_LIMIT,
                    "rule": "smallest grid mean among pis whose clean cost is within the limit; "
                            "ties go to the smaller pi"}


def evaluate_graph(graph_seed, gate, pi):
    graph = generate_graph("spike", graph_seed)
    if graph.n != 80 or len(graph.sinks) != 20:
        raise ValueError("unexpected graph dimensions")
    episode_seed = graph_seed + EPISODE_OFFSET
    clean = sample_episode(graph, episode_seed, "normal")
    clean_mode = infer_signal_mode(clean.confidence, gate)
    if clean_mode != "normal":
        raise ValueError(f"clean graph {graph_seed} misclassified as {clean_mode}")
    rows = []
    initial_reference = None

    def emit(locality, fraction, shift, snapshot, corrupted_nodes, changed_nodes):
        nonlocal initial_reference
        names = POLICIES if locality == "clean" else CELL_POLICIES
        mode = clean_mode if locality == "clean" else infer_signal_mode(snapshot.confidence, gate)
        # Mechanism diagnostic, never a policy input: where the truly erroneous nodes
        # sit in each belief ordering. Requires the hidden truth, so it is reported only.
        probe = OversightEnv(graph, snapshot, BUDGET, p_catch=P_CATCH, confidence_mode="normal")
        base_belief = np.array(probe._belief_base, dtype=np.float64)
        errors = np.asarray(snapshot.source_errors, dtype=bool)
        rank_trust = error_rank(base_belief, errors)
        rank_shrink = error_rank(mixture_belief(graph, snapshot, pi), errors)
        outcome = {}
        for name in names:
            belief_shift = 0.0
            if name == "shrink":
                audit, belief_shift = run_shrink(graph, snapshot, pi)
            else:
                audit = plain(graph, snapshot,
                              "noise" if name == "prior" else
                              mode if name == "gate" else "normal")
            if initial_reference is None:
                initial_reference = audit["initial_sink_errors"]
            elif audit["initial_sink_errors"] != initial_reference:
                raise ValueError(f"unpaired initial errors on graph {graph_seed}")
            if len(audit["trace"]) != BUDGET:
                raise ValueError(f"review budget violated on {graph_seed}/{locality}/{fraction}/{shift}/{name}")
            outcome[name] = audit["final_sink_errors"]
            rows.append((graph_seed, episode_seed, locality, fraction, shift, name, mode, pi,
                         round(belief_shift, 6), corrupted_nodes, changed_nodes,
                         audit["initial_sink_errors"], audit["final_sink_errors"],
                         sum(step["flagged"] for step in audit["trace"]), len(audit["trace"]),
                         round(rank_trust, 3), round(rank_shrink, 3)))
        if locality != "clean":
            selected = outcome["prior"] if mode == "noise" else outcome["trust"]
            if outcome["gate"] != selected:
                raise ValueError(f"gate is not a pure selector on {graph_seed}/{locality}/{fraction}/{shift}")
        if locality == "clean" and outcome["trust"] != outcome["oracle"]:
            raise ValueError(f"clean trust must reproduce oracle on graph {graph_seed}")

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
    parser.add_argument("--start", type=int, default=3400,
                        help="first graph seed; 3400-3599 is fresh (3000-3399 are spent)")
    parser.add_argument("--graphs", type=int, default=200)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if (args.start < 3400 or args.start + args.graphs > 70000
            or args.graphs < 1 or args.workers < 1):
        parser.error("graph seeds must stay in the fresh range [3400, 70000); "
                     "70000-70099 is calibration and 90000+ is development/test")
    out = args.out.resolve()
    try:
        out.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error(f"output directory already exists: {out}")

    gate = fit_signal_gate()
    pi, fit = fit_shrink_pi(args.workers)
    print(f"pi = {pi:.2f} (clean cost {fit['grid'][pi]['clean_cost']:+.4f}, "
          f"grid mean {fit['grid'][pi]['grid_mean']:.4f})", flush=True)
    print("  admissible:", fit["admissible"], flush=True)

    graph_seeds = list(range(args.start, args.start + args.graphs))
    evaluate = partial(evaluate_graph, gate=gate, pi=pi)
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
        "episode_seeds": [seed + EPISODE_OFFSET for seed in graph_seeds],
        "localities": list(LOCALITIES), "fractions": list(FRACTIONS), "shifts": list(SHIFTS),
        "policies": list(POLICIES), "signal_gate": gate,
        "corruption": "sigmoid(logit(c) + shift) on a deterministic subset of the locality pool",
        "selection_seed_offset": 991,
        "fraction_meaning": "fraction of the locality pool, not of all nodes",
        "shrink": {
            "pi": pi, "delta_grid": DELTAS.tolist(), "sigma": SIGMA,
            "mu_err": MU_ERR, "mu_good": MU_GOOD,
            "bias": "-0.4 * (rate - 0.15), identical to environment.initial_belief",
            "belief_source": "public scores, node types, base rates; calibrated on 70000-70099",
            "policy": "unchanged marginal with budget 16; only the input posterior changes",
            "diagnostic_columns": "error_rank_trust / error_rank_shrink are the mean rank of the "
                                  "truly erroneous nodes under each belief ordering; they use the "
                                  "hidden truth and are reported only, never fed to the policy",
            "fit": fit,
        },
        "preregistration": "PREREGISTER_SHRINK.md",
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
