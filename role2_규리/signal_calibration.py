"""Select between the two simulated signal models using only public scores."""

from statistics import fmean

from dag_role3 import generate_graph, sample_episode


def fit_signal_gate():
    """Estimate the two graph-mean confidence levels on a separate calibration set."""
    start, count = 70000, 100
    means = {"normal": [], "noise": []}
    for seed in range(start, start + count):
        graph = generate_graph("spike", seed)
        for mode, values in means.items():
            sample = sample_episode(graph, seed + 20000, confidence_mode=mode)
            values.append(fmean(sample.confidence))
    return {
        "graph_start": start,
        "graph_count": count,
        "episode_seed_offset": 20000,
        "centers": {mode: fmean(values) for mode, values in means.items()},
    }


def infer_signal_mode(confidence, gate):
    """Choose the closest calibration mean, resolving ties in favor of normal."""
    observed = fmean(confidence)
    centers = gate["centers"]
    return min(("normal", "noise"), key=lambda mode: abs(observed - centers[mode]))
