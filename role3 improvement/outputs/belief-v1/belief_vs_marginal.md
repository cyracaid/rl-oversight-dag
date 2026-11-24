# The oracle gap is not the belief's numbers, block 4800-4999

Pre-registration: `PREREGISTER_BELIEF_DECOMPOSITION.md` (v2 section). Verdict code: `report_belief.py`.

`marginal` and `oracle` share rule, budget and horizon; only the prior differs. The reference here keeps the belief's *ranking* exactly (one strictly monotone map applied to every node, so per-graph AUC is bit-identical by construction) and distorts only its *values*:

    q_i(gamma) = sigmoid(gamma * logit(belief_i))

`gamma = 1` reproduces `marginal` exactly, per graph, as a hard check.

## modular (n=500, N=200 graphs)

`marginal` 8.820 / `oracle` 3.930, belief AUC 0.966.

| gamma | mean errors | recovery [95% CI] | Bonferroni CI | aggregate errors closed | W/T/L |
|---:|---:|---|---|---:|---|
| 0.50 | 10.310 | -0.600 [-0.755, -0.460] | [-0.807, -0.420] | -298 of 978 | 21/44/135 |
| 0.75 | 9.145 | -0.182 [-0.257, -0.120] | [-0.288, -0.103] | -65 of 978 | 18/96/86 |
| 1.00 | 8.820 | +0.000 [+0.000, +0.000] | [+0.000, +0.000] | +0 of 978 | 0/200/0 |
| 1.25 | 8.825 | +0.016 [-0.055, +0.072] | [-0.082, +0.088] | -1 of 978 | 46/142/12 |
| 1.50 | 8.875 | -0.003 [-0.077, +0.059] | [-0.107, +0.077] | -11 of 978 | 52/129/19 |
| 2.00 | 9.115 | -0.056 [-0.143, +0.021] | [-0.177, +0.043] | -59 of 978 | 58/110/32 |

Pre-registered verdict from the peak cell: **policy-bound**. Grid-corrected interval for that cell: [-0.082, +0.088].

Read the last two columns before the ratio. `gamma = 1.25` changed the outcome on 58 of 200 graphs (46 better, 12 worse) and moved the aggregate by -1 errors of a 978-error gap. The ratio mean is positive only because the graphs it wins on are the ones with a one-or-two-error gap, so the positive number is reshuffling, not recovery.

## spike (N=200 graphs)

`marginal` 1.030 / `oracle` 0.785, belief AUC 0.971.

| gamma | mean errors | recovery [95% CI] | Bonferroni CI | aggregate errors closed | W/T/L |
|---:|---:|---|---|---:|---|
| 0.50 | 1.100 | -0.013 [-0.224, +0.184] | [-0.303, +0.237] | -14 of 49 | 6/171/23 |
| 0.75 | 1.030 | +0.039 [-0.026, +0.132] | [-0.039, +0.158] | +0 of 49 | 2/193/5 |
| 1.00 | 1.030 | +0.000 [+0.000, +0.000] | [+0.000, +0.000] | +0 of 49 | 0/200/0 |
| 1.25 | 1.040 | +0.079 [+0.000, +0.184] | [+0.000, +0.211] | -2 of 49 | 3/194/3 |
| 1.50 | 1.030 | +0.105 [+0.026, +0.211] | [+0.000, +0.237] | +0 of 49 | 4/192/4 |
| 2.00 | 1.045 | +0.053 [-0.105, +0.184] | [-0.158, +0.237] | -3 of 49 | 4/190/6 |

Pre-registered verdict from the peak cell: **calibration-partial**. Grid-corrected interval for that cell: [+0.000, +0.237].

Read the last two columns before the ratio. `gamma = 1.50` changed the outcome on 8 of 200 graphs (4 better, 4 worse) and moved the aggregate by +0 errors of a 49-error gap. The ratio mean is positive only because the graphs it wins on are the ones with a one-or-two-error gap, so the positive number is reshuffling, not recovery.

## What this does and does not show

The ranking of the belief is held fixed, so this is a test of the belief's *values* and of one one-parameter family of rescalings, not of the whole calibration space. Within that family `marginal` sits at or next to the optimum: every distortion is neutral at best and clearly worse at `gamma = 0.5`. So the residual gap to `oracle` is not a probability-scale error that a temperature fixes.

It also does not prove myopia is the cause. The belief still ranks only 0.96 and the review decisions depend on where the mass sits, not on the AUC. What the experiment removes is the cheapest explanation: 'the forward derivative is fed wrong numbers'.

