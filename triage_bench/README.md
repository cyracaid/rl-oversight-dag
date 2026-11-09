# triage_bench — the real review queue, not a simulator

`triage_bench` stops asking "would RL schedule reviews well?" and asks the prior
question: **on the actual review queue, is there anything left to schedule?**

It reads three local files from the sleep project, builds the 1,048-item review
queue, and measures how many *human-confirmed* errors a policy can surface per
review spent.

---

## Data policy (read this first)

The input data is IRB-restricted. This directory contains **code and aggregate
numbers only**.

- Data is read **in place** from `$SPLSLEEP_DATA_DIR` (default `~/Documents/splsleep`).
- `bench/config.py` **refuses to run** if the data directory resolves inside this repo.
- `outputs/` holds counts, rates and AUCs. No row-level data, no participant IDs.
- The repo `.gitignore` already blocks `*.csv` and `*.rds`; keep it that way.

```bash
export SPLSLEEP_DATA_DIR=~/Documents/splsleep   # optional, this is the default
```

If the data is absent, both scripts print `data missing` and exit 0 — a fresh
clone stays runnable, exactly like `verify_clustering.py`.

---

## Inputs

| File | Rows | Role |
|---|---:|---|
| `audit_m1_m7_decision.csv` | 13,990 | AI verdict per row; 1,048 `FLAG`s carry rule codes M1–M6 |
| `manual_error_correction_updated.csv` | 75 | manual corrections (72 unique keys) |
| `output/cleaned_data_final.csv` | 13,990 | cleaned fields (features only; label columns are dropped) |

Key: `(pid, day_num, row_id)`. Two label definitions are reported, never mixed:

- **narrow** — the 72 unique keys of the correction file (what the README calls 75)
- **broad** — `human_review == "corrected"` (85 rows, 68 of them inside the queue)

`broad` is the default: "a row a human corrected is a true error."

---

## Run

```bash
python3 triage_bench/run_bench.py        # Table 1: recall@k + CI + figure
python3 triage_bench/run_m4_mining.py    # the remaining headroom, or its absence
python3 triage_bench/run_ceiling.py      # the three bounds (coverage / type / power)
python3 triage_bench/run_unflagged.py    # the corrections the queue never sees
python3 triage_bench/run_belief_queue.py # belief greedy inside the M4-only block
python3 triage_bench/run_field_queue.py  # field-scoped review: half the reads
python3 triage_bench/run_audit_demo.py  # receipts -> cost model -> recall per minute
```

Outputs: `outputs/table1.md`, `recall_at_k.json`, `queue_summary.json`,
`participant.json`, `m4_mining.md`, `ceiling.md`, `unflagged.md`,
`belief_queue.md`, `field_queue.md`, `audit_demo.md`, plus `figures/recall_at_k.png`.

The one-page argument is [`CEILING.md`](CEILING.md); the paper draft is
[`SECTION5_CEILING.md`](SECTION5_CEILING.md); the data request for the SciForge
chain is [`SCIFORGE_ASK.md`](SCIFORGE_ASK.md); the granularity decision memo is
[`AUDIT_GRANULARITY.md`](AUDIT_GRANULARITY.md); the receipt schema we would
write ourselves is [`AUDIT_CHAIN_DESIGN.md`](AUDIT_CHAIN_DESIGN.md) with
`audit/receipts.py`.

---

## Headline results (generated 2026-11-09, **not yet rerun by a teammate**)

Queue: 1,048 candidates, 68 positives → **6.5% precision**. Measuring one error
costs ~15 reviews.

| policy | R@50 | R@100 | R@200 | R@400 |
|---|---:|---:|---:|---:|
| pipeline queue order | 4.4% | 5.9% | 13.2% | 23.5% |
| random | 4.4% | 11.8% | 19.1% | 39.7% |
| rule count (AI severity) | 19.1% | 25.0% | 26.5% | 36.8% |
| **M1-bearing first** | 23.5% | **54.4%** | **83.8%** | 83.8% |
| M1 first, then SOL gap | 26.5% | 58.8% | 83.8% | 85.3% |
| oracle | 73.5% | 100% | 100% | 100% |

- **One rule — "M1-bearing flags first" — reaches 84% of all errors in 140 of 1,048 reviews (13%).**
- **The pipeline's own order is worse than random** (23.5% vs 39.7% at k=400). Whatever ordering the default queue has, it is anti-correlated with the truth.
- The M1 block is separable; the remaining 885 M4-only flags hold 11 positives (1.24%).
- **Errors cluster inside participants** (variance/mean 2.00 vs label-shuffle null 1.10, p = 0.0005; one participant carries 7 errors).
- Inside that block, a participant-grouped CV model reaches **AUC 0.467** (worse than chance; permutation p = 0.53). The best fixed single feature (`sleepperiod_minutes`) has AUC 0.78 (family-wise p = 0.010) but yields P@100 = 3% — 3 errors per 100 reviews.
- Ranking *participants* by M1 density reaches 91.2% at k=400, but the paired difference against the row-level rule is **not significant** (@400 +7.3% [−8.6%, +10.0%], @200 −1.5% [−11.4%, +6.8%]).
- 7 corrections (narrow) / 17 (broad) are **never flagged at all**, so no ranking policy can reach them.

### The ceiling (see `CEILING.md`)

| bound | value |
|---|---|
| coverage, narrow (in queue / all corrections) | 65 / 72 = **90.3%** |
| coverage, broad | 68 / 85 = **80.0%** |
| type-only ceiling @k=100 / @k=140 | 61.8% / **83.8%** |
| detectable difference with this sample | **~10pp or larger** |

- **84% is the ceiling, not a victory.** No type-only policy can exceed it,
  because M4-only rows are exchangeable at a 1.2% rate.
- **Three escapes failed:** within-M4 features (AUC 0.467), adaptive belief over
  participants (P@200 1.5% vs 1.24%), and one extra rule `awake == getup`
  (6.5% precision = base rate).
- **17 broad corrections were never flagged** (7 in the narrow set), and 6 of
  those 7 target `time_awake` — a detector blind spot, not a ranking miss.
- **Field-scoped review halves the reading cost** without raising recall: the
  rule's witness pair contains a corrected field 96.6% of the time (58 rows),
  and reaching every reachable positive costs 117 field-reads instead of 232.

### What this means (and what it forbids claiming)

1. The queue is type-separable, and a one-line rule captures most of it. Any
   learned scheduler must beat 83.8% at k=200 — not "no review".
2. Ranking inside M4-only does **not** work with these features. That is a
   negative result and should be reported as one.
3. The remaining error mass sits in the **detector** (unflagged rows) and the
   **graph**, not in the ranker. This is the ablation's conclusion
   (noise 3.78 / normal 1.38 / oracle 0.72) reproduced on real data.
4. Do **not** write "our scheduler improves review" from this. The honest claim
   is "a type prior sets a high bar; the residual is information-limited."

---

## Files

```
bench/config.py        paths, seeds, and the refuse-to-run-inside-repo guard
bench/load.py          join queue + labels + features; label columns dropped
bench/policies.py      queue order / random / rule count / M1-first / type partition / oracle
bench/metrics.py       recall@k, precision@k, pid-clustered bootstrap, paired diff
bench/mine_m4.py       grouped CV, permutation tests, univariate rules
bench/participant.py   participant features, clustering test, participant scoring
bench/belief_queue.py  Beta-Bernoulli belief over participants, simulated deployment
audit/receipts.py      review receipt schema, append-only writer, hash-chain check
run_bench.py           Table 1
run_m4_mining.py       M4-only headroom
run_ceiling.py         coverage / type / power bounds
run_unflagged.py       profile of never-flagged corrections
run_belief_queue.py    belief greedy inside the M4-only block
run_audit_demo.py      receipts -> cost model -> recall per minute
```
