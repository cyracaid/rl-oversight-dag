# Capture-side checks: which defects no scheduler can fix

`capture_checks.py` (6/6 tests) → `runs/capture-checks/results.json`.
Input: the de-identified daily export, 196 participants with ≥ 10 nights
(2,372 nights, median 12). Aggregates only; nothing per-row is written.

## Why this file exists

§12d showed that a silent WASO→0 defect has nothing to schedule: every review
policy lands at 0.02–0.05 sink errors and even the oracle only reaches 0.01.
That is a claim about the *data*, and it was measured on a simulator. This file
measures the same thing on the real export, so the sentence "some defects are not
review problems" stops being an assertion.

The split that matters:

| where the defect can be fixed | what it looks like | can review help? |
|---|---|---|
| intake / instrument | information never recorded | **no** |
| form validation | a convention applied to one field | **no**, it is a rule |
| review | a night that contradicts the rest of the record | yes |
| analysis | a mean over fewer nights than the reader assumes | **no**, report it |

## Numbers

| check | records | % of 196 | nights |
|---|---|---|---|
| every night reports WASO = 0 | 7 | 3.6 % | 82 |
| ≥ 50 % of nights report WASO = 0 | 81 | 41.3 % | — |
| nights reporting WASO = 0 | — | 39.3 % of all nights | 933 |
| ≥ 3 consecutive WASO = 0 nights | 88 | 44.9 % | — |
| … same, expected if zeros were scattered at random | 69.3 | 35.4 % | — |
| one ±12 h shift makes an order-breaking night valid | 20 | 10.2 % | 21 |
| coverage (nights present / span), median | — | 91.7 % | — |
| coverage below 0.8 | 42 | 21.4 % | — |
| coverage below 0.5 | 0 | 0 % | — |

Median zero share per record = 40.8 % — the modal night in this cohort reports no
awakenings at all.

## Reading

**1. WASO is largely absent, not small.** 39 % of nights report exactly zero
awakenings, and 7 records report it on every night. Sleep efficiency is
`(sleep period − WASO) / time in bed`, so on those nights the numerator is at its
maximum by construction. No ordering rule can detect this: the night is perfectly
well-formed. **The conclusion C2 (low efficiency) is not reviewable on those
records — it is not interpretable.** The fix is at intake ("were awakenings
recorded?") or suppressing the conclusion, not spending human review on it.

**2. A 3-night WASO run is mostly the base rate.** 44.9 % of records have one, but
with a 41 % zero rate the permutation null already produces 35.4 %. The excess is
~18 records out of 196 (9 points). So "the diary was dropped mid-week" is a real
but *small* signal, and any rule that fires on a 3-night run will be wrong about
two-thirds of the time. It needs the null attached; without it the check is
alarming and useless.

**3. The dominant real error is a convention, not a mystery.** 20 records (10.2 %)
contain a night that breaks the order rules but is repaired by exactly one ±12 h
shift on one field. This is the `order_error` family (57/75 corrections). It is
detectable by a deterministic rule and repairable by the same rule. Review budget
should never be spent here; the form should collect 24-hour input, and the
validator should auto-repair the unambiguous cases.

**4. Coverage is mostly fine, with a long tail.** Median 91.7 % of the record's
span is present, and no record is below 50 %. But 21.4 % are below 80 %, and every
per-participant mean silently uses however many nights survived. That does not
need review either; it needs `nights present / span` printed next to the mean.

## What this changes for the proposal

The review scheduler's addressable problem is narrower than "find the bad night":

```text
record
├── information missing      → intake / suppress the conclusion     (3.6 %, 39 % of nights)
├── convention error         → deterministic ±12 h repair rule       (10.2 %)
├── coverage gap             → report the denominator                (21.4 %)
└── night contradicts record → review / schedule                     (the only reviewable part)
```

Three of the four buckets are cheaper to fix outside the scheduler, and one of
them (missing WASO) is *impossible* to fix inside it. This is the concrete form of
the §12d statement "the unit is not the bottleneck": the bottleneck is upstream of
the action.

## Limits

* The export is a snapshot; these are prevalence figures, not rates over time.
* `waso_est` is a reported field, not derivable from the clock times, so
  "WASO = 0" cannot be cross-checked against the diary here.
* The correction-log error type `sleep_awake_equal` is **not** detectable in this
  export — `awake` is the wake clock time, so `awake == sleep` means a zero-length
  sleep period, which never occurs. Do not claim that check.
* `ampm_recoverable` uses the package's own order thresholds, so it is exactly as
  strict as the QC the lab already runs; it finds the cases where a repair exists,
  not every case a human would repair.
