"""Exploratory diagnostic: where the v2 gate's decision value went.

The gate is closed on G2 (`truth_reader - marginal` = negative). This script does not change
that verdict; it establishes *why*, so the write-up states the right reason instead of the
convenient one. Three candidate explanations, each given its own policy:

  symptom_reader  review the derived node whose recorded difference is impossible, else
                  `marginal`. If this beats `marginal`, the order defect is actionable at a
                  single node and the pair never had to be resolved.
  truth_reader    review the misplaced segment nodes first (the gate's ceiling).
  oracle          rank by the marginal score evaluated at the hidden source-error vector.
                  Evaluation-only; the strongest reference that exists.

Pre-registered blocks only (graphs 5160-5171, episodes 5600-5639). No training, no tuning.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np

from dag_role3 import generate_graph
from dag_role3.ordered import OrderedEnv, sample_ordered_episode
from dag_role3.policies import choose, marginal_scores

from run_ordered_gate import EPISODE_BLOCK, GRAPH_BLOCKS, BUDGETS, bootstrap_mean

POLICIES = ("none", "random", "marginal", "symptom_reader", "truth_reader", "oracle")


def act(env, episode, policy, obs, rng):
    if policy == "symptom_reader":
        resid = obs["monotone_residual"]
        by_pair = {(left, right): node for node, left, right in episode.spec.derived}
        violated = [by_pair[(pos, pos + 1)] for pos in range(len(resid))
                    if resid[pos] > 0 and (pos, pos + 1) in by_pair
                    and not env._reviewed[by_pair[(pos, pos + 1)]]]
        if violated:
            return int(violated[0])
        return choose(obs, "marginal", rng)
    if policy == "truth_reader":
        pending = [episode.spec.chain[p] for p in episode.misplaced
                   if not env._reviewed[episode.spec.chain[p]]]
        if pending:
            return pending[0]
        return choose(obs, "marginal", rng)
    if policy == "oracle":
        score = marginal_scores(obs, base_override=env._base)
        return int(np.flatnonzero(obs["mask"])[np.argmax(score[obs["mask"]])])
    if policy == "random":
        return choose(obs, "random", rng)
    return choose(obs, "marginal", rng)


def run(family="real"):
    start, count = GRAPH_BLOCKS[family]
    ep_start, ep_count = EPISODE_BLOCK
    out = {p: [] for p in POLICIES}
    transposed = []
    for ei in range(ep_count):
        graph = generate_graph(family, start + ei % count)
        episode = sample_ordered_episode(graph, ep_start + ei)
        for policy in POLICIES:
            env = OrderedEnv(graph, episode, budget=BUDGETS[family])
            if policy == "none":
                out[policy].append(env.no_review_score())
                continue
            obs, done = env.observation(), env.done
            rng = random.Random(episode.snapshot.seed + 981)
            while not done:
                obs, _, done, info = env.step(act(env, episode, policy, obs, rng))
            out[policy].append(float(info["sink_errors"]))
        transposed.append(episode.transposed is not None)
    return out, transposed


def main():
    out, transposed = run()
    marg = np.asarray(out["marginal"])
    summary = {p: {"mean": float(np.mean(v)),
                   "minus_marginal": float(np.mean(np.asarray(v) - marg)),
                   "ci": bootstrap_mean(np.asarray(v) - marg)} for p, v in out.items()}
    t = np.asarray(transposed)
    per_group = {
        "transposed_episodes": int(t.sum()),
        "marginal_on_transposed": float(marg[t].mean()) if t.any() else None,
        "marginal_on_clean": float(marg[~t].mean()) if (~t).any() else None,
        "symptom_reader_on_transposed": float(np.asarray(out["symptom_reader"])[t].mean()) if t.any() else None,
        "truth_reader_on_transposed": float(np.asarray(out["truth_reader"])[t].mean()) if t.any() else None,
        "oracle_on_transposed": float(np.asarray(out["oracle"])[t].mean()) if t.any() else None,
    }
    payload = {"exploratory": True, "note": "post hoc; does not reopen the closed G2 gate",
               "policies": summary, "split": per_group}
    Path("outputs/ordered-gate-v2").mkdir(parents=True, exist_ok=True)
    Path("outputs/ordered-gate-v2/diagnostic.json").write_text(json.dumps(payload, indent=2) + "\n")
    for p, v in summary.items():
        print(f"{p:>15}: {v['mean']:.3f}  vs marginal {v['minus_marginal']:+.3f} "
              f"[{v['ci'][0]:+.3f}, {v['ci'][1]:+.3f}]")
    print("split:", json.dumps(per_group, indent=2))


if __name__ == "__main__":
    main()
