"""Diagnostic: is the v2 order defect localisable from a single node's own comparisons?

Written after reading the v2 and v2.1 gates, because both of them returned numbers that
contradict each other and neither asked the question it thought it was asking.

Three measurements, all on spent blocks, none of them a new verdict:

1. what the gate read (pooled AUC over all node rows) next to
2. the within-episode AUC on affected episodes only, next to
3. the AUC that separates clean from transposed episodes.

If a feature set has (2) = 0.5 and (3) = 1.0, its pooled AUC is measuring "is this episode
broken", not "which node is wrong". That is what happened.

Then a two-line rule that reads only each node's own two adjacent residual signs, and the
count of distinct feature rows per episode. Both are cheap and both are decisive.

Not a threshold, not a retune, not a new block: `PREREGISTER_ORDERED_BENCHMARK.md`
amendment 2 cites these numbers to withdraw the v2 gate reading.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from dag_role3 import generate_graph
from dag_role3.ordered import OrderedEnv, sample_ordered_episode

from run_ordered_gate import (EPISODE_BLOCK, GRAPH_BLOCKS, _auc, collect,
                              cross_validated_auc, relational_features)

V2_EPISODES = (5600, 40)
V21_EPISODES = (5640, 60)


def local_rule(clocks):
    """First descent pair start, last ascent pair end — each node's own two residuals."""
    c = np.asarray(clocks, float)
    desc = [i for i in range(len(c) - 1) if c[i] >= c[i + 1]]
    return tuple(sorted((desc[0], desc[-1] + 1))) if desc else None


def split_aucs(family, q, episode_block):
    if episode_block != V2_EPISODES:
        raise SystemExit("the v2.1 block is not run through `collect`; use rule_accuracy")
    data = collect(family, q, "normal")
    y, groups = data["y"], data["groups"]
    episodes = sorted({k[1] for k in groups})
    start, count = GRAPH_BLOCKS[family]
    transposed = {}
    for ei in episodes:
        graph = generate_graph(family, start + ei % count)
        transposed[ei] = sample_ordered_episode(graph, episode_block[0] + ei,
                                                q=q).transposed is not None
    ep_tr = np.asarray([1.0 if transposed[e] else 0.0 for e in episodes])
    rows = {}
    for name in ("node", "relational"):
        pooled, pred = cross_validated_auc(data[name], y, groups)
        m_of = lambda ei: np.array([k[1] == ei for k in groups])
        within = [_auc(y[m_of(e)], pred[m_of(e)]) for e in episodes if transposed[e]]
        means = np.asarray([pred[m_of(e)].mean() for e in episodes])
        rows[name] = {"pooled_auc": pooled, "within_episode_auc": float(np.nanmean(within)),
                      "clean_vs_transposed_auc": _auc(ep_tr, means)}
    return rows, int(ep_tr.sum()), len(episodes)


def rule_accuracy(family, q, episode_block):
    start, count = GRAPH_BLOCKS[family]
    ep_start, ep_count = episode_block
    hits, n, pairs = 0, 0, {}
    for ei in range(ep_count):
        graph = generate_graph(family, start + ei % count)
        ep = sample_ordered_episode(graph, ep_start + ei, q=q)
        if ep.transposed is None:
            continue
        n += 1
        hits += local_rule(ep.clocks) == ep.misplaced
        pairs[ep.transposed] = pairs.get(ep.transposed, 0) + 1
    return {"exact": hits, "affected": n,
            "accuracy": (hits / n) if n else float("nan"),
            "pairs": {str(k): v for k, v in sorted(pairs.items())}}


def distinct_rows(family, episode_block):
    start, count = GRAPH_BLOCKS[family]
    ep_start, ep_count = episode_block
    found = set()
    for ei in range(ep_count):
        graph = generate_graph(family, start + ei % count)
        ep = sample_ordered_episode(graph, ep_start + ei, q=0.5)
        obs = OrderedEnv(graph, ep, budget=8).observation()
        found.add(int(np.unique(np.round(relational_features(ep, obs), 9), axis=0).shape[0]))
    return sorted(found)


def main():
    out = Path("outputs/ordered-gate-v2")
    out.mkdir(parents=True, exist_ok=True)
    rows, affected, episodes = split_aucs("real", 0.5, V2_EPISODES)
    payload = {
        "note": "diagnostic on spent blocks; withdraws the v2 gate reading, adds no verdict",
        "v2_block": {"episodes": V2_EPISODES, "affected": affected, "total": episodes},
        "feature_sets": rows,
        "local_rule": {
            "description": "first descent start and last ascent end, from each node's own "
                           "two adjacent residual signs",
            "v2_q050": rule_accuracy("real", 0.5, V2_EPISODES),
            "v21_q100": rule_accuracy("real", 1.0, V21_EPISODES),
        },
        "distinct_relational_feature_rows_per_episode": distinct_rows("real", V2_EPISODES),
        "chain_length": 4,
    }
    (out / "locality.json").write_text(json.dumps(payload, indent=2) + "\n")

    print("| feature set | pooled AUC (what the gate read) | within-episode AUC "
          "| clean-vs-transposed AUC |")
    print("|---|---:|---:|---:|")
    for name, r in rows.items():
        print(f"| {name} | {r['pooled_auc']:.3f} | {r['within_episode_auc']:.3f} "
              f"| {r['clean_vs_transposed_auc']:.3f} |")
    for tag in ("v2_q050", "v21_q100"):
        lr = payload["local_rule"][tag]
        print(f"local rule {tag}: {lr['exact']}/{lr['affected']} exact "
              f"({lr['accuracy']:.3f}), pairs {lr['pairs']}")
    print("distinct relational feature rows per episode:",
          payload["distinct_relational_feature_rows_per_episode"], "of", payload["chain_length"])


if __name__ == "__main__":
    main()
