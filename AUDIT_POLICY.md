# Audit policy register

Status: **v1, frozen 2026-11-25**. Code: `role3 improvement/dag_role3/audit_policy.py`. Tests:
`role3 improvement/tests/test_audit_policy.py` (20).

This file records the rules the delivery is judged by, and who is allowed to change them. It exists
because the supervisor layer was already using four constants that nobody had named, ratified, or
versioned — and a constant that defines what a status *means* cannot be left to whoever edits the module.

## 1. The rule

| actor | may | may not |
|---|---|---|
| machine | route on procedural signals (entropy, disagreement, coverage arithmetic); **propose** a status with its basis | change `statuses`, `perspective_set`, `independence_threshold`, `construct_mapping`; **ratify** a proposal |
| person | adjudicate a new policy version between evaluations; ratify a claim status | adjudicate while an evaluation window is open |

The policy is frozen for the duration of an evaluation. Routing is not frozen: routing never asserts
anything.

## 2. Why separation, and not "review discipline"

`ENTROPY_LIMITS.md` §1: every confidence quantity in this family is invariant under relabelling, so it
cannot distinguish "the right answer holds the mass" from "the wrong answer holds the mass". A system that
tunes its own guarantee criteria against such a signal converges on whichever answer it already holds. The
objectivity of the guarantee therefore rests on the auditor and the audited object being different
parties, not on the auditor being careful.

§7 of the same file states the consequence for test-time adaptation: drift is forced, not incidental. The
lock in this module is the structural version of that finding.

**The prohibition was tested, not asserted.** `PREREGISTER_DRIFT.md` (confirmatory block 5730–5829) builds
the loop v1 forbids — an unreviewed source feeding a `partial` sink read as "the reviewers found nothing
here" — and runs it against the shipped layer on identical episodes. Verdict: `load-bearing`. The loop costs
`+0.39` / `+0.24` / `+0.55` surviving sink errors per graph on `spike` / `real` / `ticket` (95 % intervals
excluding zero), and it drives declared `inspected` sinks down from 151 to 38, 7 to 0 and 73 to 0. The
receipt does not become *wrong*; it withdraws, which is the `silent` arm reached from the inside. Result:
`role3 improvement/outputs/drift-v1/drift_vs_open.md`.

## 3. Version 1 — the four adjudicated objects

None of these values is new. Each was already implicit; the register names it, freezes it, and makes a
change cost a version.

| object | v1 value | where it was implicit | what a change would do |
|---|---|---|---|
| `statuses` | `inspected`, `partial`, `untouched`, `escalated` with the assertion each makes | `STATUSES` in `supervisor.py` | redefine what the delivery asserts; `escalated` is a refusal, so it can never be false |
| `perspective_set` | `spike`, `modular`, `real`, `ticket`, `ba`, `er` | the benchmark's six families | decide which comparisons count as independent viewpoints |
| `independence_threshold` | `0.9` | the environment's `p_catch` | decide when a reviewed source may be read as "no error upstream". This is the constant behind `false_inspection` |
| `construct_mapping` | `reviewer_verdict → source_error_absent`, `coverage_log → review_completeness` | `CLAIM_GRAPH_CONTRACT.md` | admit a new evidence channel |

The absence in the fourth row is the decision: **`confidence → truth` is not in the map**, and adding it
requires an adjudication that would have to argue against `ENTROPY_LIMITS.md` §2. That is the intended
cost.

## 4. What the lock enforces

- `begin_evaluation()` holds the window; `adjudicate()` raises `FrozenPolicyError` while it is open.
- Authority is checked **before** the freeze, so a machine attempt is always reported as
  `AuthorityError` — never disguised as a scheduling problem.
- Versions are consecutive; a change that moves no adjudicated field is rejected as a no-op; a rationale,
  a date, and a ratifier are all required.
- History is append-only: `history` returns every ratified version, and the incumbent object is frozen, so
  it cannot be mutated in place.
- `fingerprint()` returns e.g. `v1:p_catch>=0.90:statuses=4:perspectives=6:constructs=2`, which a delivery
  can quote so a reader knows the rules the numbers were produced under. `report_supervisor.py` now does:
  the string is in the render header and again in a provenance table with the block, budgets, runtime and
  source hashes. The change is presentation-only — the rendered `verdict.json` is byte-identical before and
  after, so the frozen block still says exactly what it said.

## 5. Status ledger: a proposal is not a guarantee

| step | who | output |
|---|---|---|
| arithmetic over the review log | machine | `StatusProposal(claim_id, status, basis, policy_version)` |
| signature | person | `Ratification(..., version)` |

A ratification must use a status that exists in the policy, must carry the policy version the proposal was
computed under, and supersedes rather than overwrites: `latest()` moves, `history()` keeps both rows.

This is the honest reading of the governance requirement, and it changes how the existing result should be
described: the coverage arithmetic in `outputs/supervisor-v1/` produces **proposals**. Nothing about the
measured numbers (0.898 declared share, 180/1767 false-inspected, 10.2 % → 14.9 %) changes; what changes is
that calling them "statuses" now implies a signature the frozen block does not carry.

## 6. Interaction with the frozen block

`outputs/supervisor-v1/` was produced under v1 and stays exactly as it is (block 5400–5599, spent). The
new layer is additive and stdlib-only; nothing in `supervisor.py` or the runner imports it.

**Do not re-run that block under a different policy.** A policy change that moves the numbers needs a fresh
pre-registered block (≥ 5600), and the change must be adjudicated *before* the run, not after — which is
the only ordering in which the freeze means anything.

## 7. Not implemented

Stated plainly so the claim does not outrun the code:

- **No authentication.** `is_machine()` is a keyword gate (`machine`, `model`, `agent`, `auto`, `auto:*`).
  It stops a pipeline from quietly signing its own work; it does not stop a forger. A real deployment needs
  signed receipts.
- **No escalation policy.** `escalated` is a valid status and is tested, but no policy version says when a
  proposal must escalate. Adding one is an adjudication, not a code change.
- **No cross-claim ledger.** The ledger is per claim. A conjunction over ancestor sources still needs one
  proposal per source, and the aggregation rule is not adjudicated.
