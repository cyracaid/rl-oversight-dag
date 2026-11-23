"""Train a feature-only GNN on the return from each review, then pair it with the archived terminal-reward GNN."""

import argparse
import copy
import csv
import json
from pathlib import Path
import platform
from statistics import mean

import numpy as np
import torch
from torch import nn

from evaluate_conditions import BUDGET, ROOT, OversightEnv, sha256
from evaluate_feedback import P_CATCH, fit_signal_gate, run_feedback
from evaluate_residual import marginal
from train_residual import (CONDITIONS, LR, SCALE, TEMPERATURE, VALIDATION_START, GainActor,
                            load_actor, make_case, masked_action, validation_episodes)


HERE = Path(__file__).resolve().parent
ARCHIVE = HERE / "results" / "residual-v1"
RUN = HERE / "results" / "credit-v1"
EPISODES = 384
EVAL_GRAPHS = range(96000, 96200)


def write_json(path, data):
    pending = path.with_suffix(path.suffix + ".partial")
    pending.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                       encoding="utf-8")
    pending.replace(path)


def simulate_credit(case, policy):
    """Use only the normal public-policy interface, then replay completed choices to obtain the audit."""
    actions = []

    def record(obs):
        action = policy(obs)
        actions.append(action)
        return action

    outcome = run_feedback(*case, record)
    graph, snapshot, _ = case
    replay = OversightEnv(graph, snapshot, BUDGET, p_catch=P_CATCH, confidence_mode="normal")
    for action in actions:
        replay.step(action)
    audit = replay.final_audit()
    trace = audit["trace"]
    levels = (audit["initial_sink_errors"], *(row["sink_errors_after"] for row in trace))
    if (len(trace) != BUDGET or tuple(row["sink_errors_before"] for row in trace) != levels[:-1]
            or any(after > before for before, after in zip(levels, levels[1:]))
            or sum(row["sink_errors_before"] - row["sink_errors_after"] for row in trace) != levels[0] - levels[-1]
            or outcome[:4] != (levels[0], levels[-1], sum(row["flagged"] for row in trace), len(trace))):
        raise ValueError("completed feedback trajectory and replay audit do not match")
    return levels, outcome


def weights_for(policy_errors, baseline_errors):
    if len(policy_errors) != BUDGET + 1 or len(baseline_errors) != BUDGET + 1:
        raise ValueError("expected initial error count followed by one count per review")
    terminal = baseline_errors[-1] - policy_errors[-1]
    future = np.subtract(policy_errors[:-1], baseline_errors[:-1]) + terminal
    if future[0] != terminal:
        raise ValueError("paired trajectories started at different initial errors")
    return terminal, future


def load_control(seed, gate):
    archive_meta = json.loads((ARCHIVE / "eval" / "manifest.json").read_text(encoding="utf-8"))
    receipt = archive_meta["checkpoints"][f"feature_only_s{seed}"]
    path = ROOT / receipt["path"]
    config_path, log_path = (path.with_name(name) for name in ("config.json", "training.json"))
    if (receipt["sha256"] != sha256(path) or receipt["training_config_sha256"] != sha256(config_path)
            or receipt["training_log_sha256"] != sha256(log_path)):
        raise ValueError("archived control receipt does not match source artifacts")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    expected = {"episodes": EPISODES, "episode_seed_offset": 20000, "validation_start": VALIDATION_START,
                "validation_graphs": 24, "validation_episodes": validation_episodes(EPISODES),
                "budget": BUDGET, "signal_gate": gate, "train_seed": seed, "train_start": 3000000 + seed * 10000,
                "conditions": list(CONDITIONS), "optimizer": "Adam", "lr": LR, "temperature": TEMPERATURE,
                "correction_scale": SCALE, "clip_grad_norm": 5.0,
                "python": platform.python_version(), "numpy": np.__version__, "torch": str(torch.__version__)}
    if any(config[key] != value for key, value in expected.items()):
        raise ValueError("new training conditions differ from the archived feature-only control")
    if any(sha256(ROOT / name) != digest for name, digest in config["source_sha256"].items()):
        raise ValueError("a source used for the archived control changed")
    history = json.loads(log_path.read_text(encoding="utf-8"))["feature_only"]
    if history["checkpoint_sha256"] != receipt["sha256"] or history["selected_episode"] != receipt["selected_episode"]:
        raise ValueError("archived training history does not match control")
    return receipt, history


def train(seed, folder, gate, control):
    torch.manual_seed(seed)
    actor = GainActor("feature_only")
    optimizer = torch.optim.Adam(actor.parameters(), lr=LR)
    validation_cases = {condition: [make_case(g, condition, gate) for g in range(VALIDATION_START, VALIDATION_START + 24)]
                        for condition in CONDITIONS}
    training, validation = [], []
    best = float("inf")
    selected, weights = None, None
    for index in range(EPISODES + 1):
        if index in validation_episodes(EPISODES):
            scores = {name: mean(run_feedback(*case, actor.greedy)[1] for case in cases)
                      for name, cases in validation_cases.items()}
            if index == 0 and scores != control["validation"][0]["conditions"]:
                raise ValueError("initial policy's validation scores differ from A")
            average = mean(scores.values())
            validation.append({"episode": index, "mean_sink_errors": average, "conditions": scores})
            print(f"seed {seed}: validation {index}: {average:.3f}", flush=True)
            if average < best:
                best, selected, weights = average, index, copy.deepcopy(actor.state_dict())
        if index == EPISODES:
            break
        gs = 3000000 + seed * 10000 + index
        condition = CONDITIONS[index % len(CONDITIONS)]
        case = make_case(gs, condition, gate)
        baseline, _ = simulate_credit(case, marginal)
        old = control["training"][index]
        if (old["episode"], old["graph_seed"], old["condition"], old["baseline_sink_errors"]) != (
                index + 1, gs, condition, baseline[-1]):
            raise ValueError("training case or baseline differs from matched control")
        log_probs = []

        def sample(obs):
            scores, mask = actor(obs)
            action, lp = masked_action(scores, mask, sample=True, temperature=TEMPERATURE)
            log_probs.append(lp)
            return action

        levels, _ = simulate_credit(case, sample)
        if index == 0 and levels[-1] != old["sink_errors"]:
            raise ValueError("first stochastic training outcome differs from control")
        terminal, future = weights_for(levels, baseline)
        log_probs = torch.stack(log_probs)
        loss = -(log_probs * log_probs.new_tensor(future)).sum()
        optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(actor.parameters(), 5.0, error_if_nonfinite=True)
        optimizer.step()
        training.append({"episode": index + 1, "graph_seed": gs, "condition": condition,
                         "sink_errors": levels[-1], "baseline_sink_errors": baseline[-1],
                         "terminal_advantage": terminal, "step_advantages": future.tolist(),
                         "actor_errors": levels, "rule_errors": baseline})
    checkpoint = folder / "future.pt"
    pending = folder / "future.pt.partial"
    torch.save({"format_version": 1, "variant": "feature_only", "train_seed": seed, "episodes": EPISODES,
                "selected_episode": selected, "validation_mean_errors": best, "state_dict": weights}, pending)
    pending.replace(checkpoint)
    write_json(folder / "training.json", {"training": training, "validation": validation,
                                          "selected_episode": selected, "checkpoint_sha256": sha256(checkpoint)})


def evaluate(seed, gate, archive_path, folder):
    actors = {"terminal": load_actor(archive_path), "future": load_actor(folder / "future.pt")}
    # With the same deterministic rule for every training seed, a single reference row per graph suffices.
    if seed == 1:
        actors["marginal"] = marginal
    output = folder / "episodes.csv"
    pending = output.with_suffix(".csv.partial")
    with pending.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(("graph_seed", "episode_seed", "condition", "policy", "train_seed",
                         "initial_sink_errors", "sink_errors", "flags", "reviews"))
        for i, gs in enumerate(EVAL_GRAPHS, 1):
            for condition in CONDITIONS:
                case = make_case(gs, condition, gate)
                for name, actor in actors.items():
                    result = run_feedback(*case, actor)
                    if result[3] != BUDGET:
                        raise ValueError("evaluation budget differs")
                    writer.writerow((gs, case[1].seed, condition, name, seed if name != "marginal" else "",
                                     *result[:4]))
            if i % 50 == 0:
                print(f"seed {seed}: evaluated {i}/{len(EVAL_GRAPHS)}", flush=True)
    pending.replace(output)


def run_seed(seed, directory):
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    folder = directory / f"seed-{seed}"
    folder.mkdir(parents=True, exist_ok=True)
    gate = fit_signal_gate()
    receipt, control = load_control(seed, gate)
    here = Path(__file__).resolve()
    inputs = [here, here.with_name("evaluate_residual.py"), directory / "protocol.md",
              ARCHIVE / "eval" / "manifest.json"]
    config = {"train_seed": seed, "control": receipt,
              "inputs": {p.relative_to(ROOT).as_posix(): sha256(p) for p in inputs}}
    config_path = folder / "config.json"
    if config_path.exists():
        if json.loads(config_path.read_text(encoding="utf-8")) != config:
            raise ValueError("run inputs changed; use a fresh output directory")
    else:
        write_json(config_path, config)
    log = folder / "training.json"
    if not log.exists():
        train(seed, folder, gate, control)
    if json.loads(log.read_text(encoding="utf-8"))["checkpoint_sha256"] != sha256(folder / "future.pt"):
        raise ValueError("future checkpoint differs from completed training record")
    if not (folder / "complete.json").exists():
        evaluate(seed, gate, ROOT / receipt["path"], folder)
        files = ["episodes.csv", "training.json", "future.pt", "config.json"]
        write_json(folder / "complete.json", {name: sha256(folder / name) for name in files})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, required=True, choices=range(1, 6))
    parser.add_argument("--run", type=Path, default=RUN)
    args = parser.parse_args()
    run_seed(args.seed, args.run.resolve())
