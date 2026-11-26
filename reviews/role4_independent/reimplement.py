#!/usr/bin/env python3
"""Clean-room reimplementation of the role4 structural controls (SPEC.md).

Reads only:
  * the frozen environment package  ``role3 improvement/dag_role3``  (imported, unchanged)
  * the frozen benchmark tables     ``role3 improvement/outputs/v3/benchmark_role3.csv``
                                    ``.../benchmark_summary.csv``

Writes ``out/controls.csv``, ``out/controls_summary.csv``,
``out/benchmark_worst_of_n.csv``, ``out/diagnostics.csv``.

The acceptance gate is hard: every shared frozen row (errors *and* the action
sequence) must be reproduced by the ``intact`` condition, otherwise the script
exits 2 having written nothing.

Deterministic: no wall-clock, no global RNG state, every sampler seeded from the
documented seed.
"""
from __future__ import annotations

import csv
import math
import os
import random
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "role3 improvement"))

from dag_role3 import DAG, generate_graph, propagate  # noqa: E402
from dag_role3.environment import initial_belief, sample_episode  # noqa: E402
from dag_role3.policies import choose, run_public_policy  # noqa: E402

# ---------------------------------------------------------------------------
# Frozen constants (SPEC.md "What is frozen")
# ---------------------------------------------------------------------------
FAMILIES = ("spike", "modular", "ba", "er", "real")
POLICIES = ("confidence", "structural", "marginal")
SEEDS = tuple(range(90000, 90100))
EPISODE_OFFSET = 20000            # sample_episode(graph, 20000 + seed)
BUDGET = {"spike": 16, "real": 8, "modular": 50, "ba": 50, "er": 50}
P_CATCH = 0.9
REWIRE_SEED_BASE = 4_040_000     # rng = random.Random(4_040_000 + graph_seed)
BOOTSTRAP_SEED = 411             # run_benchmark.interval, "20 x 100" replicates
BOOTSTRAP_REPLICATES = 20 * 100
CONDITIONS = ("intact", "flatten", "rewire")

BENCH_ROOT = os.path.join(ROOT, "role3 improvement", "outputs", "v3")
BENCH_CSV = os.path.join(BENCH_ROOT, "benchmark_role3.csv")
BENCH_SUMMARY_CSV = os.path.join(BENCH_ROOT, "benchmark_summary.csv")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")


# ---------------------------------------------------------------------------
# Bootstrap CI, recovered from the frozen summary (see NOTES.md, ambiguity 1)
# ---------------------------------------------------------------------------
def interval(values, seed=BOOTSTRAP_SEED, replicates=BOOTSTRAP_REPLICATES):
    """Paired percentile bootstrap of the mean, 2.5/97.5 %.

    2000 replicates = "20 x 100". Verified cell-by-cell against the
    `paired_lo`/`paired_hi` columns of the frozen benchmark_summary.csv.
    """
    vals = np.asarray(values, dtype=np.float64)
    n = len(vals)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(replicates, n))
    means = np.sort(vals[idx].mean(axis=1))
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(lo), float(hi)


# ---------------------------------------------------------------------------
# Rewire rule (SPEC.md "rewire")
# ---------------------------------------------------------------------------
def _spike_partition(n, layers, i):
    """The generator's contiguous-layer rule: min(L-1, i*L//n)."""
    return min(layers - 1, i * layers // n)


def rewire_graph(graph, graph_seed):
    """Keep parent counts, types and the sink set; redraw every parent."""
    rng = random.Random(REWIRE_SEED_BASE + graph_seed)
    n = graph.n
    layers = tuple(graph.layers)
    n_layers = max(layers) + 1
    new_parents = []
    for i in range(n):
        keep = len(graph.parents[i])
        if keep == 0:
            new_parents.append(())
            continue
        if graph.family == "spike":
            mine = _spike_partition(n, n_layers, i)
            pool = [u for u in range(n) if _spike_partition(n, n_layers, u) == mine - 1]
        elif graph.family == "real":
            pool = [u for u in range(n) if layers[u] < layers[i]]
        else:  # modular / ba / er: originals are oriented by index
            pool = list(range(i))
        if len(pool) < keep:
            raise RuntimeError(f"rewire pool too small for node {i} in {graph.family}")
        new_parents.append(tuple(sorted(rng.sample(pool, keep))))
    return DAG(parents=tuple(new_parents), types=graph.types, rates=graph.rates,
               family=graph.family, names=graph.names,
               sink_override=tuple(graph.sinks), lam=graph.lam,
               spike_probability=graph.spike_probability)


# ---------------------------------------------------------------------------
# Mismatch environment: the policy plans on `view`, the errors travel on `truth`
# ---------------------------------------------------------------------------
class MismatchEnv:
    """`OversightEnv` with the map the policy sees decoupled from the truth.

    Every line of the observation and of the belief update is taken from the
    view graph/snapshot (so `view == truth` is bit-identical to OversightEnv).
    Only the hidden error state is recomputed on the truth graph with the truth
    edge coins. Sink errors are counted on the truth graph's sinks.
    """

    def __init__(self, truth_graph, truth_base, truth_coins, view_graph,
                 view_snapshot, budget, p_catch=P_CATCH):
        self.truth_graph = truth_graph
        self.view_graph = view_graph
        self.snapshot = view_snapshot          # confidence, review uniforms, probs
        self._truth_coins = dict(truth_coins)
        self.budget, self.p_catch = int(budget), float(p_catch)
        self._edges = view_graph.edge_index()
        self._edge_prob = np.array([view_snapshot.edge_probs[u, v]
                                    for u, v in self._edges.T])
        self._base = list(truth_base)
        self._effective = propagate(truth_graph, self._base, self._truth_coins)
        self._reviewed = [False] * view_graph.n
        self._flagged = [False] * view_graph.n
        self._belief_base = initial_belief(view_graph, view_snapshot.confidence, "normal")
        self._budget_left = self.budget
        self._done = self.budget == 0
        self._initial_sink_errors = sum(self._effective[i] for i in truth_graph.sinks)

    # -- identical to OversightEnv ------------------------------------------
    @property
    def done(self):
        return self._done

    def _public_error_probabilities(self):
        p = np.zeros(self.view_graph.n, dtype=np.float64)
        for i in self.view_graph.topo:
            clean_from_parents = 1.0
            for u in self.view_graph.parents[i]:
                clean_from_parents *= (1 - p[u] * self.snapshot.edge_probs[u, i])
            p[i] = 1 - (1 - self._belief_base[i]) * clean_from_parents
        return p

    def observation(self):
        n, k = self.view_graph.n, len(self.view_graph.rates)
        f = np.zeros((n, k + 7), dtype=np.float32)
        f[np.arange(n), list(self.view_graph.types)] = 1.0
        f[:, k] = np.asarray(self.snapshot.confidence, dtype=np.float32)
        f[:, k + 1] = np.log1p(self.view_graph.sink_reach) / math.log1p(n)
        f[:, k + 2] = self._belief_base
        f[:, k + 3] = self._public_error_probabilities()
        f[:, k + 4] = self._reviewed
        f[:, k + 5] = self._flagged
        f[:, k + 6] = self._budget_left / max(1, self.budget)
        return {
            "features": f.copy(),
            "mask": np.logical_not(self._reviewed) & (not self.done),
            "edge_index": self._edges.copy(),
            "edge_probability": self._edge_prob.copy(),
            "topological_order": np.array(self.view_graph.topo),
            "sink_ids": np.asarray(self.view_graph.sinks, dtype=np.int64),
            "budget_left": self._budget_left,
            "family": self.view_graph.family,
            "node_names": list(self.view_graph.names) if self.view_graph.names
                          else [f"v{i}" for i in range(n)],
        }

    def step(self, action):
        a = int(action)
        if self._reviewed[a]:
            raise ValueError("cannot inspect the same node twice")
        flagged = bool(self._effective[a]) and self.snapshot.review_uniforms[a] < self.p_catch
        self._reviewed[a] = True
        self._flagged[a] = flagged
        if flagged:
            self._base[a] = False
            self._effective = propagate(self.truth_graph, self._base, self._truth_coins)
            self._belief_base[a] = 0.0
        else:
            q = self._belief_base[a]
            effective_risk = self._public_error_probabilities()[a]
            self._belief_base[a] = min(
                1.0, q * (1 - self.p_catch) / max(1e-12, 1 - self.p_catch * effective_risk))
        self._budget_left -= 1
        self._done = self._budget_left == 0
        after = sum(self._effective[i] for i in self.truth_graph.sinks)
        return self.observation(), -float(after) if self._done else 0.0, self._done, {"after": after}

    def final_sink_errors(self):
        if not self._done:
            raise RuntimeError("episode not finished")
        return sum(self._effective[i] for i in self.truth_graph.sinks)


def run_mismatch_policy(env, policy, rng_seed):
    """Same loop as `run_public_policy`, over a MismatchEnv."""
    rng = random.Random(rng_seed + 981)
    obs, done, actions = env.observation(), env.done, []
    while not done:
        action = choose(obs, policy, rng)
        actions.append(action)
        obs, _reward, done, _info = env.step(action)
    return env.final_sink_errors(), actions


# ---------------------------------------------------------------------------
# Frozen benchmark table
# ---------------------------------------------------------------------------
def load_frozen():
    with open(BENCH_CSV, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    with open(BENCH_SUMMARY_CSV, encoding="utf-8-sig", newline="") as fh:
        summary = list(csv.DictReader(fh))
    frozen = {}
    for r in rows:
        frozen[(r["family"], int(r["graph_seed"]), r["policy"])] = {
            "sink_errors": int(r["sink_errors"]),
            "actions": [] if not r["actions"].strip()
                       else [int(x) for x in r["actions"].split()],
            "budget": int(r["budget"]),
        }
    return rows, summary, frozen


# ---------------------------------------------------------------------------
# Spearman with average ranks for ties (scipy is not assumed installed)
# ---------------------------------------------------------------------------
def _average_ranks(values):
    a = np.asarray(values, dtype=np.float64)
    order = np.argsort(a, kind="mergesort")
    ranks = np.empty(len(a), dtype=np.float64)
    i = 0
    while i < len(a):
        j = i
        while j + 1 < len(a) and a[order[j + 1]] == a[order[i]]:
            j += 1
        ranks[order[i:j + 1]] = 0.5 * (i + j) + 1.0
        i = j + 1
    return ranks


def spearman(x, y):
    rx, ry = _average_ranks(x), _average_ranks(y)
    rx = rx - rx.mean()
    ry = ry - ry.mean()
    denom = math.sqrt(float((rx * rx).sum()) * float((ry * ry).sum()))
    if denom == 0.0:
        return float("nan")   # undefined when either side is constant
    return float((rx * ry).sum() / denom)


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------
def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)

    rows, summary, frozen = load_frozen()

    errors = {c: {} for c in CONDITIONS}      # (family, seed, policy) -> int
    actions = {c: {} for c in CONDITIONS}     # (family, seed, policy) -> list[int]
    rewired = {}
    log_every = 25

    print("loading graphs / episodes ...", flush=True)
    cache = {}
    for family in FAMILIES:
        for seed in SEEDS:
            graph = generate_graph(family, seed)
            snap = sample_episode(graph, EPISODE_OFFSET + seed)
            cache[(family, seed)] = (graph, snap)

    # ---- intact: exactly the frozen benchmark call -------------------------
    print("condition intact ...", flush=True)
    for family in FAMILIES:
        for j, seed in enumerate(SEEDS):
            graph, snap = cache[(family, seed)]
            budget = BUDGET[family]
            if snap.seed != EPISODE_OFFSET + seed:
                raise RuntimeError("episode seed mismatch")
            for policy in POLICIES:
                err, acts = run_public_policy(graph, snap, policy, budget)
                errors["intact"][(family, seed, policy)] = int(err)
                actions["intact"][(family, seed, policy)] = [int(a) for a in acts]
            if (j + 1) % log_every == 0:
                print(f"  intact {family} {j + 1}/100 ({time.time() - t0:.0f}s)", flush=True)

    # ---- acceptance gate (before anything is written) ----------------------
    print("acceptance gate ...", flush=True)
    gate_failures = []
    for family in FAMILIES:
        for seed in SEEDS:
            for policy in POLICIES:
                key = (family, seed, policy)
                ref = frozen.get(key)
                if ref is None:
                    gate_failures.append(f"{key}: missing from frozen table")
                    continue
                if errors["intact"][key] != ref["sink_errors"]:
                    gate_failures.append(
                        f"{key}: errors {errors['intact'][key]} != frozen {ref['sink_errors']}")
                if actions["intact"][key] != ref["actions"]:
                    gate_failures.append(f"{key}: action sequence differs")
    compared = len(FAMILIES) * len(SEEDS) * len(POLICIES)
    if gate_failures:
        for line in gate_failures[:20]:
            print("  GATE FAIL " + line, flush=True)
        print(f"ACCEPTANCE GATE FAILED ({len(gate_failures)} discrepancies); nothing written.",
              flush=True)
        return 2
    print(f"ACCEPTANCE GATE PASS: {compared} frozen rows reproduced "
          f"(errors and action sequences).", flush=True)

    # ---- selftest: view == truth reproduces the frozen environment ---------
    print("selftest view==truth ...", flush=True)
    selftest_n = 0
    for family in FAMILIES:
        for seed in SEEDS[:2]:
            graph, snap = cache[(family, seed)]
            for policy in POLICIES:
                env = MismatchEnv(graph, snap.source_errors, snap.edge_coins,
                                  graph, snap, BUDGET[family])
                err, acts = run_mismatch_policy(env, policy, snap.seed)
                key = (family, seed, policy)
                if err != errors["intact"][key] or acts != actions["intact"][key]:
                    print(f"  SELFTEST FAIL {key}", flush=True)
                    return 2
                selftest_n += 1
    print(f"selftest pass ({selftest_n} episodes)", flush=True)

    # ---- flatten -----------------------------------------------------------
    print("condition flatten ...", flush=True)
    for family in FAMILIES:
        for j, seed in enumerate(SEEDS):
            graph, snap = cache[(family, seed)]
            flat_coins = {e: False for e in snap.edge_coins}
            for policy in POLICIES:
                env = MismatchEnv(graph, snap.source_errors, flat_coins,
                                  graph, snap, BUDGET[family])
                err, acts = run_mismatch_policy(env, policy, snap.seed)
                errors["flatten"][(family, seed, policy)] = int(err)
                actions["flatten"][(family, seed, policy)] = acts
            if (j + 1) % log_every == 0:
                print(f"  flatten {family} {j + 1}/100 ({time.time() - t0:.0f}s)", flush=True)

    # ---- rewire ------------------------------------------------------------
    print("condition rewire ...", flush=True)
    for family in FAMILIES:
        for j, seed in enumerate(SEEDS):
            graph, snap = cache[(family, seed)]
            view = rewire_graph(graph, seed)
            view_snap = sample_episode(view, EPISODE_OFFSET + seed)
            # same parent counts per node -> identical random stream
            if (view_snap.source_errors != snap.source_errors
                    or view_snap.confidence != snap.confidence
                    or view_snap.review_uniforms != snap.review_uniforms):
                raise RuntimeError(f"rewired episode stream diverged for {family} {seed}")
            if tuple(view.sinks) != tuple(graph.sinks):
                raise RuntimeError(f"rewire changed the sink set for {family} {seed}")
            rewired[(family, seed)] = view
            for policy in POLICIES:
                env = MismatchEnv(graph, snap.source_errors, snap.edge_coins,
                                  view, view_snap, BUDGET[family])
                err, acts = run_mismatch_policy(env, policy, snap.seed)
                errors["rewire"][(family, seed, policy)] = int(err)
                actions["rewire"][(family, seed, policy)] = acts
            if (j + 1) % log_every == 0:
                print(f"  rewire {family} {j + 1}/100 ({time.time() - t0:.0f}s)", flush=True)

    # ---- gains, CIs, verdicts ---------------------------------------------
    gains = {c: {} for c in CONDITIONS}
    for family in FAMILIES:
        for cond in CONDITIONS:
            base = [errors[cond][(family, s, "confidence")] for s in SEEDS]
            for policy in POLICIES:
                gains[cond][(family, policy)] = np.array(
                    [base[i] - errors[cond][(family, SEEDS[i], policy)]
                     for i in range(len(SEEDS))], dtype=np.float64)

    def verdict(intact_lo, control_lo):
        if intact_lo <= 0:
            return "no-intact-advantage"
        if control_lo > 0:
            return "survives"
        return "removed"

    summary_rows = []
    for family in FAMILIES:
        for cond in CONDITIONS:
            for policy in POLICIES:
                g = gains[cond][(family, policy)]
                gi = gains["intact"][(family, policy)]
                lo, hi = interval(g)
                ilo, ihi = interval(gi)
                removed = gi - g
                rlo, rhi = interval(removed)
                mean_err = float(np.mean(
                    [errors[cond][(family, s, policy)] for s in SEEDS]))
                sd_err = float(np.std(
                    [errors[cond][(family, s, policy)] for s in SEEDS], ddof=1))
                cell = "primary" if (policy == "marginal" and family != "real") else "secondary"
                summary_rows.append({
                    "family": family,
                    "condition": cond,
                    "policy": policy,
                    "n_graphs": len(SEEDS),
                    "mean_sink_errors": round(mean_err, 4),
                    "sd_sink_errors": round(sd_err, 4),
                    "mean_gain": round(float(g.mean()), 4),
                    "gain_lo": round(lo, 4),
                    "gain_hi": round(hi, 4),
                    "intact_mean_gain": round(float(gi.mean()), 4),
                    "intact_lo": round(ilo, 4),
                    "intact_hi": round(ihi, 4),
                    "gain_removed_vs_intact": round(float(removed.mean()), 4),
                    "removed_lo": round(rlo, 4),
                    "removed_hi": round(rhi, 4),
                    "verdict": verdict(ilo, lo),
                    "cell": cell,
                })

    # ---- worst-of-n over the frozen benchmark -----------------------------
    worst_rows = []
    by_family_policy = {}
    for r in rows:
        by_family_policy.setdefault((r["family"], r["policy"]), []).append(int(r["sink_errors"]))
    for (family, policy), vals in sorted(by_family_policy.items()):
        arr = np.asarray(vals, dtype=np.float64)
        with_error = int((arr >= 1).sum())
        worst_rows.append({
            "family": family,
            "policy": policy,
            "n_graphs": len(vals),
            "worst_of_n": round(with_error / len(vals), 4),
            "graphs_with_any_sink_error": with_error,
            "max_sink_errors": int(arr.max()),
            "p95_sink_errors": round(float(np.percentile(arr, 95)), 4),
            "zero_error_rate": round(float((arr == 0).mean()), 4),
        })

    # ---- diagnostics -------------------------------------------------------
    diag_rows = []
    for family in FAMILIES:
        per_graph = []
        for seed in SEEDS:
            graph = cache[(family, seed)][0]
            view = rewired[(family, seed)]
            rho = spearman([len(c) for c in graph.children],
                           [len(c) for c in view.children])
            per_graph.append(rho)
            diag_rows.append({
                "diagnostic": "hub_rank_corr",
                "family": family,
                "graph_seed": seed,
                "condition": "rewire",
                "policy": "",
                "value": "" if math.isnan(rho) else round(rho, 4),
                "n": len(graph.children),
            })
        finite = [x for x in per_graph if not math.isnan(x)]
        diag_rows.append({
            "diagnostic": "hub_rank_corr",
            "family": family,
            "graph_seed": "median",
            "condition": "rewire",
            "policy": "",
            "value": round(float(np.median(finite)), 4) if finite else "",
            "n": len(graph.children),
        })

    spike_sinks = set(cache[("spike", SEEDS[0])][0].sinks)
    for policy in POLICIES:
        total, on_sink = 0, 0
        for seed in SEEDS:
            acts = actions["flatten"][("spike", seed, policy)]
            n_sink = sum(1 for a in acts if a in spike_sinks)
            total += len(acts)
            on_sink += n_sink
            diag_rows.append({
                "diagnostic": "sink_review_share",
                "family": "spike",
                "graph_seed": seed,
                "condition": "flatten",
                "policy": policy,
                "value": round(n_sink / len(acts), 4) if acts else "",
                "n": len(acts),
            })
        diag_rows.append({
            "diagnostic": "sink_review_share",
            "family": "spike",
            "graph_seed": "pooled",
            "condition": "flatten",
            "policy": policy,
            "value": round(on_sink / total, 4) if total else "",
            "n": total,
        })

    # ---- write everything --------------------------------------------------
    controls_path = os.path.join(OUT, "controls.csv")
    with open(controls_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["family", "graph_seed", "episode_seed", "condition", "policy",
                    "budget", "sink_errors", "action_count", "actions"])
        for family in FAMILIES:
            for seed in SEEDS:
                for cond in CONDITIONS:
                    for policy in POLICIES:
                        key = (family, seed, policy)
                        acts = actions[cond][key]
                        w.writerow([family, seed, EPISODE_OFFSET + seed, cond, policy,
                                    BUDGET[family], errors[cond][key], len(acts),
                                    " ".join(str(a) for a in acts)])

    def write_dicts(path, dict_rows, fields):
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            for row in dict_rows:
                w.writerow(row)

    write_dicts(os.path.join(OUT, "controls_summary.csv"), summary_rows,
                list(summary_rows[0].keys()))
    write_dicts(os.path.join(OUT, "benchmark_worst_of_n.csv"), worst_rows,
                list(worst_rows[0].keys()))
    write_dicts(os.path.join(OUT, "diagnostics.csv"), diag_rows,
                ["diagnostic", "family", "graph_seed", "condition", "policy", "value", "n"])

    # ---- short table -------------------------------------------------------
    print()
    print("primary cells: marginal, gain = errors(confidence) - errors(policy)")
    print(f"{'family':8s} {'cond':8s} {'mean_gain':>9s} {'ci':>18s} "
          f"{'removed':>8s} {'verdict':>20s}")
    for row in summary_rows:
        if row["cell"] != "primary":
            continue
        print(f"{row['family']:8s} {row['condition']:8s} {row['mean_gain']:>9.2f} "
              f"[{row['gain_lo']:>7.2f},{row['gain_hi']:>7.2f}] "
              f"{row['gain_removed_vs_intact']:>8.2f} {row['verdict']:>20s}")

    print()
    print("all cells (verdicts):")
    for family in FAMILIES:
        cells = [r for r in summary_rows if r["family"] == family]
        print(f"  {family:8s} " + "  ".join(
            f"{r['condition']}/{r['policy']}={r['verdict']}" for r in cells))

    print()
    medians = [r for r in diag_rows
               if r["diagnostic"] == "hub_rank_corr" and r["graph_seed"] == "median"]
    print("hub_rank_corr median: " + ", ".join(
        f"{r['family']}={r['value']}" for r in medians))
    pooled = [r for r in diag_rows
              if r["diagnostic"] == "sink_review_share" and r["graph_seed"] == "pooled"]
    print("sink_review_share (spike, flatten): " + ", ".join(
        f"{r['policy']}={r['value']}" for r in pooled))

    print()
    print(f"runtime {time.time() - t0:.1f}s; wrote {OUT}/{{controls,controls_summary,"
          f"benchmark_worst_of_n,diagnostics}}.csv", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
