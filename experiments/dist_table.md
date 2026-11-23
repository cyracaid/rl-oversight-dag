> ARCHIVE ONLY - NOT EVIDENCE. No saved run reproduces these numbers; see
> `experiments/DIST_PROVENANCE.md`. Configuration does not match `dist_results.json`.

N=80, budget=16, 3 seed(s) x 20000 FT episodes, held-out n=200, teacher = belief greedy

| policy | held-out mean | 95% CI |
|---|---:|---:|
| belief greedy (teacher) | 1.15 | ± 0.21 |
| student, BC only | 1.14 | ± 0.11 |
| student, BC + REINFORCE | 1.15 | ± 0.07 |

Per-seed BC only: ['1.03', '1.22', '1.17']
Per-seed BC + FT: ['1.09', '1.22', '1.15']

Reading: BC ≈ teacher means the policy can represent the rule; a large BC gap means capacity/features; BC good and FT worse means credit assignment.
