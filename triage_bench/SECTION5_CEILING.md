# 5. The information ceiling of review scheduling

> Draft paper section. English is the submission language; CN/KO translation is
> pending. Every number below is produced by `triage_bench/` from the real queue
> and is **AI-generated, not yet rerun by a teammate** (see §12 of `PROJECT_EN.md`).

Sections 5.1–5.4 define the object and three bounds. 5.5 reports the empirical
values. 5.6 states what a method paper must therefore beat. 5.7 lists what would
falsify the bounds.

---

## 5.1 Setup

A review queue is a finite set of candidate items \(Q\), \(|Q| = N\), produced by
an automatic detector. Each item \(i\) carries a flag type \(g(i) \in G\) — the
set of rules the detector fired — and a hidden label \(y_i \in \{0,1\}\), where
\(y_i = 1\) means a human, on inspection, corrected the item.

A review policy \(\pi\) spends a budget of \(k\) inspections and induces an
ordering of \(Q\). Its utility is recall at budget,

\[
R_\pi(k) \;=\; \frac{1}{|P|}\sum_{i \in \mathrm{top}_k(\pi)} y_i,
\qquad P = \{i : y_i = 1\},
\]

i.e. the fraction of all true positives surfaced by the first \(k\) inspections.

We distinguish two policy classes:

- \(\Pi_{\text{type}}\): policies whose ordering is measurable with respect to the
  flag-type partition \(G\). The policy may know how many items of each type
  exist; it may not use any per-item feature beyond \(g(i)\).
- \(\Pi_{\text{all}}\): policies that may use any pre-review feature
  \(x_i\) (field values, timestamps, detector scores, participant aggregates).

The question this section answers is not "which policy is best" but **how much
recall is available at all**, in each class, on the queue we actually have.

---

## 5.2 Bound I — coverage

Let \(P_{\text{all}}\) be the set of all human corrections, and
\(P_{\text{queue}} = P_{\text{all}} \cap Q\) those that the detector flagged.
No policy — in either class, at any budget — can surface an item outside \(Q\).
Hence

\[
R_\pi(k) \;\le\; \frac{|P_{\text{queue}}|}{|P_{\text{all}}|}
\quad\text{for all } \pi, k.
\]

This is the **coverage ceiling**. It is a detector property, not a scheduler
property: the only way to raise it is to change what gets flagged.

---

## 5.3 Bound II — the type ceiling

**Proposition 1.** *Let \(r_g = \Pr(y = 1 \mid g)\) and let \(\pi^\star\) be any
policy that orders type groups by decreasing \(r_g\). Then for every \(k\),*

\[
\mathbb{E}\big[R_{\pi}(k)\big] \;\le\; \mathbb{E}\big[R_{\pi^\star}(k)\big]
\quad \text{for all } \pi \in \Pi_{\text{type}}.
\]

*Proof.* A type-measurable policy can only allocate inspections across groups:
choose \(n_g\) with \(\sum_g n_g = k\). Conditional on \(G\), items within a
group are exchangeable, so the expected number of hits contributed by group \(g\)
is \(n_g r_g\), independent of the order *within* \(g\). Maximizing
\(\sum_g n_g r_g\) subject to \(\sum_g n_g = k\) is a fractional knapsack whose
solution takes groups in decreasing \(r_g\). Any within-group order attains the
same expectation. ∎

Two consequences matter for the paper.

1. **Within-group ordering is noise.** Under \(\Pi_{\text{type}}\), reordering
   inside a group changes the realized recall but not its expectation. Any
   reported gain from such reordering is a variance draw, not information.
2. **The ceiling is attained by the partition, not by learning.** A four-way
   partition is optimal *if* the rates are known; a coarse binary split
   (violation vs not) leaves information on the table only to the extent that
   the finer rates differ — which, on our queue, they do not detectably (§5.5).

**Remark (estimation).** Proposition 1 assumes known \(r_g\). In deployment the
rates are estimated elsewhere; the ordering is stable only if the gaps between
\(r_g\) exceed their estimation error. §5.5 reports those gaps with intervals,
and they are not resolved at this sample size. This is why we present the ceiling
as a bound and not as a deployable gain.

---

## 5.4 Bound III — statistical power

With \(|P_{\text{queue}}| = 68\) positives spread over 203 participants, the
participant-clustered bootstrap half-width on a recall difference is roughly
10 percentage points. Formally, differences smaller than

\[
\Delta_{\min} \;\approx\; z_{0.975}\,\sqrt{\frac{2\,\mathrm{Var}(\hat R)}{n_{\text{eff}}}}
\]

are not distinguishable from zero. **Consequence for the field:** a paper that
reports a 5–8 pp improvement on a queue of this size, without a paired
participant-clustered interval, is reporting noise. We therefore report intervals
for every comparison and treat any point estimate inside them as undetermined.

---

## 5.5 Empirical values

### 5.5.1 The queue

Detector output on a one-year sleep-diary pipeline: \(N = 1{,}048\) flagged rows
out of 13,990; 68 of them are human-confirmed corrections, so the queue is
**6.5% precise** — one true error per ~15 inspections.

### 5.5.2 The three bounds

| bound | value |
|---|---|
| coverage, narrow label set | 65 / 72 = **90.3%** |
| coverage, broad label set | 68 / 85 = **80.0%** |
| type ceiling at \(k=100\) | **61.8%** |
| type ceiling at \(k \ge 140\) | **83.8%** |
| detectable difference | **≈ 10 pp** |

The type ceiling saturates at \(k = 140\), the size of the order-bearing block
(103 + 37 items). Everything beyond it lives in 885 window-only items at 1.2%.

| flag type | items | positives | rate |
|---|---:|---:|---:|
| order violation only | 103 | 44 | 42.7% |
| order + window | 37 | 13 | 35.1% |
| window only | 885 | 11 | 1.2% |
| other | 23 | 0 | 0.0% |

### 5.5.3 Three attempts to escape Bound II

Each attempt is the natural next idea; each fails:

| attempt | result |
|---|---|
| within-window features, participant-grouped CV | **AUC 0.467** (below chance), permutation \(p = 0.53\) |
| best fixed univariate rule (`sleepperiod_minutes`) | AUC 0.78 (\(p = 0.010\)) but **P@100 = 3%** |
| adaptive Beta–Bernoulli belief over participants, simulated deployment | **P@200 = 1.5%** against a 1.24% base rate |
| participant-level ranking by order-violation density | AUC 0.868, but paired \(\Delta\) vs the row rule @400 = **+7.3% [−8.6, +10.0]** |
| one additional rule (`final awakening = get-up`) | 507 rows fire, 33 correct → **6.5% precision**, i.e. the base rate |

Two auxiliary facts complete the picture. First, **the detector's own ordering is
worse than random** (23.5% vs 39.7% recall at \(k=400\)); inside the window-only
block its first 200 items contain zero positives. Second, **errors cluster inside
participants** (variance/mean 2.00 against a 1.10 label-shuffle null,
\(p = 0.0005\); one participant carries 7), yet the clustering does not convert
into budget efficiency — the same information is already in the row type.

### 5.5.4 Escape route 3: change the unit of review

The row-level rules fire on a whole row, but each rule's witness names the two
timestamps that conflict (`bed_sleep`, `sleep_awake`, `awake_getup`). A curator
who reads only the witness pair reads two fields instead of four.

| measure | value |
|---|---|
| M1 rows with a recorded corrected field | 58 |
| at least one corrected field inside the pair | **56 / 58 = 96.6%** |
| *all* corrected fields inside the pair | 39 / 58 = 67.2% |
| field-reads to exhaust reachable positives, row review | 232 |
| field-reads, pair-scoped review | **117 (−50%)** |

This does not move the recall ceiling. It moves the **cost axis**: with
inspections priced in fields read rather than rows reviewed, the order block
becomes twice as cheap per recall point. The strict column also shows the
field-level analogue of propagation — a wrong bedtime surfaces as a
`sleep_awake` violation, so the fix lies one field upstream of the witness.

### 5.5.5 Relation to the synthetic result

On held-out synthetic graphs the same asymmetry appears from the other side: a
deployable belief-space greedy beats a learned policy (\(1.14\) vs \(1.56\) sink
errors; paired \(+0.42 \pm 0.15\)), and giving the learned policy its own review
outcomes changes nothing (\(-0.00 \pm 0.08\)). Information structure, not the
learner, sets performance in both regimes.

---

## 5.6 What a method paper must beat

The bounds make the bar explicit. A scheduler on this queue is only interesting
if it either

1. **exceeds 83.8% at some \(k \le 140\)** — i.e. extracts type information
   better than the partition allows, which Proposition 1 forbids within
   \(\Pi_{\text{type}}\), so it must use features with genuine within-group
   signal (we found none); or
2. **raises the coverage ceiling** — flags items the detector misses (7 of 72 in
   the narrow set, concentrated on the final-awakening field), which is a
   detector contribution; or
3. **changes the unit of review** — from row to field or claim. We measured the
   field case (§5.5.4): it halves the reading cost without raising recall. That
   is a real contribution, but it must be reported on a cost-normalised axis.

Absent one of these, the honest abstract ends: *the signal, not the scheduler, is
the bottleneck.* This is the same conclusion the synthetic ablation reached
(noise 3.78 / normal 1.38 / oracle 0.72 sink errors).

---

## 5.7 What would falsify these bounds

- **Within-group signal.** A feature that lifts window-only precision above 5%
  out-of-sample would break Bound II's empirical premise. We tested 19 features
  and three policy classes; none did.
- **A second queue.** If a SciForge evidence queue shows a type partition with
  resolved rate gaps, the ceiling is higher there and the bound becomes
  dataset-specific rather than universal.
- **Reviewer verdicts with timing.** Our correction log has no per-item
  timestamps (`resolved_at` is populated for 1 of 75 rows), so we cannot measure
  review cost, only review count. With timestamps, the bound would be stated in
  hours rather than inspections, and the comparison to human practice would be
  direct.

---

*Reproduce:* `python3 triage_bench/run_bench.py`, `run_ceiling.py`,
`run_unflagged.py`, `run_belief_queue.py`. The data is read in place and never
committed; see `triage_bench/README.md` for the data boundary.
