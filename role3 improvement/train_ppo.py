"""PPO on the oversight environment, third learned baseline.

Pre-registered in ``PREREGISTER_PPO.md``: lr 3e-3, clip 0.2, four epochs per
update, gamma 1.0 with terminal-only returns, entropy 0.01, value coefficient
0.5, eight episodes per update, gradient clip 5.0, temperature fixed at 1.0.

The critic reads a mean pool of the same node embeddings the policy uses, and is
stored under ``critic_state`` rather than ``state_dict`` so that
``benchmark.load_policy`` keeps loading these checkpoints unchanged.

One step of an episode is one graph observation, so the update re-runs the
forward pass on the stored observation of each step. Batching whole episodes
would need a disjoint-edge block-diagonal graph, which the one-hop message
passing here does not support; per-step forwards are exact and cheap at 80
nodes.
"""
import argparse

import csv
import random
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

from dag_role3 import OversightEnv, generate_graph
from dag_role3.models import GNNScorer, child_mean, masked_action, torch_obs
from dag_role3.training import BestValidation

CLIP = 0.2
EPOCHS = 4
ENTROPY = 0.01
VALUE_COEF = 0.5
EPISODES_PER_UPDATE = 8
GRAD_CLIP = 5.0
TEMPERATURE = 1.0
BUDGET = {"spike": 16, "real": 8, "ticket": 8, "modular": 50,
          "ba": 50, "er": 50}


class ActorCritic(nn.Module):
    """GNNScorer policy with a value head on the pooled node embedding."""

    def __init__(self, input_dim, hidden=32):
        super().__init__()
        self.policy = GNNScorer(input_dim, hidden)
        self.critic = nn.Sequential(nn.Linear(hidden, hidden), nn.Tanh(),
                                    nn.Linear(hidden, 1))

    def forward(self, x, edges):
        agg = child_mean(x, edges)
        h = torch.tanh(self.policy.self_layer(x) + self.policy.neigh_layer(agg))
        return self.policy.out(h).squeeze(1), self.critic(h.mean(dim=0)).squeeze(0)


def log_prob_of(scores, mask, action):
    log_probs = torch.log_softmax(scores.masked_fill(~mask, -1e9), dim=-1)
    return log_probs.gather(0, action.view(())).squeeze(())


def entropy_of(scores, mask):
    log_probs = torch.log_softmax(scores.masked_fill(~mask, -1e9), dim=-1)
    legal = mask.float()
    return -(log_probs.exp() * log_probs * legal).sum()


def run_episode(agent, family, graph_seed, episode_seed, budget):
    """Sample one episode, keeping the observation of every step."""
    env = OversightEnv.from_seed(generate_graph(family, graph_seed),
                                 episode_seed, budget)
    obs = env.observation()
    steps = []
    while not env.done:
        x, edges, mask = torch_obs(obs)
        with torch.no_grad():
            scores, value = agent(x, edges)
            action, _ = masked_action(scores, mask, sample=True,
                                      temperature=TEMPERATURE)
            logp = log_prob_of(scores, mask, torch.tensor(action))
        steps.append({"x": x, "edges": edges, "mask": mask,
                      "action": torch.tensor(action), "logp": logp,
                      "value": value})
        obs, _, _, _ = env.step(action)
    return steps, -env.final_audit()["final_sink_errors"]


def update(agent, optim, steps):
    """Clipped surrogate over stored single-step observations."""
    returns = torch.tensor([s["return"] for s in steps], dtype=torch.float32)
    values = torch.stack([s["value"] for s in steps]).detach()
    advantages = returns - values
    advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
    old = torch.stack([s["logp"] for s in steps]).detach()
    last = None
    for _ in range(EPOCHS):
        policy_loss, value_loss, entropy = 0.0, 0.0, 0.0
        for step, adv, ret, reference in zip(steps, advantages, returns, old):
            scores, value = agent(step["x"], step["edges"])
            new = log_prob_of(scores, step["mask"], step["action"])
            ratio = torch.exp(new - reference)
            clipped = torch.clamp(ratio, 1 - CLIP, 1 + CLIP)
            policy_loss = policy_loss - torch.min(ratio * adv, clipped * adv)
            value_loss = value_loss + nn.functional.mse_loss(value, ret)
            entropy = entropy + entropy_of(scores, step["mask"])
        n = len(steps)
        total = policy_loss / n + VALUE_COEF * value_loss / n - ENTROPY * entropy / n
        optim.zero_grad()
        total.backward()
        torch.nn.utils.clip_grad_norm_(agent.parameters(), GRAD_CLIP)
        optim.step()
        last = (float(policy_loss / n), float(value_loss / n), float(entropy / n))
    return last


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--family", choices=list(BUDGET), default="spike")
    ap.add_argument("--episodes", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--eval-seeds", type=int, default=30)
    ap.add_argument("--lr", type=float, default=3e-3)
    ap.add_argument("--out", type=Path, default=Path("outputs/ppo"))
    args = ap.parse_args()
    if args.seed < 1 or args.episodes < EPISODES_PER_UPDATE:
        ap.error("need a positive seed and at least one full update")
    if args.lr != 3e-3:
        ap.error("learning rate is frozen at 3e-3 by PREREGISTER_PPO.md")
    args.out.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(1)
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    family, budget = args.family, BUDGET[args.family]
    input_dim = len(generate_graph(family, seed=1).rates) + 7
    agent = ActorCritic(input_dim)
    optim = torch.optim.Adam(agent.parameters(), lr=args.lr)
    validation = BestValidation(agent.policy, family, budget, args.eval_seeds)
    rng = random.Random(args.seed)
    history, episodes = [], 0

    while episodes < args.episodes:
        batch, returns = [], []
        for _ in range(min(EPISODES_PER_UPDATE, args.episodes - episodes)):
            graph_seed = args.seed * 1_000_000 + episodes
            steps, ret = run_episode(agent, family, graph_seed,
                                     40_000 + graph_seed, budget)
            for step in steps:
                step["return"] = ret
            batch += steps
            returns.append(ret)
            episodes += 1
        policy_loss, value_loss, entropy = update(agent, optim, batch)
        history.append({"episode": episodes, "policy_loss": policy_loss,
                        "value_loss": value_loss, "entropy": entropy,
                        "train_mean_sink_errors": float(np.mean(
                            [-r for r in returns]))})
        if episodes % 100 < EPISODES_PER_UPDATE:
            validation.check(agent.policy, episodes)
        if episodes % 200 == 0:
            print(f"episode {episodes:4d}: p_loss={policy_loss:+.3f} "
                  f"v_loss={value_loss:.3f} train_errors="
                  f"{history[-1]['train_mean_sink_errors']:.2f}", flush=True)

    agent.policy.load_state_dict(validation.state)
    # One directory per training seed, matching outputs/v3/train_{seed}.
    seed_dir = args.out / f"train_{args.seed}"
    seed_dir.mkdir(parents=True, exist_ok=True)
    with open(seed_dir / "ppo_observed_validation.csv", "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["episode", "mean_sink_errors"])
        writer.writeheader()
        writer.writerows(validation.rows)
    name = f"ppo_{family}_observed"
    torch.save({"state_dict": agent.policy.state_dict(), "family": family,
                "input_dim": input_dim, "seed": args.seed,
                "episodes": args.episodes, "algorithm": "gnn_ppo",
                "critic_state": agent.critic.state_dict(),
                **validation.metadata()}, seed_dir / f"{name}.pt")
    with open(seed_dir / f"{name}_train.csv", "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(history[0]))
        writer.writeheader()
        writer.writerows(history)
    print(f"selected episode {validation.episode}: validation {validation.best:.3f}")


if __name__ == "__main__":
    main()
