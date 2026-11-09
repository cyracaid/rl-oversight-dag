# Traceability demo — change at `time_awake` (v1 → v2)

Affected nodes: **8 / 21**  |  conclusions affected: **2 / 4**  |  stale receipts: **8**, still valid: **13**

> No node is marked wrong. The system asserts only *affected* and *stale*; whether a conclusion still holds is a human verdict.

| node | kind | distance | path from the change |
|---|---|---:|---|
| `time_awake` | raw input | 0 | time_awake |
| `awake_getup_diff` | derived | 1 | time_awake → awake_getup_diff |
| `sleep_awake_diff` | derived | 1 | time_awake → sleep_awake_diff |
| `TST` | metric | 2 | time_awake → sleep_awake_diff → TST |
| `SE` | metric | 3 | time_awake → sleep_awake_diff → TST → SE |
| `TST_TIB_ratio` | metric | 3 | time_awake → sleep_awake_diff → TST → TST_TIB_ratio |
| `SE_conclusion` **(conclusion)** | conclusion | 4 | time_awake → sleep_awake_diff → TST → SE → SE_conclusion |
| `record_quality` **(conclusion)** | conclusion | 5 | time_awake → sleep_awake_diff → TST → SE → SE_conclusion → record_quality |

## Receipts invalidated by the change

`8` of 21 review receipts are bound to an earlier version of an affected node. They are **marked stale, not deleted**: the record of the review still exists, it just no longer covers the current version.

## The test a second researcher has to pass

1. pick a conclusion in the table above;
2. follow its path back to the changed input;
3. say which assumption the change touches;
4. say whether the existing receipt still covers it.

If they can do that without asking the author, the trace is doing its job.
