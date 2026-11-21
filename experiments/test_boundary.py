"""Scientific invariants for the boundary experiment harness."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import torch

import rl_boundary as B
from belief import ParticleBelief


class BoundaryTests(unittest.TestCase):
    def test_odds_scaling_is_legal(self):
        self.assertAlmostEqual(B.odds_scale(0.6, 2), 0.75)
        self.assertAlmostEqual(B.odds_scale(0.6, 0.5), 3 / 7)

    def test_bootstrap_preserves_pairing(self):
        result = B.paired_bootstrap([[2, 4, 6], [2, 4, 6]], [1, 3, 5], 100)
        self.assertEqual(result, {"mean": 1.0, "low": 1.0, "high": 1.0})

    def test_two_step_does_not_mutate_belief(self):
        belief = ParticleBelief([[], []], [0, 1], {0, 1}, {}, [.8, .2], .9, 128, 7)
        before = copy.deepcopy(belief)
        self.assertEqual(B.two_step_action(belief, [True, True], 1), belief.best_action([True, True]))
        # Both independent sinks get reviewed: no population-level unique order.
        self.assertIn(B.two_step_action(belief, [True, True], 2), [0, 1])
        np.testing.assert_array_equal(before.B, belief.B)
        self.assertEqual(before.rng.bit_generator.state, belief.rng.bit_generator.state)

    def test_environment_unchanged_by_wrong_model(self):
        left, _ = B.make_env(123, B.SCENARIOS["matched"])
        right, _ = B.make_env(123, B.SCENARIOS["prop_odds_x2"])
        for key in ("base", "coins", "conf", "nodes"):
            self.assertEqual(left[key], right[key])
        self.assertTrue(torch.equal(left["S"], right["S"]))

    def test_masked_kl_is_finite_and_differentiable(self):
        import rl_distill as D
        scores = torch.tensor([1., 2., 3.], requires_grad=True)
        kl = D.valid_kl(scores, scores.detach(), torch.tensor([False, True, False]), 1.)
        kl.backward()
        self.assertEqual(float(kl.detach()), 0.)
        self.assertTrue(torch.isfinite(scores.grad).all())

    def test_distill_cli_rejects_unsafe_arguments_and_overwrite(self):
        import subprocess, sys
        script = str(Path(__file__).with_name("rl_distill.py"))
        def run(*args):
            return subprocess.run([sys.executable, script, *args], capture_output=True, text=True)
        with tempfile.TemporaryDirectory() as tmp:
            self.assertNotEqual(run("--smoke").returncode, 0)  # --out-dir required
            self.assertNotEqual(run("--smoke", "--out", "x.json", "--out-dir", f"{tmp}/a").returncode, 0)
            self.assertNotEqual(run("--heldout", "999", "--out-dir", f"{tmp}/b").returncode, 0)
            self.assertNotEqual(run("--seeds", "1", "1", "--out-dir", f"{tmp}/c").returncode, 0)
            Path(tmp, "existing").mkdir()
            self.assertNotEqual(run("--smoke", "--out-dir", f"{tmp}/existing").returncode, 0)

    def test_distill_smoke_is_deterministic_and_writes_checkpoints(self):
        import subprocess, sys
        script = str(Path(__file__).with_name("rl_distill.py"))
        outs = []
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("a", "b"):
                out = Path(tmp, name)
                done = subprocess.run([sys.executable, script, "--smoke", "--out-dir", str(out)],
                                      capture_output=True, text=True)
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertTrue((out / "bc_1.pt").exists() and (out / "bc_ft_1.pt").exists())
                outs.append(json.loads((out / "results.json").read_text())["conditions"])
        self.assertEqual(outs[0], outs[1])

    def test_two_step_known_sink_values(self):
        belief = ParticleBelief([[], [], []], [0, 1, 2], {0, 1, 2}, {}, [1., 1., 0.], 1., 128, 1)
        self.assertEqual(B.two_step_action(belief, [True, True, True], 2), 0)

    def test_report_regenerates_from_json(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "results.json"
            B.write_report(path, {"config": {"bootstrap": 100}, "conditions": {
                "matched": {"belief greedy": [2, 3], "BC": [[1, 2], [1, 2]]}}})
            first = path.with_suffix(".md").read_text()
            B.render_report(path)
            self.assertEqual(first, path.with_suffix(".md").read_text())
            self.assertIn("-1.000", first)

    def test_saved_policy_reproduces_scores(self):
        with tempfile.TemporaryDirectory() as temp:
            old = B.SP.CFG["crn"]
            try:
                B.SP.CFG["crn"] = True
                torch.manual_seed(5)
                policy = B.GNNPolicy(d=B.M.DIM["static"])
                path = Path(temp) / "model.pt"
                B.save_policy(path, policy, "static", 5, "reinforce")
                loaded, meta = B.load_policy(path)
                env, _ = B.make_env(123, {})
                self.assertTrue(torch.equal(policy.score(env["S"], env["A"]),
                                            loaded.score(env["S"], env["A"])))
                self.assertEqual(meta["seed"], 5)
            finally:
                B.SP.CFG["crn"] = old


if __name__ == "__main__":
    unittest.main()
