# MOCK — synthetic export, no evidential weight

## review ordering — `proj_mock_sleep21`

nodes **21**, confirmed errors **6**, budget **K=5** nodes, prior **flat for marginal_adaptive; declared for type_prior/type_x_reach**

| policy | recall@K | 95% CI | precision@K | reviews→50% |
|---|---:|---|---:|---:|
| `pipeline_order` | **0.17** | [0.00, 0.50] | 0.20 | not reached |
| `random` | **0.22** | [0.00, 0.50] | — | not reached |
| `type_prior` | **0.50** | [0.00, 0.83] | 0.60 | 4 |
| `reach` | **0.17** | [0.00, 0.50] | 0.20 | not reached |
| `type_x_reach` | **0.33** | [0.00, 0.67] | 0.40 | not reached |
| `marginal_adaptive` | **0.17** | [0.00, 0.50] | 0.20 | not reached |
| `marginal_adaptive_declared` | **0.50** | [0.00, 0.80] | 0.60 | 5 |
| `receipts` | **0.17** | [0.00, 0.50] | 0.20 | not reached |
| `oracle` | **0.83** | [0.45, 1.00] | 1.00 | 3 |

`marginal_adaptive` minus baseline (paired, node-resampled):
- vs `type_prior`: -0.29 [-0.82, +0.25] — indistinguishable
- vs `reach`: +0.00 [+0.00, +0.00] — indistinguishable
- vs `pipeline_order`: +0.00 [+0.00, +0.00] — indistinguishable
- vs `marginal_adaptive_declared`: -0.26 [-0.78, +0.25] — indistinguishable

- errors never reviewed by the human receipts: **4 / 6**
