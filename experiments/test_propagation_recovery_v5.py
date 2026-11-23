"""Invariants for the v5 propagation-recovery harness (no full runs here)."""
import json
import random
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

import rl_propagation_recovery as R1
import rl_propagation_recovery_v5 as V5
import spike_active_selection as SP
from test_propagation_recovery import CatchOne, tiny_graph


class ModeTests(unittest.TestCase):
    def test_modes_distort_the_logged_posterior_in_the_expected_direction(self):
        p = 0.1
        lp = lambda mode, t=0, uid=1: V5.logged_posterior(mode, p, t, uid)
        self.assertEqual(lp("cal"), p)
        self.assertGreater(lp("shift+1.5"), p)
        self.assertLess(lp("shift-1.5"), p)
        self.assertLess(lp("shift+0.8"), lp("shift+1.5"))
        self.assertGreater(lp("scale0.5"), p)          # under-confident: pulled toward 0.5
        self.assertLess(lp("scale2"), p)               # over-confident: pushed away from 0.5
        self.assertEqual(lp("type+1.5", t=2), p)       # confined to node types >= 3
        self.assertGreater(lp("type+1.5", t=3), p)
        for mode in V5.MODES:
            self.assertTrue(0.0 < lp(mode) < 1.0)

    def test_noise_is_deterministic_per_node_and_differs_between_nodes(self):
        a = V5.logged_posterior("noise1", 0.1, 0, 5)
        self.assertEqual(a, V5.logged_posterior("noise1", 0.1, 0, 5))
        self.assertNotEqual(a, V5.logged_posterior("noise1", 0.1, 0, 6))

    def test_unknown_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            V5.logged_posterior("sideways", 0.1, 0, 1)


def event(changed, post=0.1, typ=0, uid=1, indeg=1, family=1, reviewed_before=False):
    return dict(family=family, indeg=indeg, changed=changed, reviewed_before=reviewed_before, child_post=post,
                child_type=typ, child_uid=uid, oracle_child_base=False)


class EstimatorTests(unittest.TestCase):
    def test_e4_formula_and_filtering(self):
        events = [event(True, 0.0), event(False, 0.5)]
        got = V5.e4_estimate(events, 1, "cal")
        self.assertAlmostEqual(got["mean"], 1 / 1.5)
        events += [event(True, 0.0, indeg=2), event(True, 0.0, reviewed_before=True), event(True, 0.0, family=2)]
        self.assertEqual(V5.e4_estimate(events, 1, "cal")["n"], 2)
        self.assertIsNone(V5.e4_estimate([], 1, "cal"))

    def test_a_shifted_logged_posterior_changes_the_estimate(self):
        events = [event(i < 30, 0.1, uid=i) for i in range(100)]
        cal = V5.e4_estimate(events, 1, "cal")["mean"]
        up = V5.e4_estimate(events, 1, "shift+1.5")["mean"]
        self.assertGreater(up, cal)  # higher logged posterior shrinks the denominator


def audit_roots(n, post, flag_rate_of_base, seed=1):
    """Roots whose true base rate is `post` (a calibrated posterior) when flag_rate_of_base == 1."""
    rng = random.Random(seed)
    return [dict(post=post, type=0, uid=i, flag=rng.random() < post * 0.9 * flag_rate_of_base) for i in range(n)]


def exact_roots(n_low, flags_low, post_low, n_high, flags_high, post_high):
    low = [dict(post=post_low, type=0, uid=i, flag=i < flags_low) for i in range(n_low)]
    high = [dict(post=post_high, type=0, uid=10_000 + i, flag=i < flags_high) for i in range(n_high)]
    return low + high


class CheckTests(unittest.TestCase):
    kw = dict(assumed_catch=0.9, calib_tol=0.04, bin_tol=0.15, min_bin=30, min_audit_roots=100)

    def test_accepts_a_calibrated_posterior_and_refuses_a_shifted_one_with_a_reason(self):
        roots = audit_roots(2000, 0.1, 1.0)
        ok, detail = V5.calibration_check(roots, "cal", **self.kw)
        self.assertTrue(ok, detail)
        ok, detail = V5.calibration_check(roots, "shift+1.5", **self.kw)
        self.assertFalse(ok)
        self.assertEqual(detail["reason"], "global_not_equivalent")

    def test_too_few_audited_roots_is_a_refusal(self):
        ok, detail = V5.calibration_check(audit_roots(50, 0.1, 1.0), "cal", **self.kw)
        self.assertFalse(ok)
        self.assertEqual(detail["reason"], "too_few_audited_roots")

    def test_a_gross_miscalibration_inside_one_bin_is_caught_even_when_the_global_check_passes(self):
        # 960 low-posterior roots exactly calibrated; 40 high-posterior roots detect at half the claimed rate
        roots = exact_roots(960, 43, 0.05, 40, 18, 0.9)
        ok, detail = V5.calibration_check(roots, "cal", **self.kw)
        self.assertFalse(ok)
        self.assertEqual(detail["reason"], "high_bin_gross_miscalibration")
        # without the bin check the same data would have passed the global equivalence test
        ok_global, _ = V5.calibration_check(roots, "cal", assumed_catch=0.9, calib_tol=0.04, bin_tol=10.0,
                                            min_bin=30, min_audit_roots=100)
        self.assertTrue(ok_global)

    def test_the_check_is_evidence_based_so_more_data_makes_acceptance_easier(self):
        small = V5.calibration_check(audit_roots(150, 0.1, 1.0, seed=3), "cal", **self.kw)[1]
        large = V5.calibration_check(audit_roots(3000, 0.1, 1.0, seed=3), "cal", **self.kw)[1]
        self.assertGreater(small["se"], large["se"])


class LabelTests(unittest.TestCase):
    def test_label_needs_events_frame_and_a_passed_check_and_not_width(self):
        args = Namespace(min_events=100)
        est = dict(n=150, mean=0.5, low=0.0, high=1.0)  # very wide interval
        merged = dict(audit_frame="all_eligible")
        self.assertTrue(V5.label_calibrated(est, merged, True, args))
        self.assertFalse(V5.label_calibrated(est, merged, False, args))
        self.assertFalse(V5.label_calibrated(est, dict(audit_frame="remaining"), True, args))
        self.assertFalse(V5.label_calibrated(dict(est, n=99), merged, True, args))
        self.assertFalse(V5.label_calibrated(None, merged, True, args))


class LogTests(unittest.TestCase):
    def test_log_carries_true_posterior_type_uid_and_audit_roots(self):
        graph = tiny_graph([True, False, False])
        graph["nodes"][1]["type"] = 3
        with CatchOne():
            log = V5.run_log(graph, [(0, True)], random.Random(0), uid_base=1000)
        self.assertEqual(log["audit_roots"], [dict(post=0.5, type=0, uid=1000, flag=True)])
        self.assertEqual((log["events"][0]["child_type"], log["events"][0]["child_uid"]), (3, 1001))
        with CatchOne():
            log = V5.run_log(tiny_graph([True, False, False]), [(0, False)], random.Random(0), uid_base=0)
        self.assertEqual(log["audit_roots"], [])


def table_and_checks(**over):
    table, checks = {}, {}
    for policy in V5.POLICIES:
        for mode in V5.MODES:
            checks[f"{policy}|{mode}"] = dict(pass_rate=0.97 if mode == "cal" else 0.02, refusal_reasons={})
            for fam, truth in R1.DEFAULT_P.items():
                table[f"{policy}|E4|{mode}|{fam}"] = dict(
                    truth=truth, replicates=150, missing=0, bias=0.01 if mode == "cal" else 0.08, coverage=0.95,
                    mean_n=150, calibrated_rate=0.95, wrong_upper95=0.10)
    for key, patch in over.items():
        target = checks if key in checks else table
        target[key].update(patch)
    return table, checks


class GateTests(unittest.TestCase):
    def test_passes_when_e4_is_good_checks_are_reliable_and_harmful_modes_are_refused(self):
        table, checks = table_and_checks()
        gate = V5.evaluate_gate(table, checks, R1.DEFAULT_P)
        self.assertTrue(gate["passed"])
        self.assertTrue(all(h["harmful"] for h in gate["harmful_modes"].values()))

    def test_each_part_can_fail(self):
        for patch in ({"random|E4|cal|1": dict(bias=0.06)}, {"blast|E4|cal|3": dict(coverage=0.88)},
                      {"confidence|E4|cal|2": dict(calibrated_rate=0.5)}, {"random|cal": dict(pass_rate=0.85)},
                      {"blast|shift+1.5": dict(pass_rate=0.3)}):
            table, checks = table_and_checks(**patch)
            self.assertFalse(V5.evaluate_gate(table, checks, R1.DEFAULT_P)["passed"], patch)

    def test_a_benign_mode_is_not_required_to_be_refused(self):
        table, checks = table_and_checks()
        for policy in V5.POLICIES:
            for fam in R1.DEFAULT_P:
                table[f"{policy}|E4|noise1|{fam}"]["bias"] = 0.02       # benign by the pre-registered rule
            checks[f"{policy}|noise1"]["pass_rate"] = 0.9               # accepted often, which is fine
        gate = V5.evaluate_gate(table, checks, R1.DEFAULT_P)
        self.assertTrue(gate["passed"])
        self.assertFalse(gate["harmful_modes"]["noise1"]["harmful"])

    def test_a_harmful_mode_that_slips_through_fails_the_gate(self):
        table, checks = table_and_checks()
        for fam in R1.DEFAULT_P:
            table[f"random|E4|type+1.5|{fam}"]["bias"] = 0.07
        checks["random|type+1.5"]["pass_rate"] = 0.6
        self.assertFalse(V5.evaluate_gate(table, checks, R1.DEFAULT_P)["passed"])


def parsed(*extra):
    ns, _ = V5.parse(["--out-dir", "x", "--graphs", "800", "--replicates", "1", "--draws", "50", *extra])
    return ns


class IntegrationTests(unittest.TestCase):
    def test_check_accepts_the_correct_posterior_and_refuses_a_harmful_shift_on_simulated_logs(self):
        old = SP.CFG["p_catch"]
        try:
            rep = V5.one_replicate(0, parsed(), R1.DEFAULT_P)
        finally:
            SP.CFG["p_catch"] = old
        for policy in V5.POLICIES:
            checks = rep[policy]["checks"]
            self.assertTrue(checks["cal"]["passed"], (policy, checks["cal"]))
            self.assertFalse(checks["shift+1.5"]["passed"], policy)


class CliTests(unittest.TestCase):
    def test_smoke_modes_determinism_and_overwrite(self):
        old = SP.CFG["p_catch"]
        try:
            with tempfile.TemporaryDirectory() as tmp:
                for name in ("a", "b"):
                    V5.main(["--smoke", "--out-dir", str(Path(tmp, name))])
                a = json.loads(Path(tmp, "a", "results.json").read_text())
                b = json.loads(Path(tmp, "b", "results.json").read_text())
                self.assertEqual(a["summary"], b["summary"])
                self.assertEqual(a["checks"], b["checks"])
                self.assertEqual(a["gate"]["mode"], "primary")
                self.assertIn("Calibration check", Path(tmp, "a", "results.md").read_text())
                V5.main(["--smoke", "--audit-order", "after", "--out-dir", str(Path(tmp, "n"))])
                self.assertEqual(json.loads(Path(tmp, "n", "results.json").read_text())["gate"]["mode"], "none")
                with self.assertRaises(SystemExit):
                    V5.main(["--smoke", "--out-dir", str(Path(tmp, "a"))])
        finally:
            SP.CFG["p_catch"] = old

    def test_bad_arguments_are_rejected(self):
        for extra in (["--calib-tol", "0"], ["--bin-tol", "0"], ["--min-bin", "0"], ["--graphs", "0"],
                      ["--audit-fraction", "1"], ["--prior-b", "0"], ["--obs-miss", "1"]):
            with self.assertRaises(SystemExit, msg=str(extra)):
                V5.parse(["--out-dir", "x", *extra])
        with self.assertRaises(SystemExit):
            V5.parse([])


if __name__ == "__main__":
    unittest.main()
