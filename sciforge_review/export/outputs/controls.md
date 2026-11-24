# Harness controls (synthetic placement, no evidential weight)

Structure: `proj_mock_sleep21`, 21 nodes, budget K=5, errors per rep = 6, reps = 400, primary method runs flat; declared-prior rows are the sensitivity arm.

## null

| policy | mean recall@K | sd |
|---|---:|---:|
| `pipeline_order` | 0.241 | 0.160 |
| `random_dummy` | 0.237 | 0.161 |
| `type_prior` | 0.231 | 0.160 |
| `reach` | 0.241 | 0.164 |
| `type_x_reach` | 0.231 | 0.162 |
| `marginal_adaptive` | 0.241 | 0.164 |
| `marginal_adaptive_declared` | 0.231 | 0.160 |
| `receipts` | 0.241 | 0.160 |
| `oracle` | 0.827 | 0.171 |

- `type_prior` − `pipeline_order`: -0.010 (win/tie/loss 0.35/0.28/0.37, sd 0.262)
- `reach` − `pipeline_order`: -0.000 (win/tie/loss 0.31/0.40/0.29, sd 0.169)
- `marginal_adaptive` − `type_prior`: +0.010 (win/tie/loss 0.37/0.28/0.35, sd 0.258)

## type_signal

| policy | mean recall@K | sd |
|---|---:|---:|
| `pipeline_order` | 0.131 | 0.130 |
| `random_dummy` | 0.242 | 0.161 |
| `type_prior` | 0.414 | 0.192 |
| `reach` | 0.132 | 0.136 |
| `type_x_reach` | 0.370 | 0.180 |
| `marginal_adaptive` | 0.132 | 0.136 |
| `marginal_adaptive_declared` | 0.391 | 0.189 |
| `receipts` | 0.131 | 0.130 |
| `oracle` | 0.818 | 0.171 |

- `type_prior` − `pipeline_order`: +0.283 (win/tie/loss 0.79/0.16/0.06, sd 0.262)
- `reach` − `pipeline_order`: +0.001 (win/tie/loss 0.21/0.59/0.20, sd 0.125)
- `marginal_adaptive` − `type_prior`: -0.283 (win/tie/loss 0.08/0.13/0.79, sd 0.264)

## structure_signal

| policy | mean recall@K | sd |
|---|---:|---:|
| `pipeline_order` | 0.487 | 0.119 |
| `random_dummy` | 0.240 | 0.151 |
| `type_prior` | 0.000 | 0.000 |
| `reach` | 0.622 | 0.121 |
| `type_x_reach` | 0.260 | 0.107 |
| `marginal_adaptive` | 0.622 | 0.121 |
| `marginal_adaptive_declared` | 0.163 | 0.058 |
| `receipts` | 0.487 | 0.119 |
| `oracle` | 0.828 | 0.130 |

- `type_prior` − `pipeline_order`: -0.487 (win/tie/loss 0.00/0.01/0.99, sd 0.119)
- `reach` − `pipeline_order`: +0.135 (win/tie/loss 0.69/0.27/0.04, sd 0.145)
- `marginal_adaptive` − `type_prior`: +0.622 (win/tie/loss 1.00/0.00/0.00, sd 0.121)

## How to read this

- **null**: no ordering should win: mean diffs ≈ 0 and win ≈ loss (ties allowed)
- **type_signal**: `type_prior` must beat `pipeline_order` clearly
- **structure_signal**: `reach` must beat `pipeline_order`; a prior pointing the other way must lose — that is the misspecification arm

If a row above contradicts its expectation, the evaluator or the policy wiring is wrong — fix that before touching a real export. These numbers are generated, not observed.
