"""Pilot: label-free instance-level contrastive representation of review states.

Frozen in ``PREREGISTER_CONTRASTIVE.md``. Writes ``metrics.json``, ``report.md``,
``manifest.json`` and ``run.log`` into ``--out``.

    python3 run_contrastive_check.py --out outputs/contrastive-v1
    python3 run_contrastive_check.py --report --out outputs/contrastive-v1
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import torch

from dag_role3 import contrastive as C
from dag_role3.environment import sample_episode
from dag_role3.graphs import generate_graph
from dag_role3.policies import run_public_policy

TRAIN_START, TRAIN_COUNT = 5024, 96
EVAL_START, EVAL_COUNT = 5120, 40
BUDGET = {"real": 8, "ticket": 8, "spike": 16}
SEED = 20261125


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def embed_states(encoder, ds, features):
    x, edges = C._view(features.unsqueeze(0), ds, ds.features.shape[2] - 7, None,
                       augment=False)
    with torch.no_grad():
        return encoder(x, edges)[0]


def probe_scorer(encoder, clf, ds):
    def scorer(obs):
        features = torch.as_tensor(obs["features"], dtype=torch.float32)
        z = embed_states(encoder, ds, features).numpy()
        p = clf.predict_proba(z)[:, 1]
        available = np.flatnonzero(obs["mask"])
        return int(available[np.argmax(p[available])])
    return scorer


def head_scorer(encoder, head, ds):
    def scorer(obs):
        features = torch.as_tensor(obs["features"], dtype=torch.float32)
        with torch.no_grad():
            z = embed_states(encoder, ds, features)
            p = torch.sigmoid(head(z)).numpy()
        available = np.flatnonzero(obs["mask"])
        return int(available[np.argmax(p[available])])
    return scorer


def bootstrap_mean(diff, seed=7, draws=2000):
    rng = np.random.default_rng(seed)
    diff = np.asarray(diff, dtype=float)
    means = np.array([diff[rng.integers(0, len(diff), len(diff))].mean() for _ in range(draws)])
    return float(diff.mean()), [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))]


def bootstrap_auc_delta(y, p_a, p_b, groups, seed=11, draws=2000):
    from sklearn.metrics import roc_auc_score
    rng = np.random.default_rng(seed)
    uniq = np.unique(groups)
    deltas = []
    for _ in range(draws):
        pick = rng.integers(0, len(uniq), len(uniq))
        idx = np.concatenate([np.flatnonzero(groups == uniq[i]) for i in pick])
        if len(np.unique(y[idx])) < 2:
            continue
        deltas.append(roc_auc_score(y[idx], p_a[idx]) - roc_auc_score(y[idx], p_b[idx]))
    return [float(np.percentile(deltas, 2.5)), float(np.percentile(deltas, 97.5))]


def evaluate_family(family, log):
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score

    train_seeds = tuple(range(TRAIN_START, TRAIN_START + TRAIN_COUNT))
    eval_seeds = tuple(range(EVAL_START, EVAL_START + EVAL_COUNT))
    train_ds = C.build_dataset(family, train_seeds)
    eval_ds = C.build_dataset(family, eval_seeds)
    graph = train_ds.graph
    budget = BUDGET[family]
    k = train_ds.features.shape[2] - 7

    t0 = time.time()
    enc, info = C.train_contrastive(train_ds, epochs=200, batch=64, seed=SEED)
    log(f"{family}: contrastive trained ({info['steps']} steps, {time.time() - t0:.1f}s)")

    t0 = time.time()
    sup_enc, sup_head = C.train_supervised(train_ds, epochs=200, batch=64, seed=SEED)
    log(f"{family}: supervised twin trained ({time.time() - t0:.1f}s)")

    z_train = C.embed_clean(enc, train_ds).reshape(-1, 32).numpy()
    z_eval = C.embed_clean(enc, eval_ds).reshape(-1, 32).numpy()
    own_train = C.own_features(train_ds).reshape(-1, train_ds.features.shape[2] - 7 + 4).numpy()
    own_eval = C.own_features(eval_ds).reshape(-1, eval_ds.features.shape[2] - 7 + 4).numpy()
    y_train = train_ds.labels.reshape(-1).numpy()
    y_eval = eval_ds.labels.reshape(-1).numpy()
    groups = np.repeat(np.arange(len(eval_seeds)), graph.n)

    probe = LogisticRegression(max_iter=3000, C=1.0).fit(z_train, y_train)
    own_probe = LogisticRegression(max_iter=3000, C=1.0).fit(own_train, y_train)
    p_con = probe.predict_proba(z_eval)[:, 1]
    p_own = own_probe.predict_proba(own_eval)[:, 1]
    z_sup = C.embed_clean(sup_enc, eval_ds).reshape(-1, 32)
    with torch.no_grad():
        p_sup = torch.sigmoid(sup_head(z_sup)).numpy().ravel()
    auc_con, auc_own, auc_sup = (roc_auc_score(y_eval, p_con),
                                 roc_auc_score(y_eval, p_own),
                                 roc_auc_score(y_eval, p_sup))
    delta = auc_con - auc_own
    delta_ci = bootstrap_auc_delta(y_eval, p_con, p_own, groups)
    log(f"{family}: AUC contrastive {auc_con:.3f} own {auc_own:.3f} supervised {auc_sup:.3f}")

    rho_con = C.rdm_spearman(C.embed_clean(enc, eval_ds), eval_ds.labels)
    rho_sup = C.rdm_spearman(C.embed_clean(sup_enc, eval_ds), eval_ds.labels)
    log(f"{family}: RDM rho contrastive {rho_con:.3f} supervised {rho_sup:.3f}")

    from dag_role3.environment import OversightEnv
    from dag_role3.policies import marginal_scores

    def marginal_scorer(obs):
        score = marginal_scores(obs)
        available = np.flatnonzero(obs["mask"])
        return int(available[np.argmax(score[available])])

    policies = {
        "none": lambda obs: None,
        "confidence": None,
        "marginal": marginal_scorer,
        "contrastive": probe_scorer(enc, probe, eval_ds),
        "supervised": head_scorer(sup_enc, sup_head, eval_ds),
    }
    per_episode = {name: [] for name in policies}
    for seed in eval_seeds:
        snapshot = sample_episode(graph, seed)
        for name, scorer in policies.items():
            if name == "none":
                env = OversightEnv(graph, snapshot, budget=0, p_catch=0.9)
                per_episode[name].append(float(env.no_review_score()))
            elif name == "confidence":
                score, _ = run_public_policy(graph, snapshot, "confidence", budget)
                per_episode[name].append(float(score))
            else:
                per_episode[name].append(float(C.run_policy(graph, snapshot, scorer, budget)))

    means = {name: float(np.mean(v)) for name, v in per_episode.items()}
    deltas = {}
    for name in ("contrastive", "supervised"):
        mean, ci = bootstrap_mean(np.array(per_episode[name]) - np.array(per_episode["marginal"]))
        deltas[f"{name}_minus_marginal"] = {"mean": mean, "ci": ci}
    mean, ci = bootstrap_mean(np.array(per_episode["marginal"]) - np.array(per_episode["confidence"]))
    deltas["marginal_minus_confidence"] = {"mean": mean, "ci": ci}
    log(f"{family}: sink errors " + ", ".join(f"{m} {v:.3f}" for m, v in means.items()))

    result = {
        "family": family,
        "n_nodes": graph.n,
        "budget": budget,
        "probe": {"contrastive": auc_con, "own_features": auc_own, "supervised": auc_sup,
                  "delta_contrastive_minus_own": delta,
                  "delta_ci": delta_ci},
        "rdm": {"contrastive": rho_con, "supervised": rho_sup},
        "scheduler": means,
        "deltas": deltas,
        "per_episode": {name: v for name, v in per_episode.items()},
        "training": info,
    }
    if family == "real":
        inner, overall, pct = C.time_node_concentration(C.embed_clean(enc, eval_ds))
        result["time_nodes"] = {"inner_similarity": inner, "all_pairs": overall,
                                "median_rank_percentile": pct}
        log(f"real: time-node similarity {inner:.3f} vs all pairs {overall:.3f}")
    return result


def _no_gain(delta):
    """Three-state reading of a "no gain" prediction, so an imprecise CI cannot be
    reported as a confirmation. ``contradicted`` needs the whole CI below the floor."""
    if delta["ci"][1] < -0.05:
        return "contradicted"
    if delta["mean"] >= -0.05 and delta["ci"][0] > -0.05:
        return "holds"
    return "inconclusive"


def verdicts(families):
    out = {}
    real, ticket = families.get("real"), families.get("ticket")
    pair = (("real", real), ("ticket", ticket))
    c1 = all(f is not None and f["rdm"]["contrastive"] >= 0.30 for f in (real, ticket))
    out["C1_geometry_tracks_truth"] = {
        "status": "holds" if c1 else "fails",
        "value": {name: (f["rdm"]["contrastive"] if f else None) for name, f in pair},
        "rule": "Spearman >= 0.30 on real and ticket",
    }
    def c2_one(f):
        d = f["probe"]["delta_contrastive_minus_own"]
        if d > 0.02 and f["probe"]["delta_ci"][0] > 0:
            return "fails"
        return "holds" if d <= 0.02 else "inconclusive"
    c2_status = [c2_one(f) for f in (real, ticket) if f]
    out["C2_no_new_information"] = {
        "status": "fails" if "fails" in c2_status else
                  ("holds" if c2_status and all(s == "holds" for s in c2_status) else "inconclusive"),
        "value": {name: (f["probe"]["delta_contrastive_minus_own"] if f else None)
                  for name, f in pair},
        "ci_low": {name: (f["probe"]["delta_ci"][0] if f else None) for name, f in pair},
        "rule": "fails only if AUC difference > 0.02 with a CI excluding 0",
    }
    c3_status = [_no_gain(f["deltas"]["contrastive_minus_marginal"])
                 for f in (real, ticket) if f]
    out["C3_no_scheduling_gain"] = {
        "status": "contradicted" if "contradicted" in c3_status else
                  ("holds" if c3_status and all(s == "holds" for s in c3_status) else "inconclusive"),
        "value": {name: (f["deltas"]["contrastive_minus_marginal"] if f else None)
                  for name, f in pair},
        "rule": "contradicted if the CI lies entirely below -0.05; holds only if the "
                "point estimate is >= -0.05 and the CI lower bound is > -0.05",
    }
    c4_action = [_no_gain(f["deltas"]["supervised_minus_marginal"])
                 for f in (real, ticket) if f]
    out["C4_labels_fit_not_action"] = {
        "auc_status": "holds" if all(f["probe"]["supervised"] >= f["probe"]["contrastive"]
                                     for f in (real, ticket) if f) else "fails",
        "action_status": "contradicted" if "contradicted" in c4_action else
                         ("holds" if c4_action and all(s == "holds" for s in c4_action)
                          else "inconclusive"),
        "value": {name: (f["deltas"]["supervised_minus_marginal"] if f else None)
                  for name, f in pair},
    }
    return out


def write_report(path: Path, families, predictions, config):
    lines = ["# Instance-level contrastive representation — pilot", ""]
    lines.append("Generated by `run_contrastive_check.py --report`; predictions frozen in "
                 "`PREREGISTER_CONTRASTIVE.md`. Deltas are paired inside an episode, "
                 "**policy minus comparison**, negative = fewer sink errors.")
    lines.append("")
    lines.append(f"Train seeds {config['train']} , evaluation seeds {config['eval']}. "
                 "Encoder trained with no labels; the probe and the supervised twin use labels.")
    lines.append("")
    lines.append("## Probe on held-out episodes")
    lines.append("")
    lines.append("| family | contrastive | own features | supervised | contrastive − own (95 % CI) |")
    lines.append("|---|---:|---:|---:|---|")
    for name, f in families.items():
        p = f["probe"]
        lines.append(f"| {name} | {p['contrastive']:.3f} | {p['own_features']:.3f} | "
                     f"{p['supervised']:.3f} | {p['delta_contrastive_minus_own']:+.3f} "
                     f"[{p['delta_ci'][0]:+.3f}, {p['delta_ci'][1]:+.3f}] |")
    lines.append("")
    lines.append("## Geometry (Spearman with the latent error RDM)")
    lines.append("")
    lines.append("| family | contrastive | supervised |")
    lines.append("|---|---:|---:|")
    for name, f in families.items():
        lines.append(f"| {name} | {f['rdm']['contrastive']:.3f} | {f['rdm']['supervised']:.3f} |")
    lines.append("")
    lines.append("## Sink errors per episode")
    lines.append("")
    lines.append("| family | none | confidence | marginal | contrastive | supervised |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for name, f in families.items():
        s = f["scheduler"]
        lines.append(f"| {name} | {s['none']:.3f} | {s['confidence']:.3f} | {s['marginal']:.3f} | "
                     f"{s['contrastive']:.3f} | {s['supervised']:.3f} |")
    lines.append("")
    lines.append("| family | contrastive − marginal | supervised − marginal | marginal − confidence |")
    lines.append("|---|---|---|---|")
    for name, f in families.items():
        d = f["deltas"]
        def fmt(x):
            return f"{x['mean']:+.3f} [{x['ci'][0]:+.3f}, {x['ci'][1]:+.3f}]"
        lines.append(f"| {name} | {fmt(d['contrastive_minus_marginal'])} | "
                     f"{fmt(d['supervised_minus_marginal'])} | {fmt(d['marginal_minus_confidence'])} |")
    lines.append("")
    lines.append("## Frozen predictions")
    lines.append("")
    lines.append("| # | prediction | measured | verdict |")
    lines.append("|---|---|---|---|")
    c1 = predictions["C1_geometry_tracks_truth"]
    c2 = predictions["C2_no_new_information"]
    c3 = predictions["C3_no_scheduling_gain"]
    c4 = predictions["C4_labels_fit_not_action"]
    lines.append(f"| C1 | embedding geometry tracks latent error geometry, ρ ≥ 0.30 on `real` and `ticket` | "
                 + ", ".join(f"{k} {v:+.3f}" for k, v in c1["value"].items() if v is not None) +
                 f" | **{c1['status']}** |")
    c2v = ", ".join(f"{k} {v:+.3f} (CI low {c2['ci_low'][k]:+.3f})"
                    for k, v in c2["value"].items() if v is not None) or "n/a"
    lines.append(f"| C2 | structure adds ≤ 0.02 AUC over own features | {c2v} | "
                 f"**{c2['status']}** |")
    c3v = ", ".join(f"{k} {v['mean']:+.3f} [{v['ci'][0]:+.3f}, {v['ci'][1]:+.3f}]"
                    for k, v in c3["value"].items() if v) or "n/a"
    lines.append(f"| C3 | no scheduling gain: `contrastive − marginal` ≥ −0.05 | {c3v} | "
                 f"**{c3['status']}** |")
    c4v = ", ".join(f"{k} {v['mean']:+.3f} [{v['ci'][0]:+.3f}, {v['ci'][1]:+.3f}]"
                    for k, v in c4["value"].items() if v) or "n/a"
    lines.append(f"| C4 | labels improve AUC but not the action | AUC part "
                 f"**{c4['auc_status']}**; action part **{c4['action_status']}**; {c4v} | — |")
    lines.append("")
    if "real" in families and "time_nodes" in families["real"]:
        t = families["real"]["time_nodes"]
        n_nodes = families["real"]["n_nodes"]
        t_npairs = n_nodes * (n_nodes - 1) // 2
        lines.append("## Exploratory: the four time nodes (no verdict)")
        lines.append("")
        lines.append(f"Mean cosine similarity among `time_bed`, `time_sleep`, `time_awake`, "
                     f"`time_getup`: **{t['inner_similarity']:.3f}**, against **{t['all_pairs']:.3f}** "
                     f"over all {t_npairs} node pairs (median time-node similarity sits at the "
                     f"{100 * t['median_rank_percentile']:.0f}th percentile of that distribution).")
        lines.append("")
    path.write_text("\n".join(lines) + "\n")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="outputs/contrastive-v1")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--families", default="real,ticket,spike")
    args = parser.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.report:
        families = json.loads((out / "metrics.json").read_text())["families"]
        predictions = json.loads((out / "metrics.json").read_text())["predictions"]
        write_report(out / "report.md", families, predictions, {"train": "5024–5119",
                                                                "eval": "5120–5159"})
        print(f"wrote {out / 'report.md'}")
        return 0

    log_path = out / "run.log"
    lines = []

    def log(msg):
        stamp = time.strftime("%H:%M:%S")
        entry = f"[{stamp}] {msg}"
        print(entry)
        lines.append(entry)
        log_path.write_text("\n".join(lines) + "\n")

    families = {}
    for family in args.families.split(","):
        families[family] = evaluate_family(family.strip(), log)
    predictions = verdicts(families)

    metrics = {"families": families, "predictions": predictions}
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    manifest = {
        "preregistration": "PREREGISTER_CONTRASTIVE.md",
        "families": list(families),
        "train_seeds": [TRAIN_START, TRAIN_COUNT],
        "eval_seeds": [EVAL_START, EVAL_COUNT],
        "budget": BUDGET,
        "encoder": {"hidden": 64, "embedding": 32, "rounds": 2, "temperature": 0.2,
                    "epochs": 200, "batch": 64, "seed": SEED},
        "prereg_correction": "train block widened 5024-5059 -> 5024-5119 before the first "
                             "training run, so the frozen batch of 64 is a real batch; "
                             "recorded in PREREGISTER_CONTRASTIVE.md",
        "augmentation": {"p_other": 0.3, "p_centre": 0.5, "p_edge": 0.2},
        "source_sha256": {
            "dag_role3/contrastive.py": sha256(Path(__file__).parent / "dag_role3" / "contrastive.py"),
            "dag_role3/environment.py": sha256(Path(__file__).parent / "dag_role3" / "environment.py"),
            "dag_role3/graphs.py": sha256(Path(__file__).parent / "dag_role3" / "graphs.py"),
            "run_contrastive_check.py": sha256(Path(__file__)),
        },
        "python": platform.python_version(),
        "torch": torch.__version__,
        "numpy": np.__version__,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    write_report(out / "report.md", families, predictions,
                 {"train": f"{TRAIN_START}–{TRAIN_START + TRAIN_COUNT - 1}",
                  "eval": f"{EVAL_START}–{EVAL_START + EVAL_COUNT - 1}"})
    log("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
