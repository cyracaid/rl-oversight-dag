"""Paired comparison of two belief estimators under the same review policy."""
import argparse
from pathlib import Path

import numpy as np
from dag_role3 import generate_graph, sample_episode, OversightEnv
from dag_role3.policies import choose
from run_benchmark import FAMILIES, interval, save


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--families", nargs="+", choices=FAMILIES, default=["spike","real"])
    ap.add_argument("--seeds", type=int, default=50)
    ap.add_argument("--particles", type=int, default=1024)
    ap.add_argument("--out", type=Path, default=Path("outputs"))
    args = ap.parse_args()
    if min(args.seeds, args.particles) < 1:
        ap.error("episode and particle counts must be positive")
    args.out.mkdir(parents=True, exist_ok=True)
    records, summary = [], []
    for family in args.families:
        gains, fallbacks = [], []
        for seed in range(80000, 80000 + args.seeds):
            graph = generate_graph(family, seed)
            snapshot = sample_episode(graph, 20000 + seed)
            outcomes = []
            for count in [0, args.particles]:
                env = OversightEnv(graph, snapshot, particles=count, belief_seed=seed+40000)
                obs = env.observation()
                while not env.done:
                    obs, _, _, _ = env.step(choose(obs, "marginal"))
                audit = env.final_audit()
                outcomes.append(audit["final_sink_errors"])
                records.append(dict(family=family, graph_seed=seed, episode_seed=20000+seed,
                                    particles=count, belief_seed=seed+40000,
                                    sink_errors=outcomes[-1], fallback=audit["particle_fallback"]))
            fallbacks.append(audit["particle_fallback"])
            gains.append(outcomes[0]-outcomes[1])
        lo, hi = interval(gains)
        summary.append(dict(family=family, episodes=args.seeds, particles=args.particles,
                            gain_vs_mean_field=np.mean(gains), paired_lo=lo, paired_hi=hi,
                            fallback_episodes=sum(fallbacks)))
    save(args.out/"belief_episodes.csv", records)
    save(args.out/"belief_summary.csv", summary)


if __name__ == "__main__":
    main()
