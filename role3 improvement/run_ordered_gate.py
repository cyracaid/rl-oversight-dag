"""Read the v2 gate (§ 'Gate' of `PREREGISTER_ORDERED_BENCHMARK.md` and its amendment).

Four numbers, no model:

  G1a  AUC of "is this chain position misplaced" from per-node public features only.
       Must stay <= 0.65: if a single node's own features answer the question, the mechanism
       is the one already rejected in the pre-registration and proves nothing about a
       relational state.
  G1b  AUC of the same question from the chain's order pattern (all pairwise comparisons).
       Must reach >= 0.75: if the order pattern does not answer it either, no policy can win.
  G2   truth_reader - marginal on sink errors at K=8, `real`. Must be >= 0.15, five times the
       entire v1 DP headroom of 0.030.
  G3   negative control: with `confidence_mode="noise"`, G1a must stay <= 0.65.

Blocks (reserved in `BENCHMARK_SPEC.md` before any v2 code existed): graphs 5160-5183,
episodes 5600-5639. This script is the only consumer; it does not retrain anything.
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
from dag_role3.ordered import DEFAULT_Q, ORDERED_SPECS, OrderedEnv, sample_ordered_episode
from dag_role3.policies import choose

GRAPH_BLOCKS = {"real": (5160, 12), "ticket": (5172, 12)}
EPISODE_BLOCK = (5600, 40)
BUDGETS = {"real": 8, "ticket": 8}
CONFIDENCE_MODES = ("normal", "noise")
BOOT = 2000
RNG_SEED = 20261125


def _auc(y, s):
    """Rank AUC without sklearn so the number is reproducible from numpy alone."""
    y = np.asarray(y, dtype=float)
    s = np.asarray(s, dtype=float)
    pos, neg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    order = np.argsort(np.concatenate([pos, neg]), kind="mergesort")
    ranks = np.empty(len(order), dtype=float)
    ranks[order] = np.arange(1, len(order) + 1)
    # average ranks for ties
    allv = np.concatenate([pos, neg])
    for v in np.unique(allv):
        m = allv == v
        if m.sum() > 1:
            ranks[m] = ranks[m].mean()
    r_pos = ranks[:len(pos)].sum()
    return float((r_pos - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def _fit_logistic(X, y, l2=1.0, iters=400):
    """Plain Newton/logistic fit; deterministic, no third-party dependency."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    mu, sd = X.mean(0), X.std(0)
    sd[sd == 0] = 1.0
    Z = np.column_stack([np.ones(len(X)), (X - mu) / sd])
    w = np.zeros(Z.shape[1])
    for _ in range(iters):
        p = 1.0 / (1.0 + np.exp(-Z @ w))
        g = Z.T @ (p - y) + l2 * np.r_[0.0, w[1:]]
        H = (Z * (p * (1 - p))[:, None]).T @ Z + l2 * np.diag(np.r_[0.0, np.ones(len(w) - 1)])
        step = np.linalg.solve(H + 1e-9 * np.eye(len(w)), g)
        w -= step
        if np.abs(step).max() < 1e-8:
            break
    return lambda Xn: np.column_stack([np.ones(len(Xn)), (np.asarray(Xn, float) - mu) / sd]) @ w


def node_features(episode, obs):
    """Per-node public features. No hidden flag, no cross-node comparison."""
    f = obs["features"]
    k = f.shape[1] - 7
    clocks = obs["clocks"]
    resid = obs["monotone_residual"]
    rows = []
    for p, node in enumerate(episode.chain):
        left = resid[p - 1] if p > 0 else 0.0
        right = resid[p] if p < len(resid) else 0.0
        rows.append([
            float(clocks[p]) / 1440.0,   # the node's own clock; no chain-relative normalisation
            left / 100.0, right / 100.0,
            float(f[node, k]),          # confidence
            float(f[node, k + 2]),      # belief base
            float(f[node, k + 1]),      # normalised log sink reach
            1.0 if p == 0 else 0.0,
            1.0 if p == len(episode.chain) - 1 else 0.0,
        ])
    return np.asarray(rows)


def relational_features(episode, obs):
    """The order pattern: every pairwise comparison in the chain, plus rank."""
    c = np.asarray(obs["clocks"], float)
    n = len(c)
    cmp_ = [1.0 if c[i] > c[j] else 0.0 for i in range(n) for j in range(i + 1, n)]
    order = np.argsort(np.argsort(c))
    rank = order / max(1, n - 1)
    offset = order - np.arange(n)
    return np.asarray([cmp_ + list(rank) + list(offset) for _ in range(n)])


def collect(family, q, confidence_mode):
    start, count = GRAPH_BLOCKS[family]
    ep_start, ep_count = EPISODE_BLOCK
    Xn, Xr, y, groups = [], [], [], []
    policies = {"none": [], "marginal": [], "truth_reader": []}
    transposed_episodes = 0
    for ei in range(ep_count):
        gi = ei % count
        graph = generate_graph(family, start + gi)
        if True:
            seed = ep_start + ei
            episode = sample_ordered_episode(graph, seed, q=q,
                                             confidence_mode=confidence_mode)
            if episode.transposed is not None:
                transposed_episodes += 1
            env = OrderedEnv(graph, episode, budget=BUDGETS[family],
                             confidence_mode=confidence_mode)
            obs = env.observation()
            fn = node_features(episode, obs)
            fr = relational_features(episode, obs)
            for p in range(len(episode.chain)):
                Xn.append(fn[p])
                Xr.append(fr[p])
                y.append(1.0 if p in episode.misplaced else 0.0)
                groups.append((gi, ei))
            if confidence_mode != "normal":
                continue
            policies["none"].append(_run(env, episode, "none"))
            policies["marginal"].append(_run(OrderedEnv(graph, episode, budget=BUDGETS[family]),
                                             episode, "marginal"))
            policies["truth_reader"].append(
                _run(OrderedEnv(graph, episode, budget=BUDGETS[family]), episode, "truth_reader"))
    return {
        "node": np.asarray(Xn), "relational": np.asarray(Xr), "y": np.asarray(y),
        "groups": groups, "policies": policies,
        "transposed_episodes": transposed_episodes, "episodes": ep_count,
    }


def _run(env, episode, policy):
    if policy == "none":
        return float(env.no_review_score())
    obs, done = env.observation(), env.done
    rng = random.Random(episode.snapshot.seed + 981)
    while not done:
        action = _act(env, episode, policy, obs, rng)
        obs, _, done, info = env.step(action)
    return float(info["sink_errors"])


def _act(env, episode, policy, obs, rng):
    if policy == "marginal":
        return choose(obs, "marginal", rng)
    if policy == "truth_reader":
        spec = episode.spec
        pending = [spec.chain[p] for p in episode.misplaced
                   if not env._reviewed[spec.chain[p]]]
        if pending:
            return pending[0]
        return choose(obs, "marginal", rng)
    return choose(obs, "random", rng)


def cross_validated_auc(X, y, groups, folds=5, l2=1.0):
    """Out-of-fold predictions, split by episode. Returns (auc, predictions)."""
    keys = sorted({g for g in groups})
    rng = random.Random(RNG_SEED)
    rng.shuffle(keys)
    fold_of = {k: i % folds for i, k in enumerate(keys)}
    pred = np.zeros(len(y))
    for f in range(folds):
        train = np.array([fold_of[g] != f for g in groups])
        test = ~train
        if y[train].sum() in (0, len(y[train])) or test.sum() == 0:
            pred[test] = y[train].mean() if train.sum() else 0.5
            continue
        model = _fit_logistic(X[train], y[train], l2=l2)
        pred[test] = model(X[test])
    return _auc(y, pred), pred


def bootstrap_auc(y, pred, groups, draws=BOOT):
    rng = np.random.default_rng(RNG_SEED)
    keys = sorted({g for g in groups})
    idx_by_key = {k: np.flatnonzero(np.asarray([g == k for g in groups])) for k in keys}
    out = []
    for _ in range(draws):
        pick = [keys[i] for i in rng.integers(0, len(keys), len(keys))]
        sel = np.concatenate([idx_by_key[k] for k in pick])
        v = _auc(y[sel], pred[sel])
        if np.isfinite(v):
            out.append(v)
    out = np.asarray(out)
    return [float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))]


def verdict_g1a(auc):
    if auc <= 0.65:
        return "holds"
    if auc >= 0.70:
        return "contradicted"
    return "inconclusive"


def verdict_g1b(auc):
    if auc >= 0.75:
        return "holds"
    if auc < 0.70:
        return "contradicted"
    return "inconclusive"


def verdict_g2(point, lo, hi):
    if point >= 0.15:
        return "holds"
    if hi < 0.15:
        return "contradicted"
    return "inconclusive"


def bootstrap_mean(values, draws=BOOT):
    rng = np.random.default_rng(RNG_SEED)
    v = np.asarray(values, float)
    means = np.asarray([v[rng.integers(0, len(v), len(v))].mean() for _ in range(draws)])
    return [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))]


def _g2_args(rec):
    d = rec["truth_reader_minus_marginal"]
    return d["mean"], d["ci"][0], d["ci"][1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="outputs/ordered-gate-v2")
    ap.add_argument("--q", type=float, default=DEFAULT_Q)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    results, rows = {}, []
    for family in ("real", "ticket"):
        results[family] = {}
        for mode in CONFIDENCE_MODES:
            data = collect(family, args.q, mode)
            rec = {"transposed_episodes": data["transposed_episodes"],
                   "episodes": data["episodes"],
                   "positives": int(data["y"].sum())}
            for name, X in (("node_level", data["node"]), ("relational", data["relational"])):
                auc, pred = cross_validated_auc(X, data["y"], data["groups"])
                rec[name] = {"auc": auc, "ci": bootstrap_auc(data["y"], pred, data["groups"])}
            if mode == "normal":
                pol = {k: float(np.mean(v)) for k, v in data["policies"].items()}
                diff = np.asarray(data["policies"]["truth_reader"]) - np.asarray(data["policies"]["marginal"])
                rec["policy_sink_errors"] = pol
                rec["truth_reader_minus_marginal"] = {
                    "mean": float(diff.mean()),
                    "ci": bootstrap_mean(diff),
                }
            results[family][mode] = rec
            rows.append((family, mode, rec))
            print(f"{family:>6} {mode:>6}: G1a node-level AUC {rec['node_level']['auc']:.3f} "
                  f"[{rec['node_level']['ci'][0]:.3f}, {rec['node_level']['ci'][1]:.3f}]  "
                  f"G1b relational AUC {rec['relational']['auc']:.3f} "
                  f"[{rec['relational']['ci'][0]:.3f}, {rec['relational']['ci'][1]:.3f}]  "
                  f"({rec['transposed_episodes']}/{rec['episodes']} transposed)")

    real = results["real"]["normal"]
    ticket = results["ticket"]["normal"]
    verdicts = {
        "G1a_not_local": verdict_g1a(real["node_level"]["auc"]),
        "G1b_global": verdict_g1b(real["relational"]["auc"]),
        "G2_decision_value": verdict_g2(*_g2_args(real)),
        "G3_noise_control_not_local": verdict_g1a(results["real"]["noise"]["node_level"]["auc"]),
    }
    gate_open = (verdicts["G1a_not_local"] == "holds" and verdicts["G1b_global"] == "holds"
                 and verdicts["G2_decision_value"] == "holds"
                 and verdicts["G3_noise_control_not_local"] == "holds")
    payload = {
        "preregistration": "PREREGISTER_ORDERED_BENCHMARK.md",
        "q": args.q,
        "graphs": GRAPH_BLOCKS,
        "episodes": EPISODE_BLOCK,
        "budgets": BUDGETS,
        "families": results,
        "verdicts": verdicts,
        "gate_open": bool(gate_open),
        "ticket_side_note": {
            "G1a_not_local": verdict_g1a(ticket["node_level"]["auc"]),
            "G1b_global": verdict_g1b(ticket["relational"]["auc"]),
            "G2_decision_value": verdict_g2(*_g2_args(ticket)),
        },
    }
    (out / "gate.json").write_text(json.dumps(payload, indent=2) + "\n")
    (out / "gate.md").write_text(_report(payload, rows))
    src = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
           for p in (Path("dag_role3/ordered.py"), Path("run_ordered_gate.py"))}
    (out / "manifest.json").write_text(json.dumps({
        "sources": src, "python": platform.python_version(),
        "numpy": np.__version__, "seed": RNG_SEED,
        "blocks": {"graphs": GRAPH_BLOCKS, "episodes": EPISODE_BLOCK},
    }, indent=2) + "\n")
    print("gate:", verdicts, "open" if gate_open else "closed")
    return 0 if gate_open else 1


def _report(payload, rows):
    L = ["# v2 gate", "",
         f"Pre-registration: `{payload['preregistration']}` (including the same-day amendment).",
         f"Blocks: graphs `{payload['graphs']}`, episodes `{payload['episodes']}`, q = {payload['q']}.",
         "", "| family | mode | G1a node-level AUC | G1b relational AUC | transposed episodes |",
         "|---|---|---:|---:|---:|"]
    for family, mode, rec in rows:
        L.append(f"| {family} | {mode} | {rec['node_level']['auc']:.3f} "
                 f"[{rec['node_level']['ci'][0]:.3f}, {rec['node_level']['ci'][1]:.3f}] | "
                 f"{rec['relational']['auc']:.3f} "
                 f"[{rec['relational']['ci'][0]:.3f}, {rec['relational']['ci'][1]:.3f}] | "
                 f"{rec['transposed_episodes']}/{rec['episodes']} |")
    real = payload["families"]["real"]["normal"]
    L += ["", "## Decision value, `real`, K=8", "",
          "| policy | sink errors |", "|---|---:|"]
    for name, v in real["policy_sink_errors"].items():
        L.append(f"| {name} | {v:.3f} |")
    d = real["truth_reader_minus_marginal"]
    L += ["", f"`truth_reader - marginal` = **{d['mean']:+.3f}** "
          f"[{d['ci'][0]:+.3f}, {d['ci'][1]:+.3f}]. Threshold 0.15.", ""]
    L += ["## Verdicts", ""]
    for k, v in payload["verdicts"].items():
        L.append(f"- `{k}`: **{v}**")
    L += ["", f"Gate is **{'open' if payload['gate_open'] else 'closed'}**.", "",
          "Ticket is a length-3 chain with one eligible pair and is reported as the smaller case: "
          f"G1a {payload['ticket_side_note']['G1a_not_local']}, "
          f"G1b {payload['ticket_side_note']['G1b_global']}, "
          f"G2 {payload['ticket_side_note']['G2_decision_value']}.", ""]
    return "\n".join(L)


if __name__ == "__main__":
    sys.exit(main())
