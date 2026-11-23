#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare the standard-library belief with the numpy original: policy equivalence and latency (offline, synthetic).

Task 1.1-1.3 of the OpenSpec change `add-belief-review-ranking`: before a belief ranking may enter evidence-dag (whose Python
runtime is standard-library only), show that the port (a) gives the same review outcomes as the original and (b) is fast
enough. Protocol and thresholds: `BELIEF_STDLIB_PREREG.md`. Agents run only `--smoke` and unit tests; the user runs the full run.

  python3 -u experiments/compare_belief_stdlib.py --out-dir runs/belief-stdlib-v1

Equivalence: on the same graphs (graph seeds 1000-1199, the development set) and the same reviewer randomness, run the
adaptive belief-greedy policy with each implementation (budget 16) and compare residual sink errors, paired by graph.
The two implementations draw different particles for the same seed, so they are compared statistically, not bitwise.
Latency: time construction, ranking every node, and one observation for graphs of 80, 200 and 500 nodes (1,024 particles).
"""
import argparse
import hashlib
import json
import math
import platform
import random
import statistics
import subprocess
import time
from pathlib import Path

import belief as numpy_belief
import belief_stdlib as stdlib_belief
import spike_active_selection as SP
from belief import conf_posterior

HERE = Path(__file__).resolve().parent
IMPLEMENTATIONS = {"numpy": numpy_belief.ParticleBelief, "stdlib": stdlib_belief.ParticleBelief}
EQUIVALENCE_MARGIN = 0.10          # 95% bootstrap CI of (stdlib - numpy) mean residual errors must lie inside +-margin
LATENCY_LIMITS_S = {80: 0.5, 500: 5.0}   # median seconds to rank every node, stdlib implementation


# ------------------------------------------------------------------------ equivalence
def make_env(seed):
    rng = random.Random(seed)
    nodes, topo, coins, sinks, _reach = SP.build_graph(rng)
    n = len(nodes)
    base = [rng.random() < SP.P_TYPE[nodes[i]["type"]] for i in range(n)]
    conf = SP.make_conf(nodes, base, rng)
    return dict(nodes=nodes, topo=topo, coins=coins, sinks=sinks, base=base, conf=conf,
                catch_uniforms=SP.episode_uniforms(rng, n))


def make_belief(env, cls, belief_seed, particles):
    nodes = env["nodes"]
    parents = [nd["parents"] for nd in nodes]
    edge_prob = {(p, i): SP.CFG["p_prop"] for i, ps in enumerate(parents) for p in ps}
    prior = [conf_posterior(env["conf"][i], SP.P_TYPE[nd["type"]]) for i, nd in enumerate(nodes)]
    return cls(parents, env["topo"], env["sinks"], edge_prob, prior, SP.CFG["p_catch"], particles, belief_seed)


def run_graph(seed, cls, particles, budget):
    """Adaptive belief greedy on one graph. Returns (residual sink errors, degenerate count, first action, seconds)."""
    env = make_env(seed)
    belief = make_belief(env, cls, 10000 + seed, particles)
    base = list(env["base"])
    err = SP.compute_err(base, env["nodes"], env["topo"], env["coins"])
    available = [True] * len(base)
    first, started = None, time.perf_counter()
    for _ in range(budget):
        a = belief.best_action(available)
        first = a if first is None else first
        available[a] = False
        flagged = bool(err[a] and env["catch_uniforms"][a] < SP.CFG["p_catch"])
        if flagged:
            base[a] = False
            err = SP.compute_err(base, env["nodes"], env["topo"], env["coins"])
        belief.observe(a, flagged)
    return (sum(bool(err[s]) for s in env["sinks"]), belief.n_degenerate, first, time.perf_counter() - started)


def bootstrap_ci(diffs, draws, seed=20261121):
    rng = random.Random(seed)
    n = len(diffs)
    means = sorted(sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(draws))
    return dict(mean=sum(diffs) / n, low=means[int(0.025 * draws)], high=means[min(draws - 1, int(0.975 * draws))])


def equivalence(seeds, particles, budget, draws):
    rows = {name: [run_graph(s, cls, particles, budget) for s in seeds] for name, cls in IMPLEMENTATIONS.items()}
    errors = {name: [r[0] for r in rows[name]] for name in rows}
    diffs = [b - a for a, b in zip(errors["numpy"], errors["stdlib"])]
    return dict(
        graphs=len(seeds), particles=particles, budget=budget,
        mean_errors={name: sum(v) / len(v) for name, v in errors.items()},
        paired_difference_stdlib_minus_numpy=bootstrap_ci(diffs, draws),
        degenerate={name: sum(r[1] for r in rows[name]) for name in rows},
        first_action_agreement=sum(a[2] == b[2] for a, b in zip(rows["numpy"], rows["stdlib"])) / len(seeds),
        seconds_per_graph={name: sum(r[3] for r in rows[name]) / len(seeds) for name in rows},
        per_graph={name: errors[name] for name in errors})


# ----------------------------------------------------------------------------- latency
def bench_graph(n, seed=1):
    old = SP.CFG["N"]
    SP.CFG["N"] = n
    try:
        rng = random.Random(seed)
        nodes, topo, coins, sinks, _ = SP.build_graph(rng)
    finally:
        SP.CFG["N"] = old
    parents = [nd["parents"] for nd in nodes]
    edge_prob = {(p, i): SP.CFG["p_prop"] for i, ps in enumerate(parents) for p in ps}
    return parents, topo, sinks, edge_prob


def bench(sizes, particles, repeats):
    out = {}
    for n in sizes:
        parents, topo, sinks, edge_prob = bench_graph(n)
        prior = [0.1] * n
        row = {}
        for name, cls in IMPLEMENTATIONS.items():
            build, rank, observe = [], [], []
            for r in range(repeats):
                t0 = time.perf_counter()
                belief = cls(parents, topo, sinks, edge_prob, prior, SP.CFG["p_catch"], particles, r)
                build.append(time.perf_counter() - t0)
                t0 = time.perf_counter()
                gains = [belief.gain(i) for i in range(n)]
                rank.append(time.perf_counter() - t0)
                target = max(range(n), key=lambda i: gains[i])
                t0 = time.perf_counter()
                belief.observe(target, True)
                observe.append(time.perf_counter() - t0)
            row[name] = dict(build_s=statistics.median(build), rank_all_s=statistics.median(rank),
                             observe_s=statistics.median(observe))
        out[str(n)] = row
    return out


# ------------------------------------------------------------------------------- gate
def evaluate_gate(report, margin=EQUIVALENCE_MARGIN, limits=None):
    limits = LATENCY_LIMITS_S if limits is None else limits
    ci = report["equivalence"]["paired_difference_stdlib_minus_numpy"]
    parts = [dict(part=f"equivalence: 95% CI of (stdlib - numpy) within +-{margin:.2f}",
                  passed=-margin <= ci["low"] and ci["high"] <= margin,
                  detail="mean %+.3f, CI [%+.3f, %+.3f]" % (ci["mean"], ci["low"], ci["high"]))]
    for n, limit in sorted(limits.items()):
        row = report["latency"].get(str(n))
        if row is None:
            parts.append(dict(part=f"latency: rank every node at N={n} within {limit}s", passed=False, detail="not measured"))
            continue
        seconds = row["stdlib"]["rank_all_s"]
        parts.append(dict(part=f"latency: rank every node at N={n} within {limit}s", passed=seconds <= limit,
                          detail=f"median {seconds:.3f}s (numpy {row['numpy']['rank_all_s']:.3f}s)"))
    return dict(passed=all(p["passed"] for p in parts), parts=parts)


def provenance(args):
    def git(*a):
        try:
            return subprocess.check_output(["git", *a], cwd=HERE, text=True).strip()
        except Exception:  # noqa: BLE001 - provenance must not stop a run
            return "unavailable"
    files = ["compare_belief_stdlib.py", "belief_stdlib.py", "belief.py", "spike_active_selection.py"]
    return dict(git_commit=git("rev-parse", "HEAD"), git_status=git("status", "--porcelain"),
                source_sha256={f: hashlib.sha256((HERE / f).read_bytes()).hexdigest() for f in files},
                python=platform.python_version(), simulator=dict(SP.CFG),
                args={k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()})


def render_md(report):
    eq, gate = report["equivalence"], report["gate"]
    ci = eq["paired_difference_stdlib_minus_numpy"]
    lines = ["# Standard-library belief: equivalence and latency (synthetic)", "",
             f"## Gate: **{'PASSED' if gate['passed'] else 'NOT PASSED'}**", "", "| part | passed | detail |", "|---|---|---|"]
    lines += [f"| {p['part']} | {'yes' if p['passed'] else 'NO'} | {p['detail']} |" for p in gate["parts"]]
    lines += ["", f"## Equivalence ({eq['graphs']} graphs, {eq['particles']} particles, budget {eq['budget']})", "",
              "| implementation | mean residual sink errors | degenerate observations | seconds per graph |", "|---|---:|---:|---:|"]
    for name in IMPLEMENTATIONS:
        lines.append(f"| {name} | {eq['mean_errors'][name]:.3f} | {eq['degenerate'][name]} | {eq['seconds_per_graph'][name]:.2f} |")
    lines += ["", f"Paired difference (stdlib - numpy): mean {ci['mean']:+.3f}, 95% bootstrap CI [{ci['low']:+.3f}, {ci['high']:+.3f}] "
              f"(pairs share the graph and reviewer randomness, not the particles). First chosen action agrees on "
              f"{eq['first_action_agreement']:.2f} of graphs.", "", "## Latency (median seconds)", "",
              "| nodes | implementation | build | rank every node | one observation |", "|---:|---|---:|---:|---:|"]
    for n, row in report["latency"].items():
        for name in IMPLEMENTATIONS:
            r = row[name]
            lines.append(f"| {n} | {name} | {r['build_s']:.3f} | {r['rank_all_s']:.3f} | {r['observe_s']:.3f} |")
    return "\n".join(lines) + "\n"


def parse(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out-dir", type=Path, required=True, help="new directory; refuses to overwrite")
    ap.add_argument("--smoke", action="store_true", help="tiny run for checking the harness only")
    ap.add_argument("--graphs", type=int, default=200)
    ap.add_argument("--first-seed", type=int, default=1000)
    ap.add_argument("--particles", type=int, default=1024)
    ap.add_argument("--budget", type=int, default=16)
    ap.add_argument("--bootstrap", type=int, default=10000)
    ap.add_argument("--sizes", type=int, nargs="+", default=[80, 200, 500])
    ap.add_argument("--repeats", type=int, default=5)
    args = ap.parse_args(argv)
    if args.smoke:
        args.graphs, args.particles, args.budget, args.bootstrap = 3, 64, 4, 200
        args.sizes, args.repeats = [80], 1
    for name in ("graphs", "particles", "budget", "bootstrap", "repeats"):
        if getattr(args, name) < 1:
            ap.error(f"--{name} must be positive")
    if args.particles % 8 or any(n < 8 for n in args.sizes):
        ap.error("--particles must be a multiple of 8 and --sizes at least 8")
    return args, ap


def run(args):
    seeds = list(range(args.first_seed, args.first_seed + args.graphs))
    report = dict(equivalence=equivalence(seeds, args.particles, args.budget, args.bootstrap),
                  latency=bench(args.sizes, args.particles, args.repeats))
    report["gate"] = evaluate_gate(report)
    report["provenance"] = provenance(args)
    return report


def main(argv=None):
    args, ap = parse(argv)
    try:
        args.out_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        ap.error(f"{args.out_dir} exists; use a new directory (no overwrite)")
    report = run(args)
    (args.out_dir / "results.json").write_text(json.dumps(report, indent=1, allow_nan=False) + "\n")
    (args.out_dir / "results.md").write_text(render_md(report))
    print(f"Saved {args.out_dir / 'results.json'} and results.md")


if __name__ == "__main__":
    main()
