# claim_graph — review coverage for an external case

Read-only. Takes a case repository's published claim tables, rebuilds the
per-batch ratios from the raw batch table, and writes a coverage receipt: what a
review budget of B claims can inspect, and what part of the weak mass it cannot.

Contract (what may be cited, what may not): `../CLAIM_GRAPH_CONTRACT.md`.

## Run

```bash
# from the repository root
PYTHONPATH=. python3 claim_graph/run_cuda_receipt.py
PYTHONPATH=. python3 -m unittest discover -s claim_graph -t .
```

Writes `claim_graph/outputs/cuda-case/receipt.{json,md}`. Tables are fetched at a
pinned commit and cached under `claim_graph/.cache/`; digests land in the receipt.

## Files

| file | role |
|---|---|
| `case.py` | fetch pinned tables, verify digests, rebuild ratios, build claims |
| `plan.py` | orderings, budget coverage, receipt JSON and Markdown |
| `run_cuda_receipt.py` | CLI |
| `tests/test_case.py` | 10 tests, no network |

## Result on the CUDA case (`2538d57`)

| quantity | value |
|---|---:|
| claims | 2016 |
| published as supported | 1057 |
| weak (a batch disagrees) | 1112 |
| weak and published | 230 |
| weak and filtered out | 882 |

Weak mass covered at B=128: 13.9% in table order, 55.6% weakest-first,
48.7% when spread across cells.

A weak claim is not a wrong claim. The receipt says this in its own text,
because the easiest misuse of it is to read 230 as an error count.
