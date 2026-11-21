#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parameter-recovery experiment: can edge propagation be estimated from correction logs?

Precondition for using a propagation estimator on real audit-chain records
(openspec change add-belief-review-ranking, task 1.4). Everything here is synthetic.

Idea. Generate graphs whose edge families have KNOWN propagation probabilities, run a
review policy, write the correction log an audit chain would hold, apply estimators, and
check whether the known values are recovered, including when the review policy is not
random (confidence-ordered, blast-radius-ordered).

What the log contains (observable in a real chain, no hidden truth):
  * for each review: the node, whether the reviewer flagged an error, and whether the
    flagged error was CLEARED (the node is no longer wrong after re-derivation) -- a
    cleared error was the node's own source error; a flagged-but-not-cleared error was
    inherited from a parent;
  * for each cleared correction: for each child, whether the child changed (was wrong
    before the re-derivation and not after), the child's in-degree, its edge family, and
    whether the child had itself been reviewed before.

Estimators (per edge family):
  E0 naive         changed / children of corrected nodes. Expected to under-estimate
                   (a child can be wrong for other reasons, or be reviewed already).
  E1 in-degree-1   restrict to single-parent children and divide by (1 - b_hat), where
                   b_hat is the children's own source-error rate estimated from reviewed
                   root nodes. Removes the other-parent cause, but not selection effects.
  E2 E1 + children not reviewed before the correction. Removes the effect of children
                   whose own source error the policy already cleared.

Idealisations (state them wherever results are quoted): every child is re-derived after a
correction and a true change is observed (set --obs-miss > 0 to miss some); the assumed
reviewer catch rate is known (set --assumed-catch to a wrong value to probe); family is
the child's layer; types are uniform over K.

Run (the user runs full runs; agents run only --smoke and unit tests):
  python3 experiments/rl_propagation_recovery.py --out-dir runs/propagation-recovery-v1
"""
import argparse
import hashlib
import json
import math
import platform
import random
import subprocess
from pathlib import Path

import spike_active_selection as SP
from belief import conf_posterior

HERE = Path(__file__).resolve().parent
POLICIES = ("random", "confidence", "blast")
ESTIMATORS = ("E0", "E1", "E2")
DEFAULT_P = {1: 0.3, 2: 0.6, 3: 0.85}  # propagation probability by child layer (family)


# --------------------------------------------------------------------------- world
def build_world_graph(rng, p_by_layer, N=80, K=5, L=4):
    """Same layered structure as spike_active_selection.build_graph, but the edge
    propagation probability depends on the child's layer (the edge family)."""
    per = max(1, N // L)
    nodes = []
    for layer in range(L):
        for _ in range(per):
            nodes.append({"layer": layer, "type": rng.randrange(K), "parents": []})
    nodes = nodes[:N]
    by_layer = {}
    for i, nd in enumerate(nodes):
        by_layer.setdefault(nd["layer"], []).append(i)
    for i, nd in enumerate(nodes):
        if nd["layer"] == 0:
            continue
        cands = by_layer[nd["layer"] - 1]
        nd["parents"] = rng.sample(cands, min(rng.choice([1, 2]), len(cands)))
    topo = sorted(range(len(nodes)), key=lambda i: nodes[i]["layer"])
    coins = {}
    for i, nd in enumerate(nodes):
        for p in nd["parents"]:
            coins[(p, i)] = rng.random() < p_by_layer[nd["layer"]]
    children = {i: [] for i in range(len(nodes))}
    for i, nd in enumerate(nodes):
        for p in nd["parents"]:
            children[p].append(i)
    sinks = {i for i, nd in enumerate(nodes) if nd["layer"] == L - 1}
    reach = [set() for _ in nodes]
    for i in reversed(topo):
        s = {i}
        for c in children[i]:
            s |= reach[c]
        reach[i] = s
    sink_reach = [sum(1 for j in reach[i] if j in sinks) for i in range(len(nodes))]
    return nodes, topo, coins, children, sink_reach


def build_world(seed, graphs, p_by_layer, N=80):
    """List of independent graphs with hidden base errors and observed confidences."""
    world = []
    for g in range(graphs):
        rng = random.Random(seed * 1_000_003 + g)
        nodes, topo, coins, children, sink_reach = build_world_graph(rng, p_by_layer, N=N)
        base = [rng.random() < SP.P_TYPE[nd["type"]] for nd in nodes]
        conf = SP.make_conf(nodes, base, rng)
        post = [conf_posterior(conf[i], SP.P_TYPE[nd["type"]]) for i, nd in enumerate(nodes)]
        world.append(dict(nodes=nodes, topo=topo, coins=coins, children=children,
                          sink_reach=sink_reach, base=base, post=post))
    return world


def policy_order(name, graph, budget, rng):
    n = len(graph["nodes"])
    ids = list(range(n))
    if name == "random":
        return rng.sample(ids, min(budget, n))
    if name == "confidence":
        return sorted(ids, key=lambda i: -graph["post"][i])[:budget]
    if name == "blast":
        return sorted(ids, key=lambda i: (-graph["sink_reach"][i], -graph["post"][i]))[:budget]
    raise ValueError(f"unknown policy {name}")


# ----------------------------------------------------------------------------- log
def run_log(graph, order, rng, obs_miss=0.0):
    """Review nodes in `order` on a copy of the graph state; return the correction log.

    Returns dict(events=[...], root_reviews=int, root_flags=int, inherited=int, cleared=int).
    The hidden `base` is read only by the simulator; the log holds observables only.
    """
    nodes, topo, coins = graph["nodes"], graph["topo"], graph["coins"]
    base = list(graph["base"])  # never mutate the world
    err = SP.compute_err(base, nodes, topo, coins)
    reviewed = set()
    events, root_reviews, root_flags, inherited, cleared_n = [], 0, 0, 0, 0
    for a in order:
        before = list(err)
        flagged, err = SP.review_step(a, base, err, nodes, topo, coins, rng)
        if nodes[a]["layer"] == 0:
            root_reviews += 1
            root_flags += int(flagged)
        if flagged:
            cleared = not err[a]
            if cleared:
                cleared_n += 1
                for c in graph["children"][a]:
                    changed = before[c] and not err[c]
                    if changed and obs_miss > 0 and rng.random() < obs_miss:
                        changed = False
                    events.append(dict(family=nodes[c]["layer"],
                                       indeg=len(nodes[c]["parents"]),
                                       changed=bool(changed),
                                       reviewed_before=c in reviewed))
            else:
                inherited += 1  # flagged, but still wrong after re-derivation
        reviewed.add(a)
    return dict(events=events, root_reviews=root_reviews, root_flags=root_flags,
                inherited=inherited, cleared=cleared_n)


def merge_logs(logs):
    out = dict(events=[], root_reviews=0, root_flags=0, inherited=0, cleared=0)
    for log in logs:
        out["events"].extend(log["events"])
        for key in ("root_reviews", "root_flags", "inherited", "cleared"):
            out[key] += log[key]
    return out


# ---------------------------------------------------------------------- estimators
def _beta(rng, k, n):
    return rng.betavariate(1 + k, 1 + n - k)  # uniform Beta(1,1) prior


def estimate_family(events, family, estimator, root_reviews, root_flags,
                    assumed_catch, draws, seed):
    """Posterior summary for one family. Returns dict(n, k, mean, low, high) or None."""
    if estimator == "E0":
        sel = [e for e in events if e["family"] == family]
    elif estimator == "E1":
        sel = [e for e in events if e["family"] == family and e["indeg"] == 1]
    elif estimator == "E2":
        sel = [e for e in events if e["family"] == family and e["indeg"] == 1
               and not e["reviewed_before"]]
    else:
        raise ValueError(estimator)
    n = len(sel)
    if n == 0:
        return None
    k = sum(e["changed"] for e in sel)
    rng = random.Random(seed)
    samples = []
    for _ in range(draws):
        q = _beta(rng, k, n)
        if estimator == "E0":
            samples.append(q)
            continue
        flag_rate = _beta(rng, root_flags, root_reviews) if root_reviews else 0.0
        b = min(flag_rate / assumed_catch, 0.95)
        samples.append(min(q / (1.0 - b), 1.0))
    samples.sort()
    return dict(n=n, k=k, mean=sum(samples) / draws,
                low=samples[int(0.025 * draws)], high=samples[min(draws - 1, int(0.975 * draws))])


# ------------------------------------------------------------------------ experiment
def one_replicate(rep, args, p_by_layer):
    world = build_world(args.seed + rep, args.graphs, p_by_layer, N=args.nodes)
    out = {}
    for policy in POLICIES:
        logs = []
        for g, graph in enumerate(world):
            rng = random.Random((args.seed + rep) * 7_919 + g * 31 + POLICIES.index(policy))
            order = policy_order(policy, graph, args.budget, rng)
            logs.append(run_log(graph, order, rng, args.obs_miss))
        merged = merge_logs(logs)
        res = {}
        for est in ESTIMATORS:
            for fam in sorted(p_by_layer):
                res[f"{est}|{fam}"] = estimate_family(
                    merged["events"], fam, est, merged["root_reviews"], merged["root_flags"],
                    args.assumed_catch, args.draws, seed=rep * 101 + fam)
        out[policy] = dict(estimates=res, events=len(merged["events"]),
                           cleared=merged["cleared"], inherited=merged["inherited"],
                           root_reviews=merged["root_reviews"], root_flags=merged["root_flags"])
    return out


def summarise(replicates, p_by_layer):
    """Bias, RMSE, interval coverage and missing-estimate counts per policy/estimator/family."""
    table = {}
    for policy in POLICIES:
        for est in ESTIMATORS:
            for fam, truth in sorted(p_by_layer.items()):
                got = [r[policy]["estimates"][f"{est}|{fam}"] for r in replicates]
                have = [g for g in got if g is not None]
                row = dict(truth=truth, replicates=len(got), missing=len(got) - len(have))
                if have:
                    errs = [g["mean"] - truth for g in have]
                    row.update(
                        mean_estimate=sum(g["mean"] for g in have) / len(have),
                        bias=sum(errs) / len(errs),
                        rmse=math.sqrt(sum(e * e for e in errs) / len(errs)),
                        coverage=sum(g["low"] <= truth <= g["high"] for g in have) / len(have),
                        mean_width=sum(g["high"] - g["low"] for g in have) / len(have),
                        mean_n=sum(g["n"] for g in have) / len(have))
                table[f"{policy}|{est}|{fam}"] = row
    return table


def provenance(args):
    def git(*a):
        try:
            return subprocess.check_output(["git", *a], cwd=HERE, text=True).strip()
        except Exception:  # noqa: BLE001 - provenance must not stop a run
            return "unavailable"
    files = ["rl_propagation_recovery.py", "spike_active_selection.py", "belief.py"]
    return dict(
        git_commit=git("rev-parse", "HEAD"), git_status=git("status", "--porcelain"),
        source_sha256={f: hashlib.sha256((HERE / f).read_bytes()).hexdigest() for f in files},
        python=platform.python_version(), simulator=dict(SP.CFG), type_rates=SP.P_TYPE,
        args={k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()})


def render_md(payload):
    cfg = payload["config"]
    lines = ["# Propagation recovery results (synthetic)", "",
             f"Replicates {cfg['replicates']}, graphs/replicate {cfg['graphs']}, budget {cfg['budget']}, "
             f"assumed catch {cfg['assumed_catch']}, observation miss {cfg['obs_miss']}.",
             "Truth by family (child layer): " + json.dumps(cfg["p_true"]) + ".",
             "Coverage = share of replicates whose 95% interval contains the truth. "
             "Missing = replicates with no usable event. Failures are kept.", ""]
    for policy in POLICIES:
        lines += [f"## Policy: {policy}", "",
                  "| estimator | family | truth | mean estimate | bias | RMSE | coverage | mean width | mean n | missing |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for est in ESTIMATORS:
            for fam in sorted(cfg["p_true"], key=int):
                r = payload["summary"][f"{policy}|{est}|{fam}"]
                if "bias" not in r:
                    lines.append(f"| {est} | {fam} | {r['truth']} | - | - | - | - | - | - | {r['missing']} |")
                else:
                    lines.append(f"| {est} | {fam} | {r['truth']} | {r['mean_estimate']:.3f} | {r['bias']:+.3f} | "
                                 f"{r['rmse']:.3f} | {r['coverage']:.2f} | {r['mean_width']:.3f} | "
                                 f"{r['mean_n']:.0f} | {r['missing']} |")
        lines.append("")
    lines.append("Events per policy (mean over replicates): " + json.dumps(payload["event_counts"]))
    return "\n".join(lines) + "\n"


def run(args):
    p_by_layer = {int(k): v for k, v in args.p_true.items()}
    replicates = [one_replicate(rep, args, p_by_layer) for rep in range(args.replicates)]
    counts = {pol: {key: sum(r[pol][key] for r in replicates) / len(replicates)
                    for key in ("events", "cleared", "inherited", "root_reviews", "root_flags")}
              for pol in POLICIES}
    return dict(config=dict(replicates=args.replicates, graphs=args.graphs, budget=args.budget,
                            assumed_catch=args.assumed_catch, obs_miss=args.obs_miss,
                            p_true={str(k): v for k, v in p_by_layer.items()}),
                provenance=provenance(args), summary=summarise(replicates, p_by_layer),
                event_counts=counts, replicates=replicates)


def parse(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out-dir", type=Path, required=True, help="new directory; refuses to overwrite")
    ap.add_argument("--smoke", action="store_true", help="tiny run for checking the harness only")
    ap.add_argument("--replicates", type=int, default=50)
    ap.add_argument("--graphs", type=int, default=200, help="graphs per replicate")
    ap.add_argument("--nodes", type=int, default=80)
    ap.add_argument("--budget", type=int, default=16, help="reviews per graph")
    ap.add_argument("--seed", type=int, default=20261121)
    ap.add_argument("--assumed-catch", type=float, default=0.9)
    ap.add_argument("--true-catch", type=float, default=0.9)
    ap.add_argument("--obs-miss", type=float, default=0.0)
    ap.add_argument("--draws", type=int, default=2000)
    args = ap.parse_args(argv)
    if args.smoke:
        args.replicates, args.graphs, args.draws = 2, 20, 200
    for name in ("replicates", "graphs", "nodes", "budget", "draws"):
        if getattr(args, name) < 1:
            ap.error(f"--{name.replace('_', '-')} must be positive")
    for name in ("assumed_catch", "true_catch"):
        if not 0.0 < getattr(args, name) <= 1.0:
            ap.error(f"--{name.replace('_', '-')} must be in (0, 1]")
    if not 0.0 <= args.obs_miss < 1.0:
        ap.error("--obs-miss must be in [0, 1)")
    args.p_true = {str(k): v for k, v in DEFAULT_P.items()}
    return args, ap


def main(argv=None):
    args, ap = parse(argv)
    try:
        args.out_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        ap.error(f"{args.out_dir} exists; use a new directory (no overwrite)")
    SP.CFG["p_catch"] = args.true_catch
    payload = run(args)
    (args.out_dir / "results.json").write_text(json.dumps(payload, indent=1, allow_nan=False) + "\n")
    (args.out_dir / "results.md").write_text(render_md(payload))
    print(f"Saved {args.out_dir / 'results.json'} and results.md")


if __name__ == "__main__":
    main()
