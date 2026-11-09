# The review queue has an information ceiling — and we are already at it

> Generated 2026-11-09 from `triage_bench/run_ceiling.py`, `run_unflagged.py`,
> `run_belief_queue.py`. Numbers are AI-produced and not yet rerun by a teammate.

This note turns the negative results into a bound. It is the theoretical anchor
for the paper: **on this queue, better scheduling cannot buy much, and we can say
exactly how much and why.**

---

## 1. Three bounds

### B1 — Coverage

A scheduler can only rank rows that were flagged. Corrections that never got a
FLAG are invisible to every policy.

| label set | corrections | in queue | never flagged | ceiling |
|---|---:|---:|---:|---:|
| narrow (manual file) | 72 | 65 | 7 | **90.3%** |
| broad (`human_review`) | 85 | 68 | 17 | **80.0%** |

Infinite budget cannot exceed these. The gap is a **detector** problem.

### B2 — Type information

Within a flag type the rows are exchangeable — the type is all the policy knows,
so the posterior error probability is constant inside a group. Therefore the best
a type-only policy can do is take groups in decreasing positive rate:

| flag type | items | positives | rate |
|---|---:|---:|---:|
| M1 (order only) | 103 | 44 | 42.7% |
| M1+M4 | 37 | 13 | 35.1% |
| M4 (window only) | 885 | 11 | 1.2% |
| other | 23 | 0 | 0.0% |

| k | 50 | 100 | 140 | 200+ |
|---|---:|---:|---:|---:|
| type-only ceiling | 27.9% | 61.8% | **83.8%** | 83.8% |

It saturates at k = 140, the size of the M1-bearing block (103 + 37). The
remaining 16.2% of the queue's errors sit inside 885 M4-only rows at 1.2%.

**Proof sketch.** Let the policy's information be the type partition `G`. Any
ordering that respects `G` allocates `n_g` reviews to group `g`; the expected
number of hits is `Σ n_g r_g`, independent of the order *within* a group. The
optimal allocation under `Σ n_g = k` takes groups in decreasing `r_g`. Hence the
rate-ordered partition maximizes expected recall for every `k`. ∎

### B3 — Power

With 68 positives over 203 participants, this sample cannot resolve small
differences:

- `type_partition` − `m1_first` @100: **+7.3%**, 95% CI [−8.9%, +12.8%]
- rate(M1) − rate(M1+M4): **+7.6%**, 95% CI [−13.6%, +26.8%]

**Any claim below ~10pp is not supported by this queue.** Write the CI, not the
winning row.

---

## 2. We tried to break B2 three ways. All three failed.

| attempt | result |
|---|---|
| within-M4 features, participant-grouped CV | **AUC 0.467** (worse than chance), permutation p = 0.53 |
| best fixed univariate rule (`sleepperiod_minutes`) | AUC 0.78 (p = 0.010) but **P@100 = 3%** — 3 errors per 100 reviews |
| adaptive belief over participants (simulated deployment) | **P@200 = 1.5%** vs 1.24% base; adaptive and static both ~0 hits until k = 100 |
| participant-level ranking (M1 density) | AUC 0.868, but paired Δ vs row rule @400 **+7.3% [−8.6%, +10.0%]** |
| one extra rule (`awake == getup`) | 507 rows fire, 33 corrected → **6.5% precision**, i.e. the base rate |

So the M4-only block is information-dead for the observations we have. The same
lesson appears on the synthetic side: a deployable belief greedy beats the
learned GNN (+0.42 ± 0.15), and giving the GNN its review outcomes changes
nothing. **Information, not the learner, sets the ceiling.**

---

## 3. What this means for the two venues

**NeurIPS.** The contribution is not "RL schedules reviews". It is:

1. a formulation of review scheduling as *sequential information acquisition*
   on a dependency graph, with a deployable belief-space greedy that beats
   policy gradient on held-out graphs;
2. a **ceiling theorem** for the information actually available in a real review
   queue, plus the empirical demonstration that three plausible escapes fail;
3. an honest boundary: the binding constraint is observation quality, not
   scheduling.

That is a "we measured the ceiling and it is low" paper. It is publishable
because it kills a hypothesis with real data, not because it wins a benchmark.

**Nature Communications.** The impact sentence is now directly supported:

> On a year-long sleep-diary pipeline, the review queue is 6.5% precise. A
> single type rule surfaces 84% of human-confirmed errors in 13% of the review
> budget — and that is the ceiling for any type-only policy; the remaining
> errors are invisible to the detector.

---

## 4. What would actually break the ceiling

Only one of these, and each is a different paper:

- **New observations** (cross-field consistency, participant trajectory, source
  documents). This is the detector paper.
- **A second queue** from SciForge where errors are claims, not timestamps, and
  the DAG is real. That is the transfer test.
- **Field-level review**: the labels are row-level, but the corrections target
  `time_awake` 6/7 times among the misses; a field-level queue may be separable
  where the row-level one is not.

Until one of these lands, the honest abstract ends with "the signal, not the
scheduler, is the bottleneck" — which is exactly what the ablation said.
