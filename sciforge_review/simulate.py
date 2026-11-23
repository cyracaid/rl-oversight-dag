"""Paired episode simulator for the review control plane.

This is a *demo harness*, not a reproduction of the paper's simulator.  It
reuses the N=21 pipeline DAG and the same error-propagation semantics as
``experiments/real_pipeline_graph.py``:

    P(child wrong | parent wrong) = 1 - exp(-lambda * w),  w ~ U(0.6, 1.4)
    a review clears the node's own (source) error, not errors inherited
    from an upstream node that is still wrong

The new part is the cost model: a review costs fields x per-field minutes, so
the same budget buys twice as many witness-pair reviews as whole-row reviews.
Metrics are paired: every policy sees the same seed, base errors and edge
coins.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from .graph import EvidenceGraph
from .policies import PER_FIELD_MINUTES, field_count

P_CATCH = 0.9
EDGE_LAMBDA = 0.9


@dataclass(frozen=True)
class EpisodeResult:
    sink_errors: int
    fixed_sources: int
    total_sources: int
    reviews: int
    minutes: float

    @property
    def recall(self) -> float:
        return self.fixed_sources / self.total_sources if self.total_sources else 0.0

    @property
    def errors_per_hour(self) -> float:
        return self.fixed_sources / (self.minutes / 60.0) if self.minutes else 0.0


@dataclass(frozen=True)
class Aggregate:
    policy: str
    sink_errors: float
    recall: float
    reviews: float
    minutes: float
    errors_per_hour: float


def _edge_coins(graph: EvidenceGraph, rng: random.Random) -> dict[tuple[int, int], bool]:
    coins = {}
    for node in graph.nodes:
        for parent in node.parents:
            w = rng.uniform(0.6, 1.4)
            coins[(parent, node.idx)] = rng.random() < (1.0 - math.exp(-EDGE_LAMBDA * w))
    return coins


def _propagate(
    graph: EvidenceGraph,
    base: list[bool],
    coins: dict[tuple[int, int], bool],
) -> list[bool]:
    err = [False] * graph.n
    for node in graph.nodes:  # NODES is topologically ordered by layer
        if base[node.idx]:
            err[node.idx] = True
            continue
        for parent in node.parents:
            if err[parent] and coins[(parent, node.idx)]:
                err[node.idx] = True
                break
    return err


def run_episode(
    graph: EvidenceGraph,
    order: list[int],
    budget_minutes: float,
    mode: str,
    seed: int,
) -> EpisodeResult:
    rng = random.Random(seed)
    coins = _edge_coins(graph, rng)
    base = [rng.random() < node.base_error_rate for node in graph.nodes]
    true_sources = sum(base)
    fixed: set[int] = set()
    spent = 0.0
    reviews = 0
    fields = field_count(mode)
    per_review = fields * PER_FIELD_MINUTES

    for idx in order:
        if spent + per_review > budget_minutes + 1e-9:
            break
        spent += per_review
        reviews += 1
        if base[idx] and idx not in fixed:
            if rng.random() < P_CATCH:
                fixed.add(idx)

    base_after = [base[i] and i not in fixed for i in range(graph.n)]
    err = _propagate(graph, base_after, coins)
    sink_errors = sum(1 for i in graph.sinks if err[i])
    return EpisodeResult(
        sink_errors=sink_errors,
        fixed_sources=len(fixed),
        total_sources=true_sources,
        reviews=reviews,
        minutes=spent,
    )


def sample_truth(graph: EvidenceGraph, seed: int) -> dict[str, bool]:
    """Sample a source-error truth table for one paired episode.

    Phase 1 only needs the truth (not sink propagation); using the same seed
    across policies keeps the comparison paired.
    """
    rng = random.Random(seed)
    return {node.name: rng.random() < node.base_error_rate for node in graph.nodes}


def no_review(graph: EvidenceGraph, seeds: int = 50) -> Aggregate:
    results = [run_episode(graph, [], 0.0, "row", seed) for seed in range(1, seeds + 1)]
    n = len(results)
    return Aggregate(
        policy="no review",
        sink_errors=sum(r.sink_errors for r in results) / n,
        recall=0.0,
        reviews=0.0,
        minutes=0.0,
        errors_per_hour=0.0,
    )


def evaluate(
    graph: EvidenceGraph,
    policies: dict[str, list[int]],
    budgets: tuple[float, ...] = (60.0, 120.0, 240.0),
    mode: str = "row",
    seeds: int = 50,
) -> list[Aggregate]:
    rows = []
    for policy, order in policies.items():
        for budget in budgets:
            results = [
                run_episode(graph, order, budget_minutes=budget, mode=mode, seed=seed)
                for seed in range(1, seeds + 1)
            ]
            n = len(results)
            rows.append(
                Aggregate(
                    policy=f"{policy} @ {budget:g} min ({mode})",
                    sink_errors=sum(r.sink_errors for r in results) / n,
                    recall=sum(r.recall for r in results) / n,
                    reviews=sum(r.reviews for r in results) / n,
                    minutes=sum(r.minutes for r in results) / n,
                    errors_per_hour=sum(r.errors_per_hour for r in results) / n,
                )
            )
    return rows
