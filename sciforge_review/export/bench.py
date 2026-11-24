"""Benchmark the review ordering on one exported evidence graph.

Task: rank nodes; a human reviews the top K; count confirmed errors found.
Everything is label-free except ``oracle``, which exists only as a ceiling.

The policy interface is deliberately sequential: ``order(state)`` sees the
graph, the set of already-reviewed nodes, and the verdict *of those nodes only*.
The harness owns the truth table; no policy can read an unreviewed verdict.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from functools import partial
from pathlib import Path

import numpy as np

from .load_export import ExportGraph, load_export

# Declared a priori, not estimated from the evaluation set. Rationale: a claim is
# an aggregation plus an interpretation, so it has the most ways to be wrong; a
# raw dataset value has the fewest.
TYPE_PRIOR = {"claim": 0.30, "run": 0.20, "figure": 0.15, "dataset": 0.10}
FALLBACK_PRIOR = 0.10

# P(child inherits | parent wrong). Declared, not tuned; the sleep side used 0.9.
INHERIT = 1.0 - math.exp(-0.9)


@dataclass(frozen=True)
class State:
    graph: ExportGraph
    reviewed: frozenset[int]
    revealed: dict[int, bool]

    def verdict(self, node: int) -> bool:
        if node not in self.revealed:
            raise PermissionError(f"node {node} has not been reviewed; verdict is not available")
        return self.revealed[node]


def _prior(graph: ExportGraph, flat: bool) -> np.ndarray:
    if flat:
        return np.ones(graph.n)
    return np.array([TYPE_PRIOR.get(t, FALLBACK_PRIOR) for t in graph.types])


def _posterior(graph: ExportGraph, revealed: dict[int, bool], prior: np.ndarray) -> np.ndarray:
    """Prior pushed downstream by verdicts already obtained (noisy-OR, hop by hop)."""
    p = prior.copy()
    for v in graph.topo:
        if not revealed.get(v, False):
            continue
        for child in graph.children[v]:
            p[child] = 1.0 - (1.0 - p[child]) * (1.0 - INHERIT)
    return p


def _unreviewed(state: State) -> list[int]:
    return [v for v in range(state.graph.n) if v not in state.reviewed]


def _reach_norm(graph: ExportGraph) -> np.ndarray:
    """Structure enters as a bounded modifier, never as the dominant term.

    Declared a priori: a node's reach may raise its priority by at most 2x. An
    unbounded multiplier lets one wide fan-out outrank a whole error-prone type,
    which is a modelling choice nobody has evidence for.
    """
    top = max(graph.reach) if graph.reach else 0
    return np.array([r / top for r in graph.reach]) if top else np.zeros(graph.n)


# ---- policies: each returns candidate order, best first ----------------------


def pipeline_order(state: State) -> list[int]:
    return _unreviewed(state)


def random_order(state: State, seed: int = 0) -> list[int]:
    rng = np.random.default_rng(seed)
    nodes = _unreviewed(state)
    rng.shuffle(nodes)
    return nodes


def type_prior_order(state: State, flat: bool = False) -> list[int]:
    prior = _prior(state.graph, flat)
    g = state.graph
    return sorted(_unreviewed(state), key=lambda v: (-prior[v], v))


def reach_order(state: State) -> list[int]:
    g = state.graph
    return sorted(_unreviewed(state), key=lambda v: (-g.reach[v], v))


def type_x_reach_order(state: State, flat: bool = False) -> list[int]:
    prior = _prior(state.graph, flat)
    infl = _reach_norm(state.graph)
    return sorted(_unreviewed(state), key=lambda v: (-(prior[v] * (1 + infl[v])), v))


def marginal_adaptive_order(state: State, flat: bool = False) -> list[int]:
    prior = _prior(state.graph, flat)
    p = _posterior(state.graph, state.revealed, prior)
    infl = _reach_norm(state.graph)
    return sorted(_unreviewed(state), key=lambda v: (-(p[v] * (1 + infl[v])), v))


def receipt_order(state: State) -> list[int]:
    """What humans actually read, in timestamp order, then the pipeline default."""
    ranked: list[int] = []
    seen: set[int] = set()
    for receipt in sorted(state.graph.receipts, key=lambda r: (r["reviewed_at"] or "", r["node"])):
        node = receipt["node"]
        if node not in state.reviewed and node not in seen:
            ranked.append(node)
            seen.add(node)
    ranked.extend(v for v in _unreviewed(state) if v not in seen)
    return ranked


# The declared type prior is an assumption, not a measurement. The primary
# method therefore runs flat; the declared-prior variant is the sensitivity arm.
POLICIES = {
    "pipeline_order": pipeline_order,
    "type_prior": partial(type_prior_order, flat=False),
    "reach": reach_order,
    "type_x_reach": partial(type_x_reach_order, flat=False),
    "marginal_adaptive": partial(marginal_adaptive_order, flat=True),
    "marginal_adaptive_declared": partial(marginal_adaptive_order, flat=False),
    "receipts": receipt_order,
}


# ---- episode ---------------------------------------------------------------


def _run_static(order_fn, graph: ExportGraph, truth: dict[int, bool], k: int) -> list[int]:
    reviewed: set[int] = set()
    revealed: dict[int, bool] = {}
    chosen: list[int] = []
    for _ in range(k):
        state = State(graph=graph, reviewed=frozenset(reviewed), revealed=dict(revealed))
        order = order_fn(state)
        if not order:
            break
        node = order[0]
        chosen.append(node)
        reviewed.add(node)
        revealed[node] = truth.get(node, False)
    return chosen


def _run_oracle(graph: ExportGraph, truth: dict[int, bool], k: int) -> list[int]:
    errs = sorted(truth, key=lambda v: (not truth[v], v))
    return errs[:k]


def recall_at(chosen: list[int], truth: dict[int, bool], k: int) -> float:
    total = sum(1 for v in truth if truth[v])
    if not total:
        return float("nan")
    hits = sum(1 for v in chosen[:k] if truth.get(v, False))
    return hits / total


def precision_at(chosen: list[int], truth: dict[int, bool], k: int) -> float:
    if k <= 0:
        return float("nan")
    hits = sum(1 for v in chosen[:k] if truth.get(v, False))
    return hits / k


def reviews_to_half(chosen: list[int], truth: dict[int, bool]) -> float:
    total = sum(1 for v in truth if truth[v])
    if not total:
        return float("nan")
    hits = 0
    for i, v in enumerate(chosen, start=1):
        hits += int(truth.get(v, False))
        if hits * 2 >= total:
            return float(i)
    return float("nan")


# ---- uncertainty -----------------------------------------------------------


def _weighted_recall(chosen: list[int], truth: dict[int, bool], k: int, w: np.ndarray) -> float:
    """recall@k over a resampled multiset (weights = bootstrap multiplicities)."""
    denom = sum(w[v] for v in truth if truth[v])
    if denom == 0:
        return float("nan")
    hits = 0
    taken = 0
    for v in chosen:
        if taken >= k:
            break
        take = int(min(w[v], k - taken))
        if take <= 0:
            continue
        taken += take
        if truth.get(v, False):
            hits += take
    return hits / denom


def bootstrap(chosen_a: list[int], chosen_b: list[int] | None, truth: dict[int, bool],
              k: int, n: int, reps: int, seed: int = 7) -> dict:
    rng = np.random.default_rng(seed)
    a_vals, d_vals = [], []
    for _ in range(reps):
        idx = rng.integers(0, n, size=n)
        w = np.bincount(idx, minlength=n).astype(float)
        a_vals.append(_weighted_recall(chosen_a, truth, k, w))
        if chosen_b is not None:
            d_vals.append(a_vals[-1] - _weighted_recall(chosen_b, truth, k, w))
    out = {"recall_lo95": float(np.nanpercentile(a_vals, 2.5)),
           "recall_hi95": float(np.nanpercentile(a_vals, 97.5))}
    if chosen_b is not None:
        out["diff"] = float(np.nanmean(d_vals))
        out["diff_lo95"] = float(np.nanpercentile(d_vals, 2.5))
        out["diff_hi95"] = float(np.nanpercentile(d_vals, 97.5))
    return out


# ---- reporting -------------------------------------------------------------


def episode(graph: ExportGraph, truth: dict[int, bool], k: int) -> dict[str, list[int]]:
    """One pass of every policy through the same episode."""
    chosen = {name: _run_static(fn, graph, truth, k) for name, fn in POLICIES.items()}
    chosen["oracle"] = _run_oracle(graph, truth, k)
    return chosen


def evaluate(graph: ExportGraph, budget_frac: float, random_draws: int, boot: int) -> dict:
    truth = {v: True for v in graph.corrections}
    k = max(3, int(round(budget_frac * graph.n)))
    n_errors = len(truth)

    chosen = episode(graph, truth, k)

    rng = np.random.default_rng(11)
    random_recalls = []
    for draw in range(random_draws):
        order = list(range(graph.n))
        np.random.default_rng(10_000 + draw).shuffle(order)
        random_recalls.append(recall_at(order[:k], truth, k))
    chosen["random"] = None

    rows = []
    for name, picks in chosen.items():
        if name == "random":
            point = float(np.mean(random_recalls))
            lo, hi = (float(np.percentile(random_recalls, 2.5)),
                      float(np.percentile(random_recalls, 97.5)))
            rows.append({"policy": "random", "recall": point, "lo95": lo, "hi95": hi,
                         "precision": float("nan"), "reviews_to_half": float("nan"),
                         "note": f"mean of {random_draws} permutations"})
            continue
        stats = bootstrap(picks, None, truth, k, graph.n, boot)
        rows.append({"policy": name,
                     "recall": recall_at(picks, truth, k),
                     "lo95": stats["recall_lo95"], "hi95": stats["recall_hi95"],
                     "precision": precision_at(picks, truth, k),
                     "reviews_to_half": reviews_to_half(picks, truth),
                     "note": ""})

    adapt = chosen["marginal_adaptive"]
    for base in ("type_prior", "pipeline_order", "reach", "marginal_adaptive_declared"):
        stats = bootstrap(adapt, chosen[base], truth, k, graph.n, boot)
        for row in rows:
            if row["policy"] == "marginal_adaptive":
                row[f"diff_vs_{base}"] = stats["diff"]
                row[f"diff_vs_{base}_lo95"] = stats["diff_lo95"]
                row[f"diff_vs_{base}_hi95"] = stats["diff_hi95"]

    unreviewed_by_humans = [v for v in truth if v not in {r["node"] for r in graph.receipts}]
    return {
        "budget_k": k,
        "n_nodes": graph.n,
        "n_errors": n_errors,
        "rows": rows,
        "chosen": {name: picks for name, picks in chosen.items() if picks is not None},
        "errors_never_reviewed_by_human": len(unreviewed_by_humans),
        "report": graph.report,
        "prior": "flat for marginal_adaptive; declared for type_prior/type_x_reach",
    }


def markdown(result: dict, title: str) -> str:
    lines = [f"## {title}", "",
             f"nodes **{result['n_nodes']}**, confirmed errors **{result['n_errors']}**, "
             f"budget **K={result['budget_k']}** nodes, prior **{result['prior']}**", "",
             "| policy | recall@K | 95% CI | precision@K | reviews→50% |",
             "|---|---:|---|---:|---:|"]
    order = ["pipeline_order", "random", "type_prior", "reach", "type_x_reach",
             "marginal_adaptive", "marginal_adaptive_declared", "receipts", "oracle"]
    by_name = {r["policy"]: r for r in result["rows"]}
    for name in order:
        if name not in by_name:
            continue
        r = by_name[name]
        ci = "—" if r["lo95"] != r["lo95"] else f"[{r['lo95']:.2f}, {r['hi95']:.2f}]"
        prec = "—" if r["precision"] != r["precision"] else f"{r['precision']:.2f}"
        half = "not reached" if r["reviews_to_half"] != r["reviews_to_half"] else f"{r['reviews_to_half']:.0f}"
        lines.append(f"| `{name}` | **{r['recall']:.2f}** | {ci} | {prec} | {half} |")
    m = by_name.get("marginal_adaptive")
    if m:
        lines += ["", "`marginal_adaptive` minus baseline (paired, node-resampled):"]
        for base in ("type_prior", "reach", "pipeline_order", "marginal_adaptive_declared"):
            key = f"diff_vs_{base}"
            if key in m:
                lo, hi = m[f"{key}_lo95"], m[f"{key}_hi95"]
                verdict = "indistinguishable" if lo <= 0 <= hi else ("ahead" if lo > 0 else "behind")
                lines.append(f"- vs `{base}`: {m[key]:+.2f} [{lo:+.2f}, {hi:+.2f}] — {verdict}")
    lines += ["", f"- errors never reviewed by the human receipts: "
                  f"**{result['errors_never_reviewed_by_human']} / {result['n_errors']}**"]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--export", type=Path,
                    default=Path(__file__).resolve().parent / "sciforge_mock_v1.json")
    ap.add_argument("--budget-frac", type=float, default=0.25)
    ap.add_argument("--random-draws", type=int, default=200)
    ap.add_argument("--boot", type=int, default=1000)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    graph = load_export(args.export)
    result = evaluate(graph, args.budget_frac, args.random_draws, args.boot)
    banner = ("# MOCK — synthetic export, no evidential weight\n\n"
              if graph.synthetic else "")
    text = banner + markdown(result, f"review ordering — `{graph.project}`")
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        (args.out.with_suffix(".json")).write_text(
            json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
