"""Invariants for the v2 belief comparison harness (no full runs here)."""
import json
import tempfile
import unittest
from pathlib import Path

import compare_belief_stdlib_v2 as C
import belief_stdlib as B


def report(impl_low=-0.04, impl_high=0.06, impl_share=0.15, noise_share=0.14, rank80=0.2, rank500=3.0, observe500=0.05):
    latency = {"80x10": dict(stdlib=dict(rank_all_s=rank80, observe_s=0.01), numpy=dict(rank_all_s=0.1, observe_s=0.01)),
               "500x20": dict(stdlib=dict(rank_all_s=rank500, observe_s=observe500),
                              numpy=dict(rank_all_s=2.0, observe_s=0.01))}
    return dict(equivalence=dict(
        implementation_difference=dict(mean=0.01, low=impl_low, high=impl_high, sd=0.8, differing_share=impl_share),
        noise_floor=dict(mean=0.0, low=-0.05, high=0.05, sd=0.8, differing_share=noise_share)), latency=latency)


class GateTests(unittest.TestCase):
    def test_passes_when_every_part_holds(self):
        self.assertTrue(C.evaluate_gate(report())["passed"])

    def test_each_part_can_fail(self):
        for kwargs in (dict(impl_low=-0.2), dict(impl_high=0.2), dict(impl_share=0.25), dict(rank80=0.6),
                       dict(rank500=6.0), dict(observe500=0.6)):
            self.assertFalse(C.evaluate_gate(report(**kwargs))["passed"], kwargs)

    def test_missing_latency_rows_fail(self):
        self.assertFalse(C.evaluate_gate(dict(report(), latency={}))["passed"])

    def test_the_noise_floor_allowance_is_relative_to_the_reseed(self):
        self.assertTrue(C.evaluate_gate(report(impl_share=0.30, noise_share=0.26))["passed"])
        self.assertFalse(C.evaluate_gate(report(impl_share=0.30, noise_share=0.20))["passed"])


class HelperTests(unittest.TestCase):
    def test_differing_share(self):
        self.assertEqual(C.differing_share([1, 2, 3, 4], [1, 2, 0, 0]), 0.5)

    def test_deeper_graphs_have_more_descendants_per_node(self):
        depths = {}
        for layers in (4, 10, 20):
            parents, topo, sinks, edge_prob = C.bench_graph(200, layers)
            belief = B.ParticleBelief(parents, topo, sinks, edge_prob, [0.1] * 200, 0.9, n_particles=64, seed=1)
            depths[layers] = C.mean_descendants(belief)
        self.assertLess(depths[4], depths[10])
        self.assertLess(depths[10], depths[20])

    def test_bench_graph_restores_the_simulator_configuration(self):
        import spike_active_selection as SP
        before = (SP.CFG["N"], SP.CFG["L"])
        C.bench_graph(120, 10)
        self.assertEqual((SP.CFG["N"], SP.CFG["L"]), before)


class CliTests(unittest.TestCase):
    def test_smoke_writes_reports_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            C.main(["--smoke", "--out-dir", str(Path(tmp, "a"))])
            data = json.loads(Path(tmp, "a", "results.json").read_text())
            self.assertEqual(set(data["equivalence"]["mean_errors"]), {"numpy", "numpy_reseed", "stdlib"})
            self.assertIn("noise_floor", data["equivalence"])
            self.assertTrue(Path(tmp, "a", "results.md").exists())
            with self.assertRaises(SystemExit):
                C.main(["--smoke", "--out-dir", str(Path(tmp, "a"))])

    def test_bad_arguments_and_reserved_seeds(self):
        for extra in (["--graphs", "0"], ["--particles", "100"], ["--layers", "1"], ["--sizes", "4"], ["--sizes", "80", "--layers", "24"],
                      ["--first-seed", "1900", "--graphs", "200"], ["--first-seed", "2100", "--graphs", "10"]):
            with self.assertRaises(SystemExit, msg=str(extra)):
                C.parse(["--out-dir", "x", *extra])
        C.parse(["--out-dir", "x", "--first-seed", "5000", "--graphs", "1000"])


if __name__ == "__main__":
    unittest.main()
