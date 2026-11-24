"""Map where the global-mean signal gate stops working under local corruption.

The two earlier corruption controls are point measurements: a within-type shuffle
(preserves the graph mean, so the gate necessarily classifies it as normal) and a
by-type partial shuffle with a fixed magnitude. This sweep turns the open question
into a boundary: how much corruption, of which magnitude, in which layer, is needed
before a gate that only sees the graph-mean confidence stops trusting the scores?

Corruption model. Confidence is squashed normal scores; corrupting a node means
adding a signed shift in logit space, ``sigmoid(logit(c) + shift)``. Only the
public score vector changes; hidden truth, edge coins and reviewer uniforms are
untouched (verified on every cell). Negative shifts make nodes look erroneous
(false suspicion); a positive shift hides real errors (masking).

Locality. ``uniform`` samples from all 80 nodes, ``source`` from the 20 layer-0
nodes (no parents), ``sink`` from the 20 conclusion nodes, and ``error_nodes``
from the nodes that actually carry a source error. ``fraction`` is a fraction of
that pool, so ``fraction=1.0`` corrupts the whole layer rather than the whole
graph. ``error_nodes`` is an evaluator-side adversary: like ``oracle`` it needs
the hidden truth, and it is the only locality that can *mask* a real error
reliably (positive shift on the truly wrong nodes).

Policies, all on the same paired graph:
  oracle    marginal on the clean scores (not deployable; the upper bound)
  trust     marginal on the corrupted scores
  prior     the type prior, with the corrupted scores ignored entirely
  gate      the existing global-mean gate: if it says ``noise``, fall back to the
            type prior; otherwise trust the corrupted scores
  feedback  per-flag belief updates between the normal and prior models

The scientific question is not "does the gate fail" (it must, for mean-preserving
corruption) but "where is the boundary, and is it asymmetric across layers".
"""

import argparse
import csv
from dataclasses import replace
from functools import partial
import hashlib
import json
from pathlib import Path
import platform
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from _env import ROLE3, ROOT, ensure_role3

ensure_role3()
from dag_role3 import OversightEnv, generate_graph, sample_episode
from dag_role3.policies import choose
from evaluate_conditions import BUDGET, evaluate_policy, sha256
from evaluate_feedback import P_CATCH, run_feedback
from signal_calibration import fit_signal_gate, infer_signal_mode


LOCALITIES = ("uniform", "source", "sink", "error_nodes")
FRACTIONS = (0.1, 0.25, 0.5, 1.0)
SHIFTS = (-4.0, -3.0, -2.0, -1.0, 1.0, 2.0, 3.0)
POLICIES = ("oracle", "trust", "prior", "gate", "feedback")
CELL_POLICIES = ("trust", "prior", "gate", "feedback")
FIELDS = ("graph_seed", "episode_seed", "locality", "fraction", "shift", "policy",
          "gate_mode", "corrupted_nodes", "changed_nodes", "initial_sink_errors",
          "sink_errors", "flags", "reviews", "noise_actions", "switched")


def vector_logit(values, epsilon=1e-8):
    clipped = np.clip(np.asarray(values, dtype=np.float64), epsilon, 1.0 - epsilon)
    return np.log(clipped / (1.0 - clipped))


def vector_sigmoid(values):
    return 1.0 / (1.0 + np.exp(-np.clip(np.asarray(values, dtype=np.float64), -60.0, 60.0)))


def corruption_pool(graph, locality, snapshot):
    if locality == "uniform":
        return np.arange(graph.n)
    if locality == "source":
        return np.array([i for i, parents in enumerate(graph.parents) if not parents])
    if locality == "sink":
        return np.asarray(graph.sinks)
    if locality == "error_nodes":
        # Evaluator-side adversary: it needs the hidden truth, exactly like oracle.
        return np.flatnonzero(np.asarray(snapshot.source_errors))
    raise ValueError(f"unknown locality: {locality}")


def corrupt_snapshot(graph, snapshot, episode_seed, locality, fraction, shift):
    """Shift a deterministic subset of public scores in logit space."""
    pool = corruption_pool(graph, locality, snapshot)
    count = 0 if fraction == 0 else max(1, min(len(pool), round(fraction * len(pool))))
    if len(pool) == 0:
        count = 0
    rng = np.random.default_rng(episode_seed + 991)
    selected = np.sort(rng.choice(pool, size=count, replace=False))
    scores = np.array(snapshot.confidence)
    shifted = scores.copy()
    shifted[selected] = vector_sigmoid(vector_logit(scores[selected]) + shift)
    corrupted = replace(snapshot, confidence=tuple(shifted))
    changed = int(np.count_nonzero(shifted != scores))
    return corrupted, (selected, changed)


def policy_outcome(graph, snapshot, assumed_mode, name):
    if name == "feedback":
        initial_mode = assumed_mode
        initial, final, flags, reviews, noise_actions, switched = run_feedback(
            graph, snapshot, initial_mode, partial(choose, name="marginal"))
    else:
        final, initial, flags, reviews = evaluate_policy(
            graph, snapshot, assumed_mode, partial(choose, name="marginal"))
        noise_actions = reviews if assumed_mode == "noise" else 0
        switched = 0
    return initial, final, flags, reviews, noise_actions, switched


def evaluate_graph(graph_seed, gate):
    graph = generate_graph("spike", graph_seed)
    if graph.n != 80 or len(graph.sinks) != 20:
        raise ValueError("unexpected graph dimensions")
    episode_seed = graph_seed + 20000
    clean = sample_episode(graph, episode_seed, "normal")
    clean_mode = infer_signal_mode(clean.confidence, gate)
    rows = []
    initial_reference = None

    def emit(locality, fraction, shift, snapshot, mode, corrupted_nodes, changed_nodes):
        nonlocal initial_reference
        names = POLICIES if locality == "clean" else CELL_POLICIES
        outcomes = {}
        for name in names:
            if name == "trust" or name == "oracle":
                assumed = "normal"
            elif name == "prior":
                assumed = "noise"
            else:
                assumed = mode
            outcomes[name] = assumed, policy_outcome(graph, snapshot, assumed, name)
        if "gate" in outcomes:
            # The gate must be a pure selector between trusting the scores and
            # using the type prior, not a third behaviour. Verified row by row.
            chosen = "prior" if mode == "noise" else "trust"
            if outcomes["gate"][1] != outcomes[chosen][1]:
                raise ValueError(f"gate is not a selector on {graph_seed}/{locality}/{fraction}/{shift}")
        for name in names:
            assumed, (initial, final, flags, reviews, noise_actions, switched) = outcomes[name]
            if reviews != BUDGET or not 0 <= final <= initial <= len(graph.sinks):
                raise ValueError(f"inconsistent outcome on {graph_seed}/{locality}/{fraction}/{shift}/{name}")
            if initial_reference is None:
                initial_reference = initial
            elif initial != initial_reference:
                raise ValueError(f"unpaired initial errors on graph {graph_seed}")
            rows.append((graph_seed, episode_seed, locality, fraction, shift, name, mode,
                         corrupted_nodes, changed_nodes, initial, final, flags, reviews,
                         noise_actions, switched))

    emit("clean", 0.0, 0.0, clean, clean_mode, 0, 0)
    if clean_mode != "normal":
        raise ValueError(f"clean graph {graph_seed} misclassified as {clean_mode}")

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
                mode = infer_signal_mode(corrupted.confidence, gate)
                emit(locality, fraction, shift, corrupted, mode, len(selected), changed)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="new output directory")
    parser.add_argument("--start", type=int, default=3000,
                        help="first graph seed; default 3000 is an untouched block (2000-2199 was "
                             "already spent on the confirmation run)")
    parser.add_argument("--graphs", type=int, default=200, help="number of paired graphs")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if (args.start < 3000 or args.start + args.graphs > 70000
            or args.graphs < 1 or args.workers < 1):
        parser.error("graph seeds must stay in the unused range [3000, 70000); "
                     "70000-70099 is calibration and 90000+ is development/test")
    out = args.out.resolve()
    try:
        out.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error(f"output directory already exists: {out}")

    gate = fit_signal_gate()
    graph_seeds = list(range(args.start, args.start + args.graphs))
    evaluate = partial(evaluate_graph, gate=gate)
    pending = out / "episodes.csv.partial"
    with pending.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(FIELDS)
        if args.workers > 1:
            with ProcessPoolExecutor(args.workers) as pool:
                batches = pool.map(evaluate, graph_seeds)
                for index, rows in enumerate(batches, start=1):
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
    sources = [here, here.with_name("evaluate_conditions.py"), here.with_name("evaluate_feedback.py"),
               here.with_name("signal_calibration.py"), here.with_name("shuffle_control.py"),
               ROLE3 / "dag_role3" / "policies.py", ROLE3 / "dag_role3" / "environment.py",
               ROLE3 / "dag_role3" / "graphs.py"]
    manifest = {
        "status": "complete", "family": "spike", "nodes": 80, "sinks": 20, "budget": BUDGET,
        "p_catch": P_CATCH, "particles": 0, "graph_seeds": graph_seeds,
        "episode_seeds": [seed + 20000 for seed in graph_seeds],
        "localities": list(LOCALITIES), "fractions": list(FRACTIONS), "shifts": list(SHIFTS),
        "policies": list(POLICIES), "signal_gate": gate,
        "corruption": "sigmoid(logit(c) + shift) on a deterministic subset of the locality pool",
        "selection_seed_offset": 991,
        "fraction_meaning": "fraction of the locality pool, not of all nodes",
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
