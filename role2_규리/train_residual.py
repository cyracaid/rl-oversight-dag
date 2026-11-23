"""Learn a bounded correction to the public marginal score using terminal sink errors."""

import argparse
import copy
from functools import partial
import json
import math
from pathlib import Path
import platform
from statistics import mean

import numpy as np
import torch
from torch import nn

from evaluate_conditions import ROLE3, ROOT, choose, sha256
from evaluate_feedback import fit_signal_gate, generate_graph, infer_signal_mode, run_feedback
from shuffle_control import shuffle_within_type
from dag_role3 import sample_episode
from dag_role3.graphs import SPIKE_RATES
from dag_role3.models import GNNScorer, masked_action, torch_obs
from dag_role3.policies import marginal_scores


CONDITIONS = ("matched", "uniform", "shuffled")
VARIANTS = ("residual", "feature_only")
SCALE = 0.25
TEMPERATURE = 0.12
LR = 0.003
VALIDATION_START = 74000


class GainActor(nn.Module):
    def __init__(self, variant):
        super().__init__()
        if variant not in VARIANTS:
            raise ValueError(f"unknown actor variant: {variant}")
        self.variant = variant
        self.scorer = GNNScorer(len(SPIKE_RATES) + 7 + 1)
        nn.init.zeros_(self.scorer.out.weight)
        nn.init.zeros_(self.scorer.out.bias)

    def forward(self, obs):
        features, edges, mask = torch_obs(obs)
        gain = marginal_scores(obs)
        best = float(gain[obs["mask"]].max())
        if best > 0:
            gain = gain / best
        anchor = torch.from_numpy(gain)
        inputs = torch.cat((features, anchor.float().unsqueeze(1)), dim=1)
        correction = SCALE * torch.tanh(self.scorer(inputs, edges))
        scores = anchor + correction.double() if self.variant == "residual" else correction.double()
        return scores, mask

    @torch.inference_mode()
    def greedy(self, obs):
        scores, mask = self(obs)
        return masked_action(scores, mask)[0]


def load_actor(path):
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    if checkpoint["format_version"] != 1:
        raise ValueError(f"unsupported actor format: {path}")
    actor = GainActor(checkpoint["variant"])
    actor.load_state_dict(checkpoint["state_dict"])
    return actor.eval().greedy


def make_case(graph_seed, condition, gate):
    if condition not in CONDITIONS:
        raise ValueError(f"unknown signal condition: {condition}")
    graph = generate_graph("spike", graph_seed)
    episode_seed = graph_seed + 20000
    mode = "noise" if condition == "uniform" else "normal"
    snapshot = sample_episode(graph, episode_seed, mode)
    if condition == "shuffled":
        snapshot = shuffle_within_type(snapshot, graph.types, episode_seed)
    return graph, snapshot, infer_signal_mode(snapshot.confidence, gate)


def train_variant(variant, seed, training_cases, validation_cases, out):
    torch.manual_seed(seed)
    actor = GainActor(variant)
    optimizer = torch.optim.Adam(actor.parameters(), lr=LR)
    history, validation = [], []
    best_score = float("inf")
    best_weights = None
    selected = 0
    episodes = len(training_cases)

    for episode in range(episodes + 1):
        if episode > 0:
            graph_seed, condition, case, baseline_errors = training_cases[episode - 1]
            log_probs = []

            def sample(obs):
                scores, mask = actor(obs)
                action, log_prob = masked_action(scores, mask, sample=True, temperature=TEMPERATURE)
                log_probs.append(log_prob)
                return action

            errors = run_feedback(*case, sample)[1]
            advantage = baseline_errors - errors
            loss = -advantage * torch.stack(log_probs).sum()
            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(actor.parameters(), max_norm=5.0, error_if_nonfinite=True)
            optimizer.step()
            history.append({"episode": episode, "graph_seed": graph_seed, "condition": condition,
                            "sink_errors": errors, "baseline_sink_errors": baseline_errors,
                            "advantage": advantage})

        if episode in validation_episodes(episodes):
            scores = {condition: mean(run_feedback(*case, actor.greedy)[1] for case in cases)
                      for condition, cases in validation_cases.items()}
            average = mean(scores.values())
            if not math.isfinite(average):
                raise ValueError("nonfinite validation mean")
            validation.append({"episode": episode, "mean_sink_errors": average, "conditions": scores})
            print(f"seed {seed} {variant}: validation at {episode}/{episodes}: {average:.4f}", flush=True)
            if average < best_score:
                best_score, selected = average, episode
                best_weights = copy.deepcopy(actor.state_dict())

    for row in validation:
        row["selected"] = row["episode"] == selected
    path = out / f"{variant}.pt"
    torch.save({"format_version": 1, "variant": variant, "train_seed": seed, "episodes": episodes,
                "selected_episode": selected, "validation_mean_errors": best_score,
                "state_dict": best_weights}, path)
    return {"training": history, "validation": validation, "selected_episode": selected,
            "checkpoint_sha256": sha256(path)}


def validation_episodes(episodes):
    # Evaluate after whole cycles so every regime has contributed equally.
    return sorted({0, (episodes // 6) * 3, episodes})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, required=True, choices=range(1, 6))
    parser.add_argument("--out", type=Path, required=True, help="new per-seed output directory")
    parser.add_argument("--episodes", type=int, default=384)
    parser.add_argument("--validation-graphs", type=int, default=24)
    args = parser.parse_args()
    if args.episodes <= 0 or args.episodes % 3 or args.episodes > 9999:
        parser.error("episodes must be a positive multiple of 3, at most 9999")
    if not 1 <= args.validation_graphs <= 1000:
        parser.error("validation-graphs must be between 1 and 1000")
    out = args.out.resolve()
    try:
        out.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error(f"output directory already exists: {out}")

    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    gate = fit_signal_gate()
    start = 3_000_000 + args.seed * 10_000
    sources = [Path(__file__).resolve(), *(Path(__file__).with_name(name).resolve() for name in
               ("evaluate_feedback.py", "evaluate_conditions.py", "signal_calibration.py", "shuffle_control.py")),
               *sorted((ROLE3 / "dag_role3").glob("*.py"))]
    config = {"train_seed": args.seed, "train_start": start, "episodes": args.episodes,
              "episode_seed_offset": 20000, "validation_start": VALIDATION_START,
              "validation_graphs": args.validation_graphs, "validation_episodes": validation_episodes(args.episodes),
              "conditions": CONDITIONS, "variants": VARIANTS, "budget": 16, "signal_gate": gate,
              "optimizer": "Adam", "lr": LR, "clip_grad_norm": 5.0, "correction_scale": SCALE,
              "temperature": TEMPERATURE, "python": platform.python_version(), "torch": str(torch.__version__),
              "numpy": np.__version__, "source_sha256": {p.relative_to(ROOT).as_posix(): sha256(p) for p in sources}}
    (out / "config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    validation_cases = {condition: [make_case(g, condition, gate) for g in
                        range(VALIDATION_START, VALIDATION_START + args.validation_graphs)] for condition in CONDITIONS}
    training_cases = []
    baseline = partial(choose, name="marginal")
    for index in range(args.episodes):
        condition = CONDITIONS[index % len(CONDITIONS)]
        case = make_case(start + index, condition, gate)
        baseline_errors = run_feedback(*case, baseline)[1]
        training_cases.append((start + index, condition, case, baseline_errors))
    results = {variant: train_variant(variant, args.seed, training_cases, validation_cases, out)
               for variant in VARIANTS}
    pending = out / "training.json.partial"
    pending.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    pending.replace(out / "training.json")


if __name__ == "__main__":
    main()
