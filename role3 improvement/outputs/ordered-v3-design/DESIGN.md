# v3 design study — the order channel is a solved problem in a monotone chain, so v3 is not built

Date 2026-11-25. **No seed block was spent.** No episode was sampled. Everything below is
combinatorics on permutations plus the `real` family's own constants, in
`analyse_order_localisability.py`; the numbers are in `mechanisms.json`.

v3 was going to be `k ≥ 2` disjoint transpositions, on the argument that two swaps defeat the
descent-ascent rule that solved v2. That argument is true and useless. This study exists because
v2's gate failed by testing only one cheap solver, and the same mistake was about to be made
again with a different solver.

## The candidates, on the real family's chain length (n = 4, 4000 draws each)

`local_rule_exact` = the rule's output equals the culprit set exactly.

| mechanism | descent-ascent | interval ends | **rank − index** |
|---|---:|---:|---:|
| T1 one transposition (what v2 built) | 1.000 | 0.836 | **1.000** |
| T2 two disjoint transpositions (planned v3) | **0.000** | 0.327 | **1.000** |
| ROT one rotation of a subarray | 0.601 | 0.601 | **1.000** |
| SHIFT one element moved by one place | 1.000 | 1.000 | **1.000** |

T2 does what it was designed to do — descent-ascent drops to 0.000 — and is then solved exactly
by comparing each position's rank to its index. Adding measurement noise at the sampler's own
settings (`sd = 8`, clipped at 30) changes nothing: 0.999 / 1.000 / 0.998 at `gap ∈ [20, 480]`,
1.000 across the board at `gap ∈ [120, 480]`. Raising the gap floor is not needed either.

## Why that is exact rather than lucky

**Claim.** Let the truth be a strictly increasing chain `t_0 < … < t_{n-1}`, and let the record
be a permutation of those same values (no insertion, deletion or duplication), with no ties.
Then position `p` is misplaced **iff** `rank(c_p) ≠ p`, where `rank` is over the recorded chain.

*Proof.* If position `p` holds its own value, that value is the `p`-th smallest of the multiset,
so its rank is `p`. If `rank(c_p) = p`, then `c_p` is the `p`-th smallest, hence equals `t_p`.
Both directions are immediate. ∎

Three lines of code, no search, no learning, and it holds for every permutation mechanism,
including ones nobody has proposed yet. Note what the claim needs: **the multiset is preserved.**
That is exactly what a transposition, a rotation or an adjacent shift does.

The second half of the picture is the other direction. If instead the defect is an *offset* —
one clock moved by ±12 h, which is what the real corrections actually are — the multiset is
**not** preserved and the rank rule does not apply. But the derived difference nodes then carry
the evidence: exactly two of them become inconsistent with the recorded clocks, and both name
the same segment. That is one adjacent-difference residual away, also one pass.

So the two families of defect that a monotone chain can express are both solved by a
one-pass statistic: permutation → rank vs index; offset → adjacent difference residual.
Neither needs a learned relational state, and neither is what the contrastive pilot was trying
to explain.

## What v3 would have had to be, and why that is a different project

The only way out is to corrupt the evidence the one-pass statistics rely on — make the derived
differences noisy or partly missing, so that deciding *which* of several near-consistent
readings to distrust becomes a robust-estimation problem over the whole chain. That is a real
benchmark and it is not this one: it would need a new family with corrupted durations, a
likelihood model, and a different research question ("can a representation do robust
inference?"), and it would no longer be "the real data's dominant failure mode, in the same
simulator". Nothing here is reserved for it and no file prices it.

## Decision

1. **v3 is not built.** Its mechanism is defeatable by a two-line statistic, so any gate on it
   would either pass while proving nothing (as v2 did) or measure the wrong thing.
2. **No block is spent.** Free blocks stay free: graphs 5196–5199 and 60030–60099, episodes
   5700–59999. (`60024–60029` is left out on purpose: `dag_role3/training.py` validates over
   `60000 + count`, and `count = 30` reaches into it.)
3. **The order line closes here.** Not because the environment is too hard, but because it is
   too easy: in a monotone chain the order defect is information, not latent structure, and the
   information is a permutation.
4. **The requirement in `PREREGISTER_ORDERED_BENCHMARK.md` amendment 2 is superseded.** "Ship
   with a test that descent-ascent fails" is satisfied by T2 and still admits the rank rule.
   The right test is "no statistic computed in one pass over the chain recovers it", and by the
   claim above no permutation mechanism can pass it. Amendment 3 records this.
