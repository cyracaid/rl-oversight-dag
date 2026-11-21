#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Standard-library belief v2: equivalence measured against a noise floor, with enough graphs, and latency on deep graphs.

v1 (`compare_belief_stdlib.py`, unchanged; runs/belief-stdlib-v1) failed its equivalence gate because 200 graphs cannot resolve a
+-0.10 margin when the paired sd is 0.79, and its latency graphs were only four layers deep. v2 changes:
  * about 1,000 new graphs (seeds 5000-5999; the reserved confirmation seeds 2000-2199 are not used);
  * each graph is also run with the numpy original under a different particle seed, giving the noise floor of the policy itself;
  * latency on graphs of 4, 10 and 20 layers.

  python3 -u experiments/compare_belief_stdlib_v2.py --out-dir runs/belief-stdlib-v2

Agents run only `--smoke` and unit tests; the user runs the full run. Protocol: `BELIEF_STDLIB_V2_PREREG.md`.
"""
import argparse
import hashlib
import json
import platform
import random
import statistics
import subprocess
import time
from pathlib import Path

import belief_stdlib as stdlib_belief
import compare_belief_stdlib as V1
import spike_active_selection as SP

HERE = Path(__file__).resolve().parent
NUMPY, STDLIB = V1.IMPLEMENTATIONS["numpy"], V1.IMPLEMENTATIONS["stdlib"]
EQUIVALENCE_MARGIN = 0.10
EXTRA_DIFFERING_SHARE = 0.05       # the port may change the outcome of at most 5 points more graphs than a reseed does
LATENCY_GATES = (                  # (nodes, layers, quantity, limit in seconds), stdlib implementation
    (80, 10, "rank_all_s", 0.5), (500, 20, "rank_all_s", 5.0), (500, 20, "observe_s", 0.5),
)
LAYERS = (4, 10, 20)       # the generator needs the layer count to divide the node count


def run_graph(seed, cls, particles, budget, belief_seed):
    """Adaptive belief greedy on one graph with an explicit particle seed. Returns residual sink errors and degenerate count."""
    env = V1.make_env(seed)
    belief = V1.make_belief(env, cls, belief_seed, particles)
    base = list(env["base"])
    err = SP.compute_err(base, env["nodes"], env["topo"], env["coins"])
    available = [True] * len(base)
    for _ in range(budget):
        a = belief.best_action(available)
        available[a] = False
        flagged = bool(err[a] and env["catch_uniforms"][a] < SP.CFG["p_catch"])
        if flagged:
            base[a] = False
            err = SP.compute_err(base, env["nodes"], env["topo"], env["coins"])
        belief.observe(a, flagged)
    return sum(bool(err[s]) for s in env["sinks"]), belief.n_degenerate


def differing_share(a, b):
    return sum(x != y for x, y in zip(a, b)) / len(a)


def equivalence(seeds, particles, budget, draws):
    runs = {"numpy": [], "numpy_reseed": [], "stdlib": []}
    degenerate = {name: 0 for name in runs}
    for s in seeds:
        for name, cls, belief_seed in (("numpy", NUMPY, 10000 + s), ("numpy_reseed", NUMPY, 20000 + s),
                                       ("stdlib", STDLIB, 10000 + s)):
            errors, degen = run_graph(s, cls, particles, budget, belief_seed)
            runs[name].append(errors)
            degenerate[name] += degen
    impl = [b - a for a, b in zip(runs["numpy"], runs["stdlib"])]
    noise = [b - a for a, b in zip(runs["numpy"], runs["numpy_reseed"])]
    return dict(
        graphs=len(seeds), particles=particles, budget=budget,
        mean_errors={name: sum(v) / len(v) for name, v in runs.items()},
        implementation_difference=dict(V1.bootstrap_ci(impl, draws), sd=statistics.pstdev(impl),
                                       differing_share=differing_share(runs["numpy"], runs["stdlib"])),
        noise_floor=dict(V1.bootstrap_ci(noise, draws, seed=20261122), sd=statistics.pstdev(noise),
                         differing_share=differing_share(runs["numpy"], runs["numpy_reseed"])),
        degenerate=degenerate, per_graph=runs)


def bench_graph(n, layers, seed=1):
    old_n, old_l = SP.CFG["N"], SP.CFG["L"]
    SP.CFG["N"], SP.CFG["L"] = n, layers
    try:
        nodes, topo, coins, sinks, _ = SP.build_graph(random.Random(seed))
    finally:
        SP.CFG["N"], SP.CFG["L"] = old_n, old_l
    parents = [nd["parents"] for nd in nodes]
    edge_prob = {(p, i): SP.CFG["p_prop"] for i, ps in enumerate(parents) for p in ps}
    return parents, topo, sinks, edge_prob


def mean_descendants(belief):
    return sum(len(d) for d in belief.desc) / len(belief.desc)


def bench(sizes, layers, particles, repeats):
    out = {}
    for n in sizes:
        for depth in layers:
            parents, topo, sinks, edge_prob = bench_graph(n, depth)
            row = {}
            for name, cls in V1.IMPLEMENTATIONS.items():
                build, rank, observe = [], [], []
                for r in range(repeats):
                    t0 = time.perf_counter()
                    belief = cls(parents, topo, sinks, edge_prob, [0.1] * n, SP.CFG["p_catch"], particles, r)
                    build.append(time.perf_counter() - t0)
                    t0 = time.perf_counter()
                    gains = [belief.gain(i) for i in range(n)]
                    rank.append(time.perf_counter() - t0)
                    target = max(range(n), key=lambda i: gains[i])
                    t0 = time.perf_counter()
                    belief.observe(target, True)
                    observe.append(time.perf_counter() - t0)
                row[name] = dict(build_s=statistics.median(build), rank_all_s=statistics.median(rank),
                                 observe_s=statistics.median(observe), mean_descendants=mean_descendants(belief))
            out[f"{n}x{depth}"] = row
    return out


def evaluate_gate(report, margin=EQUIVALENCE_MARGIN, extra=EXTRA_DIFFERING_SHARE, gates=LATENCY_GATES):
    eq = report["equivalence"]
    impl, noise = eq["implementation_difference"], eq["noise_floor"]
    parts = [
        dict(part=f"E1 equivalence: 95% CI of (stdlib - numpy) within +-{margin:.2f}",
             passed=-margin <= impl["low"] and impl["high"] <= margin,
             detail="mean %+.3f, CI [%+.3f, %+.3f]" % (impl["mean"], impl["low"], impl["high"])),
        dict(part=f"E2 noise floor: share of graphs whose outcome differs, port vs original, at most reseed + {extra:.2f}",
             passed=impl["differing_share"] <= noise["differing_share"] + extra,
             detail="port %.3f, reseed %.3f" % (impl["differing_share"], noise["differing_share"])),
    ]
    for n, depth, key, limit in gates:
        row = report["latency"].get(f"{n}x{depth}")
        name = f"L {key} at {n} nodes / {depth} layers within {limit}s"
        if row is None:
            parts.append(dict(part=name, passed=False, detail="not measured"))
        else:
            seconds = row["stdlib"][key]
            parts.append(dict(part=name, passed=seconds <= limit,
                              detail=f"median {seconds:.3f}s (numpy {row['numpy'][key]:.3f}s)"))
    return dict(passed=all(p["passed"] for p in parts), parts=parts)


def provenance(args):
    def git(*a):
        try:
            return subprocess.check_output(["git", *a], cwd=HERE, text=True).strip()
        except Exception:  # noqa: BLE001 - provenance must not stop a run
            return "unavailable"
    files = ["compare_belief_stdlib_v2.py", "compare_belief_stdlib.py", "belief_stdlib.py", "belief.py",
             "spike_active_selection.py"]
    return dict(git_commit=git("rev-parse", "HEAD"), git_status=git("status", "--porcelain"),
                source_sha256={f: hashlib.sha256((HERE / f).read_bytes()).hexdigest() for f in files},
                python=platform.python_version(), simulator=dict(SP.CFG),
                args={k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()})


def render_md(report):
    eq, gate = report["equivalence"], report["gate"]
    impl, noise = eq["implementation_difference"], eq["noise_floor"]
    lines = ["# Standard-library belief v2: equivalence against a noise floor, and latency (synthetic)", "",
             f"## Gate: **{'PASSED' if gate['passed'] else 'NOT PASSED'}**", "", "| part | passed | detail |", "|---|---|---|"]
    lines += [f"| {p['part']} | {'yes' if p['passed'] else 'NO'} | {p['detail']} |" for p in gate["parts"]]
    lines += ["", f"## Equivalence ({eq['graphs']} graphs, {eq['particles']} particles, budget {eq['budget']})", "",
              "| run | mean residual sink errors | degenerate observations |", "|---|---:|---:|"]
    lines += [f"| {name} | {eq['mean_errors'][name]:.3f} | {eq['degenerate'][name]} |" for name in eq["mean_errors"]]
    lines += ["", "| comparison | mean difference | 95% bootstrap CI | paired sd | graphs whose outcome differs |", "|---|---:|---|---:|---:|",
              f"| stdlib - numpy (implementation) | {impl['mean']:+.3f} | [{impl['low']:+.3f}, {impl['high']:+.3f}] | "
              f"{impl['sd']:.3f} | {impl['differing_share']:.3f} |",
              f"| numpy reseed - numpy (noise floor) | {noise['mean']:+.3f} | [{noise['low']:+.3f}, {noise['high']:+.3f}] | "
              f"{noise['sd']:.3f} | {noise['differing_share']:.3f} |", "",
              "## Latency (median seconds; nodes x layers)", "",
              "| graph | mean descendants | implementation | build | rank every node | one observation |", "|---|---:|---|---:|---:|---:|"]
    for key, row in report["latency"].items():
        for name in V1.IMPLEMENTATIONS:
            r = row[name]
            lines.append(f"| {key} | {r['mean_descendants']:.1f} | {name} | {r['build_s']:.3f} | {r['rank_all_s']:.3f} | {r['observe_s']:.3f} |")
    return "\n".join(lines) + "\n"


def parse(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out-dir", type=Path, required=True, help="new directory; refuses to overwrite")
    ap.add_argument("--smoke", action="store_true", help="tiny run for checking the harness only")
    ap.add_argument("--graphs", type=int, default=1000)
    ap.add_argument("--first-seed", type=int, default=5000)
    ap.add_argument("--particles", type=int, default=1024)
    ap.add_argument("--budget", type=int, default=16)
    ap.add_argument("--bootstrap", type=int, default=10000)
    ap.add_argument("--sizes", type=int, nargs="+", default=[80, 200, 500])
    ap.add_argument("--layers", type=int, nargs="+", default=list(LAYERS))
    ap.add_argument("--repeats", type=int, default=5)
    args = ap.parse_args(argv)
    if args.smoke:
        args.graphs, args.particles, args.budget, args.bootstrap = 3, 64, 4, 200
        args.sizes, args.layers, args.repeats = [80], [4, 10], 1
    for name in ("graphs", "particles", "budget", "bootstrap", "repeats"):
        if getattr(args, name) < 1:
            ap.error(f"--{name} must be positive")
    if args.particles % 8 or any(n < 8 for n in args.sizes) or any(layer < 2 for layer in args.layers):
        ap.error("--particles must be a multiple of 8, --sizes at least 8 and --layers at least 2")
    if any(n % layer for n in args.sizes for layer in args.layers):
        ap.error("every --layers value must divide every --sizes value (the generator builds equal layers)")
    if 2000 <= args.first_seed + args.graphs - 1 and args.first_seed <= 2199:
        ap.error("the seed range overlaps the reserved confirmation seeds 2000-2199")
    return args, ap


def run(args):
    seeds = list(range(args.first_seed, args.first_seed + args.graphs))
    report = dict(equivalence=equivalence(seeds, args.particles, args.budget, args.bootstrap),
                  latency=bench(args.sizes, args.layers, args.particles, args.repeats))
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
