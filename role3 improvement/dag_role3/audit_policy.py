"""The adjudication layer: audit objects a machine is not allowed to touch.

`supervisor.py` answers *what the delivery declares*. This module answers a
different question: *who is allowed to change the rules the declaration is
judged by*.

The distinction follows from one requirement, stated in `ENTROPY_LIMITS.md` §8:
the objectivity of a guarantee depends on separating the auditor from the
audited object. A machine may route on procedural signals, including entropy and
disagreement. It may not move the objects that decide what a status *means*,
because those are exactly the objects a self-auditing system would relax until
it always passed.

Four objects are adjudicated, and only a versioned human ratification may change
them:

* ``statuses``          -- which guarantee states exist and what each asserts.
* ``perspective_set``   -- who counts as a distinct viewpoint.
* ``independence_threshold`` -- how good a second party must be before its
  verdict may be read as absence of error. Currently the implicit ``p_catch``.
* ``construct_mapping`` -- which signal is allowed to be evidence for which
  construct. Per `ENTROPY_LIMITS.md` §5, confidence is *not* mapped to truth;
  making that absence explicit is the point of freezing the register.

Two things can still change during an evaluation, and must:

* individual claim statuses, by machine proposal followed by human
  ratification (``StatusLedger``);
* routing, by any procedural signal.

What cannot change during an evaluation is the policy. ``PolicyRegister``
enforces this: while an evaluation window is open, adjudication raises.

This module deliberately does not reach into ``supervisor.py``. The receipt is
frozen with its block; re-deriving it under a new policy would spend a block
without a pre-registration.
"""
from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "ADJUDICATED_FIELDS",
    "AuthorityError",
    "AuditPolicy",
    "FrozenPolicyError",
    "LedgerError",
    "PolicyRegister",
    "StatusLedger",
    "StatusProposal",
    "diff",
    "frozen_policy_v1",
    "is_machine",
]

ADJUDICATED_FIELDS = (
    "statuses",
    "perspective_set",
    "independence_threshold",
    "construct_mapping",
)

_MACHINE_NAMES = frozenset({"machine", "model", "agent", "auto", "system"})


class AuthorityError(Exception):
    """A machine attempted to move an adjudicated object."""


class FrozenPolicyError(Exception):
    """The policy was changed while an evaluation window was open."""


class LedgerError(Exception):
    """A status ratification violated append-only or policy conformance."""


def is_machine(who: str) -> bool:
    """True when the claimed authority is a machine rather than a person.

    Keyword-based on purpose: the failure this guards against is a pipeline that
    quietly passes its own name, not a determined forger.
    """
    name = (who or "").strip().lower()
    return name in _MACHINE_NAMES or name.startswith("auto:")


@dataclass(frozen=True)
class AuditPolicy:
    """One ratified version of the audit policy.

    Frozen so that a caller cannot mutate the incumbent in place. Changes produce
    a new object with ``version + 1`` and a fresh ratification.
    """

    version: int
    statuses: tuple[tuple[str, str], ...]
    perspective_set: tuple[str, ...]
    independence_threshold: float
    construct_mapping: tuple[tuple[str, str], ...]
    ratified_by: str
    rationale: str
    at: str

    def fingerprint(self) -> str:
        """Stable description a delivery can quote, so a reader knows the rules."""
        return (
            f"v{self.version}"
            f":p_catch>={self.independence_threshold:.2f}"
            f":statuses={len(self.statuses)}"
            f":perspectives={len(self.perspective_set)}"
            f":constructs={len(self.construct_mapping)}"
        )

    def status_names(self) -> tuple[str, ...]:
        return tuple(name for name, _ in self.statuses)


def diff(previous: AuditPolicy, new: AuditPolicy) -> tuple[str, ...]:
    """Which adjudicated fields a change would move. Empty means a no-op."""
    return tuple(f for f in ADJUDICATED_FIELDS if getattr(previous, f) != getattr(new, f))


def frozen_policy_v1() -> AuditPolicy:
    """The constants that are currently implicit in `supervisor.py`, named.

    Nothing here is a new decision. ``p_catch = 0.9`` is the environment's
    reviewer hit rate; the four statuses are `STATUSES` in `supervisor.py`; the
    six perspectives are the benchmark families; the construct map is the pair of
    channels §5 of `ENTROPY_LIMITS.md` admits, with confidence-to-truth
    deliberately absent.
    """
    return AuditPolicy(
        version=1,
        statuses=(
            ("inspected", "every source reaching this sink was reviewed"),
            ("partial", "some but not all upstream sources were reviewed"),
            ("untouched", "no upstream source was reviewed"),
            ("escalated", "refusal: coverage cannot be established"),
        ),
        perspective_set=("spike", "modular", "real", "ticket", "ba", "er"),
        independence_threshold=0.9,
        construct_mapping=(
            ("reviewer_verdict", "source_error_absent"),
            ("coverage_log", "review_completeness"),
        ),
        ratified_by="repo-owner",
        rationale="codify the constants the supervisor layer already used",
        at="2026-11-25",
    )


class PolicyRegister:
    """Append-only history of ratified policies, with an evaluation lock."""

    def __init__(self, policy: AuditPolicy | None = None):
        self._history = [policy or frozen_policy_v1()]
        self._open = False

    @property
    def current(self) -> AuditPolicy:
        return self._history[-1]

    @property
    def history(self) -> tuple[AuditPolicy, ...]:
        return tuple(self._history)

    @property
    def open(self) -> bool:
        return self._open

    def begin_evaluation(self) -> None:
        if self._open:
            raise FrozenPolicyError("an evaluation window is already open")
        self._open = True

    def end_evaluation(self) -> None:
        self._open = False

    def assert_frozen(self) -> None:
        """Raise unless the policy would still hold if the evaluation ended now."""
        if self._open:
            raise FrozenPolicyError("audit policy is frozen for this evaluation")

    def adjudicate(
        self,
        new: AuditPolicy,
        *,
        ratified_by: str,
        rationale: str,
        at: str,
    ) -> AuditPolicy:
        """Install a new policy version. Human only, and never mid-evaluation.

        The order matters. Authority is checked before the freeze so that a
        machine attempt is always reported as what it is, not as a scheduling
        problem.
        """
        if is_machine(ratified_by) or is_machine(new.ratified_by):
            raise AuthorityError(
                "guarantee status, perspective set, independence threshold and "
                "construct mapping require human adjudication"
            )
        self.assert_frozen()
        if new.version != self.current.version + 1:
            raise ValueError(
                f"policy versions are consecutive: got {new.version} after "
                f"{self.current.version}"
            )
        changed = diff(self.current, new)
        if not changed:
            raise ValueError("no adjudicated field changed")
        if not rationale.strip():
            raise ValueError("an adjudication needs a rationale")
        if not at.strip():
            raise ValueError("an adjudication needs a date")
        if not ratified_by.strip():
            raise ValueError("an adjudication needs a ratifier")
        self._history.append(new)
        return new


@dataclass(frozen=True)
class StatusProposal:
    """A machine's arithmetic about one claim. Not yet a guarantee."""

    claim_id: str
    status: str
    basis: str
    policy_version: int


@dataclass(frozen=True)
class Ratification:
    """A human's signature on one proposal, versioned per claim."""

    claim_id: str
    status: str
    proposal: StatusProposal
    ratified_by: str
    at: str
    version: int


class StatusLedger:
    """Append-only status history: proposals are free, statuses are ratified.

    The gate is the same separation as the policy register, applied per claim. A
    machine may propose as often as it likes; a status exists only once a person
    has signed it, and a later signature supersedes rather than overwrites.
    """

    def __init__(self, policy: AuditPolicy):
        self._policy = policy
        self._rows: list[Ratification] = []

    @property
    def policy(self) -> AuditPolicy:
        return self._policy

    def ratify(self, proposal: StatusProposal, *, ratified_by: str, at: str) -> Ratification:
        if is_machine(ratified_by):
            raise AuthorityError("a machine may propose a status, not ratify one")
        if proposal.status not in self._policy.status_names():
            raise LedgerError(
                f"{proposal.status!r} is not a status of {self._policy.fingerprint()}"
            )
        if proposal.policy_version != self._policy.version:
            raise LedgerError(
                f"proposal was computed under v{proposal.policy_version}, "
                f"ledger holds v{self._policy.version}"
            )
        if not at.strip():
            raise ValueError("a ratification needs a date")
        row = Ratification(
            claim_id=proposal.claim_id,
            status=proposal.status,
            proposal=proposal,
            ratified_by=ratified_by,
            at=at,
            version=len(self.history(proposal.claim_id)) + 1,
        )
        self._rows.append(row)
        return row

    def history(self, claim_id: str) -> tuple[Ratification, ...]:
        return tuple(r for r in self._rows if r.claim_id == claim_id)

    def latest(self, claim_id: str) -> Ratification | None:
        rows = self.history(claim_id)
        return rows[-1] if rows else None

    def claims(self) -> tuple[str, ...]:
        seen: list[str] = []
        for row in self._rows:
            if row.claim_id not in seen:
                seen.append(row.claim_id)
        return tuple(seen)

    def statuses(self) -> dict[str, str]:
        """Current ratified status per claim — the only statement the ledger makes."""
        return {c: self.latest(c).status for c in self.claims()}
