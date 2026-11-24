"""The budget curve must be the same environment as the published table.

`role3 improvement/outputs/v3-baselines/benchmark_summary.csv` reports, for
100 held-out episodes (graph seeds 90000-90099), budget 8:

    real    none 2.26  confidence 0.50  marginal 0.47
    ticket  none 1.87  confidence 0.32  marginal 0.29

`experiments/boundary_budget.py` sweeps the budget on the same topology, so its
budget-8 row has to land on exactly these numbers. If it does not, the curve is
measuring a different environment and none of its other points can be compared
with the published result. That is the point of this test.
"""

import os
import sys
import unittest

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "role3 improvement"))

from dag_role3 import generate_graph, sample_episode          # noqa: E402
from dag_role3.policies import run_public_policy             # noqa: E402

# Published in benchmark_summary.csv; do not edit to make a run pass.
PUBLISHED = {
    "real": {"none": 2.26, "confidence": 0.50, "marginal": 0.47},
    "ticket": {"none": 1.87, "confidence": 0.32, "marginal": 0.29},
}
SEEDS = range(90000, 90100)
BUDGET = 8


def measure(family: str, policies) -> dict:
    graph = generate_graph(family, SEEDS[0])
    out = {p: [] for p in policies}
    for seed in SEEDS:
        # Same episode-seed convention as run_benchmark.py.
        snap = sample_episode(graph, 20000 + seed)
        for p in policies:
            out[p].append(float(run_public_policy(graph, snap, p, BUDGET)[0]))
    return {p: float(np.mean(v)) for p, v in out.items()}


class PublishedParityTests(unittest.TestCase):
    def test_real_family_matches_published_table(self):
        got = measure("real", ("none", "confidence", "marginal"))
        for policy, expected in PUBLISHED["real"].items():
            self.assertAlmostEqual(got[policy], expected, places=2,
                                   msg=f"real/{policy}")

    def test_ticket_family_matches_published_table(self):
        got = measure("ticket", ("none", "confidence", "marginal"))
        for policy, expected in PUBLISHED["ticket"].items():
            self.assertAlmostEqual(got[policy], expected, places=2,
                                   msg=f"ticket/{policy}")

    def test_budget_is_the_only_change_in_the_curve(self):
        # A tighter budget must not leave fewer errors than a looser one.
        graph = generate_graph("real", 90000)
        snap = sample_episode(graph, 20101)
        tight = run_public_policy(graph, snap, "marginal", 4)[0]
        loose = run_public_policy(graph, snap, "marginal", 16)[0]
        self.assertGreaterEqual(tight, loose)


if __name__ == "__main__":
    unittest.main()
