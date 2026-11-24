"""Tests for the coverage receipt: definitions, the deletion test, frozen verdict."""
import unittest

from dag_role3.graphs import DAG
from dag_role3.supervisor import ancestor_sources, coverage_truth, receipt, score
from report_supervisor import verdict


def diamond():
    # 0 -> 1, 0 -> 2, 1 -> 3, 2 -> 3 ; 0 is the only source, 3 the only sink
    return DAG(parents=((), (0,), (0,), (1, 2)), types=(0, 0, 0, 0), rates=(0.2,),
               family="custom", sink_override=(3,))


def two_source():
    # sources 0 and 2 ; 1 <- 0 ; sink 3 <- 1, 2 ; sink 4 <- 2
    return DAG(parents=((), (0,), (), (1, 2), (2,)), types=(0, 0, 0, 0, 0),
               rates=(0.2,), family="custom", sink_override=(3, 4))


class TestCoverage(unittest.TestCase):
    def test_ancestor_sources_only_counts_sources(self):
        graph = diamond()
        self.assertEqual(ancestor_sources(graph), {3: frozenset({0})})

    def test_ancestor_sources_unions_branches(self):
        graph = two_source()
        self.assertEqual(ancestor_sources(graph)[3], frozenset({0, 2}))
        self.assertEqual(ancestor_sources(graph)[4], frozenset({2}))

    def test_vertex_cut_is_not_coverage(self):
        # reviewing the sink itself cannot remove an inherited error
        graph = diamond()
        self.assertEqual(coverage_truth(graph, [3])[3], "untouched")

    def test_partial_when_one_branch_reviewed(self):
        graph = two_source()
        self.assertEqual(coverage_truth(graph, [0, 1])[3], "partial")

    def test_inspected_needs_every_ancestor_source(self):
        graph = two_source()
        self.assertEqual(coverage_truth(graph, [0, 2])[3], "inspected")
        self.assertEqual(coverage_truth(graph, [2])[4], "inspected")

    def test_reviewed_node_without_path_is_not_coverage(self):
        graph = two_source()
        self.assertEqual(coverage_truth(graph, [0, 1])[4], "untouched")


class TestScore(unittest.TestCase):
    def setUp(self):
        self.graph = two_source()
        self.truth = {3: True, 4: False}

    def test_silent_has_no_numbers(self):
        scored = score(self.graph, [0, 1, 2], None, self.truth)
        self.assertEqual(scored["receipt"], "absent")
        self.assertIsNone(scored["declared_gap"])
        self.assertIsNone(scored["uninspected_errors"])

    def test_overclaim_calls_every_sink_inspected(self):
        scored = score(self.graph, [], receipt(self.graph, [], claim="overclaim"),
                       self.truth)
        self.assertEqual(scored["false_inspection"], 1)   # sink 3 is wrong
        self.assertEqual(scored["declared_gap"], 0)

    def test_honest_receipt_declares_the_gap(self):
        scored = score(self.graph, [], receipt(self.graph, []), self.truth)
        self.assertEqual(scored["declared_gap"], 1)
        self.assertEqual(scored["false_inspection"], 0)

    def test_false_and_declared_partition_residual_errors(self):
        for reviewed in ([], [0], [0, 1], [0, 1, 2]):
            scored = score(self.graph, reviewed, receipt(self.graph, reviewed),
                           self.truth)
            self.assertEqual(scored["false_inspection"] + scored["declared_gap"],
                             sum(self.truth.values()))

    def test_escalation_is_never_false_but_is_not_judged(self):
        statement = receipt(self.graph, [], escalated=[3, 4])
        scored = score(self.graph, [], statement, self.truth)
        self.assertEqual(scored["fidelity"], 1.0)
        self.assertEqual(scored["judged"], 0.0)

    def test_escalation_does_not_hide_a_claim_elsewhere(self):
        statement = receipt(self.graph, [], escalated=[4])
        scored = score(self.graph, [], statement, self.truth)
        self.assertEqual(scored["judged"], 0.5)
        self.assertEqual(scored["declared_gap"], 1)

    def test_overclaim_equals_residual_under_full_coverage(self):
        # every source reviewed: honest says inspected, and a missed catch is
        # still counted as a false inspection rather than hidden
        truth = {3: True, 4: True}
        scored = score(self.graph, [0, 1, 2], receipt(self.graph, [0, 1, 2]), truth)
        self.assertEqual(scored["false_inspection"], 2)
        self.assertEqual(scored["declared_gap"], 0)


class TestVerdict(unittest.TestCase):
    def test_frozen_table(self):
        self.assertEqual(verdict(p1_holds=False, declared_share=0.99), "decorative")
        self.assertEqual(verdict(p1_holds=True, declared_share=0.90), "load-bearing")
        self.assertEqual(verdict(p1_holds=True, declared_share=0.89), "weak")
        self.assertEqual(verdict(p1_holds=True, declared_share=None), "weak")


if __name__ == "__main__":
    unittest.main()
