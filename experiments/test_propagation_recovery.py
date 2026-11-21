"""Invariants for the propagation-recovery harness (no full runs here)."""
import copy
import json
import random
import tempfile
import unittest
from pathlib import Path

import rl_propagation_recovery as R
import spike_active_selection as SP


def tiny_graph(base):
    """u(0) -> v(1) -> w(2); every edge transmits."""
    nodes = [dict(layer=0, type=0, parents=[]),
             dict(layer=1, type=0, parents=[0]),
             dict(layer=2, type=0, parents=[1])]
    return dict(nodes=nodes, topo=[0, 1, 2], coins={(0, 1): True, (1, 2): True},
                children={0: [1], 1: [2], 2: []}, base=list(base), sink_reach=[1, 1, 1],
                post=[.5, .5, .5])


class CatchOne:
    """Force the reviewer to catch every error for deterministic log tests."""
    def __enter__(self):
        self.old = SP.CFG["p_catch"]
        SP.CFG["p_catch"] = 1.0

    def __exit__(self, *exc):
        SP.CFG["p_catch"] = self.old


class LogTests(unittest.TestCase):
    def test_source_error_cleared_and_child_changes(self):
        with CatchOne():
            log = R.run_log(tiny_graph([True, False, False]), [0], random.Random(0))
        self.assertEqual((log["cleared"], log["inherited"]), (1, 0))
        self.assertEqual(log["events"],
                         [dict(family=1, indeg=1, changed=True, reviewed_before=False)])

    def test_inherited_error_is_flagged_but_not_cleared_and_gives_no_event(self):
        with CatchOne():
            log = R.run_log(tiny_graph([True, False, False]), [1], random.Random(0))
        self.assertEqual((log["cleared"], log["inherited"], log["events"]), (0, 1, []))

    def test_child_with_own_error_does_not_change(self):
        with CatchOne():
            log = R.run_log(tiny_graph([True, True, False]), [0], random.Random(0))
        self.assertEqual(log["events"],
                         [dict(family=1, indeg=1, changed=False, reviewed_before=False)])

    def test_reviewed_before_is_recorded(self):
        with CatchOne():
            log = R.run_log(tiny_graph([True, True, False]), [1, 0], random.Random(0))
        self.assertEqual(log["inherited"], 1)  # v flagged first but still wrong via u
        self.assertEqual(log["events"],
                         [dict(family=1, indeg=1, changed=True, reviewed_before=True)])

    def test_run_log_does_not_mutate_the_world(self):
        graph = tiny_graph([True, True, False])
        before = copy.deepcopy(graph)
        with CatchOne():
            R.run_log(graph, [0, 1, 2], random.Random(0))
        self.assertEqual(graph, before)

    def test_roots_are_counted_for_the_base_rate(self):
        with CatchOne():
            log = R.run_log(tiny_graph([True, False, False]), [0, 1], random.Random(0))
        self.assertEqual((log["root_reviews"], log["root_flags"]), (1, 1))


class EstimatorTests(unittest.TestCase):
    def events(self, changed, total, reviewed_before=False, indeg=1, family=1):
        return [dict(family=family, indeg=indeg, changed=i < changed,
                     reviewed_before=reviewed_before) for i in range(total)]

    def test_naive_and_adjusted_estimates(self):
        ev = self.events(30, 100)
        e0 = R.estimate_family(ev, 1, "E0", 1000, 0, 0.9, 2000, 1)
        self.assertAlmostEqual(e0["mean"], 31 / 102, delta=0.02)
        self.assertLess(e0["low"], e0["mean"])
        self.assertLess(e0["mean"], e0["high"])
        # 90 flags in 1000 root reviews at catch 0.9 -> b_hat ~ 0.1 -> p ~ q / 0.9
        e1 = R.estimate_family(ev, 1, "E1", 1000, 90, 0.9, 2000, 1)
        self.assertAlmostEqual(e1["mean"], (31 / 102) / 0.9, delta=0.03)

    def test_e1_drops_multi_parent_children_and_e2_drops_reviewed_before(self):
        ev = (self.events(10, 40) + self.events(40, 40, indeg=2)
              + self.events(40, 40, reviewed_before=True))
        self.assertEqual(R.estimate_family(ev, 1, "E0", 100, 0, 0.9, 200, 1)["n"], 120)
        self.assertEqual(R.estimate_family(ev, 1, "E1", 100, 0, 0.9, 200, 1)["n"], 80)
        self.assertEqual(R.estimate_family(ev, 1, "E2", 100, 0, 0.9, 200, 1)["n"], 40)

    def test_no_events_returns_none_not_a_fake_estimate(self):
        self.assertIsNone(R.estimate_family([], 1, "E1", 100, 5, 0.9, 200, 1))
        self.assertIsNone(R.estimate_family(self.events(5, 10, family=2), 1, "E0", 100, 5, 0.9, 200, 1))

    def test_estimate_is_deterministic_for_a_seed(self):
        ev = self.events(12, 50)
        a = R.estimate_family(ev, 1, "E2", 200, 10, 0.9, 500, 7)
        b = R.estimate_family(ev, 1, "E2", 200, 10, 0.9, 500, 7)
        self.assertEqual(a, b)


class WorldTests(unittest.TestCase):
    def test_edge_coin_rate_matches_family_probability(self):
        world = R.build_world(1, 150, R.DEFAULT_P)
        for fam, p in R.DEFAULT_P.items():
            coins = [c for g in world for (src, dst), c in g["coins"].items()
                     if g["nodes"][dst]["layer"] == fam]
            self.assertGreater(len(coins), 2000)
            self.assertAlmostEqual(sum(coins) / len(coins), p, delta=0.06)

    def test_world_is_deterministic(self):
        a = R.build_world(3, 5, R.DEFAULT_P)
        b = R.build_world(3, 5, R.DEFAULT_P)
        self.assertEqual(a, b)

    def test_policy_orders_are_unique_and_budgeted(self):
        graph = R.build_world(2, 1, R.DEFAULT_P)[0]
        for name in R.POLICIES:
            order = R.policy_order(name, graph, 16, random.Random(0))
            self.assertEqual(len(order), 16)
            self.assertEqual(len(set(order)), 16)
        blast = R.policy_order("blast", graph, 16, random.Random(0))
        reach = [graph["sink_reach"][i] for i in blast]
        self.assertEqual(reach, sorted(reach, reverse=True))


class CliTests(unittest.TestCase):
    def test_smoke_is_deterministic_writes_reports_and_refuses_overwrite(self):
        old = SP.CFG["p_catch"]
        try:
            with tempfile.TemporaryDirectory() as tmp:
                for name in ("a", "b"):
                    R.main(["--smoke", "--out-dir", str(Path(tmp, name))])
                a = json.loads(Path(tmp, "a", "results.json").read_text())
                b = json.loads(Path(tmp, "b", "results.json").read_text())
                self.assertEqual(a["summary"], b["summary"])
                self.assertTrue(Path(tmp, "a", "results.md").exists())
                self.assertIn("provenance", a)
                with self.assertRaises(SystemExit):
                    R.main(["--smoke", "--out-dir", str(Path(tmp, "a"))])
        finally:
            SP.CFG["p_catch"] = old

    def test_bad_arguments_are_rejected(self):
        for argv in (["--smoke"], ["--smoke", "--out-dir", "x", "--assumed-catch", "0"],
                     ["--smoke", "--out-dir", "x", "--obs-miss", "1"],
                     ["--out-dir", "x", "--graphs", "0"]):
            with self.assertRaises(SystemExit):
                R.parse(argv)


if __name__ == "__main__":
    unittest.main()
