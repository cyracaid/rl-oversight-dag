N=80, budget=16, 5 training seeds x 20000 episodes, held-out graphs 1000..1199 (n=200), particles=1024

| policy | legacy seeds 1-20 | held-out mean | 95% CI |
|---|---:|---:|---:|
| conf threshold | 2.30 | 1.41 | ± 0.25 |
| structural greedy | 1.45 | 1.45 | ± 0.22 |
| belief greedy | 0.90 | 1.14 | ± 0.20 |
| GNN + REINFORCE (static state) | 1.51 ± 0.41 | 1.56 | ± 0.29 (over training seeds) |
| GNN + REINFORCE (observed state) | 1.68 ± 0.56 | 1.56 | ± 0.15 (over training seeds) |

Paired differences on held-out graphs (per graph, GNN averaged over training seeds; negative = left side has fewer sink errors):

- GNN observed − GNN static: -0.00 ± 0.08
- GNN observed − belief greedy: +0.42 ± 0.15
- GNN static − structural greedy: +0.11 ± 0.16
