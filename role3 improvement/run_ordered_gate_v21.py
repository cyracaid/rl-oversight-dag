"""Read the v2.1 gate: the conditional endpoint, on a fresh block.

Pre-registration: `PREREGISTER_ORDERED_BENCHMARK_V21.md`. One number decides it:

    recovery(e) = (marginal(e) - truth_reader(e)) / (marginal(e) - oracle(e))

and `R` is its mean over episodes that have an oracle-readable gap. Episodes with no gap are
dropped and counted. H1 holds at `R >= 0.50` with a CI lower bound above 0.25.

No encoder, no training, no labels-as-input. This only asks whether the pair information is
convertible into better decisions on episodes that contain a transposition.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import random
import sys
from pathlib import Path

import numpy as np

from dag_role3 import generate_graph
from dag_role3.ordered import OrderedEnv, sample_ordered_episode
from dag_role3.policies import choose, marginal_scores

from run_ordered_gate import (EPISODE_BLOCK, bootstrap_auc, bootstrap_mean,
                              cross_validated_auc, node_features, relational_features)

GRAPH_BLOCK = (5184, 12)
EPISODE_BLOCK_21 = (5640, 60)
BUDGET = 8
Q = 1.0
POLICIES = ("marginal", "truth_reader", "symptom_reader", "oracle")
RNG_SEED = 20261125


def act(env, episode, policy, obs, rng):
    if policy == "symptom_reader":
        by_pair = {(left, right): node for node, left, right in episode.spec.derived}
        resid = obs["monotone_residual"]
        violated = [by_pair[(pos, pos + 1)] for pos in range(len(resid))
                    if resid[pos] > 0 and (pos, pos + 1) in by_pair
                    and not env._reviewed[by_pair[(pos, pos + 1)]]]
        return int(violated[0]) if violated else choose(obs, "marginal", rng)
    if policy == "truth_reader":
        pending = [episode.spec.chain[p] for p in episode.misplaced
                   if not env._reviewed[episode.spec.chain[p]]]
        return int(pending[0]) if pending else choose(obs, "marginal", rng)
    if policy == "oracle":
        score = marginal_scores(obs, base_override=env._base)
        mask = np.flatnonzero(obs["mask"])
        return int(mask[np.argmax(score[mask])])
    return choose(obs, "marginal", rng)


def run(family="real"):
    start, count = GRAPH_BLOCK
    ep_start, ep_count = EPISODE_BLOCK_21
    sink = {p: [] for p in POLICIES}
    Xn, Xr, y, groups = [], [], [], []
    for ei in range(ep_count):
        graph = generate_graph(family, start + ei % count)
        episode = sample_ordered_episode(graph, ep_start + ei, q=Q)
        for policy in POLICIES:
            env = OrderedEnv(graph, episode, budget=BUDGET)
            obs, done = env.observation(), env.done
            rng = random.Random(episode.snapshot.seed + 981)
            while not done:
                obs, _, done, info = env.step(act(env, episode, policy, obs, rng))
            sink[policy].append(float(info["sink_errors"]))
        obs = OrderedEnv(graph, episode, budget=BUDGET).observation()
        fn, fr = node_features(episode, obs), relational_features(episode, obs)
        for p in range(len(episode.chain)):
            Xn.append(fn[p]); Xr.append(fr[p])
            y.append(1.0 if p in episode.misplaced else 0.0)
            groups.append((ei,))
    return sink, np.asarray(Xn), np.asarray(Xr), np.asarray(y), groups


def bootstrap_ratio(num, den, draws=2000):
    """Bootstrap over episodes of mean(num)/mean(den)."""
    rng = np.random.default_rng(RNG_SEED)
    num, den = np.asarray(num, float), np.asarray(den, float)
    out = []
    for _ in range(draws):
        idx = rng.integers(0, len(num), len(num))
        d = den[idx].mean()
        if d > 0:
            out.append(num[idx].mean() / d)
    out = np.asarray(out)
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def _verdict_h2(h2):
    lo, hi = bootstrap_mean(h2)
    if lo >= 0:
        return "holds"
    if hi < 0:
        return "contradicted"
    return "inconclusive"


def verdict_h1(R, lo, hi):
    if R >= 0.50 and lo > 0.25:
        return "holds"
    if hi < 0.50:
        return "contradicted"
    return "inconclusive"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="outputs/ordered-gate-v21")
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)

    sink, Xn, Xr, y, groups = run()
    marg = np.asarray(sink["marginal"])
    truth = np.asarray(sink["truth_reader"])
    orac = np.asarray(sink["oracle"])
    gap, gain = marg - orac, marg - truth
    keep = gap > 0
    R = float(gain[keep].mean() / gap[keep].mean()) if keep.any() else float("nan")
    ci = bootstrap_ratio(gain[keep], gap[keep])
    h2 = sink["symptom_reader"] - marg
    a_node, p_node = cross_validated_auc(Xn, y, groups)
    a_rel, p_rel = cross_validated_auc(Xr, y, groups)
    payload = {
        "preregistration": "PREREGISTER_ORDERED_BENCHMARK_V21.md",
        "blocks": {"graphs": GRAPH_BLOCK, "episodes": EPISODE_BLOCK_21},
        "q": Q, "budget": BUDGET, "episodes": int(len(marg)),
        "kept_episodes": int(keep.sum()), "dropped_no_gap": int((~keep).sum()),
        "sink_errors": {p: float(np.mean(v)) for p, v in sink.items()},
        "gap_marginal_oracle": {"mean": float(gap.mean()),
                                "ci": bootstrap_mean(gap)},
        "recovery": {"R": R, "ci": list(ci)},
        "H1": verdict_h1(R, *ci),
        "H2_symptom": {"mean": float(h2.mean()), "ci": bootstrap_mean(h2)},
        "H2": _verdict_h2(h2),
        "H3": {"node_level_auc": a_node, "node_level_ci": bootstrap_auc(y, p_node, groups),
               "relational_auc": a_rel, "relational_ci": bootstrap_auc(y, p_rel, groups),
               "node_ok": a_node <= 0.65, "relational_ok": a_rel >= 0.75},
    }
    (out / "gate.json").write_text(json.dumps(payload, indent=2) + "\n")
    (out / "gate.md").write_text(_report(payload))
    (out / "manifest.json").write_text(json.dumps({
        "sources": {str(p): hashlib.sha256(Path(p).read_bytes()).hexdigest()
                    for p in ("dag_role3/ordered.py", "run_ordered_gate_v21.py")},
        "python": platform.python_version(), "numpy": np.__version__, "seed": RNG_SEED,
        "blocks": {"graphs": GRAPH_BLOCK, "episodes": EPISODE_BLOCK_21},
    }, indent=2) + "\n")
    print(f"R = {R:.3f} [{ci[0]:.3f}, {ci[1]:.3f}]  gap {gap.mean():.3f}  "
          f"kept {int(keep.sum())}/{len(marg)}  H1 {payload['H1']}  H2 {payload['H2']}")
    return 0 if payload["H1"] == "holds" else 1


def _report(p):
    s = p["sink_errors"]; r = p["recovery"]; h2 = p["H2_symptom"]; h3 = p["H3"]
    return "\n".join([
        "# v2.1 gate — conditional endpoint", "",
        f"Pre-registration: `{p['preregistration']}`. "
        f"Blocks: graphs `{p['blocks']['graphs']}`, episodes `{p['blocks']['episodes']}`, "
        f"q = {p['q']}, K = {p['budget']}.", "",
        f"Episodes with an oracle-readable gap: **{p['kept_episodes']}/{p['episodes']}** "
        f"(dropped {p['dropped_no_gap']}).", "",
        "| policy | sink errors |", "|---|---:|",
        *[f"| {k} | {v:.3f} |" for k, v in s.items()], "",
        f"`marginal − oracle` = {p['gap_marginal_oracle']['mean']:.3f}.", "",
        f"**Recovery R = {r['R']:.3f}** [{r['ci'][0]:.3f}, {r['ci'][1]:.3f}] — "
        "fraction of the oracle-readable gap recovered by the pair information.", "",
        "## Verdicts", "",
        f"- `H1 recovery ≥ 0.50`: **{p['H1']}**",
        f"- `H2 symptom repair is not the source`: **{p['H2']}** "
        f"({h2['mean']:+.3f} [{h2['ci'][0]:+.3f}, {h2['ci'][1]:+.3f}])",
        f"- `H3 still not locally solvable`: node-level {h3['node_level_auc']:.3f}, "
        f"order pattern {h3['relational_auc']:.3f} → "
        f"{'ok' if h3['node_ok'] and h3['relational_ok'] else 'NOT ok'}", "",
    ])


if __name__ == "__main__":
    sys.exit(main())
