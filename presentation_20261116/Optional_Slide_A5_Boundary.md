# Optional appendix slide — the boundary (A5)

Not in the deck. Add only if someone asks *why spike wins but real/ticket tie*, or if the
teacher pushes on "is graph structure useful at all". Numbers are from
`experiments/BOUNDARY_REPORT.md`; nothing here is new data.

**Slide title:** Where does graph-aware triage actually pay?

**Body (three lines, no bullet nesting):**

- Three published results, one axis we never plotted: **review budget ÷ nodes**
  - spike 20 % → **+6.2 pp** · real 38 % → **+1.3 pp** · ticket 38 % → **+1.6 pp**
- Sweeping the budget on the real topology: 10 % → **+16.8 pp**, 38 % → **+1.3 pp**, ≥67 % → **0**
- **16 reviews = +6.2 pp at n=80, +0.3 pp at n=21.** Not the count; the coverage.

**Footer:** `experiments/BOUNDARY_REPORT.md` · 200 paired draws per point · error-realization bootstrap

---

## Speaker note (35 s)

Take the three numbers we already showed and put them on one axis: how much of the graph the
budget covers. Spike got 16 reviews out of 80 nodes — 20 %. Real and ticket got 8 out of 21 —
38 %. On one axis they stop being three findings and become one curve.

Then sweep it directly: same 21-node topology, only the budget changes. At 10 % coverage the
graph rule removes 17 percentage points more of the errors than greedy minimum-confidence.
At 38 % it is 1.3 points, with an interval through zero. Past two thirds, exactly nothing.

The sharpest version: 16 reviews give 6.2 points at eighty nodes and 0.3 points at twenty-one.
So the claim is not *graph structure helps*. The claim is **it helps only while the budget is
still smaller than the error surface** — and both real and ticket sit on the flat part of that
curve. That is why they tie. It is not a property of those domains.

## If asked "so what should we do?"

- Below ~30 % coverage: order matters, use the graph.
- Above ~50 %: ordering is not the lever. Spend the effort on what gets observed, not on ordering.
- The 500-node families are the ones with low coverage, which is where the +8 to +20 error
  gains came from — consistent with the same curve.

## Do not say

- "Graph-aware review is generally better." It is not, above half coverage.
- "This predicts real data." It is a simulator; the real chain's review counts are not the same
  budget definition.
- "Win rates were low, so the method is weak." 96 % of realizations are exact ties at 38 %;
  ties are the expected state on the flat part of the curve.
