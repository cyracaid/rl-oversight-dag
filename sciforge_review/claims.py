"""Claim-level audit primitives (shape B).

This is the interface, not the full reading pipeline.  A claim carries a
verbatim span; the sufficiency gate refuses to call it supported when the
evidence is missing or implausible.  The rules mirror the failure taxonomy we
borrowed from BioBasicsBench and the errors the 3-paper pilot actually caught:

    no control / missing n / implausible effect size / incomplete statistics
        -> insufficient, with reasons.

The point is to make "insufficient evidence" a first-class, scorable action
rather than a silent default.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ClaimKind(str, Enum):
    RESULT = "result"
    METHOD = "method"
    LIMITATION = "limitation"
    DEFINITION = "definition"


class ClaimVerdict(str, Enum):
    SUPPORTED = "supported"
    INSUFFICIENT = "insufficient"
    CONTRADICTED = "contradicted"


@dataclass(frozen=True)
class Span:
    section: str
    char_start: int
    char_end: int
    quote: str

    def __post_init__(self) -> None:
        if self.char_end <= self.char_start:
            raise ValueError("char_end must be greater than char_start")
        if not self.quote.strip():
            raise ValueError("quote must not be empty")


@dataclass(frozen=True)
class Claim:
    claim_id: str
    text: str
    span: Span
    kind: ClaimKind = ClaimKind.RESULT


@dataclass(frozen=True)
class Sufficiency:
    verdict: ClaimVerdict
    reasons: tuple[str, ...]


def span_is_verbatim(claim: Claim, source_text: str) -> bool:
    """Mechanical check: the quote must occur at the recorded offsets."""
    start, end = claim.span.char_start, claim.span.char_end
    return source_text[start:end] == claim.span.quote


def sufficiency_check(
    claim: Claim,
    *,
    has_control: bool | None,
    n: int | None,
    effect_size: float | None,
    stats_complete: bool,
) -> Sufficiency:
    """Checklist gate for a result claim.

    Returns ``insufficient`` with every reason that fired; an empty reason
    tuple means the claim passed the checklist (not that it is true).
    """
    if claim.kind is not ClaimKind.RESULT:
        return Sufficiency(ClaimVerdict.SUPPORTED, ("not a result claim",))

    reasons: list[str] = []
    if has_control is None:
        reasons.append("control condition not reported")
    elif not has_control:
        reasons.append("no control condition")
    if n is None:
        reasons.append("sample size not reported")
    elif n <= 0:
        reasons.append("invalid sample size")
    if effect_size is not None and abs(effect_size) > 3.0:
        reasons.append(f"implausible effect size ({effect_size:g})")
    if not stats_complete:
        reasons.append("statistical reporting incomplete")

    if reasons:
        return Sufficiency(ClaimVerdict.INSUFFICIENT, tuple(reasons))
    return Sufficiency(ClaimVerdict.SUPPORTED, ())
