# Pre-registration — the supervisor axis: does a delivery know what it covered?

Frozen 2026-11-24, before any run. Block: graph seeds **5400–5599**, 200 per
family. Episode seed = `20000 + graph_seed`. Committed before the runner exists.

## Question

Every number in this repository measures one axis: how many sink errors a policy
leaves behind. The exact-DP ceiling says that axis is nearly closed — the optimum
of the rule's own model is worth 0.022 errors per graph against a 5–7 error gap
(`outputs/dp-ceiling/`).

This preregistration measures a second axis that changes no action:

> Given the same review log, can the delivery state what it covered, and is that
> statement (a) consistent with the log and (b) informative about the errors
> that remain?

The claim under test is the contract's deletion test, made numeric: **remove the
receipt and the question "how many wrong sinks did we not cover" has no answer.**

## Definitions, fixed here

`ancestor_sources(s)` = the set of source nodes (no parents) that can reach sink
`s` structurally. This is the only coverage notion that matches the environment:
a catch clears a node's *local* source error, so an inherited error passes
through a reviewed node untouched. A vertex cut is therefore **not** coverage.

For each sink, from the public review log alone:

| status | condition | means |
|---|---|---|
| `inspected` | every ancestor source was reviewed | nothing was skipped *upstream* |
| `partial` | some but not all reviewed | a known gap exists |
| `untouched` | none reviewed | the sink was never in scope |
| `escalated` | declared by policy | a refusal; never false |

Three quantities, computed against the hidden truth after the episode ends:

* `fidelity` — share of sinks whose claimed status equals the recomputable one.
  With `escalated` counted as never-wrong, so `judged` is printed beside it to
  show how much was actually described.
* `false_inspection` — wrong sinks labelled `inspected`. **Positive by
  construction whenever `p_catch < 1`**: "every source was reviewed" is not
  "every source is clean".
* `declared_gap` — wrong sinks labelled `partial` or `untouched`.

`false_inspection` and `declared_gap` partition the residual sink errors.

## Arms

The receipt is post-hoc. Both arms run the identical policy on the identical
episode, so actions cannot differ; the runner verifies that instead of assuming
it.

| arm | statement | exists? |
|---|---|---|
| `honest` | copy the review log | yes |
| `overclaim` | label every sink `inspected` | yes — what a system with no coverage field effectively does when asked |
| `silent` | none | no — the delivery without a receipt |

Policies: `marginal` (deployable, primary) and `oracle` (evaluation-only ceiling
reference). Families and budgets: the frozen suite — `spike` 16, `modular` 50,
`real` 8, `ticket` 8.

## Predictions

| | prediction | falsified if |
|---|---|---|
| P1 | the two arms produce **identical** action sequences and residual errors on 800/800 graphs | any graph differs |
| P2 | honest `fidelity` = 1.0 on every graph | < 1.0 anywhere (would mean the receipt and the log disagree, an implementation bug, not a finding) |
| P3 | honest `false_inspection` > 0 on at least one family | 0 on all four (would mean coverage implies correctness here, and the receipt is stronger than argued) |
| P4 | `declared_gap / (declared_gap + false_inspection)` ≥ 0.90 on `spike` and `modular` | < 0.90 on either |
| P5 | `oracle`'s `declared_gap` share is **lower** than `marginal`'s on `modular` | not lower (would mean better coverage does not shift errors into the inspected bucket) |

P4 is the load-bearing one. If residual errors sit inside `inspected` sinks, the
receipt is answering the wrong question and must say so.

## Verdict table (frozen)

Per family:

| verdict | condition |
|---|---|
| `decorative` | P1 fails — the receipt changed the run, so the axes are not orthogonal |
| `load-bearing` | P1 holds and P4 holds (share ≥ 0.90) |
| `weak` | P1 holds and the share < 0.90 |

P2 and P3 are reported, never used to grade: P2 is a self-consistency check and
P3 is a property of `p_catch`, not of the receipt.

## What this cannot show

* It cannot show the receipt is *useful to a reader*. That needs a reader.
* It cannot show calibration. `fidelity` is about structure only; nothing here
  says a claim is true, only whether it was in scope.
* `escalated` is implemented and tested but **no escalation policy is
  preregistered**, so `judged` = 1.0 on every row and no refusal inflates
  `fidelity`. Choosing when to refuse is a policy, and a policy needs its own
  block.
* The `overclaim` arm is bad by construction. It is measured to size the gap, not
  to compete.

## Cost

`marginal` + `oracle` only, no training, no planning: minutes, not hours.
