#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Propagation recovery v3: a truly random audit, a frame-verifying label rule and a negative control.

v2 (`rl_propagation_recovery_v2.py`, unchanged; runs/propagation-recovery-v2) did not pass. Cause found in its
saved counts: the audit drew nodes from those the policy had NOT picked, so under confidence-ordered review the audit
roots were depleted of errors (b_hat 0.017 vs true 0.104). v3 changes:

  1. The audit is drawn FIRST, uniformly from ALL nodes; the policy then chooses among the rest
     (`--audit-order before`, default). `--audit-order after` reproduces the v2 flaw as a negative control.
  2. The `calibrated` label does not use interval width. It requires: enough usable events, and for estimators with
     a data-driven b source a verified sampling frame (`--attest-frame`, what the workflow records), enough
     audited roots, and an audit flag rate consistent with the external prior in BOTH directions.
     Width is reported separately as `usable`.
  3. The label criterion is noise-aware (Wilson upper bound) and must not be vacuous (the rule must label).
  4. Diagnostics for the residual bias seen in v2 with an exact prior: an oracle child-error rate (hidden, never
     read by an estimator) and E4, a per-child adjustment using the child's observed posterior (no b source).

Estimators (E0, E2, E3a, E3b as in v2; single-parent, not reviewed before, divided by 1 - b):
  E0   naive, all children (lower-bound reference)
  E2   b from all reviewed roots (v1 source; expected to be refused by the label under confidence order)
  E3a  b from an external prior (--prior-b)
  E3b  b from roots reviewed in the random audit   <- the estimator under the gate
  E4   exploratory: sum(changed) / sum(1 - child posterior); sandwich interval; no b source; never labelled
  Eo   diagnostic: oracle child base rate (reads hidden simulator state; never labelled)

Run (the user runs full runs; agents run only --smoke and unit tests):
  python3 -u experiments/rl_propagation_recovery_v3.py --out-dir runs/propagation-recovery-v3
  python3 -u experiments/rl_propagation_recovery_v3.py --audit-order after --attest-frame all_eligible \\
      --out-dir runs/propagation-recovery-v3-negcontrol
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
import spike_active_selection as SP

HERE = Path(__file__).resolve().parent
POLICIES = R.POLICIES
ESTIMATORS = ("E0", "E2", "E3a", "E3b", "E4", "Eo")
LABELLABLE = ("E2", "E3a", "E3b")
GATE_ESTIMATOR = "E3b"
TRUE_MEAN_B = V2.TRUE_MEAN_B


def wilson_upper(x, n, z=1.96):
    """Upper end of the Wilson score interval for x successes in n trials (n > 0)."""
    p = x / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return min(1.0, (centre + spread) / (1 + z * z / n))


# ----------------------------------------------------------------------------- log
def policy_pick(name, graph, candidates, k, rng):
    """Policy choice restricted to `candidates` (the nodes the audit did not take)."""
    if name == "random":
        return rng.sample(candidates, min(k, len(candidates)))
    if name == "confidence":
        return sorted(candidates, key=lambda i: -graph["post"][i])[:k]
    if name == "blast":
        return sorted(candidates, key=lambda i: (-graph["sink_reach"][i], -graph["post"][i]))[:k]
    raise ValueError(f"unknown policy {name}")


def make_order(policy, graph, budget, audit_fraction, rng, audit_order="before", attest_frame=None):
    """Return ([(node, is_audit)], true_frame, attested_frame).

    before: audit uniform over ALL nodes first (frame all_eligible); the policy picks among the rest.
    after:  the policy picks first; the audit is uniform over what remains (frame remaining) -- the v2 flaw.
    """
    n_policy, n_audit = V2.split_budget(budget, audit_fraction)
    ids = list(range(len(graph["nodes"])))
    if audit_order == "before":
        audit = rng.sample(ids, min(n_audit, len(ids)))
        taken = set(audit)
        picked = policy_pick(policy, graph, [i for i in ids if i not in taken], n_policy, rng)
        frame = "all_eligible"
    elif audit_order == "after":
        picked = policy_pick(policy, graph, ids, n_policy, rng)
        taken = set(picked)
        audit = rng.sample([i for i in ids if i not in taken], min(n_audit, len(ids) - len(taken)))
        frame = "remaining"
    else:
        raise ValueError(audit_order)
    order = [(a, True) for a in audit] + [(a, False) for a in picked]
    return order, frame, (attest_frame or frame)


def run_log(graph, order, rng, obs_miss=0.0):
    """Correction log. Event fields an audit chain could record: family, in-degree, whether the child changed,
    whether it had been reviewed before, and the child's observed posterior. `oracle_child_base` is hidden
    simulator state kept for diagnostics only; no estimator except the oracle diagnostic may read it."""
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
                    log["events"].append(dict(
                        family=nodes[c]["layer"], indeg=len(nodes[c]["parents"]), changed=bool(changed),
                        reviewed_before=c in reviewed, child_post=graph["post"][c],
                        oracle_child_base=bool(graph["base"][c])))
            else:
                log["inherited"] += 1
        reviewed.add(a)
    return log


def merge(logs, audit_frame):
    out = dict(events=[], root_reviews=0, root_flags=0, audit_root_reviews=0, audit_root_flags=0,
               inherited=0, cleared=0, audit_frame=audit_frame)
    for log in logs:
        out["events"].extend(log["events"])
        for key in ("root_reviews", "root_flags", "audit_root_reviews", "audit_root_flags", "inherited", "cleared"):
            out[key] += log[key]
    return out


# ---------------------------------------------------------------------- estimators
def eligible(events, family, estimator):
    if estimator == "E0":
        return [e for e in events if e["family"] == family]
    return [e for e in events if e["family"] == family and e["indeg"] == 1 and not e["reviewed_before"]]


def estimate(merged, family, estimator, assumed_catch, prior_b, draws, seed):
    """Summary for one family: dict(n, k, mean, low, high[, b_hat, b_trials]) or None if not computable."""
    sel = eligible(merged["events"], family, estimator)
    n = len(sel)
    if n == 0:
        return None
    k = sum(e["changed"] for e in sel)
    if estimator == "E4":
        w = [1.0 - e["child_post"] for e in sel]
        sw = sum(w)
        if sw <= 0:
            return None
        p = min(k / sw, 1.0)
        var = sum((e["changed"] - p * wi) ** 2 for e, wi in zip(sel, w)) / (sw * sw)
        se = math.sqrt(var)
        return dict(n=n, k=k, mean=p, low=max(0.0, p - 1.96 * se), high=min(1.0, p + 1.96 * se))
    rng = random.Random(seed)
    source = None
    if estimator == "E2":
        source = ("reviewed_roots", merged["root_flags"], merged["root_reviews"])
    elif estimator == "E3b":
        source = ("audit_roots", merged["audit_root_flags"], merged["audit_root_reviews"])
    if source is not None and source[2] == 0:
        return None
    if estimator == "Eo":
        b_oracle = min(sum(e["oracle_child_base"] for e in sel) / n, 0.95)
    samples = []
    for _ in range(draws):
        q = R._beta(rng, k, n)
        if estimator == "E0":
            samples.append(q)
            continue
        if estimator == "E3a":
            b = prior_b
        elif estimator == "Eo":
            b = b_oracle
        else:
            b = min(R._beta(rng, source[1], source[2]) / assumed_catch, 0.95)
        samples.append(min(q / (1.0 - b), 1.0))
    samples.sort()
    out = dict(n=n, k=k, mean=sum(samples) / draws, low=samples[int(0.025 * draws)],
               high=samples[min(draws - 1, int(0.975 * draws))])
    if source is not None:
        out["b_hat"] = (source[1] / source[2]) / assumed_catch
        out["b_trials"] = source[2]
    return out


def label_calibrated(estimator, est, merged, prior_b, check_ratio, min_audit_roots, min_events):
    """The `calibrated` label. Never uses interval width. Verifies the sampling frame and the audit flag rate."""
    if estimator not in LABELLABLE or est["n"] < min_events:
        return False
    if estimator == "E3a":
        return True  # b is an external prior; its validity is not a sampling question
    in_range = prior_b / check_ratio <= est["b_hat"] <= prior_b * check_ratio
    if estimator == "E2":
        return in_range
    return (merged["audit_frame"] == "all_eligible" and est["b_trials"] >= min_audit_roots and in_range)


# ------------------------------------------------------------------------ experiment
def one_replicate(rep, args, p_by_layer):
    seed = args.seed + rep
    world = R.build_world(seed, args.graphs, p_by_layer, N=args.nodes)
    out = {}
    for pi, policy in enumerate(POLICIES):
        logs, frame = [], None
        for g, graph in enumerate(world):
            rng = random.Random(seed * 7_919 + g * 31 + pi)
            order, _true, frame = make_order(policy, graph, args.budget, args.audit_fraction, rng,
                                             args.audit_order, args.attest_frame)
            logs.append(run_log(graph, order, rng, args.obs_miss))
        merged = merge(logs, frame)
        est = {}
        for e in ESTIMATORS:
            for fam in sorted(p_by_layer):
                got = estimate(merged, fam, e, args.assumed_catch, args.prior_b, args.draws, rep * 101 + fam)
                if got is not None:
                    got["usable"] = (got["high"] - got["low"]) < args.width_threshold
                    got["calibrated"] = label_calibrated(e, got, merged, args.prior_b, args.check_ratio,
                                                         args.min_audit_roots, args.min_events)
                    if e == "E2":
                        got["child_base_oracle"] = sum(
                            x["oracle_child_base"] for x in eligible(merged["events"], fam, "E2")) / got["n"]
                est[f"{e}|{fam}"] = got
        counts = {k: v for k, v in merged.items() if k not in ("events", "audit_frame")}
        out[policy] = dict(estimates=est, events=len(merged["events"]), **counts)
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
                    lab = [o for g, o in zip(have, outside) if g["calibrated"]]
                    row.update(
                        mean_estimate=sum(g["mean"] for g in have) / len(have),
                        bias=sum(errs) / len(errs),
                        rmse=math.sqrt(sum(x * x for x in errs) / len(errs)),
                        coverage=1 - sum(outside) / len(outside),
                        mean_width=sum(g["high"] - g["low"] for g in have) / len(have),
                        mean_n=sum(g["n"] for g in have) / len(have),
                        usable_rate=sum(g["usable"] for g in have) / len(have),
                        calibrated_rate=len(lab) / len(have), calibrated_count=len(lab),
                        wrong_given_calibrated=_rate(sum(lab), len(lab)),
                        wrong_upper95=(wilson_upper(sum(lab), len(lab)) if lab else None))
                table[f"{policy}|{e}|{fam}"] = row
    return table


def oracle_child_base(replicates, p_by_layer):
    """Mean hidden base-error rate of the children E2/E3 use, per policy and family (diagnostic only)."""
    out = {}
    for policy in POLICIES:
        for fam in sorted(p_by_layer):
            vals = [r[policy]["estimates"][f"E2|{fam}"]["child_base_oracle"] for r in replicates
                    if r[policy]["estimates"][f"E2|{fam}"] is not None]
            out[f"{policy}|{fam}"] = sum(vals) / len(vals) if vals else None
    return out


def evaluate_gate(summary, p_by_layer, tol_bias=0.05, min_cov=0.90, min_n=100, min_label_rate=0.80,
                  max_wrong_upper=0.20):
    """Primary gate for GATE_ESTIMATOR (honest audit order). Pure function of the summary."""
    checks, ok = [], True
    for policy in POLICIES:
        for fam in sorted(p_by_layer):
            r = summary[f"{policy}|{GATE_ESTIMATOR}|{fam}"]
            if "bias" not in r:
                checks.append(dict(policy=policy, family=fam, passed=False, reason="no usable estimate"))
                ok = False
                continue
            ub = r["wrong_upper95"]
            parts = dict(bias=abs(r["bias"]) <= tol_bias, coverage=r["coverage"] >= min_cov,
                         events=r["mean_n"] >= min_n, missing=r["missing"] == 0,
                         label_not_vacuous=r["calibrated_rate"] >= min_label_rate,
                         label_wrong_rate=(ub is not None and ub <= max_wrong_upper))
            passed = all(parts.values())
            ok = ok and passed
            checks.append(dict(policy=policy, family=fam, passed=passed, parts=parts))
    return dict(mode="primary", estimator=GATE_ESTIMATOR, passed=ok, checks=checks,
                thresholds=dict(max_abs_bias=tol_bias, min_coverage=min_cov, min_mean_events=min_n,
                                min_calibrated_rate=min_label_rate, max_wrong_upper95=max_wrong_upper))


def evaluate_negative_control(summary, p_by_layer, max_label_rate=0.10):
    """Negative control: with a flawed audit mislabelled as sound, the label rule must refuse under confidence order."""
    checks, ok = [], True
    for fam in sorted(p_by_layer):
        r = summary[f"confidence|{GATE_ESTIMATOR}|{fam}"]
        rate = r.get("calibrated_rate")
        passed = rate is not None and rate <= max_label_rate
        ok = ok and passed
        checks.append(dict(policy="confidence", family=fam, passed=passed, calibrated_rate=rate))
    return dict(mode="negative_control", estimator=GATE_ESTIMATOR, passed=ok, checks=checks,
                thresholds=dict(max_calibrated_rate=max_label_rate))


def provenance(args):
    def git(*a):
        try:
            return subprocess.check_output(["git", *a], cwd=HERE, text=True).strip()
        except Exception:  # noqa: BLE001 - provenance must not stop a run
            return "unavailable"
    files = ["rl_propagation_recovery_v3.py", "rl_propagation_recovery_v2.py", "rl_propagation_recovery.py",
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
    lines = ["# Propagation recovery v3 results (synthetic)", "",
             f"Replicates {cfg['replicates']}, graphs/replicate {cfg['graphs']}, budget {cfg['budget']} "
             f"(audit fraction {cfg['audit_fraction']}, audit order **{cfg['audit_order']}**, attested frame "
             f"**{cfg['attest_frame'] or 'honest'}**), assumed catch {cfg['assumed_catch']}, prior b "
             f"{cfg['prior_b']:.3f}, observation miss {cfg['obs_miss']}.",
             "Truth by family (child layer): " + json.dumps(cfg["p_true"]) + ".",
             "`calibrated` never uses interval width (frame, audited roots and audit flag rate vs prior instead); "
             "`usable` = interval narrower than the width threshold. `wrong\\|cal` = share of calibrated-labelled "
             "replicates whose 95% interval misses the truth; `ub95` its Wilson upper bound. Failures are kept.", ""]
    if gate["mode"] == "none":
        lines += ["## Gate", "", "Exploratory configuration: no pre-registered gate applies.", ""]
    else:
        title = "Primary gate" if gate["mode"] == "primary" else "Negative control"
        lines += [f"## {title} ({gate['estimator']}): **{'PASSED' if gate['passed'] else 'NOT PASSED'}**", "",
                  "| policy | family | passed | detail |", "|---|---:|---|---|"]
        for c in gate["checks"]:
            if gate["mode"] == "primary":
                detail = ", ".join(k for k, v in c.get("parts", {}).items() if not v) or c.get("reason", "-")
            else:
                detail = f"calibrated rate {fmt(c['calibrated_rate'], '.2f')}"
            lines.append(f"| {c['policy']} | {c['family']} | {'yes' if c['passed'] else 'NO'} | {detail or '-'} |")
        lines.append("")
    for policy in POLICIES:
        lines += [f"## Policy: {policy}", "",
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
    keys = ("events", "cleared", "inherited", "root_reviews", "root_flags", "audit_root_reviews", "audit_root_flags")
    counts = {pol: {k: sum(r[pol][k] for r in replicates) / len(replicates) for k in keys} for pol in POLICIES}
    summary = summarise(replicates, p_by_layer)
    if args.audit_order == "before" and not args.attest_frame:
        gate = evaluate_gate(summary, p_by_layer)
    elif args.audit_order == "after" and args.attest_frame == "all_eligible":
        gate = evaluate_negative_control(summary, p_by_layer)
    else:
        gate = dict(mode="none", estimator=GATE_ESTIMATOR, passed=None, checks=[])
    return dict(config=dict(replicates=args.replicates, graphs=args.graphs, budget=args.budget,
                            audit_fraction=args.audit_fraction, audit_order=args.audit_order,
                            attest_frame=args.attest_frame, assumed_catch=args.assumed_catch,
                            prior_b=args.prior_b, obs_miss=args.obs_miss, width_threshold=args.width_threshold,
                            check_ratio=args.check_ratio, min_audit_roots=args.min_audit_roots,
                            min_events=args.min_events, p_true={str(k): v for k, v in p_by_layer.items()}),
                provenance=provenance(args), summary=summary, gate=gate,
                oracle_child_base=oracle_child_base(replicates, p_by_layer), counts=counts, replicates=replicates)


def parse(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out-dir", type=Path, required=True, help="new directory; refuses to overwrite")
    ap.add_argument("--smoke", action="store_true", help="tiny run for checking the harness only")
    ap.add_argument("--replicates", type=int, default=100)
    ap.add_argument("--graphs", type=int, default=800, help="graphs per replicate")
    ap.add_argument("--nodes", type=int, default=80)
    ap.add_argument("--budget", type=int, default=16, help="reviews per graph (policy + audit)")
    ap.add_argument("--audit-fraction", type=float, default=0.25)
    ap.add_argument("--audit-order", choices=("before", "after"), default="before")
    ap.add_argument("--attest-frame", choices=("all_eligible", "remaining"), default=None,
                    help="frame the workflow records; default is the true frame. Used only for the negative control")
    ap.add_argument("--seed", type=int, default=20261123, help="differs from v1 and v2")
    ap.add_argument("--assumed-catch", type=float, default=0.9)
    ap.add_argument("--true-catch", type=float, default=0.9)
    ap.add_argument("--obs-miss", type=float, default=0.0)
    ap.add_argument("--prior-b", type=float, default=round(TRUE_MEAN_B, 3))
    ap.add_argument("--width-threshold", type=float, default=0.15)
    ap.add_argument("--check-ratio", type=float, default=2.0)
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
    if args.width_threshold <= 0 or args.check_ratio <= 1:
        ap.error("--width-threshold must be positive and --check-ratio greater than 1")
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
