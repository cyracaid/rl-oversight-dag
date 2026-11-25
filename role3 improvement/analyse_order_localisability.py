"""Design study for v3: can the order chain hold a defect that is both identifiable and non-local?

No episodes, no seeds, no blocks. Pure combinatorics on permutations plus the real family's
own constants, so the answer is a property of the information available and not of a sampler.

The question v3 has to answer before it may spend a block:

  identifiable  at least one algorithm recovers the culprit set from the recorded chain
  non-local     no function of a single position's own value and its own adjacent pair
                comparisons recovers it

If those two cannot hold together at the chain length the simulated families actually have,
then no gate can rescue the mechanism, and the block must not be spent.

Mechanisms enumerated:

  T1   one transposition, any distance          (what v2 built)
  T2   two disjoint transpositions              (what v3 was going to build)
  ROT  one rotation of a contiguous subarray    (values shifted, no value keeps its position)
  SHIFT one subarray moved by +-1 position      (an insertion, the classic "order error")

Rules enumerated, all of them local by construction:

  descent_ascent   first descent start, last ascent end            (v2's rescuer)
  interval_ends    endpoints of every maximal violated run
  rank_offset      per position: rank(clock) - position           (needs the whole chain)

`rank_offset` is included on purpose: if it solves the mechanism, then the relational content
is a rank vector, exactly computable in two lines, which is the opposite of a latent structure
worth learning.
"""
from __future__ import annotations

import itertools
import json
import random
from pathlib import Path

import numpy as np

REAL = {"clock_start": (1200.0, 1560.0), "gap": (20.0, 480.0), "noise_sd": 8.0}
DRAWS = 4000
SEED = 20261125


def true_chain(n, rng, spec=REAL):
    t = [rng.uniform(*spec["clock_start"])]
    for _ in range(n - 1):
        t.append(t[-1] + rng.uniform(*spec["gap"]))
    return t


def apply(mechanism, t, rng):
    """Return (recorded, culprit_positions). Culprit = position whose value is not its own."""
    n = len(t)
    r = list(t)
    if mechanism == "T1":
        i, j = sorted(rng.sample(range(n), 2))
        r[i], r[j] = r[j], r[i]
        return r, {i, j}
    if mechanism == "T2":
        order = list(range(n))
        rng.shuffle(order)
        pairs = [(order[2 * b], order[2 * b + 1]) for b in range(n // 2)]
        culprits = set()
        for i, j in pairs:
            r[i], r[j] = r[j], r[i]
            culprits |= {i, j}
        return r, culprits
    if mechanism == "ROT":
        lo = rng.randrange(0, n - 1)
        hi = rng.randrange(lo + 1, n)
        k = rng.randrange(1, hi - lo + 1)
        block = r[lo:hi + 1]
        r[lo:hi + 1] = block[-k:] + block[:-k]
        culprits = {p for p in range(lo, hi + 1) if r[p] != t[p]}
        return r, culprits
    if mechanism == "SHIFT":
        lo = rng.randrange(0, n - 1)
        hi = rng.randrange(lo + 1, n)
        block = r[lo:hi + 1]
        # move one element by one position inside the block
        p = rng.randrange(0, len(block) - 1)
        block[p], block[p + 1] = block[p + 1], block[p]
        r[lo:hi + 1] = block
        culprits = {q for q in range(lo, hi + 1) if r[q] != t[q]}
        return r, culprits
    raise ValueError(mechanism)


def descents(r):
    return [i for i in range(len(r) - 1) if r[i] >= r[i + 1]]


def rule_descent_ascent(r):
    d = descents(r)
    if not d:
        return set()
    return {d[0], d[-1] + 1}


def rule_interval_ends(r):
    """Endpoints of every maximal run of consecutive violated constraints."""
    out = set()
    for i in descents(r):
        if i == 0 or i - 1 not in descents(r):
            out.add(i)
    for i in descents(r):
        if i == len(r) - 2 or i + 1 not in descents(r):
            out.add(i + 1)
    return out


def rule_rank_offset(r, tolerance=0.5):
    """Positions whose rank differs from their index by more than half a place."""
    order = np.argsort(np.argsort(np.asarray(r, float)))
    return {p for p in range(len(r)) if abs(order[p] - p) > tolerance}


def identifiable_sets(r, size):
    """Every position subset of `size` whose removal leaves an increasing sequence."""
    n = len(r)
    out = []
    for keep in itertools.combinations(range(n), n - size):
        vals = [r[i] for i in keep]
        if all(vals[k] < vals[k + 1] for k in range(len(vals) - 1)):
            out.append(tuple(sorted(set(range(n)) - set(keep))))
    return out


def main():
    rng = random.Random(SEED)
    rows = []
    for n in (4, 5, 6, 7):
        for mechanism in ("T1", "T2", "ROT", "SHIFT"):
            hits = {"descent_ascent": 0, "interval_ends": 0, "rank_offset": 0}
            exact_perm = 0
            ambiguous = 0
            draws = 0
            for _ in range(DRAWS):
                t = true_chain(n, rng)
                r, culprits = apply(mechanism, t, rng)
                if not culprits:
                    continue
                draws += 1
                for name, rule in (("descent_ascent", rule_descent_ascent),
                                   ("interval_ends", rule_interval_ends),
                                   ("rank_offset", rule_rank_offset)):
                    hits[name] += rule(r) == culprits
                # is the culprit set recoverable in principle, from monotonicity alone?
                cand = identifiable_sets(r, len(culprits))
                exact_perm += tuple(sorted(culprits)) in cand
                ambiguous += len(cand) > 1
            rows.append({
                "n": n, "mechanism": mechanism, "draws": draws,
                "local_rule_exact": {k: v / draws for k, v in hits.items()},
                "culprit_set_admits_a_solution": exact_perm / draws,
                "culprit_set_is_unique": 1 - ambiguous / draws,
            })
            r = rows[-1]
            print(f"n={n} {mechanism:>5}: local rules exact "
                  f"desc/ascent {r['local_rule_exact']['descent_ascent']:.3f}  "
                  f"interval {r['local_rule_exact']['interval_ends']:.3f}  "
                  f"rank-offset {r['local_rule_exact']['rank_offset']:.3f} | "
                  f"admits {r['culprit_set_admits_a_solution']:.3f}  "
                  f"unique {(1 - ambiguous / draws):.3f}")

    out = Path("outputs/ordered-v3-design")
    out.mkdir(parents=True, exist_ok=True)
    (out / "mechanisms.json").write_text(json.dumps({
        "note": "combinatorial design study; no seeds consumed, no episodes sampled",
        "spec": REAL, "draws": DRAWS, "seed": SEED, "rows": rows,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
