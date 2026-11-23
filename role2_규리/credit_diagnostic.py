"""Compare unclipped policy gradients on identical trajectories from a frozen initial actor."""

import argparse
from pathlib import Path

import numpy as np
import torch

from train_credit import (CONDITIONS, RUN, TEMPERATURE, GainActor, fit_signal_gate, make_case,
                          marginal, masked_action, sha256, simulate_credit, weights_for, write_json)


def gradient_statistics(samples):
    values = np.asarray(samples, dtype=np.float64)
    norms = np.linalg.norm(values, axis=1)
    nonzero = norms > 0
    unit = values[nonzero] / norms[nonzero, None]
    count = len(unit)
    paired_cosine = None
    if count > 1:
        gram = unit @ unit.T
        paired_cosine = float(gram[np.triu_indices(count, 1)].mean())
    return {"covariance_trace": float(values.var(axis=0, ddof=1).sum()),
            "mean_pairwise_cosine_nonzero": paired_cosine,
            "zero_gradients": int((~nonzero).sum()), "trajectories": len(values)}


def compare(seed, gate):
    torch.manual_seed(seed)
    actor = GainActor("feature_only")
    samples = {"terminal": [], "future": []}
    for index in range(24):
        case = make_case(3_000_000 + seed * 10_000 + index, CONDITIONS[index % len(CONDITIONS)], gate)
        reference, _ = simulate_credit(case, marginal)
        log_probs = []

        def sample(obs):
            scores, mask = actor(obs)
            action, log_prob = masked_action(scores, mask, sample=True, temperature=TEMPERATURE)
            log_probs.append(log_prob)
            return action

        observed, _ = simulate_credit(case, sample)
        terminal, future = weights_for(observed, reference)
        path = torch.stack(log_probs)
        losses = {"terminal": -terminal * path.sum(), "future": -(path * path.new_tensor(future)).sum()}
        for name, loss in losses.items():
            gradient = torch.autograd.grad(loss, tuple(actor.parameters()), retain_graph=name == "terminal")
            samples[name].append(torch.cat([g.flatten() for g in gradient]).detach().numpy())
    return {name: gradient_statistics(rows) for name, rows in samples.items()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=RUN / "diagnostic.json")
    args = parser.parse_args()
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    gate = fit_signal_gate()
    results = {seed: compare(seed, gate) for seed in range(1, 6)}
    write_json(args.out, {"source_sha256": sha256(Path(__file__)),
                          "training_source_sha256": sha256(Path(__file__).with_name("train_credit.py")),
                          "episodes_per_seed": 24, "updates": 0, "seeds": results})
