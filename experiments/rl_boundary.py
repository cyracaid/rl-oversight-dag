#!/usr/bin/env python3
"""Reproducible boundary controls; no training or evaluation runs on import."""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import platform
import random
import subprocess
import time

import numpy as np
import torch

import rl_gnn_multiseed as M
import spike_active_selection as SP
from belief import ParticleBelief, conf_posterior
from rl_cmdp_gnn import GNNPolicy


# Environment stays fixed except in the explicitly named catch-shift conditions.
SCENARIOS = {
    "matched": {},
    "prop_odds_x0.5": {"prop_odds": .5},
    "prop_odds_x2": {"prop_odds": 2.},
    "conf_logit_minus0.5": {"conf_offset": -.5},
    "conf_logit_plus0.5": {"conf_offset": .5},
    "catch0.7_known": {"true_catch": .7, "model_catch": .7},
    "catch0.7_unknown": {"true_catch": .7, "model_catch": .9},
}


def odds_scale(p, factor):
    if not 0 <= p <= 1 or factor <= 0:
        raise ValueError("probability must be in [0,1]; odds factor must be positive")
    return factor * p / (1 - p + factor * p)


def paired_bootstrap(values, reference, draws=10000, seed=20261112):
    """Crossed bootstrap: independently resample training seeds and graph IDs.

    Resampling uses the same graph indices for candidate and reference. A single
    candidate row (planner) has graph uncertainty only. No seed×graph flattening.
    """
    x, y = np.asarray(values, dtype=float), np.asarray(reference, dtype=float)
    if x.ndim != 2 or y.ndim != 1 or x.shape[1] != len(y) or not x.size:
        raise ValueError("expected nonempty seed×graph matrix and graph reference")
    if not np.isfinite(x).all() or not np.isfinite(y).all() or draws < 1:
        raise ValueError("finite values and positive bootstrap draws required")
    rng = np.random.default_rng(seed)
    delta = x - y[None, :]
    samples = np.empty(draws)
    for i in range(draws):
        rows = rng.integers(0, x.shape[0], x.shape[0])
        cols = rng.integers(0, x.shape[1], x.shape[1])
        samples[i] = delta[np.ix_(rows, cols)].mean()
    lo, hi = np.quantile(samples, [.025, .975])
    return {"mean": float(delta.mean()), "low": float(lo), "high": float(hi)}


def provenance():
    root = Path(__file__).resolve().parent
    sources = sorted(root.glob("*.py"))
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=root, text=True).strip()
    return {
        "git_commit": git("rev-parse", "HEAD"),
        "git_status": git("status", "--porcelain"),
        "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        "python": platform.python_version(), "torch": str(torch.__version__),
        "numpy": np.__version__, "simulator": dict(SP.CFG), "type_rates": SP.P_TYPE,
    }


def write_report(path, payload):
    """JSON is authoritative; Markdown is rendered by reading that saved JSON."""
    path = Path(path)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")
    render_report(path)


def render_report(path):
    path = Path(path)
    data = json.loads(path.read_text())
    lines = ["# Boundary experiment", "", "Generated from `" + path.name + "`.",
             "Negative difference = fewer sink errors than belief greedy.", "",
             "| condition | policy | sink errors | paired Δ | bootstrap 95% CI |",
             "|---|---|---:|---:|---|" ]
    for condition, rows in data["conditions"].items():
        ref = rows["belief greedy"]
        for name, values in rows.items():
            matrix = values if isinstance(values[0], list) else [values]
            ci = paired_bootstrap(matrix, ref, data["config"]["bootstrap"])
            lines.append(f"| {condition} | {name} | {np.mean(matrix):.3f} | "
                         f"{ci['mean']:+.3f} | [{ci['low']:+.3f}, {ci['high']:+.3f}] |")
    lines += ["", "## Additional paired controls", "",
              "| condition | contrast | paired Δ | bootstrap 95% CI |",
              "|---|---|---:|---|"]
    for condition, rows in data["conditions"].items():
        for name, values in rows.items():
            reference = None
            if name in ("BC+FT", "BC+KL-FT") and "BC" in rows:
                reference = "BC"
            elif isinstance(values[0], list) and "2-step greedy" in rows:
                reference = "2-step greedy"
            if reference is None:
                continue
            delta = np.asarray(values) - np.asarray(rows[reference])
            ci = paired_bootstrap(delta, np.zeros(delta.shape[1]), data["config"]["bootstrap"])
            lines.append(f"| {condition} | {name} − {reference} | {ci['mean']:+.3f} | "
                         f"[{ci['low']:+.3f}, {ci['high']:+.3f}] |")
    if "completed_seeds" in data:
        lines += ["", f"Completed seeds: {data['completed_seeds']}; requested: {data['config']['seeds']}.",
                  "Partial runs and smoke runs are not confirmatory evidence."]
    path.with_suffix(".md").write_text("\n".join(lines) + "\n")


def make_env(seed, scenario):
    rng = random.Random(seed)
    env = M.build_env(rng, 10000 + seed, with_belief=False)
    # Pre-draw node-indexed reviewer randomness, independently of chosen actions.
    env["catch_uniforms"] = SP.episode_uniforms(rng, M.N)
    env["true_catch"] = scenario.get("true_catch", .9)
    parents = [n["parents"] for n in env["nodes"]]
    p = odds_scale(SP.CFG["p_prop"], scenario.get("prop_odds", 1.))
    edges = {(j, i): p for i, ps in enumerate(parents) for j in ps}
    prior = []
    for c, node in zip(env["conf"], env["nodes"]):
        logit = math.log(c / (1 - c)) + scenario.get("conf_offset", 0.)
        assumed_conf = 1 / (1 + math.exp(-logit))
        prior.append(conf_posterior(assumed_conf, SP.P_TYPE[node["type"]]))
    env["belief"] = ParticleBelief(parents, env["topo"], env["sinks"], edges, prior,
                                   scenario.get("model_catch", .9),
                                   SP.CFG["n_particles"], 10000 + seed)
    return env, rng


def two_step_action(belief, available, remaining):
    """Adaptive depth-2 receding-horizon control over ALL available actions.

    Integrates both observations, then maximizes second-step gain separately.
    Posterior branches use the existing particle resampler; this is approximate
    particle lookahead, not an exact POMDP solver. Parent RNG/state never change.
    """
    if remaining <= 1:
        return belief.best_action(available)
    best, best_value = None, -float("inf")
    for a, allowed in enumerate(available):
        if not allowed:
            continue
        next_available = list(available)
        next_available[a] = False
        value = belief.gain(a)
        if any(next_available):
            p_flag = belief.p_catch * belief.err[a].bit_count() / belief.M
            for flag, prob in ((False, 1 - p_flag), (True, p_flag)):
                if prob <= 0:
                    continue
                branch = copy.deepcopy(belief)
                branch.observe(a, flag)
                value += prob * max(branch.gain(b) for b, ok in enumerate(next_available) if ok)
        if value > best_value:
            best, best_value = a, value
    return best


def evaluate(seed, scenario, name, policy=None, variant=None):
    env, _ = make_env(seed, scenario)
    base = list(env["base"])
    err = SP.compute_err(base, env["nodes"], env["topo"], env["coins"])
    reviewed, flagged = [False] * M.N, [False] * M.N
    for t in range(M.R):
        available = [not r for r in reviewed]
        if policy is not None:
            scores = policy.score(M.features(env, variant, reviewed, flagged, M.R - t), env["A"])
            a = int(scores.masked_fill(torch.tensor(reviewed), -float("inf")).argmax())
        elif name == "belief greedy":
            a = env["belief"].best_action(available)
        elif name == "2-step greedy":
            a = two_step_action(env["belief"], available, M.R - t)
        elif name == "conf threshold":
            a = min((i for i in range(M.N) if available[i]), key=lambda i: env["conf"][i])
        else:
            raise ValueError(name)
        flag = bool(err[a] and env["catch_uniforms"][a] < env["true_catch"])
        if flag:
            base[a] = False
            err = SP.compute_err(base, env["nodes"], env["topo"], env["coins"])
        reviewed[a], flagged[a] = True, flag
        env["belief"].observe(a, flag)
    return sum(bool(err[s]) for s in env["sinks"]), env["belief"].n_degenerate


def save_policy(path, policy, variant, seed, kind, training_config=None):
    torch.save({"state_dict": policy.state_dict(), "variant": variant, "seed": seed,
                "kind": kind, "crn": SP.CFG["crn"], "training_config": training_config,
                "provenance": provenance()}, path)


def load_policy(path):
    ckpt = torch.load(path, map_location="cpu", weights_only=True)
    if not ckpt["crn"]:
        raise ValueError(f"{path}: checkpoint was trained without node-paired CRN")
    model = GNNPolicy(d=M.DIM[ckpt["variant"]])
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    return model, ckpt


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    train = sub.add_parser("train")
    train.add_argument("--variant", choices=list(M.DIM), required=True)
    train.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3, 4, 5])
    train.add_argument("--episodes", type=int, default=20000)
    train.add_argument("--out-dir", type=Path, required=True)
    ev = sub.add_parser("eval")
    ev.add_argument("--checkpoints", nargs="*", type=Path, default=[])
    ev.add_argument("--scenarios", nargs="+", choices=list(SCENARIOS), default=list(SCENARIOS))
    ev.add_argument("--two-step", action="store_true")
    ev.add_argument("--heldout", type=int, default=200)
    ev.add_argument("--start", type=int, default=1000)
    ev.add_argument("--bootstrap", type=int, default=10000)
    ev.add_argument("--out-dir", type=Path, required=True)
    report = sub.add_parser("report")
    report.add_argument("path", type=Path)
    args = ap.parse_args()
    if args.command == "report":
        render_report(args.path)
        return
    if args.command == "eval" and (args.heldout < 1 or args.bootstrap < 1):
        ap.error("heldout and bootstrap must be positive")
    if args.command == "train" and (args.episodes < 1 or len(set(args.seeds)) != len(args.seeds)):
        ap.error("positive episodes and unique seeds required")
    torch.set_num_threads(1)
    SP.CFG["crn"] = True
    args.out_dir.mkdir(parents=True, exist_ok=False)
    config = {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()}
    if "checkpoints" in config:
        config["checkpoints"] = [str(p) for p in args.checkpoints]
    if args.command == "train":
        (args.out_dir / "manifest.json").write_text(json.dumps({"config": config, "provenance": provenance()}, indent=2))
        for seed in args.seeds:
            policy, curve = M.train(args.variant, seed, args.episodes)
            save_policy(args.out_dir / f"{args.variant}_{seed}.pt", policy, args.variant, seed,
                        "reinforce", config)
            (args.out_dir / f"curve_{seed}.json").write_text(json.dumps(curve))
            print(f"saved {args.variant} seed={seed}", flush=True)
        (args.out_dir / "manifest.json").write_text(json.dumps({"config": config, "provenance": provenance()}, indent=2))
        return
    groups, checkpoint_meta = {}, {}
    for path in args.checkpoints:
        policy, meta = load_policy(path)
        label = meta["kind"] + "/" + meta["variant"]
        if any(m["seed"] == meta["seed"] for _, m in groups.get(label, [])):
            raise ValueError(f"duplicate training seed in {label}")
        groups.setdefault(label, []).append((policy, meta))
        checkpoint_meta[str(path)] = {"seed": meta["seed"], "label": label,
                                      "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                      "training_config": meta["training_config"],
                                      "training_provenance": meta["provenance"]}
    payload = {"config": config, "provenance": provenance(), "checkpoints": checkpoint_meta,
               "graph_seeds": list(range(args.start, args.start + args.heldout)),
               "conditions": {}, "degeneracies": {}, "seconds": {}}
    for condition in args.scenarios:
        rows, degeneracies = {}, {}
        start = time.monotonic()
        names = ["conf threshold", "belief greedy"] + (["2-step greedy"] if args.two_step else [])
        with torch.no_grad():
            for name in names:
                results = [evaluate(s, SCENARIOS[condition], name) for s in payload["graph_seeds"]]
                rows[name] = [r[0] for r in results]
                degeneracies[name] = [r[1] for r in results]
                print(f"{condition}: {name}={np.mean(rows[name]):.3f}", flush=True)
            for name, models in groups.items():
                rows[name], degeneracies[name] = [], []
                for policy, meta in models:
                    results = [evaluate(s, SCENARIOS[condition], name, policy, meta["variant"])
                               for s in payload["graph_seeds"]]
                    rows[name].append([r[0] for r in results])
                    degeneracies[name].append([r[1] for r in results])
                    print(f"{condition}: {name} seed={meta['seed']} done", flush=True)
        payload["conditions"][condition] = rows
        payload["degeneracies"][condition] = degeneracies
        payload["seconds"][condition] = time.monotonic() - start
        write_report(args.out_dir / "results.json", payload)


if __name__ == "__main__":
    main()
