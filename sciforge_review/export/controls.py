"""Controls for the export benchmark: does the harness see a planted signal, and
only when one exists?

Three error-placement regimes on the same 21-node structure:

    null               errors independent of type and reach
    type_signal        errors drawn from the declared role prior
    structure_signal   errors only on the highest-reach half of nodes

A working harness must (a) detect both planted signals and (b) show no advantage
under the null. This validates the evaluator. It says nothing about SciForge.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from .bench import (FALLBACK_PRIOR, POLICIES, TYPE_PRIOR, _reach_norm, episode,
                    recall_at)
from .load_export import load_export

HERE = Path(__file__).resolve().parent
MODES = ("null", "type_signal", "structure_signal")
SEEDS = {"null": 901, "type_signal": 902, "structure_signal": 903}


def place(mode: str, n: int, types: tuple[str, ...], reach_norm: np.ndarray,
          n_errors: int, rng: np.random.Generator) -> dict[int, bool]:
    if mode == "null":
        prob = np.full(n, n_errors / n)
    elif mode == "type_signal":
        prob = np.array([TYPE_PRIOR.get(t, FALLBACK_PRIOR) for t in types])
        prob = prob / prob.sum() * n_errors
    elif mode == "structure_signal":
        eligible = np.flatnonzero(reach_norm >= 0.5)
        prob = np.zeros(n)
        prob[eligible] = n_errors / max(len(eligible), 1)
    else:
        raise ValueError(mode)
    prob = np.clip(prob, 0.0, 1.0)
    return {v: bool(rng.random() < prob[v]) for v in range(n)}


def run(graph, mode: str, reps: int, k: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    infl = _reach_norm(graph)
    n_errors = len(graph.corrections)
    names = list(POLICIES) + ["oracle", "random_dummy"]
    scores: dict[str, list[float]] = {name: [] for name in names}
    for rep in range(reps):
        truth = place(mode, graph.n, graph.types, infl, n_errors, rng)
        if not any(truth.values()):
            continue
        chosen = episode(graph, truth, k)
        for name in POLICIES:
            scores[name].append(recall_at(chosen[name], truth, k))
        scores["oracle"].append(recall_at(chosen["oracle"], truth, k))
        order = list(range(graph.n))
        np.random.default_rng(50_000 + rep).shuffle(order)
        scores["random_dummy"].append(recall_at(order[:k], truth, k))
    return {name: np.array(vals) for name, vals in scores.items() if vals}


def compare(scores: dict[str, np.ndarray], a: str, b: str) -> dict:
    diff = scores[a] - scores[b]
    return {"mean": float(diff.mean()), "sd": float(diff.std(ddof=1)),
            "win": float((diff > 0).mean()), "tie": float((diff == 0).mean()),
            "loss": float((diff < 0).mean())}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--export", type=Path, default=HERE / "sciforge_mock_v1.json")
    ap.add_argument("--reps", type=int, default=400)
    ap.add_argument("--budget-frac", type=float, default=0.25)
    ap.add_argument("--out", type=Path, default=HERE / "outputs" / "controls.md")
    args = ap.parse_args()

    graph = load_export(args.export)
    k = max(3, int(round(args.budget_frac * graph.n)))
    lines = ["# Harness controls (synthetic placement, no evidential weight)", "",
             f"Structure: `{graph.project}`, {graph.n} nodes, budget K={k}, "
             f"errors per rep = {len(graph.corrections)}, reps = {args.reps}, "
             "primary method runs flat; declared-prior rows are the sensitivity arm.", ""]

    for mode in MODES:
        scores = run(graph, mode, args.reps, k, seed=SEEDS[mode])
        lines += [f"## {mode}", "",
                  "| policy | mean recall@K | sd |", "|---|---:|---:|"]
        for name in ["pipeline_order", "random_dummy", "type_prior", "reach",
                     "type_x_reach", "marginal_adaptive", "marginal_adaptive_declared",
                     "receipts", "oracle"]:
            if name in scores:
                lines.append(f"| `{name}` | {scores[name].mean():.3f} | {scores[name].std(ddof=1):.3f} |")
        lines.append("")
        for a, b in (("type_prior", "pipeline_order"), ("reach", "pipeline_order"),
                     ("marginal_adaptive", "type_prior")):
            c = compare(scores, a, b)
            lines.append(f"- `{a}` − `{b}`: {c['mean']:+.3f} "
                         f"(win/tie/loss {c['win']:.2f}/{c['tie']:.2f}/{c['loss']:.2f}, "
                         f"sd {c['sd']:.3f})")
        lines.append("")

    expected = {
        "null": "no ordering should win: mean diffs ≈ 0 and win ≈ loss (ties allowed)",
        "type_signal": "`type_prior` must beat `pipeline_order` clearly",
        "structure_signal": ("`reach` must beat `pipeline_order`; a prior pointing the other "
                             "way must lose — that is the misspecification arm"),
    }
    lines += ["## How to read this", ""]
    for mode, text in expected.items():
        lines.append(f"- **{mode}**: {text}")
    lines += ["", "If a row above contradicts its expectation, the evaluator or the policy "
                  "wiring is wrong — fix that before touching a real export. These numbers "
                  "are generated, not observed."]

    text = "\n".join(lines)
    print(text)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
