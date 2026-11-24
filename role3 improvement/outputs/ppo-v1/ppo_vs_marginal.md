# PPO vs marginal on spike, fresh block 4200-4399

Pre-registration: `PREREGISTER_PPO.md`. Verdict code: `report_ppo.py`; the rules were fixed before the trainer existed.

Paired over 200 graphs, episode seed 20000 + graph seed, budget 16.
Delta is PPO minus `marginal`, so positive means the learner is worse.

| seed | PPO | marginal | delta | 95% CI | W/T/L |
|---|---:|---:|---:|---|---|
| gnn_s1 | 1.225 | 0.875 | +0.350 | [+0.230, +0.480] | 2/160/38 |
| gnn_s2 | 1.335 | 0.875 | +0.460 | [+0.335, +0.600] | 3/138/59 |
| gnn_s3 | 1.340 | 0.875 | +0.465 | [+0.325, +0.620] | 2/148/50 |

**Verdict: `third-loss`.**

P2 (PPO between marginal and the REINFORCE GNN, bound +0.403): observed mean delta +0.425, every seed inside the bound: False.

Absolute means are not comparable with `outputs/v3/`: different graph
seed block. Only the paired deltas travel.
