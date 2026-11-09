# The information ceiling of the real queue

## 1. Coverage (what no policy can reach)

| label set | corrections | in queue | never flagged | ceiling |
|---|---:|---:|---:|---:|
| narrow (manual file) | 72 | 65 | 7 | **90.3%** |
| broad (human_review) | 85 | 68 | 17 | **80.0%** |

An infinite review budget still cannot exceed these numbers, because the
unflagged rows never enter the queue.

## 2. Type ceiling (what a type-only policy can reach)

| flag type | items | positives | rate |
|---|---:|---:|---:|
| M1 | 103 | 44 | 42.7% |
| M1+M4 | 37 | 13 | 35.1% |
| M4 | 885 | 11 | 1.2% |
| other | 23 | 0 | 0.0% |

Within a type group the items are exchangeable, so the best a type-only
policy can do is take the groups in rate order. That ceiling is:

| k | 50 | 100 | 140 | 200 | 400 |
|---|---:|---:|---:|---:|---:|
| ceiling recall | 27.9% | 61.8% | 83.8% | 83.8% | 83.8% |

It saturates at the k that exhausts the M1-bearing block (103 + 37 = 140).

## 3. Power (what this sample can even detect)

`type_partition` (M1-only > M1+M4 > M4 > other) minus `m1_first`:

| k | difference | 95% CI |
|---|---:|---|
| 50 | +4.4% | [-6.1%, +10.7%] |
| 100 | +7.3% | [-8.9%, +12.8%] |
| 140 | +0.0% | [-3.8%, +6.2%] |

Every CI crosses zero. With 68 positives across 203 participants, a ~7pp
difference is inside the noise: **this sample cannot support claims below
roughly 10pp.** Say that in the paper instead of picking the winning row.
