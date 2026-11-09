# Audit chain demo: receipts to recall per minute

Chain verified: **True** (ok); 200 receipts, median review 62s at an assumed 30s per field.

| review budget | row-level (4 fields) | witness pair (2 fields) |
|---|---:|---:|
| 30 min | 4.4% | 8.8% |
| 60 min | 8.8% | 25.0% |
| 120 min | 25.0% | 63.2% |
| 240 min | 63.2% | 83.8% |

| target recall | row-level | witness pair |
|---|---:|---:|
| 25pct | 115 min | 58 min |
| 50pct | 195 min | 98 min |
| 75pct | 279 min | 139 min |


The per-field seconds are an assumption; the ratio is not. Replace the
assumption with the median from real receipts and the table rescales.

Receipt log: `outputs/demo_receipts.jsonl` (subject ids hashed, no raw keys).
