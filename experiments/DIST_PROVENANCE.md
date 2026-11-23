# Distillation artifacts: provenance and admissibility

2026-11-23. These two files were sitting untracked in `experiments/`. They are
archived here so nothing is lost, **not** because they support a claim.
`BOUNDARY_PREREG.md` already states that `dist_table.md` conflicts with
`dist_results.json` and is inadmissible until reproduced. That verdict stands.

## `dist_results.json` — smoke run, not a result

Read the config block, not the means:

```json
"graphs": 40, "bc_epochs": 1, "episodes": 30, "seeds": [1],
"heldout": 20, "lr_bc": 0.001, "lr_ft": 0.003, "kl_beta": 0.5,
"smoke": true
```

One seed, one behaviour-cloning epoch, thirty fine-tuning episodes, twenty
held-out graphs. Teacher 1.0, BC 5.1, FT 5.1, and `ft_curve` is empty, so no
fine-tuning trajectory was recorded at all.

What it does establish: the distillation harness trains, evaluates and writes
JSON without crashing. What it does not establish: anything about behaviour
cloning versus fine-tuning. A BC gap of four errors on a one-epoch smoke run is
an implementation signal, not a finding.

Missing for reproducibility: no config hash, no code hash, no graph seed list in
the file. The generator script is **not** in this repository, so the numbers
cannot be re-derived from what is saved here.

## `dist_table.md` — unprovenanced, do not cite

```text
N=80, budget=16, 3 seed(s) x 20000 FT episodes, held-out n=200
teacher 1.15 | BC only 1.14 | BC + REINFORCE 1.15
```

This configuration matches no saved artifact:

| | `dist_results.json` | `dist_table.md` |
|---|---|---|
| graphs | 40 | 80 |
| seeds | 1 | 3 |
| FT episodes | 30 | 20000 |
| held-out | 20 | 200 |
| teacher mean | 1.00 | 1.15 |

No run directory, no JSON, and no script producing these numbers exists in the
repository. Treat the table as a note of an intended experiment, not a result.
If the run is recovered, add the artifact under `runs/` and regenerate the table
from it; until then the honest citation is "not available".

## Rule this file enforces

A table that cannot be regenerated from a saved artifact with a recorded config
is not evidence. Both files stay in the repository as a paper trail, and both
carry this banner.
