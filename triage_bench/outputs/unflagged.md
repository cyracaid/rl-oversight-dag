# The corrections the queue never sees

These rows are `human_review == corrected` but never got a FLAG, so no
ranking policy -- learned or hand-written -- can surface them.

## Narrow set: 7 of 72

| error_type | n |
|---|---:|
| (unlabeled) | 3 |
| sleep_awake_equal_error | 2 |
| awake_getup_diff_error | 1 |
| order_error | 1 |

| corrected column | n |
|---|---:|
| time_awake_corrected | 6 |
| time_sleep_corrected | 1 |

Audit verdict on those rows: `AUTO_PASS` 6, `absent` 1

## Broad set: 17 of 85

| has_correction | n |
|---|---:|
| manual | 17 |

## Does one obvious rule fix it?

`final awakening == get-up` (the raw signature behind several awake/getup
corrections):

- rows firing: **507**
- corrected rows inside: **33** -> precision **6.5%**
- of the unflagged broad rows it would catch: **5**

Its precision equals the queue base rate (6.5%), so it is not a new
discriminator -- it is the same haystack with a different label. The fix
has to change *what is observed* (cross-field consistency), not where the
threshold sits.
