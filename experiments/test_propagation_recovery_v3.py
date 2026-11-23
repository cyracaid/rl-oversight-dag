"""Invariants for the v3 propagation-recovery harness (no full runs here)."""
import json
import random
import tempfile
import unittest
from pathlib import Path

import rl_propagation_recovery as R1
import rl_propagation_recovery_v3 as V3
import spike_active_selection as SP
from test_propagation_recovery import CatchOne, tiny_graph


def ev(changed, total, family=1, indeg=1, reviewed_before=False, post=0.1):
    return [dict(family=family, indeg=indeg, changed=i < changed, reviewed_before=reviewed_before,
                 child_post=post, oracle_child_base=(i % 10 == 0)) for i in range(total)]


def merged_with(events, root_reviews=1000, root_flags=90, audit_reviews=100, audit_flags=10,
                frame="all_eligible"):
    return dict(events=events, root_reviews=root_reviews, root_flags=root_flags,
                audit_root_reviews=audit_reviews, audit_root_flags=audit_flags, inherited=0, cleared=0,
                audit_frame=frame)


class WilsonTests(unittest.TestCase):
    def test_values_and_monotonicity(self):
        self.assertAlmostEqual(V3.wilson_upper(0, 50), 0.0713, places=3)
        self.assertTrue(0.17 < V3.wilson_upper(4, 50) < 0.21)
        self.assertLess(V3.wilson_upper(2, 50), V3.wilson_upper(4, 50))
        self.assertLessEqual(V3.wilson_upper(50, 50), 1.0)


class OrderTests(unittest.TestCase):
    def setUp(self):
        self.graph = R1.build_world(5, 1, R1.DEFAULT_P)[0]

    def test_before_audit_is_first_and_the_policy_chooses_among_the_rest(self):
        order, true_frame, attested = V3.make_order("confidence", self.graph, 16, 0.25, random.Random(3))
        audit = [a for a, is_audit in order if is_audit]
        policy = [a for a, is_audit in order if not is_audit]
        self.assertEqual((len(audit), len(policy), len(set(a for a, _ in order))), (4, 12, 16))
        rest = sorted((i for i in range(80) if i not in set(audit)), key=lambda i: -self.graph["post"][i])
        self.assertEqual(policy, rest[:12])
        self.assertEqual((true_frame, attested), ("all_eligible", "all_eligible"))

    def test_after_reproduces_the_v2_flaw_and_labels_its_true_frame(self):
        order, true_frame, attested = V3.make_order("confidence", self.graph, 16, 0.25, random.Random(3),
                                                    audit_order="after")
        policy = [a for a, is_audit in order if not is_audit]
        audit = [a for a, is_audit in order if is_audit]
        top = sorted(range(80), key=lambda i: -self.graph["post"][i])[:12]
        self.assertEqual(policy, top)
        self.assertFalse(set(audit) & set(top))
        self.assertEqual((true_frame, attested), ("remaining", "remaining"))

    def test_mislabelled_attestation_is_possible_for_the_negative_control(self):
        _, true_frame, attested = V3.make_order("confidence", self.graph, 16, 0.25, random.Random(3),
                                                audit_order="after", attest_frame="all_eligible")
        self.assertEqual((true_frame, attested), ("remaining", "all_eligible"))

    def test_audit_before_is_unbiased_for_the_base_rate_and_after_is_not(self):
        world = R1.build_world(9, 150, R1.DEFAULT_P)

        def audited_base_rate(audit_order):
            hits = total = 0
            for g, graph in enumerate(world):
                order, _, _ = V3.make_order("confidence", graph, 16, 0.25, random.Random(g), audit_order)
                for a, is_audit in order:
                    if is_audit:
                        total += 1
                        hits += graph["base"][a]
            return hits / total
        before, after = audited_base_rate("before"), audited_base_rate("after")
        self.assertGreater(before, 0.07)   # population mean is 0.104
        self.assertLess(after, 0.06)       # depleted by the policy's selection
        self.assertGreater(before, after + 0.03)


class LogAndEstimatorTests(unittest.TestCase):
    def test_log_events_carry_observable_posterior_and_hidden_oracle_field(self):
        graph = tiny_graph([True, False, False])
        with CatchOne():
            log = V3.run_log(graph, [(0, False)], random.Random(0))
        self.assertEqual(log["events"][0]["child_post"], 0.5)
        self.assertIn("oracle_child_base", log["events"][0])

    def test_estimators_other_than_the_oracle_ignore_the_hidden_field(self):
        events = ev(30, 100)
        stripped = [{k: v for k, v in e.items() if k != "oracle_child_base"} for e in events]
        for estimator in ("E0", "E2", "E3a", "E3b", "E4"):
            a = V3.estimate(merged_with(events), 1, estimator, 0.9, 0.104, 300, 1)
            b = V3.estimate(merged_with(stripped), 1, estimator, 0.9, 0.104, 300, 1)
            self.assertEqual(a, b, estimator)

    def test_e4_per_child_adjustment(self):
        merged = merged_with([dict(family=1, indeg=1, changed=True, reviewed_before=False, child_post=0.0,
                                   oracle_child_base=False),
                              dict(family=1, indeg=1, changed=False, reviewed_before=False, child_post=0.5,
                                   oracle_child_base=False)])
        got = V3.estimate(merged, 1, "E4", 0.9, 0.104, 100, 1)
        self.assertAlmostEqual(got["mean"], 1 / 1.5, places=9)
        merged = merged_with(ev(27, 90, post=0.1))
        got = V3.estimate(merged, 1, "E4", 0.9, 0.104, 100, 1)
        self.assertAlmostEqual(got["mean"], 27 / (90 * 0.9), places=9)
        self.assertLess(got["low"], got["mean"])
        self.assertLess(got["mean"], got["high"])

    def test_oracle_diagnostic_does_use_the_hidden_rate(self):
        merged = merged_with(ev(30, 100))  # oracle base rate 0.10
        got = V3.estimate(merged, 1, "Eo", 0.9, 0.104, 2000, 1)
        self.assertAlmostEqual(got["mean"], (31 / 102) / 0.9, delta=0.03)

    def test_oracle_diagnostic_never_divides_by_zero(self):
        events = [dict(family=1, indeg=1, changed=False, reviewed_before=False, child_post=0.5,
                       oracle_child_base=True) for _ in range(10)]
        got = V3.estimate(merged_with(events), 1, "Eo", 0.9, 0.104, 50, 1)
        self.assertLessEqual(got["high"], 1.0)

    def test_audit_source_and_missing_audit(self):
        m = merged_with(ev(30, 100), root_flags=900, audit_flags=10)
        self.assertAlmostEqual(V3.estimate(m, 1, "E3b", 0.9, 0.104, 300, 1)["b_hat"], 0.10 / 0.9, places=6)
        self.assertGreater(V3.estimate(m, 1, "E2", 0.9, 0.104, 2000, 1)["mean"],
                           V3.estimate(m, 1, "E3b", 0.9, 0.104, 2000, 1)["mean"] + 0.2)
        none = merged_with(ev(30, 100), audit_reviews=0, audit_flags=0)
        self.assertIsNone(V3.estimate(none, 1, "E3b", 0.9, 0.104, 200, 1))


class LabelTests(unittest.TestCase):
    def label(self, estimator, b_hat=0.11, trials=200, n=150, frame="all_eligible", width=0.05):
        est = dict(n=n, k=1, mean=0.5, low=0.5 - width / 2, high=0.5 + width / 2, b_hat=b_hat, b_trials=trials)
        return V3.label_calibrated(estimator, est, dict(audit_frame=frame), 0.104, 2.0, 100, 100)

    def test_e3b_requires_frame_audit_size_and_a_consistent_flag_rate_in_both_directions(self):
        self.assertTrue(self.label("E3b"))
        self.assertFalse(self.label("E3b", frame="remaining"))          # frame not verified
        self.assertFalse(self.label("E3b", trials=99))                   # too few audited roots
        self.assertFalse(self.label("E3b", b_hat=0.483))                 # far above the prior
        self.assertFalse(self.label("E3b", b_hat=0.017))                 # far below the prior (the v2 flaw)
        self.assertFalse(self.label("E3b", n=99))                        # too few usable events

    def test_a_mislabelled_frame_is_still_caught_by_the_flag_rate_check(self):
        # attested all_eligible but the audit was drawn from the remaining nodes: b_hat is far too low
        self.assertFalse(self.label("E3b", frame="all_eligible", b_hat=0.017))

    def test_e2_uses_the_flag_rate_check_only(self):
        self.assertTrue(self.label("E2", frame="remaining", trials=1))
        self.assertFalse(self.label("E2", b_hat=0.453))

    def test_other_estimators_and_interval_width(self):
        self.assertTrue(self.label("E3a"))
        for estimator in ("E0", "E4", "Eo"):
            self.assertFalse(self.label(estimator))
        # width is not part of the label: a very wide interval is still labelled when the checks pass
        self.assertTrue(self.label("E3b", width=0.9))


def cell(mean, low, high, n=200, calibrated=True, usable=True):
    return dict(n=n, k=1, mean=mean, low=low, high=high, calibrated=calibrated, usable=usable)


def synthetic_replicates(per_key):
    reps = []
    for r in range(len(next(iter(per_key.values())))):
        rep = {}
        for policy in V3.POLICIES:
            est = {f"{e}|{f}": None for e in V3.ESTIMATORS for f in R1.DEFAULT_P}
            for (p, e, f), lst in per_key.items():
                if p == policy:
                    est[f"{e}|{f}"] = lst[r]
            rep[policy] = dict(estimates=est)
        reps.append(rep)
    return reps


class SummaryAndGateTests(unittest.TestCase):
    def test_summary_separates_usable_from_calibrated_and_adds_a_noise_aware_bound(self):
        cells = ([cell(0.6, 0.55, 0.65, calibrated=True) for _ in range(46)]
                 + [cell(0.9, 0.85, 0.89, calibrated=True) for _ in range(4)]  # 4 labelled and wrong
                 + [cell(0.6, 0.4, 0.8, calibrated=False, usable=False) for _ in range(10)])
        row = V3.summarise(synthetic_replicates({("random", "E3b", 2): cells}), R1.DEFAULT_P)["random|E3b|2"]
        self.assertAlmostEqual(row["calibrated_rate"], 50 / 60)
        self.assertAlmostEqual(row["wrong_given_calibrated"], 4 / 50)
        self.assertGreater(row["wrong_upper95"], 4 / 50)
        self.assertAlmostEqual(row["usable_rate"], 50 / 60)

    def summary(self, **override):
        s = {}
        for policy in V3.POLICIES:
            for fam, truth in R1.DEFAULT_P.items():
                s[f"{policy}|E3b|{fam}"] = dict(truth=truth, replicates=100, missing=0, bias=0.01, coverage=0.94,
                                                mean_n=150, calibrated_rate=0.95, wrong_upper95=0.12)
        for key, patch in override.items():
            s[key].update(patch)
        return s

    def test_primary_gate_passes_and_fails_on_each_part(self):
        self.assertTrue(V3.evaluate_gate(self.summary(), R1.DEFAULT_P)["passed"])
        for patch in (dict(bias=0.06), dict(coverage=0.89), dict(mean_n=99), dict(missing=1),
                      dict(calibrated_rate=0.5), dict(wrong_upper95=0.25), dict(wrong_upper95=None)):
            gate = V3.evaluate_gate(self.summary(**{"blast|E3b|3": patch}), R1.DEFAULT_P)
            self.assertFalse(gate["passed"], patch)

    def test_a_rule_that_never_labels_cannot_pass(self):
        gate = V3.evaluate_gate(self.summary(**{"random|E3b|1": dict(calibrated_rate=0.0, wrong_upper95=None)}),
                                R1.DEFAULT_P)
        self.assertFalse(gate["passed"])

    def test_negative_control(self):
        s = self.summary()
        for fam in R1.DEFAULT_P:
            s[f"confidence|E3b|{fam}"]["calibrated_rate"] = 0.0
        self.assertTrue(V3.evaluate_negative_control(s, R1.DEFAULT_P)["passed"])
        s["confidence|E3b|2"]["calibrated_rate"] = 0.4
        self.assertFalse(V3.evaluate_negative_control(s, R1.DEFAULT_P)["passed"])


class CliTests(unittest.TestCase):
    def run_smoke(self, tmp, name, *extra):
        V3.main(["--smoke", "--out-dir", str(Path(tmp, name)), *extra])
        return json.loads(Path(tmp, name, "results.json").read_text())

    def test_modes_determinism_and_overwrite(self):
        old = SP.CFG["p_catch"]
        try:
            with tempfile.TemporaryDirectory() as tmp:
                a = self.run_smoke(tmp, "a")
                b = self.run_smoke(tmp, "b")
                self.assertEqual(a["summary"], b["summary"])
                self.assertEqual(a["gate"]["mode"], "primary")
                self.assertTrue(Path(tmp, "a", "results.md").exists())
                neg = self.run_smoke(tmp, "n", "--audit-order", "after", "--attest-frame", "all_eligible")
                self.assertEqual(neg["gate"]["mode"], "negative_control")
                other = self.run_smoke(tmp, "o", "--audit-order", "after")
                self.assertEqual(other["gate"]["mode"], "none")
                self.assertIn("oracle_child_base", a)
                with self.assertRaises(SystemExit):
                    V3.main(["--smoke", "--out-dir", str(Path(tmp, "a"))])
        finally:
            SP.CFG["p_catch"] = old

    def test_bad_arguments_are_rejected(self):
        for extra in (["--audit-fraction", "1"], ["--prior-b", "0"], ["--graphs", "0"], ["--check-ratio", "1"],
                      ["--min-events", "0"], ["--obs-miss", "1"], ["--audit-order", "sideways"]):
            with self.assertRaises(SystemExit, msg=str(extra)):
                V3.parse(["--out-dir", "x", *extra])
        with self.assertRaises(SystemExit):
            V3.parse([])

    def test_world_and_policies_are_the_unchanged_v1_reference(self):
        self.assertIs(V3.R.build_world, R1.build_world)


if __name__ == "__main__":
    unittest.main()
