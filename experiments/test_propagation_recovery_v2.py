"""Invariants for the v2 propagation-recovery harness (no full runs here)."""
import json
import random
import tempfile
import unittest
from pathlib import Path

import rl_propagation_recovery as R1
import rl_propagation_recovery_v2 as V2
import spike_active_selection as SP
from test_propagation_recovery import CatchOne, tiny_graph


def events(changed, total, family=1, indeg=1, reviewed_before=False):
    return [dict(family=family, indeg=indeg, changed=i < changed, reviewed_before=reviewed_before)
            for i in range(total)]


def merged_with(ev, root_reviews=1000, root_flags=90, audit_reviews=100, audit_flags=10):
    return dict(events=ev, root_reviews=root_reviews, root_flags=root_flags,
                audit_root_reviews=audit_reviews, audit_root_flags=audit_flags, inherited=0, cleared=0)


class BudgetTests(unittest.TestCase):
    def test_split(self):
        self.assertEqual(V2.split_budget(16, 0.25), (12, 4))
        self.assertEqual(V2.split_budget(16, 0.0), (16, 0))
        self.assertEqual(V2.split_budget(1, 0.5), (1, 0))  # never leave the policy with no review

    def test_audit_nodes_are_disjoint_from_policy_nodes_and_total_is_the_budget(self):
        graph = R1.build_world(5, 1, R1.DEFAULT_P)[0]
        for policy in V2.POLICIES:
            order = V2.make_order(policy, graph, 16, 0.25, random.Random(3))
            nodes = [a for a, _ in order]
            self.assertEqual(len(order), 16)
            self.assertEqual(len(set(nodes)), 16)
            self.assertEqual(sum(1 for _, audit in order if audit), 4)

    def test_policy_part_matches_the_v1_policy(self):
        graph = R1.build_world(5, 1, R1.DEFAULT_P)[0]
        order = V2.make_order("confidence", graph, 16, 0.25, random.Random(3))
        policy_part = [a for a, audit in order if not audit]
        self.assertEqual(policy_part, R1.policy_order("confidence", graph, 12, random.Random(3)))


class LogTests(unittest.TestCase):
    def test_audit_root_counts_only_count_audit_reviews_of_roots(self):
        with CatchOne():
            log = V2.run_log(tiny_graph([True, False, False]), [(0, True), (1, False)], random.Random(0))
        self.assertEqual((log["root_reviews"], log["audit_root_reviews"], log["audit_root_flags"]), (1, 1, 1))
        with CatchOne():
            log = V2.run_log(tiny_graph([True, False, False]), [(0, False)], random.Random(0))
        self.assertEqual((log["root_reviews"], log["audit_root_reviews"], log["audit_root_flags"]), (1, 0, 0))

    def test_events_match_v1_semantics_and_world_is_not_mutated(self):
        graph = tiny_graph([True, False, False])
        base_before = list(graph["base"])
        with CatchOne():
            log = V2.run_log(graph, [(0, False)], random.Random(0))
        self.assertEqual(log["events"], [dict(family=1, indeg=1, changed=True, reviewed_before=False)])
        self.assertEqual(graph["base"], base_before)


class EstimatorTests(unittest.TestCase):
    def test_prior_source_uses_the_given_b(self):
        m = merged_with(events(30, 100))
        got = V2.estimate(m, 1, "E3a", 0.9, 0.10, 2000, 1)
        self.assertAlmostEqual(got["mean"], (31 / 102) / 0.90, delta=0.03)

    def test_audit_source_uses_only_audit_counts(self):
        m = merged_with(events(30, 100), root_reviews=1000, root_flags=900, audit_reviews=100, audit_flags=10)
        e3b = V2.estimate(m, 1, "E3b", 0.9, 0.10, 2000, 1)
        e2 = V2.estimate(m, 1, "E2", 0.9, 0.10, 2000, 1)
        self.assertAlmostEqual(e3b["b_hat"], 0.10 / 0.9, places=6)
        self.assertGreater(e2["mean"], e3b["mean"] + 0.2)  # selected roots inflate b and the estimate

    def test_no_audit_roots_means_no_estimate_not_a_fake_one(self):
        m = merged_with(events(30, 100), audit_reviews=0, audit_flags=0)
        self.assertIsNone(V2.estimate(m, 1, "E3b", 0.9, 0.10, 200, 1))
        self.assertIsNotNone(V2.estimate(m, 1, "E3a", 0.9, 0.10, 200, 1))

    def test_e0_uses_all_children_and_ignores_b(self):
        m = merged_with(events(10, 40) + events(40, 40, indeg=2) + events(40, 40, reviewed_before=True))
        self.assertEqual(V2.estimate(m, 1, "E0", 0.9, 0.10, 200, 1)["n"], 120)
        self.assertEqual(V2.estimate(m, 1, "E3b", 0.9, 0.10, 200, 1)["n"], 40)

    def test_selection_check(self):
        self.assertFalse(V2.selection_check("E2", dict(b_hat=0.483), 0.104, 2.0, 100))
        self.assertTrue(V2.selection_check("E2", dict(b_hat=0.107), 0.104, 2.0, 100))
        self.assertFalse(V2.selection_check("E3b", dict(b_trials=99), 0.104, 2.0, 100))
        self.assertTrue(V2.selection_check("E3b", dict(b_trials=100), 0.104, 2.0, 100))


def synthetic_replicates(per_key):
    """Replicates where every estimate is None except those given in per_key[(policy, estimator, family)]."""
    reps = []
    for r in range(len(next(iter(per_key.values())))):
        rep = {}
        for policy in V2.POLICIES:
            est = {f"{e}|{f}": None for e in V2.ESTIMATORS for f in R1.DEFAULT_P}
            for (p, e, f), lst in per_key.items():
                if p == policy:
                    est[f"{e}|{f}"] = lst[r]
            rep[policy] = dict(estimates=est)
        reps.append(rep)
    return reps


def cell(mean, low, high, n=200, cal_width=True, cal_robust=True):
    return dict(n=n, k=1, mean=mean, low=low, high=high, cal_width=cal_width, cal_robust=cal_robust)


class SummaryAndGateTests(unittest.TestCase):
    def test_width_only_rule_accepts_narrow_wrong_estimates_but_robust_rule_does_not(self):
        wrong = [cell(0.99, 0.97, 1.0, cal_width=True, cal_robust=False) for _ in range(10)]
        reps = synthetic_replicates({("confidence", "E2", 2): wrong})
        row = V2.summarise(reps, R1.DEFAULT_P)["confidence|E2|2"]
        self.assertEqual(row["calibrated_width_rate"], 1.0)
        self.assertEqual(row["wrong_given_calibrated_width"], 1.0)
        self.assertEqual(row["calibrated_robust_rate"], 0.0)
        self.assertIsNone(row["wrong_given_calibrated_robust"])
        self.assertEqual(row["coverage"], 0.0)

    def make_summary(self, **override):
        summary = {}
        for policy in V2.POLICIES:
            for fam, truth in R1.DEFAULT_P.items():
                summary[f"{policy}|E3b|{fam}"] = dict(
                    truth=truth, replicates=50, missing=0, bias=0.01, coverage=0.94, mean_n=150,
                    wrong_given_calibrated_robust=0.02)
        for key, patch in override.items():
            summary[key].update(patch)
        return summary

    def test_gate_passes_when_every_cell_passes(self):
        self.assertTrue(V2.evaluate_gate(self.make_summary(), R1.DEFAULT_P)["passed"])

    def test_gate_fails_on_each_criterion(self):
        for patch in (dict(bias=0.06), dict(coverage=0.88), dict(mean_n=99), dict(missing=1),
                      dict(wrong_given_calibrated_robust=0.10)):
            gate = V2.evaluate_gate(self.make_summary(**{"blast|E3b|3": patch}), R1.DEFAULT_P)
            self.assertFalse(gate["passed"], patch)

    def test_gate_treats_a_missing_estimate_as_a_failure(self):
        summary = self.make_summary()
        summary["random|E3b|1"] = dict(truth=0.3, replicates=50, missing=50)
        self.assertFalse(V2.evaluate_gate(summary, R1.DEFAULT_P)["passed"])

    def test_gate_does_not_penalise_a_cell_with_no_calibrated_label(self):
        summary = self.make_summary(**{"random|E3b|1": dict(wrong_given_calibrated_robust=None)})
        self.assertTrue(V2.evaluate_gate(summary, R1.DEFAULT_P)["passed"])


class CliTests(unittest.TestCase):
    def test_smoke_is_deterministic_and_refuses_overwrite(self):
        old = SP.CFG["p_catch"]
        try:
            with tempfile.TemporaryDirectory() as tmp:
                for name in ("a", "b"):
                    V2.main(["--smoke", "--out-dir", str(Path(tmp, name))])
                a = json.loads(Path(tmp, "a", "results.json").read_text())
                b = json.loads(Path(tmp, "b", "results.json").read_text())
                self.assertEqual(a["summary"], b["summary"])
                self.assertIn("gate", a)
                self.assertIn("provenance", a)
                self.assertTrue(Path(tmp, "a", "results.md").exists())
                self.assertIn("Gate (E3b)", Path(tmp, "a", "results.md").read_text())
                with self.assertRaises(SystemExit):
                    V2.main(["--smoke", "--out-dir", str(Path(tmp, "a"))])
        finally:
            SP.CFG["p_catch"] = old

    def test_bad_arguments_are_rejected(self):
        for extra in (["--audit-fraction", "1"], ["--prior-b", "0"], ["--prior-b", "0.95"],
                      ["--graphs", "0"], ["--width-threshold", "0"], ["--obs-miss", "1"],
                      ["--assumed-catch", "0"], ["--min-audit-roots", "0"]):
            with self.assertRaises(SystemExit, msg=str(extra)):
                V2.parse(["--out-dir", "x", *extra])
        with self.assertRaises(SystemExit):
            V2.parse([])

    def test_v1_module_is_the_unchanged_reference(self):
        # v2 must reuse v1 world construction and policies rather than redefine them.
        self.assertIs(V2.R.build_world, R1.build_world)
        self.assertIs(V2.R.policy_order, R1.policy_order)


if __name__ == "__main__":
    unittest.main()
