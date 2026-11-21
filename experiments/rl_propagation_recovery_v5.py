#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Propagation recovery v5: one canonical estimator, and a posterior-calibration check whose error rates are measured.

v4 (`rl_propagation_recovery_v4.py`, unchanged; runs/propagation-recovery-v4*) showed that an estimator conditioning
on each child's logged posterior (E4) recovers the propagation probability under random, blast-radius and
confidence-ordered review, and that a fixed-band balance check on the population-rate estimators is noise-limited.
v5 drops the population-rate path from the gate (E0, E2, E3a, E3b, Eo stay as references without labels) and answers
the question E4 leaves open: how reliable is the check that the logged posterior is calibrated?

The same simulated logs are analysed under several miscalibrations of the LOGGED posterior (the simulated world and the
review policy still use the true posterior, so only what the audit chain would record is distorted):
  cal         identity (correctly specified; false-refusal rate is measured here)
  shift+-1.5  logit shift by 1.5 (harmful in v4)        shift+-0.8  logit shift by 0.8 (mild)
  scale2      logit times 2 (over-confident)            scale0.5    logit times 0.5 (under-confident)
  type+1.5    logit shift 1.5 only for node types >= 3  noise1      logit plus N(0,1) noise per node

Calibration check on the audited roots (observable): per-node residual d_i = flag_i / assumed_catch - logged_posterior_i.
  global   accept only if the 90% interval of mean(d) lies inside +-calib_tol (an equivalence test: evidence is needed to
           accept, which controls false acceptance of a miscalibrated posterior; its cost is a measured false-refusal rate)
  bins     additionally refuse when, in the low (< 0.5) or high (>= 0.5) logged-posterior bin with at least min_bin roots,
           the 95% interval of mean(d) lies entirely outside +-bin_tol (gross miscalibration within a bin)

E4 label (never uses interval width): audit frame verified (all_eligible), >= min_audit_roots audited roots,
calibration check passed, and >= min_events usable events.

Run (the user runs full runs; agents run only --smoke and unit tests):
  python3 -u experiments/rl_propagation_recovery_v5.py --out-dir runs/propagation-recovery-v5
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
MODES = ("cal", "shift+1.5", "shift-1.5", "shift+0.8", "shift-0.8", "scale2", "scale0.5", "type+1.5", "noise1")
REFERENCES = ("E0", "E2", "E3a", "E3b")
TRUE_MEAN_B = V2.TRUE_MEAN_B


# -------------------------------------------------------------------- miscalibration
def _logit(p):
    p = min(max(p, 1e-9), 1 - 1e-9)
    return math.log(p / (1 - p))


def _sigmoid(x):
    return 1.0 / (1.0 + math.exp(-x))


def logged_posterior(mode, post, node_type, uid):
    """The posterior the audit chain would have recorded under `mode` (the true value is `post`)."""
    if mode == "cal":
        return post
    x = _logit(post)
    if mode.startswith("shift"):
        return _sigmoid(x + float(mode[5:]))
    if mode.startswith("scale"):
        return _sigmoid(x * float(mode[5:]))
    if mode == "type+1.5":
        return _sigmoid(x + 1.5) if node_type >= 3 else post
    if mode == "noise1":
        return _sigmoid(x + random.Random(uid * 7919 + 13).gauss(0.0, 1.0))
    raise ValueError(mode)


# ----------------------------------------------------------------------------- log
def run_log(graph, order, rng, uid_base, obs_miss=0.0):
    """Correction log. Events and audited roots carry the TRUE posterior; `logged_posterior` distorts it later.
    `oracle_child_base` is hidden simulator state for diagnostics only."""
    nodes, topo, coins = graph["nodes"], graph["topo"], graph["coins"]
    base = list(graph["base"])
    err = SP.compute_err(base, nodes, topo, coins)
    reviewed = set()
    log = dict(events=[], audit_roots=[], root_reviews=0, root_flags=0, audit_root_reviews=0, audit_root_flags=0,
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
                log["audit_roots"].append(dict(post=graph["post"][a], type=nodes[a]["type"],
                                               uid=uid_base + a, flag=bool(flagged)))
        if flagged:
            if not err[a]:
                log["cleared"] += 1
                for c in graph["children"][a]:
                    changed = before[c] and not err[c]
                    if changed and obs_miss > 0 and rng.random() < obs_miss:
                        changed = False
                    log["events"].append(dict(
                        family=nodes[c]["layer"], indeg=len(nodes[c]["parents"]), changed=bool(changed),
                        reviewed_before=c in reviewed, child_post=graph["post"][c], child_type=nodes[c]["type"],
                        child_uid=uid_base + c, oracle_child_base=bool(graph["base"][c])))
            else:
                log["inherited"] += 1
        reviewed.add(a)
    return log


def merge(logs, audit_frame):
    keys = ("root_reviews", "root_flags", "audit_root_reviews", "audit_root_flags", "inherited", "cleared")
    out = dict(events=[], audit_roots=[], audit_frame=audit_frame, **{k: 0 for k in keys})
    for log in logs:
        out["events"].extend(log["events"])
        out["audit_roots"].extend(log["audit_roots"])
        for k in keys:
            out[k] += log[k]
    return out


# ---------------------------------------------------------------------- estimator
def e4_estimate(events, family, mode):
    """E4 under the logged posterior of `mode`: changed / sum(1 - logged posterior); sandwich interval."""
    sel = [e for e in events if e["family"] == family and e["indeg"] == 1 and not e["reviewed_before"]]
    if not sel:
        return None
    w = [1.0 - logged_posterior(mode, e["child_post"], e["child_type"], e["child_uid"]) for e in sel]
    sw = sum(w)
    if sw <= 0:
        return None
    k = sum(e["changed"] for e in sel)
    p = min(k / sw, 1.0)
    se = math.sqrt(sum((e["changed"] - p * wi) ** 2 for e, wi in zip(sel, w))) / sw
    return dict(n=len(sel), k=k, mean=p, low=max(0.0, p - 1.96 * se), high=min(1.0, p + 1.96 * se))


# --------------------------------------------------------------------------- check
def _mean_se(values):
    n = len(values)
    mean = sum(values) / n
    if n < 2:
        return mean, float("inf")
    var = sum((v - mean) ** 2 for v in values) / (n - 1)
    return mean, math.sqrt(var / n)


def calibration_check(audit_roots, mode, assumed_catch, calib_tol, bin_tol, min_bin, min_audit_roots):
    """Evidence-based posterior calibration check on audited roots. Returns (passed, detail)."""
    if len(audit_roots) < min_audit_roots:
        return False, dict(reason="too_few_audited_roots", n=len(audit_roots))
    logged = [logged_posterior(mode, r["post"], r["type"], r["uid"]) for r in audit_roots]
    d = [r["flag"] / assumed_catch - p for r, p in zip(audit_roots, logged)]
    mean, se = _mean_se(d)
    detail = dict(n=len(d), mean_residual=mean, se=se)
    if abs(mean) + 1.645 * se > calib_tol:
        detail["reason"] = "global_not_equivalent"
        return False, detail
    for name, pick in (("low", lambda p: p < 0.5), ("high", lambda p: p >= 0.5)):
        sub = [x for x, p in zip(d, logged) if pick(p)]
        if len(sub) >= min_bin:
            m, s = _mean_se(sub)
            if abs(m) - 1.96 * s > bin_tol:
                detail["reason"] = f"{name}_bin_gross_miscalibration"
                return False, detail
    return True, detail


def label_calibrated(est, merged, passed_check, args):
    return (est is not None and est["n"] >= args.min_events and merged["audit_frame"] == "all_eligible"
            and passed_check)


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
            logs.append(run_log(graph, order, rng, uid_base=g * 1000, obs_miss=args.obs_miss))
        merged = merge(logs, frame)
        est, checks = {}, {}
        for mode in MODES:
            passed, detail = calibration_check(merged["audit_roots"], mode, args.assumed_catch, args.calib_tol,
                                               args.bin_tol, args.min_bin, args.min_audit_roots)
            checks[mode] = dict(passed=passed, **{k: v for k, v in detail.items() if k in ("reason", "mean_residual")})
            for fam in sorted(p_by_layer):
                got = e4_estimate(merged["events"], fam, mode)
                if got is not None:
                    got["calibrated"] = label_calibrated(got, merged, passed, args)
                est[f"E4|{mode}|{fam}"] = got
        for ref in REFERENCES:
            for fam in sorted(p_by_layer):
                est[f"{ref}|ref|{fam}"] = V3.estimate(merged, fam, ref, args.assumed_catch, args.prior_b,
                                                      args.draws, rep * 101 + fam)
        counts = {k: v for k, v in merged.items() if k not in ("events", "audit_roots", "audit_frame")}
        out[policy] = dict(estimates=est, checks=checks, events=len(merged["events"]), **counts)
    return out


def _rate(num, den):
    return None if den == 0 else num / den


def summarise(replicates, p_by_layer):
    """Per policy, mode and family for E4; per policy and family for the references."""
    table, checks = {}, {}
    for policy in POLICIES:
        for mode in MODES:
            passed = [r[policy]["checks"][mode]["passed"] for r in replicates]
            reasons = {}
            for r in replicates:
                reason = r[policy]["checks"][mode].get("reason")
                if reason:
                    reasons[reason] = reasons.get(reason, 0) + 1
            checks[f"{policy}|{mode}"] = dict(pass_rate=sum(passed) / len(passed), refusal_reasons=reasons)
            for fam, truth in sorted(p_by_layer.items()):
                got = [r[policy]["estimates"][f"E4|{mode}|{fam}"] for r in replicates]
                have = [g for g in got if g is not None]
                row = dict(truth=truth, replicates=len(got), missing=len(got) - len(have))
                if have:
                    errs = [g["mean"] - truth for g in have]
                    outside = [not (g["low"] <= truth <= g["high"]) for g in have]
                    lab = [o for g, o in zip(have, outside) if g["calibrated"]]
                    row.update(mean_estimate=sum(g["mean"] for g in have) / len(have),
                               bias=sum(errs) / len(errs), rmse=math.sqrt(sum(x * x for x in errs) / len(errs)),
                               coverage=1 - sum(outside) / len(outside), mean_n=sum(g["n"] for g in have) / len(have),
                               calibrated_rate=len(lab) / len(have), wrong_given_calibrated=_rate(sum(lab), len(lab)),
                               wrong_upper95=(V3.wilson_upper(sum(lab), len(lab)) if lab else None))
                table[f"{policy}|E4|{mode}|{fam}"] = row
        for ref in REFERENCES:
            for fam, truth in sorted(p_by_layer.items()):
                got = [r[policy]["estimates"][f"{ref}|ref|{fam}"] for r in replicates]
                have = [g for g in got if g is not None]
                row = dict(truth=truth, replicates=len(got), missing=len(got) - len(have))
                if have:
                    errs = [g["mean"] - truth for g in have]
                    row.update(bias=sum(errs) / len(errs),
                               coverage=sum(g["low"] <= truth <= g["high"] for g in have) / len(have),
                               mean_n=sum(g["n"] for g in have) / len(have))
                table[f"{policy}|{ref}|ref|{fam}"] = row
    return table, checks


def harmful_modes(table, p_by_layer, tol_bias=0.05):
    """Pre-registered rule: a mode (other than `cal`) is harmful if the mean E4 |bias| exceeds the tolerance in at
    least one policy-family cell."""
    out = {}
    for mode in MODES:
        if mode == "cal":
            continue
        worst = max(abs(table[f"{p}|E4|{mode}|{f}"].get("bias", 0.0)) for p in POLICIES for f in p_by_layer)
        out[mode] = dict(max_abs_bias=worst, harmful=worst > tol_bias)
    return out


def evaluate_gate(table, checks, p_by_layer, tol_bias=0.05, min_cov=0.90, min_n=100, min_label_rate=0.80,
                  max_wrong_upper=0.20, min_cal_pass=0.90, max_harmful_pass=0.10):
    """Primary gate: E4 in the correctly specified mode, false-refusal rate, and refusal of every harmful mode."""
    parts, ok = [], True
    for policy in POLICIES:
        for fam in sorted(p_by_layer):
            r = table[f"{policy}|E4|cal|{fam}"]
            if "bias" not in r:
                parts.append(dict(part="E4 correctly specified", policy=policy, family=fam, passed=False,
                                  detail="no usable estimate"))
                ok = False
                continue
            ub = r["wrong_upper95"]
            sub = dict(bias=abs(r["bias"]) <= tol_bias, coverage=r["coverage"] >= min_cov, events=r["mean_n"] >= min_n,
                       missing=r["missing"] == 0, label_not_vacuous=r["calibrated_rate"] >= min_label_rate,
                       label_wrong_rate=(ub is not None and ub <= max_wrong_upper))
            passed = all(sub.values())
            ok = ok and passed
            parts.append(dict(part="E4 correctly specified", policy=policy, family=fam, passed=passed,
                              detail=", ".join(k for k, v in sub.items() if not v) or "-"))
    for policy in POLICIES:
        rate = checks[f"{policy}|cal"]["pass_rate"]
        passed = rate >= min_cal_pass
        ok = ok and passed
        parts.append(dict(part="false refusal (calibration check, cal mode)", policy=policy, family="-",
                          passed=passed, detail=f"pass rate {rate:.2f}"))
    harmful = harmful_modes(table, p_by_layer, tol_bias)
    for mode, h in harmful.items():
        if not h["harmful"]:
            continue
        for policy in POLICIES:
            rate = checks[f"{policy}|{mode}"]["pass_rate"]
            passed = rate <= max_harmful_pass
            ok = ok and passed
            parts.append(dict(part=f"harmful mode {mode} refused", policy=policy, family="-", passed=passed,
                              detail=f"check pass rate {rate:.2f}"))
    return dict(mode="primary", passed=ok, parts=parts, harmful_modes=harmful,
                thresholds=dict(max_abs_bias=tol_bias, min_coverage=min_cov, min_mean_events=min_n,
                                min_calibrated_rate=min_label_rate, max_wrong_upper95=max_wrong_upper,
                                min_cal_check_pass_when_correct=min_cal_pass,
                                max_cal_check_pass_when_harmful=max_harmful_pass))


def provenance(args):
    def git(*a):
        try:
            return subprocess.check_output(["git", *a], cwd=HERE, text=True).strip()
        except Exception:  # noqa: BLE001 - provenance must not stop a run
            return "unavailable"
    files = ["rl_propagation_recovery_v5.py", "rl_propagation_recovery_v3.py", "rl_propagation_recovery_v2.py",
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
    lines = ["# Propagation recovery v5 results (synthetic)", "",
             f"Replicates {cfg['replicates']}, graphs/replicate {cfg['graphs']}, budget {cfg['budget']} (audit "
             f"fraction {cfg['audit_fraction']}, audit order **{cfg['audit_order']}**), assumed catch "
             f"{cfg['assumed_catch']}, calibration tolerance {cfg['calib_tol']}, bin tolerance {cfg['bin_tol']}.",
             "Truth by family (child layer): " + json.dumps(cfg["p_true"]) + ".",
             "Each mode distorts only the LOGGED posterior; the simulated world and policies are identical across modes. "
             "`check pass` = share of replicates in which the audit-based calibration check accepted the logged "
             "posterior. `wrong\\|cal` = share of E4-labelled replicates whose 95% interval misses the truth. Failures "
             "are kept.", ""]
    if gate["mode"] == "none":
        lines += ["## Gate", "", "Exploratory configuration: no pre-registered gate applies.", ""]
    else:
        lines += [f"## Primary gate: **{'PASSED' if gate['passed'] else 'NOT PASSED'}**", "",
                  "| part | policy | family | passed | detail |", "|---|---|---|---|---|"]
        for p in gate["parts"]:
            lines.append(f"| {p['part']} | {p['policy']} | {p['family']} | {'yes' if p['passed'] else 'NO'} | {p['detail']} |")
        lines += ["", "Harmful modes (rule: mean E4 |bias| above the tolerance in at least one cell):", "",
                  "| mode | max mean \\|bias\\| | harmful |", "|---|---:|---|"]
        for mode, h in gate["harmful_modes"].items():
            lines.append(f"| {mode} | {h['max_abs_bias']:.3f} | {'yes' if h['harmful'] else 'no'} |")
        lines.append("")
    lines += ["## Calibration check: pass rate by mode and policy (and why it refused)", "",
              "| mode | random | confidence | blast | refusal reasons (confidence policy) |", "|---|---:|---:|---:|---|"]
    for mode in MODES:
        cells = [payload["checks"][f"{p}|{mode}"] for p in POLICIES]
        lines.append(f"| {mode} | " + " | ".join(f"{c['pass_rate']:.2f}" for c in cells) + " | "
                     + json.dumps(cells[1]["refusal_reasons"]) + " |")
    lines.append("")
    for policy in POLICIES:
        lines += [f"## Policy: {policy} - E4 by mode", "",
                  "| mode | fam | truth | mean est. | bias | RMSE | coverage | mean n | missing | cal. rate | wrong\\|cal | ub95 |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for mode in MODES:
            for fam in sorted(cfg["p_true"], key=int):
                r = payload["summary"][f"{policy}|E4|{mode}|{fam}"]
                if "bias" not in r:
                    lines.append(f"| {mode} | {fam} | {r['truth']} | - | - | - | - | - | {r['missing']} | - | - | - |")
                    continue
                lines.append(f"| {mode} | {fam} | {r['truth']} | {r['mean_estimate']:.3f} | {r['bias']:+.3f} | "
                             f"{r['rmse']:.3f} | {r['coverage']:.2f} | {r['mean_n']:.0f} | {r['missing']} | "
                             f"{r['calibrated_rate']:.2f} | {fmt(r['wrong_given_calibrated'], '.2f')} | "
                             f"{fmt(r['wrong_upper95'], '.2f')} |")
        lines += ["", f"### Policy: {policy} - references (no labels; population-rate path, not gated)", "",
                  "| estimator | fam | truth | bias | coverage | mean n | missing |", "|---|---:|---:|---:|---:|---:|---:|"]
        for ref in REFERENCES:
            for fam in sorted(cfg["p_true"], key=int):
                r = payload["summary"][f"{policy}|{ref}|ref|{fam}"]
                if "bias" not in r:
                    lines.append(f"| {ref} | {fam} | {r['truth']} | - | - | - | {r['missing']} |")
                else:
                    lines.append(f"| {ref} | {fam} | {r['truth']} | {r['bias']:+.3f} | {r['coverage']:.2f} | "
                                 f"{r['mean_n']:.0f} | {r['missing']} |")
        lines.append("")
    lines.append("Counts per policy (mean over replicates): " + json.dumps(payload["counts"]))
    return "\n".join(lines) + "\n"


def run(args):
    p_by_layer = {int(k): v for k, v in args.p_true.items()}
    replicates = [one_replicate(rep, args, p_by_layer) for rep in range(args.replicates)]
    keys = ("events", "cleared", "inherited", "root_reviews", "root_flags", "audit_root_reviews", "audit_root_flags")
    counts = {pol: {k: sum(r[pol][k] for r in replicates) / len(replicates) for k in keys} for pol in POLICIES}
    table, checks = summarise(replicates, p_by_layer)
    if args.audit_order == "before" and not args.attest_frame:
        gate = evaluate_gate(table, checks, p_by_layer)
    else:
        gate = dict(mode="none", passed=None, parts=[], harmful_modes=harmful_modes(table, p_by_layer))
    return dict(config=dict(replicates=args.replicates, graphs=args.graphs, budget=args.budget,
                            audit_fraction=args.audit_fraction, audit_order=args.audit_order,
                            attest_frame=args.attest_frame, assumed_catch=args.assumed_catch,
                            prior_b=args.prior_b, obs_miss=args.obs_miss, calib_tol=args.calib_tol,
                            bin_tol=args.bin_tol, min_bin=args.min_bin, min_audit_roots=args.min_audit_roots,
                            min_events=args.min_events, modes=list(MODES),
                            p_true={str(k): v for k, v in p_by_layer.items()}),
                provenance=provenance(args), summary=table, checks=checks, gate=gate, counts=counts,
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
    ap.add_argument("--seed", type=int, default=20261125, help="differs from v1-v4")
    ap.add_argument("--assumed-catch", type=float, default=0.9)
    ap.add_argument("--true-catch", type=float, default=0.9)
    ap.add_argument("--obs-miss", type=float, default=0.0)
    ap.add_argument("--prior-b", type=float, default=round(TRUE_MEAN_B, 3))
    ap.add_argument("--calib-tol", type=float, default=0.04)
    ap.add_argument("--bin-tol", type=float, default=0.15)
    ap.add_argument("--min-bin", type=int, default=30)
    ap.add_argument("--min-audit-roots", type=int, default=100)
    ap.add_argument("--min-events", type=int, default=100)
    ap.add_argument("--draws", type=int, default=2000)
    args = ap.parse_args(argv)
    if args.smoke:
        args.replicates, args.graphs, args.draws = 2, 20, 200
        args.min_audit_roots, args.min_events, args.min_bin = 5, 5, 3
    for name in ("replicates", "graphs", "nodes", "budget", "draws", "min_audit_roots", "min_events", "min_bin"):
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
    if args.calib_tol <= 0 or args.bin_tol <= 0:
        ap.error("--calib-tol and --bin-tol must be positive")
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
