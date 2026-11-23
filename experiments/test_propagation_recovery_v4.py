"""Invariants for the v4 propagation-recovery harness (no full runs here)."""
import json
import random
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

import rl_propagation_recovery as R1
import rl_propagation_recovery_v4 as V4
import spike_active_selection as SP
from test_propagation_recovery import CatchOne, tiny_graph


def args(**over):
    base = dict(min_events=100, min_audit_roots=100, assumed_catch=0.9, calib_tol=0.04, balance_ratio=1.25,
                prior_b=0.104, check_ratio=2.0)
    base.update(over)
    return Namespace(**base)


def merged_with(root_reviews=200, root_flags=20, post_mean=0.10, frame="all_eligible"):
    return dict(events=[], audit_root_reviews=root_reviews, audit_root_flags=root_flags,
                audit_root_post_sum=post_mean * root_reviews, audit_frame=frame)


def est(n=150, child_post_mean=0.10, b_hat=0.11, b_trials=200):
    return dict(n=n, mean=0.5, low=0.4, high=0.6, child_post_mean=child_post_mean, b_hat=b_hat, b_trials=b_trials)


class ShiftTests(unittest.TestCase):
    def test_shift_is_identity_at_zero_monotone_and_moves_the_right_way(self):
        self.assertEqual(V4.shift_logit(0.1, 0), 0.1)
        values = [V4.shift_logit(p, 0.8) for p in (0.01, 0.1, 0.5, 0.9)]
        self.assertEqual(values, sorted(values))
        self.assertGreater(V4.shift_logit(0.1, 0.8), 0.1)
        self.assertLess(V4.shift_logit(0.1, -0.8), 0.1)
        self.assertTrue(0 < V4.shift_logit(0.0, 0.8) < 1 and 0 < V4.shift_logit(1.0, -0.8) < 1)


class CheckTests(unittest.TestCase):
    def test_calibration_check(self):
        self.assertTrue(V4.calibration_ok(merged_with(), 0.9, 0.04, 100))                  # 0.111 vs 0.10
        self.assertFalse(V4.calibration_ok(merged_with(post_mean=0.20), 0.9, 0.04, 100))   # inflated posterior
        self.assertFalse(V4.calibration_ok(merged_with(post_mean=0.02), 0.9, 0.04, 100))   # deflated posterior
        self.assertFalse(V4.calibration_ok(merged_with(root_reviews=99, root_flags=10), 0.9, 0.04, 100))

    def test_balance_ratio(self):
        self.assertAlmostEqual(V4.balance_ratio(merged_with(post_mean=0.104), est(child_post_mean=0.063)),
                               0.063 / 0.104)
        self.assertIsNone(V4.balance_ratio(merged_with(root_reviews=0, root_flags=0), est()))


class LabelTests(unittest.TestCase):
    def test_e4_needs_frame_calibration_and_events(self):
        self.assertTrue(V4.label_calibrated("E4", est(), merged_with(), args()))
        self.assertFalse(V4.label_calibrated("E4", est(), merged_with(frame="remaining"), args()))
        self.assertFalse(V4.label_calibrated("E4", est(), merged_with(post_mean=0.2), args()))
        self.assertFalse(V4.label_calibrated("E4", est(n=99), merged_with(), args()))

    def test_population_b_estimators_are_refused_when_children_are_depleted(self):
        depleted = est(child_post_mean=0.063)  # the v3 confidence-order situation
        for estimator in ("E2", "E3a", "E3b"):
            self.assertTrue(V4.label_calibrated(estimator, est(), merged_with(post_mean=0.104), args()), estimator)
            self.assertFalse(V4.label_calibrated(estimator, depleted, merged_with(post_mean=0.104), args()), estimator)

    def test_e3b_keeps_the_v3_checks_and_e2_the_flag_rate_check(self):
        m = merged_with(post_mean=0.104)
        self.assertFalse(V4.label_calibrated("E3b", est(), merged_with(post_mean=0.104, frame="remaining"), args()))
        self.assertFalse(V4.label_calibrated("E3b", est(b_hat=0.017), m, args()))
        self.assertFalse(V4.label_calibrated("E3b", est(b_trials=99), m, args()))
        self.assertFalse(V4.label_calibrated("E2", est(b_hat=0.453), m, args()))

    def test_other_estimators_and_width(self):
        for estimator in ("E0", "Eo"):
            self.assertFalse(V4.label_calibrated(estimator, est(), merged_with(), args()))
        wide = est()
        wide.update(low=0.0, high=1.0)
        self.assertTrue(V4.label_calibrated("E4", wide, merged_with(), args()))  # width is not a criterion


class LogTests(unittest.TestCase):
    def test_audited_root_posterior_and_child_posterior_are_logged_shifted(self):
        graph = tiny_graph([True, False, False])
        with CatchOne():
            plain = V4.run_log(graph, [(0, True)], random.Random(0))
            shifted = V4.run_log(graph, [(0, True)], random.Random(0), post_shift=0.8)
        self.assertEqual(plain["audit_root_post_sum"], 0.5)
        self.assertAlmostEqual(shifted["audit_root_post_sum"], V4.shift_logit(0.5, 0.8))
        self.assertAlmostEqual(shifted["events"][0]["child_post"], V4.shift_logit(0.5, 0.8))
        self.assertEqual((plain["audit_root_reviews"], plain["audit_root_flags"]), (1, 1))

    def test_policy_reviews_do_not_enter_the_audit_posterior_sum(self):
        with CatchOne():
            log = V4.run_log(tiny_graph([True, False, False]), [(0, False)], random.Random(0))
        self.assertEqual((log["audit_root_reviews"], log["audit_root_post_sum"]), (0, 0.0))


def parsed(*extra):
    ns, _ = V4.parse(["--out-dir", "x", "--graphs", "400", "--replicates", "1", "--draws", "100", *extra])
    return ns


class IntegrationTests(unittest.TestCase):
    def test_calibration_check_passes_when_calibrated_and_fails_under_a_shift(self):
        old = SP.CFG["p_catch"]
        try:
            ok = V4.one_replicate(0, parsed(), R1.DEFAULT_P)
            bad = V4.one_replicate(0, parsed("--post-shift", "1.5"), R1.DEFAULT_P)
        finally:
            SP.CFG["p_catch"] = old
        for policy in V4.POLICIES:
            self.assertTrue(ok[policy]["calibration_ok"], policy)
            self.assertFalse(bad[policy]["calibration_ok"], policy)

    def test_balance_check_refuses_population_b_estimators_under_confidence_but_not_random(self):
        rep = V4.one_replicate(0, parsed("--min-events", "20"), R1.DEFAULT_P)
        self.assertFalse(any(rep["confidence"]["estimates"][f"E3b|{f}"]["calibrated"] for f in (1, 2, 3)))
        self.assertTrue(any(rep["random"]["estimates"][f"E3b|{f}"]["calibrated"] for f in (1, 2, 3)))


def summary_with(**over):
    s = {}
    for policy in V4.POLICIES:
        for fam, truth in R1.DEFAULT_P.items():
            s[f"{policy}|E4|{fam}"] = dict(truth=truth, replicates=150, missing=0, bias=0.01, coverage=0.95,
                                           mean_n=150, calibrated_rate=0.95, wrong_upper95=0.10)
            s[f"{policy}|E3b|{fam}"] = dict(truth=truth, replicates=150, missing=0, bias=0.0, coverage=0.95,
                                            mean_n=150, wrong_upper95=0.1,
                                            calibrated_rate=0.0 if policy == "confidence" else 0.95)
    for key, patch in over.items():
        s[key].update(patch)
    return s


class GateTests(unittest.TestCase):
    def test_primary_gate_passes_and_fails_on_each_part(self):
        self.assertTrue(V4.evaluate_gate(summary_with(), R1.DEFAULT_P)["passed"])
        for patch in (dict(bias=0.06), dict(coverage=0.89), dict(mean_n=99), dict(missing=1),
                      dict(calibrated_rate=0.5), dict(wrong_upper95=0.25), dict(wrong_upper95=None)):
            gate = V4.evaluate_gate(summary_with(**{"blast|E4|3": patch}), R1.DEFAULT_P)
            self.assertFalse(gate["passed"], patch)

    def test_gate_requires_the_label_to_refuse_the_biased_estimator_and_to_accept_the_unbiased_one(self):
        gate = V4.evaluate_gate(summary_with(**{"confidence|E3b|2": dict(calibrated_rate=0.5)}), R1.DEFAULT_P)
        self.assertFalse(gate["passed"])
        gate = V4.evaluate_gate(summary_with(**{"random|E3b|1": dict(calibrated_rate=0.5)}), R1.DEFAULT_P)
        self.assertFalse(gate["passed"])

    def test_miscalibration_control(self):
        s = summary_with()
        for policy in V4.POLICIES:
            for fam in R1.DEFAULT_P:
                s[f"{policy}|E4|{fam}"]["calibrated_rate"] = 0.0
        self.assertTrue(V4.evaluate_miscalibration_control(s, R1.DEFAULT_P)["passed"])
        s["random|E4|2"]["calibrated_rate"] = 0.3
        self.assertFalse(V4.evaluate_miscalibration_control(s, R1.DEFAULT_P)["passed"])


class CliTests(unittest.TestCase):
    def run_smoke(self, tmp, name, *extra):
        V4.main(["--smoke", "--out-dir", str(Path(tmp, name)), *extra])
        return json.loads(Path(tmp, name, "results.json").read_text())

    def test_modes_determinism_and_overwrite(self):
        old = SP.CFG["p_catch"]
        try:
            with tempfile.TemporaryDirectory() as tmp:
                a, b = self.run_smoke(tmp, "a"), self.run_smoke(tmp, "b")
                self.assertEqual(a["summary"], b["summary"])
                self.assertEqual(a["gate"]["mode"], "primary")
                self.assertEqual(self.run_smoke(tmp, "m", "--post-shift", "1.5")["gate"]["mode"],
                                 "miscalibration_control")
                self.assertEqual(self.run_smoke(tmp, "n", "--post-shift", "-1.5")["gate"]["mode"],
                                 "miscalibration_control")
                self.assertEqual(self.run_smoke(tmp, "o", "--post-shift", "0.8")["gate"]["mode"], "none")
                self.assertEqual(self.run_smoke(tmp, "p", "--post-shift", "1.5", "--audit-order", "after")
                                 ["gate"]["mode"], "none")
                self.assertTrue(Path(tmp, "a", "results.md").exists())
                self.assertIn("Primary gate (E4)", Path(tmp, "a", "results.md").read_text())
                with self.assertRaises(SystemExit):
                    V4.main(["--smoke", "--out-dir", str(Path(tmp, "a"))])
        finally:
            SP.CFG["p_catch"] = old

    def test_bad_arguments_are_rejected(self):
        for extra in (["--calib-tol", "0"], ["--balance-ratio", "1"], ["--check-ratio", "1"], ["--graphs", "0"],
                      ["--audit-fraction", "1"], ["--prior-b", "0"], ["--obs-miss", "1"]):
            with self.assertRaises(SystemExit, msg=str(extra)):
                V4.parse(["--out-dir", "x", *extra])
        with self.assertRaises(SystemExit):
            V4.parse([])

    def test_earlier_versions_are_reused_not_redefined(self):
        self.assertIs(V4.V3.estimate, V4.V3.estimate)
        self.assertIs(V4.R.build_world, R1.build_world)


if __name__ == "__main__":
    unittest.main()
