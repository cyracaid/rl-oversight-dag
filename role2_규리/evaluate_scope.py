"""Pre-registered two-level scope experiment (see PREREGISTER_SCOPE.md).

`shrink` decides, per node and independently, whether that node's score was
shifted. That is the wrong question when the whole graph moves together: node by
node, "I was shifted" and "everything was shifted" look the same, so a global
upward shift is credited to clean nodes that were pushed up and the true errors
are demoted.

This adds the missing level. Three hypotheses compete per graph:

    H0        no shift                       likelihood  prod_i L_i(0)
    H1(delta) every node shifted by delta    likelihood  prod_i L_i(delta)
    H2        a subset of nodes shifted      likelihood  prod_i [(1-pi) L_i(0) + pi mean_d L_i(d)]

H1 only wins when the 80 nodes agree on one delta, and then the node posterior
is the delta-undone one, i.e. the clean posterior. H2 is exactly `shrink`. Node
posteriors are the posterior-weighted average over the three hypotheses, and the
policy (marginal, budget 16) is untouched.

Only public data enters: scores, node types and base rates, graph structure.
"""

import argparse
import csv
from functools import partial
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import platform

import numpy as np

from _env import ROLE3, ROOT, ensure_role3

ensure_role3()
from dag_role3 import OversightEnv, generate_graph, sample_episode
from dag_role3.policies import choose
from evaluate_conditions import BUDGET, sha256
from evaluate_corruption import FRACTIONS, LOCALITIES, SHIFTS, corrupt_snapshot, vector_logit
from evaluate_feedback import P_CATCH
from evaluate_shrink import DELTAS, MU_ERR, MU_GOOD, SIGMA, node_rates, run_shrink
from signal_calibration import fit_signal_gate, infer_signal_mode


PI = 0.15          # shrink-v1's per-node fraction; kept as the shrink baseline constant
Q_GRID = (0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.65, 0.80, 1.00)
# One delta and one fraction, shared by every node, because that is what the
# corruption generator does: it picks one locality and shifts a fraction of it by
# a single amount. p0 = prior mass on "nothing was shifted"; fitted on 70000-70029.
P0_GRID = (0.20, 0.35, 0.50, 0.65, 0.80)
CALIBRATION_START = 70000
CALIBRATION_COUNT = 30
CLEAN_COST_LIMIT = 0.05
EPISODE_OFFSET = 20000
POLICIES = ("oracle", "trust", "prior", "gate", "shrink", "scope")
CELL_POLICIES = ("trust", "prior", "gate", "shrink", "scope")
FIELDS = ("graph_seed", "episode_seed", "locality", "fraction", "shift", "policy",
          "gate_mode", "p0", "belief_shift", "post_none", "post_frac", "post_global",
          "map_q", "map_delta", "corrupted_nodes", "changed_nodes", "initial_sink_errors",
          "sink_errors", "flags", "reviews")


def log_gaussian(values, mean):
    return -0.5 * ((values - mean) / SIGMA) ** 2 - np.log(SIGMA * np.sqrt(2 * np.pi))


def node_terms(graph, snapshot):
    """Per node: marginal log-likelihood and P(error | delta) for every delta in the grid.

    Column 0 is delta = 0, so an unshifted graph can select "no shift" and reproduce
    the environment's own posterior exactly instead of a spurious +-0.5 rescaling.
    """
    z = vector_logit(snapshot.confidence)
    rates = node_rates(graph)
    bias = -0.4 * (rates - 0.15)
    grid = np.concatenate(([0.0], DELTAS))
    log_r, log_1r = np.log(rates), np.log1p(-rates)
    shifted = z[:, None] - grid[None, :]                       # (n, k)
    log_err = log_r[:, None] + log_gaussian(shifted, (MU_ERR + bias)[:, None])
    log_good = log_1r[:, None] + log_gaussian(shifted, (MU_GOOD + bias)[:, None])
    log_joint = np.logaddexp(log_err, log_good)                # (n, k)
    posterior = np.exp(log_err - log_joint)                    # P(b_i = 1 | delta)
    return grid, log_joint, posterior


def scope_cells(graph, snapshot, p0):
    """Score every (fraction, delta) cell, including the no-shift cell.

    Returns the cell array, their posterior weights, and the per-cell node posterior
    input needed to average the node beliefs.
    """
    _, log_joint, posterior = node_terms(graph, snapshot)
    zero, rest = log_joint[:, :1], log_joint[:, 1:]
    fractions, deltas, log_evidence = [0.0], [0.0], [float(zero.sum())]
    for q in Q_GRID:
        moved = (np.log(q) + rest)                             # (n, 16)
        stayed = (np.log(1.0 - q) if q < 1.0 else -np.inf) + zero   # (n, 1)
        log_evidence.extend(np.logaddexp(stayed, moved).sum(axis=0).tolist())
        fractions.extend([q] * len(DELTAS))
        deltas.extend(DELTAS.tolist())
    fractions, deltas = np.array(fractions), np.array(deltas)
    log_evidence = np.array(log_evidence)
    log_prior = np.where(fractions == 0.0, np.log(p0),
                         np.log((1.0 - p0) / len(Q_GRID)) - np.log(len(DELTAS)))
    weights = np.exp(log_evidence + log_prior - float((log_evidence + log_prior).max()))
    weights /= weights.sum()
    return fractions, deltas, log_evidence, weights, posterior, zero, rest


def scope_belief(graph, snapshot, p0):
    """Node posteriors from a shared (fraction, delta) mixture, with the scope posterior.

    Two nested hypotheses compete: nothing moved (q = 0), and one fraction q of the
    nodes moved by one delta. Tying both to the same delta is what makes "the whole
    graph moved" and "these nodes moved" distinguishable; the grid over q is what
    keeps a partially corrupted graph from being explained as a global shift.
    """
    fractions, deltas, log_evidence, weights, posterior, zero, rest = scope_cells(
        graph, snapshot, p0)
    belief = weights[0] * posterior[:, 0]
    for k in range(1, len(fractions)):
        if weights[k] < 1e-12:
            continue
        q, delta = float(fractions[k]), float(deltas[k])
        column = 1 + int(np.where(np.isclose(DELTAS, delta))[0][0])
        stayed = np.log(1.0 - q) if q < 1.0 else -np.inf
        num = np.logaddexp(stayed + zero[:, 0] + np.log(np.clip(posterior[:, 0], 1e-300, None)),
                           np.log(q) + rest[:, column - 1] +
                           np.log(np.clip(posterior[:, column], 1e-300, None)))
        den = np.logaddexp(stayed + zero[:, 0], np.log(q) + rest[:, column - 1])
        belief = belief + weights[k] * np.exp(num - den)
    best = int(np.argmax(log_evidence + np.log(np.where(
        fractions == 0.0, p0, (1.0 - p0) / len(Q_GRID) / len(DELTAS)))))
    diagnostics = {
        "post_none": float(weights[0]),
        "post_frac": float(weights[(fractions > 0.0) & (fractions < 1.0)].sum()),
        "post_global": float(weights[fractions == 1.0].sum()),
        "map_q": float(fractions[best]), "map_delta": float(deltas[best]),
    }
    return belief, diagnostics


def finish(env, observation):
    while not env.done:
        observation, _, _, _ = env.step(partial(choose, name="marginal")(observation))
    return env.final_audit()


def run_scope(graph, snapshot, p0):
    env = OversightEnv(graph, snapshot, BUDGET, p_catch=P_CATCH, confidence_mode="normal")
    baseline = np.array(env._belief_base, dtype=np.float64)
    belief, diagnostics = scope_belief(graph, snapshot, p0)
    belief_shift = float(np.abs(belief - baseline).mean())
    env._belief_base = belief.copy()
    observed = env.observation()["features"][:, len(graph.rates) + 2]
    if not np.allclose(observed, belief.astype(np.float32), atol=1e-6):
        raise ValueError("belief override did not reach the observation")
    return finish(env, env.observation()), belief_shift, diagnostics


def plain(graph, snapshot, mode):
    env = OversightEnv(graph, snapshot, BUDGET, p_catch=P_CATCH, confidence_mode=mode)
    return finish(env, env.observation())


def calibration_graph(graph_seed, p0s):
    graph = generate_graph("spike", graph_seed)
    episode_seed = graph_seed + EPISODE_OFFSET
    clean = sample_episode(graph, episode_seed, "normal")
    row = {"trust_clean": plain(graph, clean, "normal")["final_sink_errors"],
           "clean": {}, "grid": {p0: [] for p0 in p0s}}
    for p0 in p0s:
        row["clean"][p0] = run_scope(graph, clean, p0)[0]["final_sink_errors"]
    for locality in LOCALITIES:
        for fraction in FRACTIONS:
            for shift in SHIFTS:
                corrupted, _ = corrupt_snapshot(graph, clean, episode_seed, locality, fraction, shift)
                for p0 in p0s:
                    row["grid"][p0].append(
                        run_scope(graph, corrupted, p0)[0]["final_sink_errors"])
    return row


def fit_scope_p0(workers):
    seeds = list(range(CALIBRATION_START, CALIBRATION_START + CALIBRATION_COUNT))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(partial(calibration_graph, p0s=P0_GRID), seeds))
    trust_clean = float(np.mean([row["trust_clean"] for row in rows]))
    table = {}
    for p0 in P0_GRID:
        clean = float(np.mean([row["clean"][p0] for row in rows]))
        grid = float(np.mean([value for row in rows for value in row["grid"][p0]]))
        table[f"{p0:.2f}"] = {"p0": p0, "clean_mean": clean, "clean_cost": clean - trust_clean,
                              "grid_mean": grid, "admissible": clean - trust_clean <= CLEAN_COST_LIMIT}
    admissible = [key for key, row in table.items() if row["admissible"]]
    if not admissible:
        admissible = [min(table, key=lambda key: table[key]["clean_cost"])]
    chosen_key = min(admissible, key=lambda key: (table[key]["grid_mean"], table[key]["p0"]))
    return table[chosen_key]["p0"], {
        "trust_clean_mean": trust_clean, "grid": table, "admissible": admissible,
        "chosen": chosen_key, "graph_start": CALIBRATION_START, "graph_count": CALIBRATION_COUNT,
        "episode_seed_offset": EPISODE_OFFSET, "clean_cost_limit": CLEAN_COST_LIMIT,
        "q_grid": list(Q_GRID), "delta_grid": DELTAS.tolist(),
        "rule": "smallest grid mean among p0 values whose clean cost is within the limit",
    }


def evaluate_graph(graph_seed, gate, p0):
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
        diagnostics = {"post_none": 0.0, "post_frac": 0.0, "post_global": 0.0,
                       "map_q": 0.0, "map_delta": 0.0}
        outcome = {}
        for name in names:
            belief_shift = 0.0
            if name == "scope":
                audit, belief_shift, diagnostics = run_scope(graph, snapshot, p0)
            elif name == "shrink":
                audit, belief_shift = run_shrink(graph, snapshot, PI)
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
            rows.append((graph_seed, episode_seed, locality, fraction, shift, name, mode, p0,
                         round(belief_shift, 6), round(diagnostics["post_none"], 6),
                         round(diagnostics["post_frac"], 6), round(diagnostics["post_global"], 6),
                         diagnostics["map_q"], diagnostics["map_delta"],
                         corrupted_nodes, changed_nodes, audit["initial_sink_errors"],
                         audit["final_sink_errors"],
                         sum(step["flagged"] for step in audit["trace"]), len(audit["trace"])))
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
    parser.add_argument("--start", type=int, default=3600,
                        help="first graph seed; 3600-3799 is fresh (3000-3599 are spent)")
    parser.add_argument("--graphs", type=int, default=200)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if (args.start < 3600 or args.start + args.graphs > 70000
            or args.graphs < 1 or args.workers < 1):
        parser.error("graph seeds must stay in the fresh range [3600, 70000); "
                     "70000-70099 is calibration and 90000+ is development/test")
    out = args.out.resolve()
    try:
        out.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error(f"output directory already exists: {out}")

    gate = fit_signal_gate()
    p0, fit = fit_scope_p0(args.workers)
    chosen = fit["grid"][fit["chosen"]]
    print(f"p0 = {p0:.2f} (clean cost {chosen['clean_cost']:+.4f}, "
          f"grid mean {chosen['grid_mean']:.4f}); admissible {fit['admissible']}", flush=True)

    graph_seeds = list(range(args.start, args.start + args.graphs))
    evaluate = partial(evaluate_graph, gate=gate, p0=p0)
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
    sources = [here, here.with_name("evaluate_shrink.py"), here.with_name("evaluate_corruption.py"),
               here.with_name("evaluate_conditions.py"), here.with_name("evaluate_feedback.py"),
               here.with_name("signal_calibration.py"), ROLE3 / "dag_role3" / "policies.py",
               ROLE3 / "dag_role3" / "environment.py", ROLE3 / "dag_role3" / "graphs.py"]
    manifest = {
        "status": "complete", "family": "spike", "nodes": 80, "sinks": 20, "budget": BUDGET,
        "p_catch": P_CATCH, "particles": 0, "graph_seeds": graph_seeds,
        "episode_seeds": [seed + EPISODE_OFFSET for seed in graph_seeds],
        "localities": list(LOCALITIES), "fractions": list(FRACTIONS), "shifts": list(SHIFTS),
        "policies": list(POLICIES), "signal_gate": gate,
        "corruption": "sigmoid(logit(c) + shift) on a deterministic subset of the locality pool",
        "selection_seed_offset": 991,
        "fraction_meaning": "fraction of the locality pool, not of all nodes",
        "scope": {
            "p0": p0, "q_grid": list(Q_GRID), "delta_grid": DELTAS.tolist(),
            "sigma": SIGMA, "mu_err": MU_ERR, "mu_good": MU_GOOD,
            "model": "one shared (q, delta): q = 0 means nothing moved, otherwise a fraction "
                     "q of the 80 nodes moved by the same delta; node posteriors are the "
                     "posterior-weighted mixture over cells",
            "shrink_reference_pi": PI,
            "belief_source": "public scores, node types, base rates; p0 fitted on 70000-70029",
            "policy": "unchanged marginal with budget 16; only the input posterior changes",
            "diagnostic_columns": "post_none / post_frac / post_global / map_q / map_delta are "
                                  "graph-level posterior summaries; they use no hidden truth and "
                                  "are not fed back into the policy",
            "fit": fit,
        },
        "preregistration": "PREREGISTER_SCOPE_V2.md",
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
