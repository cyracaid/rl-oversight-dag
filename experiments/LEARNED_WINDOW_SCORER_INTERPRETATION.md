# Is the cross-night score learnable?

`learned_window_scorer.py` (8/8 tests) → `runs/learned-window-scorer/results.json`.
196 participants, 118 train / 78 held-out (split by a stable hash of the pid),
8 training seeds, 20 evaluation seeds, budgets 2 and 4 nights read.
Logistic regression on 11 observable window features, plain numpy, no sklearn.

## Question

§12d ended on "the score is the bottleneck, not the unit", where the score was
hand-crafted: distance from the record's medoid midpoint. A reviewer is entitled
to ask whether that is a fact about review or a lucky formula. This experiment
replaces the formula with a learned one and asks whether the result survives.

## Held-out ranking quality

| model | AUC (held-out windows) | largest weights |
|---|---|---|
| visible (±12 h run) | **0.991** | qc_max +3.13, qc_sum +2.82 |
| silent WASO→0 run | **0.816** | waso_zero_frac +1.59 |
| silent 90 min shift | **0.840** | mid_dev +1.64, tst_dev −0.75 |
| **one pooled model, no family label** | 0.981 / 0.749 / 0.720 | qc_sum +1.62, mid_dev +1.00, waso_zero_frac +0.68 |

The learned weights are the interpretation: for visible defects it *reconstructs
the QC rule*; for silent WASO it uses the feature no hand-crafted score had
(`waso_zero_frac`); for the shift it uses midpoint deviation, i.e. it rediscovers
the hand-crafted score.

## Policy performance (mean sink errors, 4 conclusions; lower is better)

| corruption | budget | night QC | hand-crafted shift score | learned (per family) | **learned (pooled)** | greedy oracle |
|---|---|---|---|---|---|---|
| visible ±12 h | 2 | 0.180 | 1.354 | 0.214 | 0.170 | 0.148 |
| | 4 | 0.000 | 1.054 | 0.005 | 0.009 | 0.003 |
| silent WASO→0 | 2 | 0.039 | 0.034 | **0.014** | 0.015 | 0.017 |
| | 4 | 0.032 | 0.033 | **0.013** | 0.013 | 0.013 |
| silent 90 min shift | 2 | 0.162 | **0.071** | 0.083 | 0.091 | 0.079 |
| | 4 | 0.056 | 0.043 | **0.041** | 0.058 | 0.016 |

Paired deltas over the 20 evaluation seeds (95 % CI, bootstrap over seeds only —
the 78 held-out participants are fixed):

| comparison | budget | Δ |
|---|---|---|
| learned − night QC, visible | 2 | +0.034 [−0.006, +0.077] |
| learned − night QC, WASO | 2 | **−0.025 [−0.027, −0.023]** |
| learned − night QC, shift | 2 | **−0.079 [−0.096, −0.062]** |
| pooled − night QC, visible | 2 | −0.010 [−0.048, +0.028] |
| pooled − night QC, WASO | 2 | **−0.024 [−0.026, −0.021]** |
| pooled − night QC, shift | 2 | **−0.071 [−0.086, −0.056]** |
| learned − shift score, shift | 2 | +0.013 [+0.003, +0.025] |
| learned − shift score, shift | 4 | −0.001 [−0.009, +0.006] |

## Reading

**1. On the defect that dominates the correction log, learning adds nothing.**
For a visible ±12 h run the learned scorer puts all its weight on the QC flags and
lands where the QC rule already is (0.214 vs 0.180 at budget 2; both ≈ 0 at budget
4). This is the expected, useful null: 76 % of the real corrections are already
solved by a rule, and no scorer will improve them.

**2. On silent defects a learned score beats the per-night rule by 1.5–2.9×.** The
WASO case is the clearest: 0.039 → 0.014 at budget 2, because `waso_zero_frac`
is a feature the hand-crafted scores never had and the QC flags never fire on a
zero-WASO night. The learned score also beats the hand-crafted cross-night score
there (0.014 vs 0.034).

**3. One score, no family label, keeps most of the gain.** The pooled model loses
ranking quality (AUC 0.75–0.72 on the silent families) but still beats per-night
QC on all three families at budget 2, with CIs that exclude zero on the two silent
ones. That is the sentence worth carrying: **you do not have to know which defect
you are looking for to profit from a cross-night score.**

**4. The hand-crafted formula was not special.** Where the hand-crafted score wins
(shift, budget 2, by 0.013) it wins inside a CI that is nearly closed at 4 nights.
The formula was a good guess at `mid_dev`; the learned model finds the same
feature and adds the ones the guess omitted.

**5. The greedy oracle is beatable.** On the WASO family at budget 2 the learned
policy scores 0.014 against the oracle's 0.017. The "oracle" here maximises
overlap with the corrupted run and ignores the repair mechanics (two inspected
nights are needed to name a shared cause), so it is a reference point, not a
bound. Do not present it as one.

## Limits

* Training labels come from the simulator, not from human review. This is a
  mechanism result: it says the signal is present in observable features, not
  that a lab should deploy this scorer as-is.
* The per-family models are the strong version; the pooled model is the honest
  single-score version and it is weaker. Report both, never only the strong one.
* CIs cover seed variation only. The participant split is fixed, so between-person
  variation is not in these intervals.
* `learned` and `pooled` pick window length jointly (2 or 3), whereas
  `block3_shift` is fixed at 3 (or the affordable remainder). The comparison is
  fair in budget units — both spend nights read — but the learned policy has one
  more degree of freedom.

## Consequence

§12d's recommendation — "build a cross-night consistency signal before tuning the
action" — is now an engineering statement with a recipe: 11 features, a logistic
fit, a held-out participant split, and a paired comparison against the existing
QC rule. Nothing in it is specific to sleep except the feature names.
