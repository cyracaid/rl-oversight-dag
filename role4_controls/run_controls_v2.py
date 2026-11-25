"""Person 4 controls, v2 amendment (README section "v2 — frozen before outcomes").

Changes against v1, chosen after reading v1 and frozen before any v2 outcome:
  1. a second rewire rule, `rewire_order`, that breaks the index-hub link (modular/BA/ER);
  2. K = 10 fixed-seed rewire draws per graph instead of one;
  3. a three-level verdict with an equivalence margin of 20 % of the intact gain.
v1 code and results are untouched; v1's rewire is draw 0 of `rewire_index` (asserted).

    python3 run_controls_v2.py --selftest   # invariants + hub-rank check, no outcome
    python3 run_controls_v2.py --jobs 4     # writes results/v2/
"""
from __future__ import annotations

import argparse
import csv
import random
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_controls as rc  # noqa: E402
from dag_role3 import DAG, generate_graph, sample_episode  # noqa: E402
from dag_role3.policies import run_public_policy  # noqa: E402
from diagnostics import out_degrees, spearman  # noqa: E402

K_DRAWS = 10
MARGIN = 0.20                     # equivalence margin, fraction of the intact marginal gain
INDEX_BASE = 4_040_000            # v1 seed base; draw k uses + 100_000*k  (k=0 == v1)
ORDER_BASE = 5_050_000            # rewire_order seed base, same layout
ORDER_FAMILIES = ("modular", "ba", "er")
POLICIES = rc.POLICIES


def index_seed(graph_seed, k):
    return INDEX_BASE + 100_000 * k + graph_seed


def order_seed(graph_seed, k):
    return ORDER_BASE + 100_000 * k + graph_seed


def rewire_index(graph, graph_seed, k):
    """v1 rule with draw-specific seed. k=0 reproduces rc.rewire exactly."""
    saved = rc.REWIRE_SEED_OFFSET
    try:
        rc.REWIRE_SEED_OFFSET = index_seed(graph_seed, k) - graph_seed
        return rc.rewire(graph, graph_seed)
    finally:
        rc.REWIRE_SEED_OFFSET = saved


def rewire_order(graph, graph_seed, k):
    """Break the index-hub link (modular/BA/ER only).

    Build a random feasible order: at each step pick uniformly, among unplaced nodes whose
    parent count is at most the number already placed, the next node. Then every node draws
    its parents uniformly from the nodes placed before it. Parent counts, types and the sink
    set are kept; the result is acyclic; node index no longer decides who can be a parent.
    """
    rng = random.Random(order_seed(graph_seed, k))
    need = [len(p) for p in graph.parents]
    unplaced = set(range(graph.n))
    order = []
    while unplaced:
        feasible = sorted(v for v in unplaced if need[v] <= len(order))
        v = rng.choice(feasible)
        order.append(v)
        unplaced.remove(v)
    position = {v: i for i, v in enumerate(order)}
    parents = [()] * graph.n
    for v in order:
        if need[v]:
            parents[v] = tuple(sorted(rng.sample(order[:position[v]], need[v])))
    return DAG(tuple(parents), graph.types, graph.rates, graph.family, graph.names,
               sink_override=graph.sinks, lam=graph.lam,
               spike_probability=graph.spike_probability)


def conditions_for(family):
    out = ["intact", "flatten"] + [f"rewire_index:{k}" for k in range(K_DRAWS)]
    if family in ORDER_FAMILIES:
        out += [f"rewire_order:{k}" for k in range(K_DRAWS)]
    return out


def view_for(graph, graph_seed, condition):
    rule, k = condition.split(":")
    k = int(k)
    return rewire_index(graph, graph_seed, k) if rule == "rewire_index" else \
        rewire_order(graph, graph_seed, k)


def run_graph(args):
    family, graph_seed = args
    graph = generate_graph(family, graph_seed)
    episode_seed = rc.EPISODE_OFFSET + graph_seed
    snap = sample_episode(graph, episode_seed)
    budget = rc.budget_for(family)
    rows = []
    for condition in conditions_for(family):
        if condition == "intact":
            runs = {p: run_public_policy(graph, snap, p, budget) for p in POLICIES}
        elif condition == "flatten":
            flat = rc.dataclasses.replace(snap, edge_coins={e: False for e in snap.edge_coins})
            runs = {p: run_public_policy(graph, flat, p, budget) for p in POLICIES}
        else:
            view = view_for(graph, graph_seed, condition)
            vsnap = sample_episode(view, episode_seed)
            for name in ("source_errors", "confidence", "review_uniforms"):
                assert getattr(vsnap, name) == getattr(snap, name), (family, graph_seed, condition)
            assert [len(p) for p in view.parents] == [len(p) for p in graph.parents]
            runs = {p: rc.run_view(view, vsnap, graph, snap.edge_coins, p, budget) for p in POLICIES}
        for p, (errors, actions) in runs.items():
            rows.append(dict(family=family, graph_seed=graph_seed, condition=condition, policy=p,
                             sink_errors=int(errors), actions=" ".join(map(str, actions))))
    return rows


# --------------------------------------------------------------------- verdict (frozen)
def verdict3(intact_lo, intact_mean, lo, hi):
    if not intact_lo > 0:
        return "no-intact-advantage"
    if lo > 0:
        return "survives"
    m = MARGIN * intact_mean
    if -m <= lo and hi <= m:
        return "removed"
    return "inconclusive"


def summarise(rows):
    by = {}
    for r in rows:
        rule = r["condition"].split(":")[0]
        by.setdefault((r["family"], rule, r["policy"]), {}).setdefault(int(r["graph_seed"]), []) \
            .append(int(r["sink_errors"]))
    by_draw = {}
    for r in rows:
        by_draw.setdefault((r["family"], r["condition"], r["policy"]), []).append(int(r["sink_errors"]))
    out = []
    for family in rc.FAMILIES:
        rules = ["intact", "flatten", "rewire_index"] + (["rewire_order"] if family in ORDER_FAMILIES else [])
        seeds = sorted(by[family, "intact", "confidence"])
        intact_stats = {}
        for rule in rules:
            for policy in POLICIES:
                # per graph: mean over draws of (confidence - policy), both under the same rule,
                # as in v1. Graphs are the bootstrap unit; draws are averaged within a graph.
                conf = np.array([np.mean(by[family, rule, "confidence"][s]) for s in seeds], float)
                pol = np.array([np.mean(by[family, rule, policy][s]) for s in seeds], float)
                gain = conf - pol
                lo, hi = rc.interval(gain)
                if rule == "intact":
                    intact_stats[policy] = (lo, gain.mean(), gain)
                label = "" if policy == "confidence" or rule == "intact" else \
                    verdict3(intact_stats[policy][0], intact_stats[policy][1], lo, hi)
                draws = [c for c in by_draw if c[0] == family and c[1].startswith(rule + ":") and c[2] == policy]
                draw_means = [np.mean(by_draw[family, c[1], "confidence"]) - np.mean(by_draw[c])
                              for c in sorted(draws)]
                within = [np.var(by[family, rule, policy][s], ddof=1) for s in seeds] if draws else [0.0]
                out.append(dict(
                    family=family, rule=rule, policy=policy, n_graphs=len(seeds),
                    n_draws=len(by[family, rule, policy][seeds[0]]),
                    mean_sink_errors=pol.mean(), gain_vs_confidence=gain.mean(),
                    paired_lo=lo, paired_hi=hi,
                    margin=MARGIN * intact_stats.get(policy, (0, 0))[1] if rule != "intact" else "",
                    draw_gain_min=min(draw_means) if draw_means else "",
                    draw_gain_max=max(draw_means) if draw_means else "",
                    within_graph_sd=float(np.sqrt(np.mean(within))),
                    between_graph_sd=float(pol.std(ddof=1)),
                    verdict=label))
    return out


# ------------------------------------------------------------------------- checks
def selftest():
    seeds = range(rc.START_SEED, rc.START_SEED + rc.N_SEEDS)
    for family in rc.FAMILIES:
        for s in list(seeds)[:5]:
            g = generate_graph(family, s)
            a, b = rc.rewire(g, s), rewire_index(g, s, 0)
            assert a.parents == b.parents, "draw 0 must equal v1 rewire"
            if family in ORDER_FAMILIES:
                for k in range(2):
                    v = rewire_order(g, s, k)
                    assert [len(p) for p in v.parents] == [len(p) for p in g.parents]
                    assert v.sinks == g.sinks and v.types == g.types
                    # DAG() itself raised if the rewired graph had a cycle
    print("hub-rank correlation of out-degree, original vs rewired (median over 100 graphs, draw 0):")
    for family in ORDER_FAMILIES:
        r_idx = np.median([spearman(out_degrees(generate_graph(family, s)),
                                    out_degrees(rewire_index(generate_graph(family, s), s, 0))) for s in seeds])
        r_ord = np.median([spearman(out_degrees(generate_graph(family, s)),
                                    out_degrees(rewire_order(generate_graph(family, s), s, 0))) for s in seeds])
        print(f"  {family:8} rewire_index {r_idx:+.2f}   rewire_order {r_ord:+.2f}")
    print("selftest ok (no control outcome computed)")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=HERE / "results" / "v2")
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return
    tasks = [(f, s) for f in rc.FAMILIES for s in range(rc.START_SEED, rc.START_SEED + rc.N_SEEDS)]
    if args.jobs > 1:
        with ProcessPoolExecutor(args.jobs) as pool:
            chunks = list(pool.map(run_graph, tasks, chunksize=4))
    else:
        chunks = [run_graph(t) for t in tasks]
    rows = [r for chunk in chunks for r in chunk]

    # acceptance: intact == frozen benchmark, rewire_index:0 and flatten == v1 controls.csv
    frozen = rc.frozen_rows()
    with open(HERE / "results" / "controls.csv", encoding="utf-8") as f:
        v1 = {(r["family"], int(r["graph_seed"]), r["condition"], r["policy"]): r for r in csv.DictReader(f)}
    bad = []
    for r in rows:
        key = (r["family"], r["graph_seed"], r["policy"])
        if r["condition"] == "intact":
            ref = frozen[key]
        elif r["condition"] in ("flatten", "rewire_index:0"):
            ref = v1[r["family"], r["graph_seed"], r["condition"].split(":")[0].replace("rewire_index", "rewire"), r["policy"]]
        else:
            continue
        if int(ref["sink_errors"]) != r["sink_errors"] or ref["actions"] != r["actions"]:
            bad.append((r["family"], r["graph_seed"], r["condition"], r["policy"]))
    if bad:
        print("STOP: v2 does not reproduce the frozen benchmark / v1 rows:", bad[:10], file=sys.stderr)
        sys.exit(2)
    print("intact == frozen benchmark; flatten and rewire_index:0 == v1 controls.csv (errors and actions)")

    rc.save(args.out / "controls_v2.csv", rows)
    summary = summarise(rows)
    rc.save(args.out / "controls_v2_summary.csv",
            [{k: (rc.fmt(v, 4) if isinstance(v, float) else v) for k, v in r.items()} for r in summary])
    print(f"wrote {args.out}/controls_v2.csv, controls_v2_summary.csv")


if __name__ == "__main__":
    main()
