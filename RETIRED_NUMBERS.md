# Retired numbers

A number retires when the run that produced it stops being the run we cite: a seed
block turns out to be contaminated, a metric is redefined, a script had a bug. The
new number goes into the documents; the old one must not survive anywhere a reader
could take it as current.

That is not free. The exact-DP rerun (`79fb5b1`) moved fourteen files to block
5000–5023 and still left the old P2 miss in three paper drafts, one planning note,
and a guard that asserted the old value was present. The guard exists so the next
rerun is a one-line registry entry instead of a hunt.

## How to retire a number

1. Land the replacement run first. A retired number needs a live successor.
2. Add a row to the block below: the old value as a regex, the new value, the commit
   that superseded it, and the paths where the old value may legitimately remain.
3. Run `python3 experiments/test_retired_numbers.py`. Every other `.md` in the repo
   must be clean.
4. Never allowlist a living document to make the test pass. The allowlist is for
   frozen evidence — run directories, amendments, pre-registrations — and for this
   file.

Two things the allowlist must never hold: the paper drafts, and anything under
`experiments/` that is interpretation rather than output. If a frozen prereg quotes
a number that later moved, allowlist the prereg; editing it would be worse than the
stale number.

## The registry

Patterns are matched against the whole file, after `U+2212` is folded to `-`. Keep
them specific enough that they cannot fire on an unrelated run's value: `0.0219` is
a retirement, `1.73` is not (the block-review table legitimately has 1.73 errors
with no review at all), which is why the ratio entry is written `ratio 1\.73`.

<!-- retired:begin -->
# pattern	replacement	superseded by	still allowed in (comma-separated globs)	why
0\.0219	-0.030	79fb5b1	role3 improvement/outputs/**,PREREGISTER_*.md	DP ceiling rerun on a clean block; `dp − marginal` on `real`
[−-]0\.0059	-0.002	79fb5b1	role3 improvement/outputs/**,PREREGISTER_*.md	same rerun; `dp − marginal` on `ticket` (sign-anchored: an unsigned 0.0059 is a different run's value)
ratio 1\.73	ratio 1.81	79fb5b1	role3 improvement/outputs/**,PREREGISTER_*.md	same rerun; planning value sub-linearity (P3)
missed by 0\.0019	missed by 0.0083	79fb5b1	role3 improvement/outputs/**,PREREGISTER_*.md	same rerun; P2 shortfall against the nominal 0.02 bound
<!-- retired:end -->

The first DP run was not wrong, it was measured on the wrong block: `PREREGISTER_DP.md`
asked for a block nothing had touched and named 60000–60023, which `BestValidation`
already evaluates for every trained model. That run stays on disk as the sensitivity
check, so its numbers are frozen evidence and stay allowlisted — but they are not
citable as the ceiling.
