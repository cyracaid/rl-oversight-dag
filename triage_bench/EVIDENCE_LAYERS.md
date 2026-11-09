# Three layers, and the line between "affected" and "wrong"

> Written 2026-11-09 in response to an external advisory that proposed splitting
> provenance / evidence / review. The split is right and it sharpens what we have.
> This page records what we adopt, what we reject, and the one rule that must not
> be blurred.

---

## 1. The three layers

| Layer | Question | Our artefacts | Status |
|---|---|---|---|
| **Provenance** | where did this value come from? | `artifact-versions` (`createdAt` + `actor`), `evidence-dag` deltas, the N=21 sleep pipeline DAG | partially exists; do not rebuild PROV |
| **Evidence** | what does this result support? | the claim/edge layer in the SciForge design; `supports` / `contradicts` | design only |
| **Review** | why should we believe it? | our receipt schema, `audit/receipts.py`, the demo pipeline | built and tested |

The value is not any one layer — W3C PROV, RO-Crate and Snakemake already cover
provenance. The value is **where the seams break**: a value can be produced correctly
and still fail to support the claim it is attached to, and a claim can rest on a value
whose upstream has since changed.

## 2. The rule that must not be blurred

> **Impact propagation is not error propagation.**

In the synthetic simulator, an upstream error propagates to descendants with
probability `p_prop`, and that is a modelling assumption for RL. In a real research
system, an upstream change means:

- the downstream value **may** have changed,
- its **evidence basis** is now uncertain,
- its **review receipts are stale**,
- and the conclusion needs **re-review**, not deletion.

So the real system needs a state that the simulator does not have:

| State | Meaning | Who sets it |
|---|---|---|
| `unreviewed` | nobody has checked | system |
| `accepted` | checked, passes | human |
| `rejected` | checked, wrong | human |
| `needs_revision` | checked, fix required | human |
| `unresolved` | evidence insufficient to decide | human |
| **`stale`** | was accepted, but an upstream version changed | **system, derived** |

`stale` is derived, never typed by a human, and it is the only state the system may
assert on its own. This is the concrete form of "the machine never stamps".

## 3. Edge types, and which ones propagate

| Edge | Means | On upstream change |
|---|---|---|
| `derived_from` | value produced from a value | mark downstream **affected** |
| `uses` | analysis consumed an input | mark **affected**; verify the actual dependency |
| `supports` | evidence supports a claim | re-evaluate **support strength**, not truth |
| `contradicts` | evidence conflicts with a claim | open a **conflict review** |
| `reviewed_by` | a human checked it | never propagates |
| `supersedes` | new version replaces old | old result becomes `stale` |

None of these edges may write "false" into a downstream node. They write "affected"
and "stale".

## 4. What we adopt into the receipt schema

Adopted today (`audit/receipts.py`):

- verdicts: `accepted` / `corrected` / `rejected` / **`needs_revision`** / **`unresolved`** / `skipped`;
- optional `second_reviewer`, so a receipt can say it was double-read;
- the receipt stays bound to `artifact_version` + `field_path`, never to a mutable node id.

Not adopted: a separate "review thread" object. Discussion stays a comment; only a
submission produces a receipt. That boundary already exists and is worth keeping.

## 5. What we refuse to do

| Proposal | Why we decline it now |
|---|---|
| Rebuild a full provenance platform (Phase 1 + 2) | multi-month engineering; the course deadline is 12/05 and Stage 1 must not wait |
| Adopt the 60/25/15 resource split | it assumes a product team; we are five students with one deadline — our split is 100% Stage 1 until 12/05 |
| Treat the RL module as "phase 3, optional" | true for the product, false for the course: RL *is* the deliverable, and the belief-vs-RL comparison is the research content |
| Add a claim layer now | nothing in our data supports claims yet; designing it without an instance is how projects die |

## 6. The one question worth stealing

The advisory's acceptance test is better than any of its architecture advice:

> Can a second researcher independently reconstruct why a result exists, what
> assumptions produced it, what has changed since it was reviewed, and whether it is
> still supported?

That is testable on the N=21 pipeline we already have, without any new platform:

1. change one upstream node (e.g. timestamp parsing),
2. list the affected derived variables, results and stale receipts,
3. ask whether a second person can follow the list to the right places.

If that demo works, Stage 2 has a concrete artefact. If it does not, no amount of RL
will make the system useful.

**Note the ordering this implies:** our own measurement says review prioritisation is
worth little on the sleep queue (6.5% precision, 84% ceiling). That is an argument for
building the traceability demo *before* the smart scheduler, not after.
