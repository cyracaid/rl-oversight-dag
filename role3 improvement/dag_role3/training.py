"""Shared validation, checkpoint metadata and public potential for training."""
import copy
import numpy as np
import torch
from . import OversightEnv, generate_graph
from .models import torch_obs, masked_action


FEATURE_SCHEMA = "type_confidence_reach_source_effective_reviewed_flagged_budget_v1"


def potential(obs):
    if obs["budget_left"] == 0:
        return 0.0
    k = obs["features"].shape[1] - 7
    return -float(obs["features"][obs["sink_ids"], k + 3].sum())


def replay_observation(obs):
    # Replay needs only model inputs. Do not duplicate node labels or diagnostics.
    return {key: obs[key] for key in ("features", "edge_index", "mask")}


@torch.inference_mode()
def evaluate(model, family, budget, count, static=False):
    errors = []
    for seed in range(60000, 60000 + count):
        env = OversightEnv.from_seed(generate_graph(family, seed), 300000 + seed, budget)
        obs = env.observation()
        while not env.done:
            x, edges, mask = torch_obs(obs, static=static)
            action = masked_action(model(x, edges), mask)[0]
            obs, _, _, _ = env.step(action)
        errors.append(env.final_audit()["final_sink_errors"])
    return float(np.mean(errors))


class BestValidation:
    def __init__(self, model, family, budget, count, static=False):
        self.family, self.budget, self.count, self.static = family, budget, count, static
        self.rows = []
        self.best = float("inf")
        self.episode = 0
        self.state = None
        self.check(model, 0)

    def check(self, model, episode):
        score = evaluate(model, self.family, self.budget, self.count, self.static)
        self.rows.append({"episode": episode, "mean_sink_errors": score})
        if score < self.best:
            self.best, self.episode = score, episode
            self.state = copy.deepcopy(model.state_dict())
        return score

    def metadata(self):
        return {"selected_episode": self.episode, "validation_mean": self.best,
                "validation_start": 60000, "validation_count": self.count,
                "feature_schema": FEATURE_SCHEMA, "format_version": 2}
