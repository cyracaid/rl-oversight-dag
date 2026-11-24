"""Check the planner against actual Role 3 flag/miss transitions on a small DAG."""

from dataclasses import replace
import math
from pathlib import Path
import unittest

import numpy as np

from planning_policy import PlanningPolicy

from _env import ensure_role3

ensure_role3()
from dag_role3 import DAG, OversightEnv, sample_episode
from dag_role3.policies import marginal_scores


class PlanningTest(unittest.TestCase):
    def test_both_hypothetical_outcomes_against_the_environment(self):
        # A parent with a larger ID than its child and a shared downstream sink.
        graph = DAG(parents=((4,), (), (0, 1), (1,), (), (2, 3), (3,)),
                    types=(0, 1, 2, 1, 0, 2, 1), rates=(0.4, 0.2, 0.6))
        ids = np.arange(graph.n)
        for seed, weight in ((11, 0.2), (19, 0.8), (27, 0.5)):
            snap = sample_episode(graph, seed)
            weights = np.array([weight, 1 - weight])
            models = ("normal", "noise")
            obs = [OversightEnv(graph, snap, 2, confidence_mode=m).observation() for m in models]
            planner = PlanningPolicy(obs[0])
            odds = math.log(weight / (1 - weight))
            base = weights @ np.stack([marginal_scores(o) for o in obs])
            first = np.argsort(-base, kind="stable")[:6]
            adaptive_values, fixed_values = {}, {}
            followup, fixed_followup = {}, {}
            for a in first:
                flag = np.clip([0.9 * float(o["features"][a, -4]) for o in obs], 1e-6, 1 - 1e-6)
                subsequent = ids[ids != a]
                gains = []
                for caught, likelihood in ((True, flag), (False, 1 - flag)):
                    # Only this reference test fixes hidden truth. Public initial beliefs
                    # stay identical, so step() supplies an independent branch oracle.
                    forced = replace(snap, source_errors=(caught,) * graph.n,
                                     review_uniforms=(0.0,) * graph.n,
                                     edge_coins=dict.fromkeys(snap.edge_coins, False))
                    joint_gain = np.zeros(graph.n)
                    for model, mass in zip(models, weights * likelihood):
                        env = OversightEnv(graph, forced, 2, confidence_mode=model)
                        after, _, _, info = env.step(a)
                        self.assertEqual(info["flagged"], caught)
                        joint_gain += mass * marginal_scores(after)
                    gains.append(joint_gain[subsequent])
                followup[a] = gains
                fixed_followup[a] = gains[0] + gains[1]
                adaptive_values[a] = base[a] + sum(g.max() for g in gains)
                fixed_values[a] = base[a] + fixed_followup[a].max()
            for mode, values in (("adaptive", adaptive_values), ("open_loop", fixed_values)):
                with self.subTest(seed=seed, mode=mode):
                    choice = planner.decide(*obs, odds, mode)
                    self.assertAlmostEqual(values[choice.action], max(values.values()), places=6)
                    self.assertAlmostEqual(base[choice.greedy_action], max(base), places=6)
                    second = ids[ids != choice.action].tolist()
                    if mode == "adaptive":
                        for node, gain in zip((choice.flag_next, choice.miss_next), followup[choice.action]):
                            self.assertAlmostEqual(gain[second.index(node)], gain.max(), places=6)
                    else:
                        gain = fixed_followup[choice.action]
                        self.assertEqual(choice.flag_next, choice.miss_next)
                        self.assertAlmostEqual(gain[second.index(choice.flag_next)], gain.max(), places=6)
                    expected_flag = sum(w * np.clip(0.9 * float(o["features"][choice.action, -4]),
                                                    1e-6, 1 - 1e-6) for w, o in zip(weights, obs))
                    self.assertAlmostEqual(choice.flag_prob, expected_flag)
            after = [OversightEnv(graph, snap, 2, confidence_mode=m).step(first[0])[0] for m in models]
            last = [planner.decide(*after, odds, mode) for mode in ("mixture", "open_loop", "adaptive")]
            self.assertEqual(len({choice.action for choice in last}), 1)
            self.assertNotEqual(last[0].action, first[0])
            self.assertTrue(all(choice.flag_next == choice.miss_next == -1 for choice in last))


if __name__ == "__main__":
    unittest.main()
