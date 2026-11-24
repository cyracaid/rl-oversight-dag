# Claim graph contract — review coverage for an external case

Frozen 2026-11-24. Interface between a case repository (claims + raw batches)
and this repository (budgeted review scheduling).

The point of this file is to make one dependency checkable:

> **If you delete `receipt.json`, can the case still say what its delivery
> covered and what it did not?** If yes, this layer is decoration and the
> design has failed. If no, the layer is load-bearing.

## What each side owns

| | case repository | this repository |
|---|---|---|
| owns | claims, raw batches, its own screen, its tolerance choices | ordering under a budget, coverage accounting, the unreachable list |
| must not | adopt our ordering as a correctness verdict | re-derive, second-guess or relabel their screen |
| artefact | `data/derived/*.csv` at a pinned commit | `claim_graph/outputs/<case>/receipt.{json,md}` |

Nothing in the receipt is a statement about whether a claim is *true*. A claim
is either unanimous across its batches or it is not. That is all the receipt
measures, and the receipt says so in its own text.

## Inputs

Three tables, addressed by commit, never by branch:

```
comparisons.csv   one row per claim: cell, contrast, metric, field,
                  passes_screen, paired_ratios, relative MADs
raw_numbers.csv   per batch values, used to rebuild the ratios independently
metrics.csv       per cell, method, metric dispersion
```

Every digest is recorded in `receipt.json.provenance`. If the case changes a
table, the digest changes and the receipt is a different receipt. There is no
"latest" in the provenance record on purpose.

## Output schema (`receipt.json`)

| key | meaning |
|---|---|
| `provenance.case`, `.pin` | repository and commit the tables came from |
| `provenance.tables.*.sha256` | digest of each table as read |
| `provenance.recomputed_from_raw` | claims whose ratios this repo rebuilt bit-exactly |
| `inventory.claims` | size of the claim set |
| `inventory.presented` | claims the case's own screen publishes as supported |
| `inventory.weak` | claims with at least one batch on the other side of unity |
| `inventory.weak_presented` | weak **and** published: the mass a reviewer can still fix |
| `inventory.weak_off_queue` | weak and filtered out: invisible to a queue-only scheduler |
| `inventory.screen` | 2x2 of the case's screen against unanimity |
| `coverage[]` | per ranking per budget: inspected, weak hit, share, wasted reviews, unreachable id digest |

`unreachable_ids` is a digest of the ids not inspected at that budget, so a
reader can check later whether the uncovered set changed without shipping the
whole list.

## The four rules the receipt obeys

1. **Recompute, do not copy.** Ratios are rebuilt from `raw_numbers.csv`.
   Where that is impossible (within-method contrasts), the claim is marked
   `recomputed: false` and the receipt states the count. A published column is
   never the audit's input. Current instance: 1728 of 2016 recomputed, 0
   mismatches.
2. **No error count.** The word "weak" means disagreement across batches. It is
   not "wrong", and quoting the receipt as an error rate is a misuse. The
   receipt repeats this in its own text so it survives being screenshotted.
3. **Budget is a count of claims.** Not wall clock, not currency. A model that
   converts to time would need a per-claim cost that neither side has measured.
4. **No cross-case comparison.** Numbers from this receipt are not comparable
   with `BENCHMARK_SPEC.md` means or with `triage_bench` recall. Different
   claim sets, different verifiers.

## What the case may cite

One sentence, and it must carry the budget:

> At a review budget of B claims, we re-measured x of the y claims whose
> batches disagree, covering p% of that mass; z% remains unverified, listed by
> digest in `receipt.json`.

Without `receipt.json` the same sentence cannot be written, because neither
`x`, `y`, `p` nor the digest exists anywhere in the case tables.

## First instance — CUDA case

`claim_graph/run_cuda_receipt.py`, pinned to `2538d57`:

| quantity | value |
|---|---:|
| claims | 2016 |
| cells | 72 |
| published as supported | 1057 |
| weak | 1112 |
| weak and published | 230 |
| weak and filtered out | 882 |
| weak mass covered at B=128, queue order | 13.9% |
| weak mass covered at B=128, weakest-first | 55.6% |

The last two rows are the argument for having an ordering at all: the same
budget covers four times more weak mass once the order is not the table order.

`cell_diverse` reaches 48.7% at the same budget, which is the cost of spreading
reviews across cells instead of exhausting the weakest ones first. That trade is
visible in the table rather than argued in prose.

## Known limits

- The weak/unanimous split is one rule. A claim can be unanimous and still be
  meaningless if its batches share a systematic error; this layer cannot see
  that, and says so.
- The 2x2 of the case's screen mixes two criteria (direction and dispersion) in
  a way these tables cannot separate. The receipt reports the cell counts and
  refuses to interpret them as a screen failure rate.
- Coverage assumes a re-measurement settles the claim. A re-measurement that
  repeats the same systematic error changes nothing, and no budget model here
  would notice.
- Ordering rules implemented so far are stability, dispersion, cell-diverse,
  queue and random. The learned and mean-field rules from `role3 improvement`
  are not wired in, because the claim hierarchy here is two levels deep and the
  propagation assumption would need its own justification.
