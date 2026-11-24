# Amendment to the verdict code — recorded, not silent

Date: 2026-11-24, after the first complete report.

## What changed

`P2` was tested as `dp5 − greedy_exact <= 0.02`, a **signed** comparison. Deltas in this
project are `policy − comparison`, so a planning gain is negative and the signed test
passes for *any* gain whatsoever. The first report printed:

    | P2 | value of planning (dp5 − greedy_exact) ≤ 0.02 | -0.0219 | holds |

`-0.0219` is a gain of **0.0219**, which is above the 0.02 the prediction named. The
verdict was right by accident and the comparison was not testing the claim.

The check is now on magnitude, against the threshold `PREREGISTER_DP.md` itself fixed for
falsification (`> 0.05`), and the nominal miss is printed rather than rounded away. `P5`
was signed too and is now `abs(...) < 0.10`; that one changes nothing here because both
measured values are negative.

## Why this is admissible after seeing results

The correction makes the reported result **worse**, not better:

- before: `holds`, no qualification
- after: `holds — nominal 0.02 missed by 0.0019; still inside the 0.05 falsification bound`

A post-hoc edit that files its own result closer to falsification is not a degree of
freedom being spent on the answer. The alternative — leaving a signed comparison in place
because it happened to produce the friendlier table — is exactly the failure mode this
repo has a test for elsewhere (`experiments/test_published_numbers.py`).

## What did not change

- `dp_episodes.csv` sha256 `0236eba3…27000` — untouched. Re-running graph 60000 with the
  current code reproduces its five rows bit-for-bit.
- No prediction threshold was edited. `PREREGISTER_DP.md` is unchanged.
- `exact_dp.py` sha256 at run time was `c32bd619…f01e6d` (in `manifest.json`); the current
  file differs only in `report()` and in the added source-hash block. `--report` reads the
  CSV and writes markdown; it computes no episode value.

## Reproduction

    cd "role3 improvement"
    python3 exact_dp.py --report --out outputs/dp-ceiling   # regenerates report.md
    python3 -m pytest tests/test_exact_dp.py -q             # 8 pass
