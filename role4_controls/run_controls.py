"""Person 4 structural controls on the frozen role3 environment (tag role3-env-v3).

Three paired episode conditions on the frozen benchmark graphs (seeds 90000-90099):

  intact   the episode exactly as the frozen benchmark runs it (``run_public_policy``)
  flatten  same episode, every hidden edge coin set to False: errors no longer travel.
           The policy still sees the graph and its edge probabilities, as specified in
           TEAM_REQUESTS_P4_P5.md.
  rewire   the policy plans on a *rewired* copy of the graph, while errors still travel
           on the true graph. Source errors, confidences and reviewer randomness are
           identical (asserted). See README.md "Frozen before outcomes" for the rule.

Nothing in ``role3 improvement/dag_role3`` is copied or changed; it is imported.

    python3 run_controls.py --out results/
    python3 run_controls.py --selftest      # invariants only, prints no control outcome
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import math
import os
import random
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROLE3 = HERE.parent / "role3 improvement"
sys.path.insert(0, str(ROLE3))

from dag_role3 import DAG, OversightEnv, generate_graph, propagate, sample_episode  # noqa: E402
from dag_role3.policies import choose, run_public_policy  # noqa: E402

FAMILIES = ("spike", "modular", "ba", "er", "real")
POLICIES = ("confidence", "structural", "marginal")
CONDITIONS = ("intact", "flatten", "rewire")
START_SEED, N_SEEDS = 90000, 100
EPISODE_OFFSET = 20000          # frozen benchmark: episode_seed = 20000 + graph_seed
REWIRE_SEED_OFFSET = 4_040_000  # frozen before outcomes: Random(4_040_000 + graph_seed)
BUDGET = {"spike": 16, "real": 8}  # 50 otherwise, as in run_benchmark.py
FROZEN_ROWS = ROLE3 / "outputs" / "v3" / "benchmark_role3.csv"


def budget_for(family: str) -> int:
    return BUDGET.get(family, 50)


# ---------------------------------------------------------------- rewire rule (frozen)
def rewire(graph: DAG, graph_seed: int) -> DAG:
    """Keep every node's number of parents, its type and the sink set; redraw parents.

    spike : parents drawn from the previous layer (the generator's own rule)
    real  : parents drawn from all nodes in strictly lower layers
    modular / ba / er : parents drawn from all nodes with a lower index
            (the original graphs are oriented by index, so this keeps a DAG;
            "all other nodes" would allow cycles)
    """
    rng = random.Random(REWIRE_SEED_OFFSET + graph_seed)
    layer = graph.layers
    parents = []
    for v, ps in enumerate(graph.parents):
        k = len(ps)
        if k == 0:
            parents.append(())
            continue
        if graph.family == "spike":
            cands = [u for u in range(graph.n) if layer[u] == layer[v] - 1]
        elif graph.family == "real":
            cands = [u for u in range(graph.n) if layer[u] < layer[v]]
        else:
            cands = list(range(v))
        parents.append(tuple(sorted(rng.sample(cands, k))))
    return DAG(tuple(parents), graph.types, graph.rates, graph.family, graph.names,
               sink_override=graph.sinks, lam=graph.lam,
               spike_probability=graph.spike_probability)


# ---------------------------------------------------- environment with a wrong map
class MapMismatchEnv(OversightEnv):
    """The policy observes ``view`` (graph + snapshot); errors travel on ``truth``.

    Only the hidden error state is recomputed on the true graph after the parent
    class updates it. Observations, belief updates and the reviewer draw are the
    parent's own code. With view == truth this reproduces OversightEnv exactly
    (checked by --selftest).
    """

    def __init__(self, view_graph, view_snapshot, truth_graph, truth_coins, budget):
        self._truth = (truth_graph, truth_coins)
        super().__init__(view_graph, view_snapshot, budget=budget)

    def _truth_effective(self):
        graph, coins = self._truth
        return propagate(graph, self._base, coins)

    def _sink_errors(self):
        return sum(self._effective[i] for i in self._truth[0].sinks)

    def reset(self):
        obs = super().reset()
        self._effective = self._truth_effective()
        self._initial_sink_errors = self._sink_errors()
        return obs

    def step(self, action):
        obs, _, done, info = super().step(action)
        self._effective = self._truth_effective()
        after = self._sink_errors()
        self._trace[-1]["sink_errors_after"] = after
        if done:
            info["sink_errors"] = after
            info["initial_sink_errors"] = self._initial_sink_errors
        return obs, (-float(after) if done else 0.0), done, info


def run_view(view_graph, view_snapshot, truth_graph, truth_coins, policy, budget):
    """Same loop as run_public_policy, with the mismatch environment."""
    env = MapMismatchEnv(view_graph, view_snapshot, truth_graph, truth_coins, budget)
    rng = random.Random(view_snapshot.seed + 981)
    obs, done, actions = env.observation(), env.done, []
    while not done:
        action = choose(obs, policy, rng)
        actions.append(action)
        obs, _, done, _ = env.step(action)
    return env.final_audit()["final_sink_errors"], actions


def episode_inputs(family, graph_seed):
    graph = generate_graph(family, graph_seed)
    episode_seed = EPISODE_OFFSET + graph_seed
    snapshot = sample_episode(graph, episode_seed)
    flat = dataclasses.replace(snapshot, edge_coins={e: False for e in snapshot.edge_coins})
    view_graph = rewire(graph, graph_seed)
    view_snapshot = sample_episode(view_graph, episode_seed)
    for name in ("source_errors", "confidence", "review_uniforms"):
        if getattr(view_snapshot, name) != getattr(snapshot, name):
            raise AssertionError(f"rewire changed {name} on {family} {graph_seed}")
    if sorted(map(len, view_graph.parents)) != sorted(map(len, graph.parents)) or \
            [len(p) for p in view_graph.parents] != [len(p) for p in graph.parents]:
        raise AssertionError("rewire changed in-degrees")
    return graph, episode_seed, snapshot, flat, view_graph, view_snapshot


def run_one(family, graph_seed, policy, condition, inputs):
    graph, _, snapshot, flat, view_graph, view_snapshot = inputs
    budget = budget_for(family)
    if condition == "intact":
        return run_public_policy(graph, snapshot, policy, budget)
    if condition == "flatten":
        return run_public_policy(graph, flat, policy, budget)
    return run_view(view_graph, view_snapshot, graph, snapshot.edge_coins, policy, budget)


# ------------------------------------------------------------------- statistics
def interval(xs):
    """Verbatim from role3 run_benchmark.interval: paired bootstrap, seed 411, 20x100."""
    xs = np.asarray(xs, dtype=float)
    if len(xs) < 2:
        return "", ""
    rng = np.random.default_rng(411)
    means = [xs[rng.integers(len(xs), size=(100, len(xs)))].mean(axis=1)
             for _ in range(20)]
    return tuple(np.quantile(np.concatenate(means), [.025, .975]))


def verdict(intact_lo, cond_lo, cond_hi):
    """Frozen labels (README). Positive gain = policy leaves fewer errors than confidence."""
    if not intact_lo > 0:
        return "no-intact-advantage"
    if cond_lo > 0:
        return "survives"
    return "removed"


def save(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", newline="", encoding="utf-8", dir=path.parent,
                                     delete=False) as stream:
        tmp = stream.name
        writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)


def fmt(x, nd=3):
    return "" if x == "" else f"{x:.{nd}f}"


def frozen_rows():
    with open(FROZEN_ROWS, encoding="utf-8-sig") as f:
        return {(r["family"], int(r["graph_seed"]), r["policy"]): r for r in csv.DictReader(f)}


def summarise(rows):
    errors = {}
    for r in rows:
        errors.setdefault((r["family"], r["condition"], r["policy"]), []).append(r["sink_errors"])
    out = []
    present = {r["family"] for r in rows}
    for family in (f for f in FAMILIES if f in present):
        intact_lo = {}
        for condition in CONDITIONS:
            base = np.asarray(errors[family, condition, "confidence"], dtype=float)
            for policy in POLICIES:
                e = np.asarray(errors[family, condition, policy], dtype=float)
                gain = base - e
                lo, hi = interval(gain)
                if condition == "intact":
                    intact_lo[policy] = lo
                    shift, slo, shi, label = 0.0, 0.0, 0.0, ""
                else:
                    intact = np.asarray(errors[family, "intact", "confidence"], dtype=float) - \
                        np.asarray(errors[family, "intact", policy], dtype=float)
                    shift = intact - gain             # how much of the gain the control removed
                    slo, shi = interval(shift)
                    shift = shift.mean()
                    label = "" if policy == "confidence" else verdict(intact_lo[policy], lo, hi)
                out.append(dict(
                    family=family, condition=condition, policy=policy, n_graphs=len(e),
                    mean_sink_errors=e.mean(), zero_error_rate=float(np.mean(e == 0)),
                    worst_of_n=float(np.mean(e >= 1)), max_sink_errors=e.max(),
                    gain_vs_confidence=gain.mean(), paired_lo=lo, paired_hi=hi,
                    wins=int((gain > 0).sum()), ties=int((gain == 0).sum()),
                    losses=int((gain < 0).sum()),
                    gain_removed_vs_intact=shift, removed_lo=slo, removed_hi=shi,
                    verdict=label))
    return out


def worst_of_n_table():
    """worst-of-n for every policy already in the frozen benchmark: a groupby, no rerun."""
    groups = {}
    with open(FROZEN_ROWS, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            groups.setdefault((r["family"], r["policy"]), []).append(int(r["sink_errors"]))
    out = []
    for (family, policy), e in groups.items():
        e = np.asarray(e)
        out.append(dict(family=family, policy=policy, n_graphs=len(e),
                        mean_sink_errors=e.mean(),
                        worst_of_n=float(np.mean(e >= 1)),
                        graphs_with_error=int((e >= 1).sum()),
                        max_sink_errors=int(e.max()),
                        p95_sink_errors=float(np.quantile(e, .95))))
    return out


# ------------------------------------------------------------------------- main
def selftest(seeds=5):
    """Invariants only; prints nothing about flatten or rewire outcomes."""
    for family in FAMILIES:
        for s in range(START_SEED, START_SEED + seeds):
            inputs = episode_inputs(family, s)
            graph, _, snapshot, *_ = inputs
            for policy in POLICIES:
                a = run_public_policy(graph, snapshot, policy, budget_for(family))
                b = run_view(graph, snapshot, graph, snapshot.edge_coins, policy, budget_for(family))
                if a != b:
                    raise AssertionError(f"mismatch env != frozen env on {family} {s} {policy}")
    print(f"selftest ok: rewire invariants hold and MapMismatchEnv(view=truth) == frozen env "
          f"on {len(FAMILIES)} families x {seeds} graphs x {len(POLICIES)} policies")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=HERE / "results")
    ap.add_argument("--families", nargs="+", choices=FAMILIES, default=list(FAMILIES))
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return

    frozen = frozen_rows()
    rows, mismatches = [], []
    for family in args.families:
        for s in range(START_SEED, START_SEED + N_SEEDS):
            inputs = episode_inputs(family, s)
            for condition in CONDITIONS:
                for policy in POLICIES:
                    errors, actions = run_one(family, s, policy, condition, inputs)
                    rows.append(dict(family=family, graph_seed=s, episode_seed=inputs[1],
                                     condition=condition, policy=policy, budget=budget_for(family),
                                     sink_errors=int(errors),
                                     actions=" ".join(map(str, actions))))
                    if condition == "intact":
                        ref = frozen[family, s, policy]
                        if int(ref["sink_errors"]) != errors or ref["actions"] != rows[-1]["actions"]:
                            mismatches.append((family, s, policy, ref["sink_errors"], errors))
        print(f"{family}: done", flush=True)
    if mismatches:
        print("STOP: intact does not reproduce the frozen benchmark", file=sys.stderr)
        for m in mismatches[:20]:
            print("  ", m, file=sys.stderr)
        sys.exit(2)
    print(f"intact reproduces the frozen benchmark: "
          f"{sum(r['condition'] == 'intact' for r in rows)} rows, errors and actions identical")

    save(args.out / "controls.csv", rows)
    summary = summarise(rows)
    save(args.out / "controls_summary.csv",
         [{k: (fmt(v, 4) if isinstance(v, float) else v) for k, v in r.items()} for r in summary])
    save(args.out / "benchmark_worst_of_n.csv",
         [{k: (fmt(v, 4) if isinstance(v, float) else v) for k, v in r.items()}
          for r in worst_of_n_table()])
    print(f"wrote {args.out}/controls.csv, controls_summary.csv, benchmark_worst_of_n.csv")


if __name__ == "__main__":
    main()
