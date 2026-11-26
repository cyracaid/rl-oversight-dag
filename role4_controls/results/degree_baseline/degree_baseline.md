# Degree-only baseline — block 13000–13099

Pre-registered in `PREREG_DEGREE_BASELINE.md` (commit `ef3a495`), before the first episode.
`gain` is paired per graph, `confidence` minus `policy`; positive means the policy leaves fewer
sink errors. Intervals: paired bootstrap, seed 411, 20 × 100, graphs as the resampling unit.

## Decision table (intact)

| family | marginal gain | deg1 gain | deg1/marginal | Δ = marginal − deg1 | label | best grid member | Δ vs best | final |
|---|---|---|---|---|---|---|---|---|
| spike | +0.34 | -0.71 | -2.09 [-4.60, -0.96] | +1.05 [+0.76, +1.35] | propagation-necessary | deg0.5 (-0.18) | [+0.32, +0.74] propagation-necessary | **propagation-necessary** |
| modular | +0.97 | -3.74 | -3.86 [-9.21, -2.10] | +4.71 [+3.76, +5.74] | propagation-necessary | deg0.5 (-1.54) | [+1.73, +3.38] propagation-necessary | **propagation-necessary** |
| ba | +19.60 | -21.21 | -1.08 [-2.07, -0.54] | +40.81 [+29.33, +52.59] | propagation-necessary | deg0.5 (-11.89) | [+21.28, +42.42] propagation-necessary | **propagation-necessary** |
| er | +2.96 | -17.80 | -6.01 [-9.87, -4.16] | +20.76 [+19.05, +22.53] | propagation-necessary | deg0.5 (-13.89) | [+15.18, +18.59] propagation-necessary | **propagation-necessary** |
| real | +0.05 | -0.29 | -5.80 | +0.34 [+0.20, +0.49] | propagation-necessary | deg0.5 (+0.00) | [-0.04, +0.14] inconclusive | **inconclusive** |

## All cells

| family | condition | policy | mean errors | gain vs confidence | 95 % CI | W/T/L |
|---|---|---|---|---|---|---|
| spike | intact | confidence | 1.210 | +0.000 | [+0.00, +0.00] | 0/100/0 |
| spike | intact | marginal | 0.870 | +0.340 | [+0.19, +0.51] | 21/77/2 |
| spike | intact | hub | 5.050 | -3.840 | [-4.29, -3.43] | 1/3/96 |
| spike | intact | deg0.5 | 1.390 | -0.180 | [-0.37, -0.02] | 9/75/16 |
| spike | intact | deg1 | 1.920 | -0.710 | [-1.03, -0.42] | 9/53/38 |
| spike | intact | deg2 | 2.370 | -1.160 | [-1.56, -0.79] | 7/38/55 |
| spike | rewire_index | confidence | 1.210 | +0.000 | [+0.00, +0.00] | 0/100/0 |
| spike | rewire_index | marginal | 2.020 | -0.810 | [-1.16, -0.50] | 12/40/48 |
| spike | rewire_index | hub | 5.050 | -3.840 | [-4.29, -3.43] | 1/3/96 |
| spike | rewire_index | deg0.5 | 1.390 | -0.180 | [-0.37, -0.02] | 9/75/16 |
| spike | rewire_index | deg1 | 1.920 | -0.710 | [-1.03, -0.42] | 9/53/38 |
| spike | rewire_index | deg2 | 2.370 | -1.160 | [-1.56, -0.79] | 7/38/55 |
| modular | intact | confidence | 9.350 | +0.000 | [+0.00, +0.00] | 0/100/0 |
| modular | intact | marginal | 8.380 | +0.970 | [+0.43, +1.57] | 40/33/27 |
| modular | intact | hub | 30.760 | -21.410 | [-23.02, -19.86] | 0/0/100 |
| modular | intact | deg0.5 | 10.890 | -1.540 | [-2.28, -0.91] | 13/38/49 |
| modular | intact | deg1 | 13.090 | -3.740 | [-4.68, -2.85] | 8/12/80 |
| modular | intact | deg2 | 20.760 | -11.410 | [-13.00, -10.07] | 3/0/97 |
| modular | rewire_index | confidence | 9.350 | +0.000 | [+0.00, +0.00] | 0/100/0 |
| modular | rewire_index | marginal | 17.340 | -7.990 | [-9.40, -6.59] | 7/4/89 |
| modular | rewire_index | hub | 30.760 | -21.410 | [-23.02, -19.86] | 0/0/100 |
| modular | rewire_index | deg0.5 | 10.890 | -1.540 | [-2.28, -0.91] | 13/38/49 |
| modular | rewire_index | deg1 | 13.090 | -3.740 | [-4.68, -2.85] | 8/12/80 |
| modular | rewire_index | deg2 | 20.760 | -11.410 | [-13.00, -10.07] | 3/0/97 |
| ba | intact | confidence | 37.120 | +0.000 | [+0.00, +0.00] | 0/100/0 |
| ba | intact | marginal | 17.520 | +19.600 | [+12.24, +28.25] | 46/24/30 |
| ba | intact | hub | 66.320 | -29.200 | [-39.72, -19.59] | 10/1/89 |
| ba | intact | deg0.5 | 49.010 | -11.890 | [-19.97, -4.96] | 3/88/9 |
| ba | intact | deg1 | 58.330 | -21.210 | [-31.34, -12.22] | 3/80/17 |
| ba | intact | deg2 | 58.330 | -21.210 | [-31.34, -12.22] | 3/80/17 |
| ba | rewire_index | confidence | 37.120 | +0.000 | [+0.00, +0.00] | 0/100/0 |
| ba | rewire_index | marginal | 21.710 | +15.410 | [+8.48, +23.41] | 39/12/49 |
| ba | rewire_index | hub | 66.320 | -29.200 | [-39.72, -19.59] | 10/1/89 |
| ba | rewire_index | deg0.5 | 49.010 | -11.890 | [-19.97, -4.96] | 3/88/9 |
| ba | rewire_index | deg1 | 58.330 | -21.210 | [-31.34, -12.22] | 3/80/17 |
| ba | rewire_index | deg2 | 58.330 | -21.210 | [-31.34, -12.22] | 3/80/17 |
| er | intact | confidence | 20.800 | +0.000 | [+0.00, +0.00] | 0/100/0 |
| er | intact | marginal | 17.840 | +2.960 | [+1.87, +4.06] | 49/24/27 |
| er | intact | hub | 42.510 | -21.710 | [-23.41, -19.97] | 0/0/100 |
| er | intact | deg0.5 | 34.690 | -13.890 | [-15.68, -12.21] | 0/2/98 |
| er | intact | deg1 | 38.600 | -17.800 | [-19.55, -16.08] | 0/1/99 |
| er | intact | deg2 | 40.400 | -19.600 | [-21.34, -17.91] | 0/0/100 |
| er | rewire_index | confidence | 20.800 | +0.000 | [+0.00, +0.00] | 0/100/0 |
| er | rewire_index | marginal | 20.780 | +0.020 | [-1.01, +1.02] | 31/14/55 |
| er | rewire_index | hub | 42.510 | -21.710 | [-23.41, -19.97] | 0/0/100 |
| er | rewire_index | deg0.5 | 34.690 | -13.890 | [-15.68, -12.21] | 0/2/98 |
| er | rewire_index | deg1 | 38.600 | -17.800 | [-19.55, -16.08] | 0/1/99 |
| er | rewire_index | deg2 | 40.400 | -19.600 | [-21.34, -17.91] | 0/0/100 |
| real | intact | confidence | 0.500 | +0.000 | [+0.00, +0.00] | 0/100/0 |
| real | intact | marginal | 0.450 | +0.050 | [-0.04, +0.14] | 7/91/2 |
| real | intact | hub | 1.960 | -1.460 | [-1.70, -1.23] | 0/27/73 |
| real | intact | deg0.5 | 0.500 | +0.000 | [-0.07, +0.07] | 4/92/4 |
| real | intact | deg1 | 0.790 | -0.290 | [-0.44, -0.15] | 4/75/21 |
| real | intact | deg2 | 1.200 | -0.700 | [-0.93, -0.49] | 5/54/41 |
| real | rewire_index | confidence | 0.500 | +0.000 | [+0.00, +0.00] | 0/100/0 |
| real | rewire_index | marginal | 1.010 | -0.510 | [-0.71, -0.32] | 4/62/34 |
| real | rewire_index | hub | 1.960 | -1.460 | [-1.70, -1.23] | 0/27/73 |
| real | rewire_index | deg0.5 | 0.500 | +0.000 | [-0.07, +0.07] | 4/92/4 |
| real | rewire_index | deg1 | 0.790 | -0.290 | [-0.44, -0.15] | 4/75/21 |
| real | rewire_index | deg2 | 1.200 | -0.700 | [-0.93, -0.49] | 5/54/41 |

## Post-rewire coherence (this block vs the published figure)

`rewire_index` keeps every parent count, so the `hub` / `deg*` cells are *identical* in the two
conditions (asserted in `--selftest`): a degree-only policy is rewire-invariant by construction.
The `marginal` row therefore shows what the rewire preserves of the *propagation* gain.

| family | marginal gain, intact | marginal gain, rewire_index | retention here | published retention (90000 / 7100) |
|---|---|---|---|---|
| spike | +0.34 | -0.81 [-1.16, -0.50] | -2.38 | — (gain reverses) |
| modular | +0.97 | -7.99 [-9.40, -6.59] | -8.24 | — (gain reverses) |
| ba | +19.60 | +15.41 [+8.48, +23.41] | 0.79 | 73 % / 84 % |
| er | +2.96 | +0.02 [-1.01, +1.02] | 0.01 | 31 % / 32 % |
| real | +0.05 | -0.51 [-0.71, -0.32] | -10.20 | — |

## Reading

- **ba** — a score that never propagates is far *worse* than confidence here, so the gain cannot be a degree-profile artifact; the edges carry it: deg1 leaves 21.21 errors more than confidence against 19.60 for `marginal` (Δ = marginal − deg1 = +40.81 [+29.33, +52.59]).
- **er** — a score that never propagates is far *worse* than confidence here, so the gain cannot be a degree-profile artifact; the edges carry it: deg1 leaves 17.80 errors more than confidence against 2.96 for `marginal` (Δ = marginal − deg1 = +20.76 [+19.05, +22.53]).
- **ER retention is not stable across blocks.** This block keeps 0.01 of the ER gain after `rewire_index` (+0.02 [-1.01, +1.02]), against 31 % / 32 % on 90000–90099 and 7100–7199. Three blocks, three different answers: the ER `survives` label is not a stable property of the family.
- **The grid is partly degenerate on BA.** deg1 and deg2 select identical actions there (the same high-in-degree node wins under both exponents), so the exponent sweep adds no independent competitor on that family; deg0.5 is the only distinct degree-only score.
