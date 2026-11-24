"""The sleep labels in the shape both instances publish.

`error_type = {layer, code}` is the shared meta-schema (see `../ERROR_TAXONOMY.md`):
the code sets are closed per instance, and `layer` is the only field comparable
across instances.

Every sleep correction is a value-level defect — the datum exists, it is cited in the
pipeline, and it is simply wrong — so the layer belongs to the instance, not to a
table of per-code lookups. That is why this module does not enumerate the six known
codes: a code nobody has seen yet is still a value-layer defect, and a lookup table
would silently drop it instead of labelling it.

The SciForge side does the opposite for the same reason: its audit findings split
9 evidence / 6 argument, because there the layer really does vary per code.
"""

from __future__ import annotations

import math
from typing import Any

LAYER = "value"

# What the correction file holds when a row was corrected but never typed.
MISSING = "(unlabeled)"


def as_error_type(code: Any) -> dict[str, str] | None:
    """Wrap one sleep correction type as `{layer, code}`, or `None` if there is none."""
    if code is None:
        return None
    if isinstance(code, float) and math.isnan(code):
        return None
    text = str(code).strip()
    if not text or text == MISSING:
        return None
    return {"layer": LAYER, "code": text}


def as_key(code: Any) -> str:
    """The same label as a stable string key, for counters and JSON objects."""
    pair = as_error_type(code)
    return MISSING if pair is None else f"{pair['layer']}:{pair['code']}"
