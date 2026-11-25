"""Pin the closed-form information accounting (course report section 6).

These are arithmetic identities, not experimental results, so the tests are cheap and
consume no seed. Their job is to stop three claims from drifting silently:

1. a node that reaches no conclusion has exactly zero value of information;
2. information about the repairable variable cannot exceed information about the
   effective-error variable;
3. the shipped `marginal_scores` keeps the ordering of exact one-step VoI even though its
   magnitude is not comparable (so it may be quoted as a ranking, never as a value).
"""
import unittest

import numpy as np

from dag_role3.graphs import gen_real, gen_ticket

from analyse_information_budget import (
    asymmetric_channel_information,
    binary_entropy,
    forward_marginals,
    P_CATCH,
)


class TestClosedForm(unittest.TestCase):
    def test_z_channel_endpoints(self):
        self.assertAlmostEqual(binary_entropy(0.5), 1.0)
        self.assertAlmostEqual(binary_entropy(0.0), 0.0)
        # A certainty is worth zero bits, and a perfect channel recovers all of it.
        self.assertAlmostEqual(asymmetric_channel_information(0.0, 1.0, 0.0), 0.0)
        self.assertAlmostEqual(asymmetric_channel_information(0.5, 1.0, 0.0), 1.0)
        # A flag never fires on a clean node, so the channel is asymmetric; at a low prior
        # "not flagged" is nearly conclusive, which is why the yield is a large share of
        # H(E) rather than a small one. It is still bounded by the entropy.
        low = asymmetric_channel_information(0.05, P_CATCH, 0.0)
        self.assertLessEqual(low, binary_entropy(0.05))
        self.assertGreater(low, 0.2)

    def test_marginals_are_bounded_and_monotone_in_base(self):
        graph = gen_real()
        base = np.array([graph.rates[graph.types[i]] for i in range(graph.n)])
        w = np.full((graph.n, graph.n), 0.5)
        p = forward_marginals(graph, base, w)
        self.assertTrue(np.all((p >= 0) & (p <= 1)))
        raised = base.copy()
        raised[0] = 1.0
        self.assertGreaterEqual(forward_marginals(graph, raised, w)[0], p[0])


class TestAccounting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from analyse_information_budget import analyse
        cls.results = [analyse(g, label="nominal") for g in (gen_real(), gen_ticket())]

    def test_zero_reach_nodes_have_zero_voi(self):
        for r in self.results:
            unreachable = [x for x in r["nodes"] if x["sink_reach"] == 0]
            self.assertTrue(unreachable)
            for x in unreachable:
                self.assertEqual(x["voi"], 0.0)
                self.assertEqual(x["delta"], 0.0)
                # ... while still carrying information about being wrong.
                self.assertGreater(x["information_bits"], 0.0)

    def test_repairable_information_is_a_lower_bound(self):
        for r in self.results:
            for x in r["nodes"]:
                self.assertLessEqual(
                    x["repairable_information_bits"], x["information_bits"] + 1e-12
                )

    def test_baseline_ranks_like_exact_voi_but_does_not_match_it(self):
        for r in self.results:
            self.assertGreater(r["spearman"]["voi_vs_marginal_baseline"], 0.6)
            # The magnitudes are not comparable, which is why it is a ranking only.
            self.assertGreater(r["max_abs_error_baseline_vs_exact_voi"], r["voi_range"][1])

    def test_information_ranking_is_not_the_value_ranking(self):
        for r in self.results:
            self.assertNotEqual(r["top1"]["by_information"], r["top1"]["by_voi"])
            self.assertLess(abs(r["spearman"]["information_vs_voi"]), 0.5)

    def test_budget_is_below_repairable_entropy(self):
        for r in self.results:
            bound = 8 * r["max_repairable_information_bits"]
            self.assertLess(bound, r["total_repairable_entropy_bits"])
            self.assertLess(bound / r["total_repairable_entropy_bits"], 0.6)


if __name__ == "__main__":
    unittest.main()
