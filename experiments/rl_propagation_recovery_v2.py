#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Propagation recovery v2: a base-error-rate source that does not depend on selection.

v1 (`rl_propagation_recovery.py`, unchanged; results in runs/propagation-recovery-v1) failed its gate under
confidence-ordered review because the children's own source-error rate b was estimated from reviewed root
nodes, which that policy selects for being wrong (b_hat 0.483 vs true 0.104). v2 keeps the same worlds,
policies and propagation estimator and changes only where b comes from, and adds a test of the proposed
`calibrated` rule.

Review budget per graph = policy reviews + a random AUDIT share (`--audit-fraction`). Audit nodes are drawn
uniformly from the nodes the policy did not pick, independent of confidence or graph position.

Base-error-rate sources:
  reviewed_roots  all reviewed root nodes (the v1 source; expected to fail under confidence order)
  audit_roots     root nodes reviewed in the random audit only (selection-independent, data-driven)
  prior           an external prior by node type, passed as one number (--prior-b); ablation that isolates
                  the b-estimation error from the structural adjustment

Estimators (all: single-parent children, not reviewed before the correction, divided by 1 - b):
  E0   naive change rate (lower bound reference, no adjustment, all children)
  E2   b from reviewed_roots (v1 reference)
  E3a  b from prior
  E3b  b from audit_roots   <- the estimator under the gate

Calibrated-label rules evaluated per replicate (see PROPAGATION_RECOVERY_V2_PREREG.md):
  width   calibrated iff 95% interval width < --width-threshold
  robust  width AND a selection check: for E2 the flag rate of the b source must not exceed the prior
          by more than --check-ratio; for E3b the audit must have at least --min-audit-roots roots

Run (the user runs full runs; agents run only --smoke and unit tests):
  python3 -u experiments/rl_propagation_recovery_v2.py --out-dir runs/propagation-recovery-v2
"""
import argparse
import hashlib
import json
import math
import platform
import random
import subprocess
from pathlib import Path

import rl_propagation_recovery as R
import spike_active_selection as SP

HERE = Path(__file__).resolve().parent
POLICIES = R.POLICIES
ESTIMATORS = ("E0", "E2", "E3a", "E3b")
GATE_ESTIMATOR = "E3b"
TRUE_MEAN_B = sum(SP.P_TYPE) / len(SP.P_TYPE)


# ----------------------------------------------------------------------------- log
def split_budget(budget, audit_fraction):
    audit = min(budget - 1, max(0, round(audit_fraction * budget)))
    return budget - audit, audit


def make_order(policy, graph, budget, audit_fraction, rng):
    """Return a list of (node, is_audit). Audit nodes are uniform among nodes the policy did not pick."""
    n_policy, n_audit = split_budget(budget, audit_fraction)
    picked = R.policy_order(policy, graph, n_policy, rng)
    rest = [i for i in range(len(graph["nodes"])) if i not in set(picked)]
    audit = rng.sample(rest, min(n_audit, len(rest)))
    return [(a, True) for a in audit] + [(a, False) for a in picked]


def run_log(graph, order, rng, obs_miss=0.0):
    """Like v1 `run_log`, with audit tags. Observable data only; `base` is read by the simulator alone."""
    nodes, topo, coins = graph["nodes"], graph["topo"], graph["coins"]
    base = list(graph["base"])
    err = SP.compute_err(base, nodes, topo, coins)
    reviewed = set()
    log = dict(events=[], root_reviews=0, root_flags=0, audit_root_reviews=0, audit_root_flags=0,
               inherited=0, cleared=0)
    for a, is_audit in order:
        before = list(err)
        flagged, err = SP.review_step(a, base, err, nodes, topo, coins, rng)
        if nodes[a]["layer"] == 0:
            log["root_reviews"] += 1
            log["root_flags"] += int(flagged)
            if is_audit:
                log["audit_root_reviews"] += 1
                log["audit_root_flags"] += int(flagged)
        if flagged:
            if not err[a]:
                log["cleared"] += 1
                for c in graph["children"][a]:
                    changed = before[c] and not err[c]
                    if changed and obs_miss > 0 and rng.random() < obs_miss:
                        changed = False
                    log["events"].append(dict(family=nodes[c]["layer"], indeg=len(nodes[c]["parents"]),
                                              changed=bool(changed), reviewed_before=c in reviewed))
            else:
                log["inherited"] += 1
        reviewed.add(a)
    return log


def merge(logs):
    out = dict(events=[], root_reviews=0, root_flags=0, audit_root_reviews=0, audit_root_flags=0,
               inherited=0, cleared=0)
    for log in logs:
        out["events"].extend(log["events"])
        for key in out:
            if key != "events":
                out[key] += log[key]
    return out


# ---------------------------------------------------------------------- estimators
def b_source(estimator, merged, prior_b):
    """(kind, successes, trials) for the base-error-rate source of an estimator; None for E0."""
    if estimator == "E0":
        return None
    if estimator == "E2":
        return ("reviewed_roots", merged["root_flags"], merged["root_reviews"])
    if estimator == "E3a":
        return ("prior", None, None)
    if estimator == "E3b":
        return ("audit_roots", merged["audit_root_flags"], merged["audit_root_reviews"])
    raise ValueError(estimator)


def estimate(merged, family, estimator, assumed_catch, prior_b, draws, seed):
    """Posterior summary for one family or None when no usable event exists."""
    events = merged["events"]
    if estimator == "E0":
        sel = [e for e in events if e["family"] == family]
    else:
        sel = [e for e in events if e["family"] == family and e["indeg"] == 1 and not e["reviewed_before"]]
    n = len(sel)
    if n == 0:
        return None
    k = sum(e["changed"] for e in sel)
    src = b_source(estimator, merged, prior_b)
    if src is not None and src[0] != "prior" and src[2] == 0:
        return None  # no root was reviewed in this source: no b estimate, not a fake one
    rng = random.Random(seed)
    samples = []
    for _ in range(draws):
        q = R._beta(rng, k, n)
        if src is None:
            samples.append(q)
            continue
        if src[0] == "prior":
            b = prior_b
        else:
            b = min(R._beta(rng, src[1], src[2]) / assumed_catch, 0.95)
        samples.append(min(q / (1.0 - b), 1.0))
    samples.sort()
    out = dict(n=n, k=k, mean=sum(samples) / draws, low=samples[int(0.025 * draws)],
               high=samples[min(draws - 1, int(0.975 * draws))])
    if src is not None and src[0] != "prior":
        out["b_hat"] = (src[1] / src[2]) / assumed_catch
        out["b_trials"] = src[2]
    return out


def selection_check(estimator, est, prior_b, check_ratio, min_audit_roots):
    """Is the b source plausibly free of selection? Used only by the `robust` label rule."""
    if estimator == "E0":
        return True
    if estimator == "E3a":
        return True  # b is an external prior; its validity is not a selection question
    if estimator == "E2":
        return est["b_hat"] <= prior_b * check_ratio
    if estimator == "E3b":
        return est["b_trials"] >= min_audit_roots
    raise ValueError(estimator)


# ------------------------------------------------------------------------ experiment
def one_replicate(rep, args, p_by_layer):
    seed = args.seed + rep
    world = R.build_world(seed, args.graphs, p_by_layer, N=args.nodes)
    out = {}
    for pi, policy in enumerate(POLICIES):
        logs = []
        for g, graph in enumerate(world):
            rng = random.Random(seed * 7_919 + g * 31 + pi)
            order = make_order(policy, graph, args.budget, args.audit_fraction, rng)
            logs.append(run_log(graph, order, rng, args.obs_miss))
        merged = merge(logs)
        est = {}
        for e in ESTIMATORS:
            for fam in sorted(p_by_layer):
                got = estimate(merged, fam, e, args.assumed_catch, args.prior_b, args.draws, rep * 101 + fam)
                if got is not None:
                    width = got["high"] - got["low"]
                    got["cal_width"] = width < args.width_threshold
                    got["cal_robust"] = got["cal_width"] and selection_check(
                        e, got, args.prior_b, args.check_ratio, args.min_audit_roots)
                est[f"{e}|{fam}"] = got
        out[policy] = dict(estimates=est, **{k: v for k, v in merged.items() if k != "events"},
                           events=len(merged["events"]))
    return out


def _rate(num, den):
    return None if den == 0 else num / den


def summarise(replicates, p_by_layer):
    table = {}
    for policy in POLICIES:
        for e in ESTIMATORS:
            for fam, truth in sorted(p_by_layer.items()):
                got = [r[policy]["estimates"][f"{e}|{fam}"] for r in replicates]
                have = [g for g in got if g is not None]
                row = dict(truth=truth, replicates=len(got), missing=len(got) - len(have))
                if have:
                    errs = [g["mean"] - truth for g in have]
                    outside = [not (g["low"] <= truth <= g["high"]) for g in have]
                    cw = [(g, o) for g, o in zip(have, outside) if g["cal_width"]]
                    cr = [(g, o) for g, o in zip(have, outside) if g["cal_robust"]]
                    row.update(
                        mean_estimate=sum(g["mean"] for g in have) / len(have),
                        bias=sum(errs) / len(errs),
                        rmse=math.sqrt(sum(x * x for x in errs) / len(errs)),
                        coverage=1 - sum(outside) / len(outside),
                        mean_width=sum(g["high"] - g["low"] for g in have) / len(have),
                        mean_n=sum(g["n"] for g in have) / len(have),
                        calibrated_width_rate=len(cw) / len(have),
                        wrong_given_calibrated_width=_rate(sum(o for _, o in cw), len(cw)),
                        calibrated_robust_rate=len(cr) / len(have),
                        wrong_given_calibrated_robust=_rate(sum(o for _, o in cr), len(cr)))
                table[f"{policy}|{e}|{fam}"] = row
    return table


def evaluate_gate(summary, p_by_layer, tol_bias=0.05, min_cov=0.90, min_n=100, max_wrong=0.05):
    """Pre-registered gate for GATE_ESTIMATOR over every policy and family. Pure function of the summary."""
    checks, ok = [], True
    for policy in POLICIES:
        for fam in sorted(p_by_layer):
            r = summary[f"{policy}|{GATE_ESTIMATOR}|{fam}"]
            if "bias" not in r:
                checks.append(dict(policy=policy, family=fam, passed=False, reason="no usable estimate"))
                ok = False
                continue
            wrong = r["wrong_given_calibrated_robust"]
            parts = dict(bias=abs(r["bias"]) <= tol_bias, coverage=r["coverage"] >= min_cov,
                         events=r["mean_n"] >= min_n, missing=r["missing"] == 0,
                         robust_label=(wrong is None or wrong <= max_wrong))
            passed = all(parts.values())
            ok = ok and passed
            checks.append(dict(policy=policy, family=fam, passed=passed, parts=parts))
    return dict(estimator=GATE_ESTIMATOR, passed=ok, checks=checks,
                thresholds=dict(max_abs_bias=tol_bias, min_coverage=min_cov, min_mean_events=min_n,
                                max_wrong_given_calibrated_robust=max_wrong))


def provenance(args):
    def git(*a):
        try:
            return subprocess.check_output(["git", *a], cwd=HERE, text=True).strip()
        except Exception:  # noqa: BLE001 - provenance must not stop a run
            return "unavailable"
    files = ["rl_propagation_recovery_v2.py", "rl_propagation_recovery.py",
             "spike_active_selection.py", "belief.py"]
    return dict(git_commit=git("rev-parse", "HEAD"), git_status=git("status", "--porcelain"),
                source_sha256={f: hashlib.sha256((HERE / f).read_bytes()).hexdigest() for f in files},
                python=platform.python_version(), simulator=dict(SP.CFG), type_rates=SP.P_TYPE,
                true_mean_b=TRUE_MEAN_B,
                args={k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()})


def fmt(x, spec):
    return "-" if x is None else format(x, spec)


def render_md(payload):
    cfg, gate = payload["config"], payload["gate"]
    lines = ["# Propagation recovery v2 results (synthetic)", "",
             f"Replicates {cfg['replicates']}, graphs/replicate {cfg['graphs']}, budget {cfg['budget']} "
             f"(audit fraction {cfg['audit_fraction']}), assumed catch {cfg['assumed_catch']}, "
             f"prior b {cfg['prior_b']:.3f}, observation miss {cfg['obs_miss']}.",
             "Truth by family (child layer): " + json.dumps(cfg["p_true"]) + ".",
             "Coverage = share of replicates whose 95% interval contains the truth. Missing = replicates with no "
             "usable estimate. `cal.width` / `cal.robust` = share labelled calibrated by each rule; "
             "`wrong|cal` = share of those whose interval misses the truth. Failures are kept.", "",
             f"## Gate ({gate['estimator']}): **{'PASSED' if gate['passed'] else 'NOT PASSED'}**", "",
             "| policy | family | passed | failed parts |", "|---|---:|---|---|"]
    for c in gate["checks"]:
        failed = [k for k, v in c.get("parts", {}).items() if not v] or ([c["reason"]] if "reason" in c else [])
        lines.append(f"| {c['policy']} | {c['family']} | {'yes' if c['passed'] else 'NO'} | {', '.join(failed) or '-'} |")
    lines.append("")
    for policy in POLICIES:
        lines += [f"## Policy: {policy}", "",
                  "| estimator | family | truth | mean est. | bias | RMSE | coverage | width | mean n | missing "
                  "| cal.width | wrong\\|cal.width | cal.robust | wrong\\|cal.robust |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for e in ESTIMATORS:
            for fam in sorted(cfg["p_true"], key=int):
                r = payload["summary"][f"{policy}|{e}|{fam}"]
                if "bias" not in r:
                    lines.append(f"| {e} | {fam} | {r['truth']} | - | - | - | - | - | - | {r['missing']} | - | - | - | - |")
                    continue
                lines.append(
                    f"| {e} | {fam} | {r['truth']} | {r['mean_estimate']:.3f} | {r['bias']:+.3f} | {r['rmse']:.3f} | "
                    f"{r['coverage']:.2f} | {r['mean_width']:.3f} | {r['mean_n']:.0f} | {r['missing']} | "
                    f"{r['calibrated_width_rate']:.2f} | {fmt(r['wrong_given_calibrated_width'], '.2f')} | "
                    f"{r['calibrated_robust_rate']:.2f} | {fmt(r['wrong_given_calibrated_robust'], '.2f')} |")
        lines.append("")
    lines.append("Counts per policy (mean over replicates): " + json.dumps(payload["counts"]))
    return "\n".join(lines) + "\n"


def run(args):
    p_by_layer = {int(k): v for k, v in args.p_true.items()}
    replicates = [one_replicate(rep, args, p_by_layer) for rep in range(args.replicates)]
    keys = ("events", "cleared", "inherited", "root_reviews", "root_flags", "audit_root_reviews", "audit_root_flags")
    counts = {pol: {k: sum(r[pol][k] for r in replicates) / len(replicates) for k in keys} for pol in POLICIES}
    summary = summarise(replicates, p_by_layer)
    return dict(config=dict(replicates=args.replicates, graphs=args.graphs, budget=args.budget,
                            audit_fraction=args.audit_fraction, assumed_catch=args.assumed_catch,
                            prior_b=args.prior_b, obs_miss=args.obs_miss, width_threshold=args.width_threshold,
                            check_ratio=args.check_ratio, min_audit_roots=args.min_audit_roots,
                            p_true={str(k): v for k, v in p_by_layer.items()}),
                provenance=provenance(args), summary=summary, gate=evaluate_gate(summary, p_by_layer),
                counts=counts, replicates=replicates)


def parse(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out-dir", type=Path, required=True, help="new directory; refuses to overwrite")
    ap.add_argument("--smoke", action="store_true", help="tiny run for checking the harness only")
    ap.add_argument("--replicates", type=int, default=50)
    ap.add_argument("--graphs", type=int, default=800, help="graphs per replicate")
    ap.add_argument("--nodes", type=int, default=80)
    ap.add_argument("--budget", type=int, default=16, help="reviews per graph (policy + audit)")
    ap.add_argument("--audit-fraction", type=float, default=0.25)
    ap.add_argument("--seed", type=int, default=20261122, help="differs from v1 so the run is independent")
    ap.add_argument("--assumed-catch", type=float, default=0.9)
    ap.add_argument("--true-catch", type=float, default=0.9)
    ap.add_argument("--obs-miss", type=float, default=0.0)
    ap.add_argument("--prior-b", type=float, default=round(TRUE_MEAN_B, 3),
                    help="external prior for the children's own error rate (E3a)")
    ap.add_argument("--width-threshold", type=float, default=0.15)
    ap.add_argument("--check-ratio", type=float, default=2.0)
    ap.add_argument("--min-audit-roots", type=int, default=100)
    ap.add_argument("--draws", type=int, default=2000)
    args = ap.parse_args(argv)
    if args.smoke:
        args.replicates, args.graphs, args.draws, args.min_audit_roots = 2, 20, 200, 5
    for name in ("replicates", "graphs", "nodes", "budget", "draws", "min_audit_roots"):
        if getattr(args, name) < 1:
            ap.error(f"--{name.replace('_', '-')} must be positive")
    for name in ("assumed_catch", "true_catch"):
        if not 0.0 < getattr(args, name) <= 1.0:
            ap.error(f"--{name.replace('_', '-')} must be in (0, 1]")
    if not 0.0 <= args.obs_miss < 1.0:
        ap.error("--obs-miss must be in [0, 1)")
    if not 0.0 <= args.audit_fraction < 1.0:
        ap.error("--audit-fraction must be in [0, 1)")
    if not 0.0 < args.prior_b < 0.95:
        ap.error("--prior-b must be in (0, 0.95)")
    if args.width_threshold <= 0 or args.check_ratio <= 0:
        ap.error("--width-threshold and --check-ratio must be positive")
    args.p_true = {str(k): v for k, v in R.DEFAULT_P.items()}
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
