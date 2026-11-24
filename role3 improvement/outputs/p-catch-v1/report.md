# Reviewer hit rate: `p_catch` sensitivity

Pre-registered in `PREREGISTER_P_CATCH.md` before the sweep ran; the
verdict code in `report_p_catch.py` was frozen at the same commit.
Graph seeds 4000-4199, paired cells, 200 episodes per cell.

**Verdict: `inverted`**

The advantage grows as the hit rate rises, opposite to the prediction. Report the reversal as a finding and leave the direction of the main conclusion unchanged.

| test | result |
|---|---|
| P1 sign holds on all 4 spike cells | True |
| P1 at least 3 intervals exclude zero | True |
| P2 advantage monotone non-increasing in the hit rate | False |
| P2 reversed | True |
| P4 any cell where confidence wins with an interval excluding zero | False |

## Spike: mean remaining conclusion errors

| policy | p=0.60 | p=0.75 | p=0.90 | p=1.00 |
|---|---:|---:|---:|---:|
| confidence | 3.105 | 2.300 | 1.440 | 0.820 |
| marginal | 2.850 | 1.950 | 1.025 | 0.290 |
| oracle | 2.750 | 1.775 | 0.785 | 0.000 |

## Spike: learned policies (evaluated out of distribution)

Checkpoints were trained at `p_catch = 0.9` and are not retrained, so the
question these rows answer is what a deployed policy does when the true hit
rate differs from the assumed one.

| policy | p=0.60 | p=0.75 | p=0.90 | p=1.00 |
|---|---:|---:|---:|---:|
| gnn_s1 | 3.025 | 2.165 | 1.310 | 0.600 |
| gnn_s2 | 3.060 | 2.225 | 1.370 | 0.660 |
| gnn_s3 | 3.140 | 2.305 | 1.445 | 0.780 |

## Spike: paired difference against `confidence`

Positive means fewer remaining errors than `confidence`. Brackets are paired
95% intervals over 200 episodes.

| policy | p=0.60 | p=0.75 | p=0.90 | p=1.00 |
|---|---:|---:|---:|---:|
| confidence | +0.000 [+0.000, +0.000] | +0.000 [+0.000, +0.000] | +0.000 [+0.000, +0.000] | +0.000 [+0.000, +0.000] |
| marginal | +0.255 [+0.150, +0.375] | +0.350 [+0.220, +0.490] | +0.415 [+0.275, +0.570] | +0.530 [+0.370, +0.705] |
| oracle | +0.355 [+0.245, +0.480] | +0.525 [+0.375, +0.685] | +0.655 [+0.490, +0.825] | +0.820 [+0.645, +1.020] |
| gnn_s1 | +0.080 [-0.015, +0.185] | +0.135 [+0.030, +0.255] | +0.130 [+0.010, +0.255] | +0.220 [+0.075, +0.375] |
| gnn_s2 | +0.045 [-0.060, +0.155] | +0.075 [-0.045, +0.215] | +0.070 [-0.070, +0.215] | +0.160 [+0.000, +0.340] |
| gnn_s3 | -0.035 [-0.120, +0.055] | -0.005 [-0.105, +0.100] | -0.005 [-0.120, +0.120] | +0.040 [-0.135, +0.200] |

## real: descriptive only

The real cells are reported for completeness and do not enter
the verdict, which the preregistration fixed to `spike`.

| policy | p=0.60 | p=0.75 | p=0.90 | p=1.00 |
|---|---:|---:|---:|---:|
| confidence | 1.350 | 0.910 | 0.555 | 0.235 |
| marginal | 1.330 | 0.860 | 0.490 | 0.165 |
| oracle | 1.305 | 0.815 | 0.395 | 0.025 |

## What this does not show

- It does not show that a learned policy can adapt to a different hit rate;
  no retraining happened, by design.
- It does not license comparing absolute means with `outputs/v3/`; the graph
  seed block is different and only paired differences transfer.
- It does not put a bound on the case where the reviewer is adversarial rather
  than merely less reliable; that is a different model.
