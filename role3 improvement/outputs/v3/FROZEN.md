# Role 3 environment v3 — frozen

Status: **frozen 2026-11-24**, git tag `role3-env-v3`.
Owner of the code: 오현석 (Role 3). This note only records what was verified, not a redesign.

## What is frozen

| Item | Path |
|---|---|
| Environment package | `dag_role3/` (7 modules) |
| Installable metadata | `pyproject.toml` (`pip install -e "role3 improvement"`) |
| Trained checkpoints | `outputs/v3/train_{1,2,3}/{gnn_spike_observed,dqn_spike}.pt` |
| Run manifest (hashes, Python/numpy, seeds) | `outputs/v3/manifest.json` |
| Per-policy, per-graph results | `outputs/v3/benchmark_role3.csv` (3,600 rows) |
| Aggregates with paired CIs | `outputs/v3/benchmark_summary.csv` |
| Figure | `outputs/v3/benchmark_summary.png` |
| Revision notes (Korean) | `../변경내역.md` |

No further changes to `dag_role3/` without a new tag. Role 2 depends on this package; changing it silently changes
every Role 2 table.

## Verification run on 2026-11-24

The CSVs were missing from the repository (they are `*.csv`, caught by the root `.gitignore`). They were
regenerated and committed, and the published table in `변경내역.md` was checked against them:

| Family | confidence | marginal | gain [paired 95% CI] |
|---|---:|---:|---:|
| spike | 1.03 | 0.66 | 0.37 [0.20, 0.56] |
| modular | 10.59 | 8.78 | 1.81 [1.10, 2.56] |
| ba | 29.65 | 20.13 | 9.52 [4.25, 15.99] |
| er | 21.75 | 16.76 | 4.99 [3.52, 6.61] |
| real | 0.50 | 0.47 | 0.03 [0.00, 0.07] |

Every cell equals `변경내역.md` to the printed precision. GNN seeds 0.96 / 1.17 / 1.06 and DQN seeds
1.53 / 1.23 / 1.34 also reproduce.

Command:

```bash
cd "role3 improvement"
python3 run_benchmark.py --out /tmp/r3bench \
  --checkpoints outputs/v3/train_1/dqn_spike.pt outputs/v3/train_1/gnn_spike_observed.pt \
                outputs/v3/train_2/dqn_spike.pt outputs/v3/train_2/gnn_spike_observed.pt \
                outputs/v3/train_3/dqn_spike.pt outputs/v3/train_3/gnn_spike_observed.pt
```

Machine used: Python 3.13.5, numpy 2.4.4, macOS 15.4.1 arm64.
The committed manifest was produced on Python 3.12.14 / numpy 2.3.5 and records identical `source_sha256`
for all 17 source files. The numbers did not move across that numpy minor, so the environment is not
version-fragile at this scale.

File hashes of the committed tables:

```
1b75842c93f7e90d7ec75af9bc705270c1424a744aa077e8071282a940db71fe  benchmark_summary.csv
b2f681d00058fc2eea9fd2fc83d144d76dd9aea087d32334453cf4ac2ad9597d  benchmark_role3.csv
```

## Boundaries of what this supports

- Errors, confidences and propagation probabilities are **simulated**. The prior and the edge model are known to
  the policies. No claim is made that these are measured properties of real LLM output.
- `real` is a fixed 21-node topology with 4 declared sinks and budget 8; it is not a distribution over real
  pipelines.
- `marginal` is a mean-field approximation that ignores correlation along shared paths; the particle filter can
  lose diversity and fall back (1 recovery event in 100 spike graphs).
- CIs cover test-episode uncertainty only, not training-seed uncertainty.
- These numbers are **not** comparable with `experiments/results.md` or `role2_규리/results/`: different sink
  sets, budgets and environment versions. See `../../CROSS_IMPLEMENTATION_VALIDATION.md`.
