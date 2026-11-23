#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Propagation recovery v4: condition on the logged selection score, check its calibration, check covariate balance.

v3 (`rl_propagation_recovery_v3.py`, unchanged; runs/propagation-recovery-v3*) fixed the audit but exposed a second
selection effect: under confidence-ordered review the children an estimator may use are depleted of source errors
(hidden base rate 0.063 vs 0.104), so adjusting by the population base rate over-corrects, and the label rule did not
see it. An estimator conditioning on the child's observed posterior (E4) was unbiased in every v3 cell. v4 makes that
the estimator under the gate and adds what it needs to be trusted:

  * E4 (gate): changed / sum(1 - child posterior) over single-parent children not reviewed before; sandwich
    interval; no base-error-rate source. The child's posterior is the selection score logged at review time.
  * posterior calibration check: the random audit's observed root base-error rate (flags / roots / catch) must match
    the mean posterior of the audited roots to within --calib-tol. Without it E4 would silently inherit any miscalibration.
  * covariate-balance check: for the population-b estimators (E2, E3a, E3b) the mean posterior of the children they use
    must be within a factor --balance-ratio of the audited roots' mean posterior; otherwise the label is refused.
  * miscalibration control: --post-shift moves the logged posterior on the logit scale (ranking unchanged); with
    |shift| >= 1.0 the E4 label must be refused. A shift of 0.8 is too weak to detect with --calib-tol 0.04 and is
    also too weak to bias E4 beyond the 0.05 tolerance, so it is not treated as a control.

Calibrated-label rules (never use interval width; `usable` is reported separately):
  E2   flag-rate consistency (prior/ratio .. prior*ratio) and balance
  E3a  balance
  E3b  frame verified (all_eligible), audited roots >= --min-audit-roots, flag-rate consistency, balance
  E4   frame verified, audited roots >= --min-audit-roots, posterior calibration check
  all  usable events >= --min-events

Run (the user runs full runs; agents run only --smoke and unit tests):
  python3 -u experiments/rl_propagation_recovery_v4.py --out-dir runs/propagation-recovery-v4
  python3 -u experiments/rl_propagation_recovery_v4.py --post-shift 1.5 --out-dir runs/propagation-recovery-v4-miscal
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
import rl_propagation_recovery_v2 as V2
import rl_propagation_recovery_v3 as V3
import spike_active_selection as SP

HERE = Path(__file__).resolve().parent
POLICIES = V3.POLICIES
ESTIMATORS = V3.ESTIMATORS
GATE_ESTIMATOR = "E4"
POP_B_ESTIMATORS = ("E2", "E3a", "E3b")
TRUE_MEAN_B = V2.TRUE_MEAN_B


def shift_logit(p, delta):
    """Move a probability on the logit scale (monotone, so any ranking by it is unchanged)."""
    if delta == 0:
        return p
    p = min(max(p, 1e-9), 1 - 1e-9)
    return 1.0 / (1.0 + math.exp(-(math.log(p / (1 - p)) + delta)))


# ----------------------------------------------------------------------------- log
def run_log(graph, order, rng, obs_miss=0.0, post_shift=0.0):
    """v3 correction log plus the audited roots' logged posterior (needed for the calibration and balance checks).

    `child_post` and `audit_root_post_sum` hold the LOGGED posterior (shifted when --post-shift is set); the hidden
    `oracle_child_base` is simulator state for diagnostics only."""
    nodes, topo, coins = graph["nodes"], graph["topo"], graph["coins"]
    base = list(graph["base"])
    err = SP.compute_err(base, nodes, topo, coins)
    reviewed = set()
    log = dict(events=[], root_reviews=0, root_flags=0, audit_root_reviews=0, audit_root_flags=0,
               audit_root_post_sum=0.0, inherited=0, cleared=0)
    for a, is_audit in order:
        before = list(err)
        flagged, err = SP.review_step(a, base, err, nodes, topo, coins, rng)
        if nodes[a]["layer"] == 0:
            log["root_reviews"] += 1
            log["root_flags"] += int(flagged)
            if is_audit:
                log["audit_root_reviews"] += 1
                log["audit_root_flags"] += int(flagged)
                log["audit_root_post_sum"] += shift_logit(graph["post"][a], post_shift)
        if flagged:
            if not err[a]:
                log["cleared"] += 1
                for c in graph["children"][a]:
                    changed = before[c] and not err[c]
                    if changed and obs_miss > 0 and rng.random() < obs_miss:
                        changed = False
                    log["events"].append(dict(
                        family=nodes[c]["layer"], indeg=len(nodes[c]["parents"]), changed=bool(changed),
                        reviewed_before=c in reviewed, child_post=shift_logit(graph["post"][c], post_shift),
                        oracle_child_base=bool(graph["base"][c])))
            else:
                log["inherited"] += 1
        reviewed.add(a)
    return log


def merge(logs, audit_frame):
    keys = ("root_reviews", "root_flags", "audit_root_reviews", "audit_root_flags", "audit_root_post_sum",
            "inherited", "cleared")
    out = dict(events=[], audit_frame=audit_frame, **{k: 0 for k in keys})
    for log in logs:
        out["events"].extend(log["events"])
        for k in keys:
            out[k] += log[k]
    return out


# ------------------------------------------------------------------------- checks
def calibration_ok(merged, assumed_catch, calib_tol, min_audit_roots):
    """Posterior calibration-in-the-large on the audited roots: observed base rate vs mean logged posterior."""
    n = merged["audit_root_reviews"]
    if n < min_audit_roots:
        return False
    observed = merged["audit_root_flags"] / n / assumed_catch
    return abs(observed - merged["audit_root_post_sum"] / n) <= calib_tol


def balance_ratio(merged, est):
    """Mean logged posterior of the children an estimate uses / mean logged posterior of the audited roots."""
    n = merged["audit_root_reviews"]
    if n == 0 or est.get("child_post_mean") is None:
        return None
    return est["child_post_mean"] / (merged["audit_root_post_sum"] / n)


def label_calibrated(estimator, est, merged, args):
    """The v4 `calibrated` label. Never uses interval width."""
    if estimator not in ("E2", "E3a", "E3b", "E4") or est["n"] < args.min_events:
        return False
    if estimator == "E4":
        return (merged["audit_frame"] == "all_eligible"
                and calibration_ok(merged, args.assumed_catch, args.calib_tol, args.min_audit_roots))
    ratio = balance_ratio(merged, est)
    balanced = ratio is not None and 1.0 / args.balance_ratio <= ratio <= args.balance_ratio
    if estimator == "E3a":
        return balanced
    in_range = args.prior_b / args.check_ratio <= est["b_hat"] <= args.prior_b * args.check_ratio
    if estimator == "E2":
        return in_range and balanced
    return (merged["audit_frame"] == "all_eligible" and est["b_trials"] >= args.min_audit_roots
            and in_range and balanced)


# ------------------------------------------------------------------------ experiment
def one_replicate(rep, args, p_by_layer):
    seed = args.seed + rep
    world = R.build_world(seed, args.graphs, p_by_layer, N=args.nodes)
    out = {}
    for pi, policy in enumerate(POLICIES):
        logs, frame = [], None
        for g, graph in enumerate(world):
            rng = random.Random(seed * 7_919 + g * 31 + pi)
            order, _true, frame = V3.make_order(policy, graph, args.budget, args.audit_fraction, rng,
                                                args.audit_order, args.attest_frame)
            logs.append(run_log(graph, order, rng, args.obs_miss, args.post_shift))
        merged = merge(logs, frame)
        est = {}
        for e in ESTIMATORS:
            for fam in sorted(p_by_layer):
                got = V3.estimate(merged, fam, e, args.assumed_catch, args.prior_b, args.draws, rep * 101 + fam)
                if got is not None:
                    sel = V3.eligible(merged["events"], fam, e)
                    got["child_post_mean"] = sum(x["child_post"] for x in sel) / len(sel)
                    got["usable"] = (got["high"] - got["low"]) < args.width_threshold
                    got["calibrated"] = label_calibrated(e, got, merged, args)
                    if e == "E2":
                        got["child_base_oracle"] = sum(x["oracle_child_base"] for x in sel) / len(sel)
                est[f"{e}|{fam}"] = got
        counts = {k: v for k, v in merged.items() if k not in ("events", "audit_frame")}
        out[policy] = dict(estimates=est, events=len(merged["events"]),
                           calibration_ok=calibration_ok(merged, args.assumed_catch, args.calib_tol,
                                                         args.min_audit_roots), **counts)
    return out


def evaluate_gate(summary, p_by_layer, tol_bias=0.05, min_cov=0.90, min_n=100, min_label_rate=0.80,
                  max_wrong_upper=0.20, refuse_rate=0.10):
    """Primary gate: E4 in every policy and family, plus the label must refuse the biased population-b estimator."""
    checks, ok = [], True
    for policy in POLICIES:
        for fam in sorted(p_by_layer):
            r = summary[f"{policy}|{GATE_ESTIMATOR}|{fam}"]
            if "bias" not in r:
                checks.append(dict(policy=policy, family=fam, estimator=GATE_ESTIMATOR, passed=False,
                                   reason="no usable estimate"))
                ok = False
                continue
            ub = r["wrong_upper95"]
            parts = dict(bias=abs(r["bias"]) <= tol_bias, coverage=r["coverage"] >= min_cov,
                         events=r["mean_n"] >= min_n, missing=r["missing"] == 0,
                         label_not_vacuous=r["calibrated_rate"] >= min_label_rate,
                         label_wrong_rate=(ub is not None and ub <= max_wrong_upper))
            passed = all(parts.values())
            ok = ok and passed
            checks.append(dict(policy=policy, family=fam, estimator=GATE_ESTIMATOR, passed=passed, parts=parts))
    for policy in POLICIES:
        for fam in sorted(p_by_layer):
            r = summary[f"{policy}|E3b|{fam}"]
            rate = r.get("calibrated_rate")
            if policy == "confidence":
                passed, part = rate is not None and rate <= refuse_rate, "label_refuses_biased_population_b"
            else:
                passed, part = rate is not None and rate >= min_label_rate, "label_accepts_unbiased_population_b"
            ok = ok and passed
            checks.append(dict(policy=policy, family=fam, estimator="E3b", passed=passed, parts={part: passed},
                               calibrated_rate=rate))
    return dict(mode="primary", estimator=GATE_ESTIMATOR, passed=ok, checks=checks,
                thresholds=dict(max_abs_bias=tol_bias, min_coverage=min_cov, min_mean_events=min_n,
                                min_calibrated_rate=min_label_rate, max_wrong_upper95=max_wrong_upper,
                                max_refused_rate=refuse_rate))


def evaluate_miscalibration_control(summary, p_by_layer, max_label_rate=0.10):
    """With a miscalibrated logged posterior the E4 label must be refused in every policy and family."""
    checks, ok = [], True
    for policy in POLICIES:
        for fam in sorted(p_by_layer):
            r = summary[f"{policy}|{GATE_ESTIMATOR}|{fam}"]
            rate = r.get("calibrated_rate")
            passed = rate is not None and rate <= max_label_rate
            ok = ok and passed
            checks.append(dict(policy=policy, family=fam, estimator=GATE_ESTIMATOR, passed=passed,
                               calibrated_rate=rate, bias=r.get("bias")))
    return dict(mode="miscalibration_control", estimator=GATE_ESTIMATOR, passed=ok, checks=checks,
                thresholds=dict(max_calibrated_rate=max_label_rate))


def provenance(args):
    def git(*a):
        try:
            return subprocess.check_output(["git", *a], cwd=HERE, text=True).strip()
        except Exception:  # noqa: BLE001 - provenance must not stop a run
            return "unavailable"
    files = ["rl_propagation_recovery_v4.py", "rl_propagation_recovery_v3.py", "rl_propagation_recovery_v2.py",
             "rl_propagation_recovery.py", "spike_active_selection.py", "belief.py"]
    return dict(git_commit=git("rev-parse", "HEAD"), git_status=git("status", "--porcelain"),
                source_sha256={f: hashlib.sha256((HERE / f).read_bytes()).hexdigest() for f in files},
                python=platform.python_version(), simulator=dict(SP.CFG), type_rates=SP.P_TYPE,
                true_mean_b=TRUE_MEAN_B,
                args={k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()})


def fmt(x, spec):
    return "-" if x is None else format(x, spec)


def render_md(payload):
    cfg, gate = payload["config"], payload["gate"]
    lines = ["# Propagation recovery v4 results (synthetic)", "",
             f"Replicates {cfg['replicates']}, graphs/replicate {cfg['graphs']}, budget {cfg['budget']} "
             f"(audit fraction {cfg['audit_fraction']}, audit order **{cfg['audit_order']}**), logged posterior shift "
             f"**{cfg['post_shift']}** (logit), assumed catch {cfg['assumed_catch']}, prior b {cfg['prior_b']:.3f}, "
             f"observation miss {cfg['obs_miss']}.",
             "Truth by family (child layer): " + json.dumps(cfg["p_true"]) + ".",
             "`calibrated` never uses interval width. `wrong\\|cal` = share of calibrated-labelled replicates whose 95% "
             "interval misses the truth; `ub95` its Wilson upper bound. `post.ok` = share of replicates in which the "
             "audit-based posterior calibration check passed. Failures are kept.", ""]
    if gate["mode"] == "none":
        lines += ["## Gate", "", "Exploratory configuration: no pre-registered gate applies.", ""]
    else:
        title = {"primary": "Primary gate", "miscalibration_control": "Miscalibration control"}[gate["mode"]]
        lines += [f"## {title} ({gate['estimator']}): **{'PASSED' if gate['passed'] else 'NOT PASSED'}**", "",
                  "| estimator | policy | family | passed | detail |", "|---|---|---:|---|---|"]
        for c in gate["checks"]:
            if gate["mode"] == "primary" and c["estimator"] == GATE_ESTIMATOR:
                detail = ", ".join(k for k, v in c.get("parts", {}).items() if not v) or c.get("reason", "-")
            elif gate["mode"] == "primary":
                detail = f"{list(c['parts'])[0]}: calibrated rate {fmt(c['calibrated_rate'], '.2f')}"
            else:
                detail = f"calibrated rate {fmt(c['calibrated_rate'], '.2f')}, bias {fmt(c['bias'], '+.3f')}"
            lines.append(f"| {c['estimator']} | {c['policy']} | {c['family']} | {'yes' if c['passed'] else 'NO'} | "
                         f"{detail or '-'} |")
        lines.append("")
    for policy in POLICIES:
        ok_rate = sum(r[policy]["calibration_ok"] for r in payload["replicates"]) / len(payload["replicates"])
        lines += [f"## Policy: {policy}  (posterior calibration check passed in {ok_rate:.2f} of replicates)", "",
                  "| est. | fam | truth | mean est. | bias | RMSE | coverage | width | mean n | missing | usable "
                  "| cal. rate | wrong\\|cal | ub95 |",
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
                    f"{r['usable_rate']:.2f} | {r['calibrated_rate']:.2f} | {fmt(r['wrong_given_calibrated'], '.2f')} | "
                    f"{fmt(r['wrong_upper95'], '.2f')} |")
        lines.append("")
    lines += ["## Diagnostic: hidden base-error rate of the children used by the adjusted estimators "
              f"(population mean {payload['provenance']['true_mean_b']:.3f})", "",
              "| policy | family 1 | family 2 | family 3 |", "|---|---:|---:|---:|"]
    for policy in POLICIES:
        cells = [fmt(payload["oracle_child_base"][f"{policy}|{fam}"], ".3f") for fam in sorted(cfg["p_true"], key=int)]
        lines.append(f"| {policy} | " + " | ".join(cells) + " |")
    lines += ["", "Counts per policy (mean over replicates): " + json.dumps(payload["counts"])]
    return "\n".join(lines) + "\n"


def run(args):
    p_by_layer = {int(k): v for k, v in args.p_true.items()}
    replicates = [one_replicate(rep, args, p_by_layer) for rep in range(args.replicates)]
    keys = ("events", "cleared", "inherited", "root_reviews", "root_flags", "audit_root_reviews",
            "audit_root_flags", "audit_root_post_sum")
    counts = {pol: {k: sum(r[pol][k] for r in replicates) / len(replicates) for k in keys} for pol in POLICIES}
    summary = V3.summarise(replicates, p_by_layer)
    standard = args.audit_order == "before" and not args.attest_frame
    if standard and args.post_shift == 0:
        gate = evaluate_gate(summary, p_by_layer)
    elif standard and abs(args.post_shift) >= 1.0:
        gate = evaluate_miscalibration_control(summary, p_by_layer)
    else:
        gate = dict(mode="none", estimator=GATE_ESTIMATOR, passed=None, checks=[])
    return dict(config=dict(replicates=args.replicates, graphs=args.graphs, budget=args.budget,
                            audit_fraction=args.audit_fraction, audit_order=args.audit_order,
                            attest_frame=args.attest_frame, post_shift=args.post_shift,
                            assumed_catch=args.assumed_catch, prior_b=args.prior_b, obs_miss=args.obs_miss,
                            width_threshold=args.width_threshold, check_ratio=args.check_ratio,
                            calib_tol=args.calib_tol, balance_ratio=args.balance_ratio,
                            min_audit_roots=args.min_audit_roots, min_events=args.min_events,
                            p_true={str(k): v for k, v in p_by_layer.items()}),
                provenance=provenance(args), summary=summary, gate=gate,
                oracle_child_base=V3.oracle_child_base(replicates, p_by_layer), counts=counts,
                replicates=replicates)


def parse(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out-dir", type=Path, required=True, help="new directory; refuses to overwrite")
    ap.add_argument("--smoke", action="store_true", help="tiny run for checking the harness only")
    ap.add_argument("--replicates", type=int, default=150)
    ap.add_argument("--graphs", type=int, default=800, help="graphs per replicate")
    ap.add_argument("--nodes", type=int, default=80)
    ap.add_argument("--budget", type=int, default=16, help="reviews per graph (policy + audit)")
    ap.add_argument("--audit-fraction", type=float, default=0.25)
    ap.add_argument("--audit-order", choices=("before", "after"), default="before")
    ap.add_argument("--attest-frame", choices=("all_eligible", "remaining"), default=None)
    ap.add_argument("--post-shift", type=float, default=0.0,
                    help="logit shift applied to the logged posterior (miscalibration control)")
    ap.add_argument("--seed", type=int, default=20261124, help="differs from v1, v2 and v3")
    ap.add_argument("--assumed-catch", type=float, default=0.9)
    ap.add_argument("--true-catch", type=float, default=0.9)
    ap.add_argument("--obs-miss", type=float, default=0.0)
    ap.add_argument("--prior-b", type=float, default=round(TRUE_MEAN_B, 3))
    ap.add_argument("--width-threshold", type=float, default=0.15)
    ap.add_argument("--check-ratio", type=float, default=2.0)
    ap.add_argument("--calib-tol", type=float, default=0.04)
    ap.add_argument("--balance-ratio", type=float, default=1.25)
    ap.add_argument("--min-audit-roots", type=int, default=100)
    ap.add_argument("--min-events", type=int, default=100)
    ap.add_argument("--draws", type=int, default=2000)
    args = ap.parse_args(argv)
    if args.smoke:
        args.replicates, args.graphs, args.draws = 2, 20, 200
        args.min_audit_roots, args.min_events = 5, 5
    for name in ("replicates", "graphs", "nodes", "budget", "draws", "min_audit_roots", "min_events"):
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
    if args.width_threshold <= 0 or args.check_ratio <= 1 or args.balance_ratio <= 1 or args.calib_tol <= 0:
        ap.error("--width-threshold and --calib-tol must be positive; --check-ratio and --balance-ratio above 1")
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
