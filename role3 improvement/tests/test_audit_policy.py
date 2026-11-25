"""Tests for the adjudication layer: who may move an audit object."""
import unittest
from dataclasses import replace

from dag_role3.audit_policy import (
    ADJUDICATED_FIELDS,
    AuthorityError,
    AuditPolicy,
    FrozenPolicyError,
    LedgerError,
    PolicyRegister,
    StatusLedger,
    StatusProposal,
    diff,
    frozen_policy_v1,
    is_machine,
)
from dag_role3.supervisor import STATUSES


def bumped(base: AuditPolicy, **changes) -> AuditPolicy:
    """The next version of ``base``, with the given adjudicated field changed."""
    return replace(base, version=base.version + 1, **changes)


class AuthorityTests(unittest.TestCase):
    def setUp(self):
        self.register = PolicyRegister()
        self.base = self.register.current

    def test_machine_names_are_recognised(self):
        for name in ("machine", "Model ", "AUTO", "auto:planner", "agent"):
            self.assertTrue(is_machine(name), name)
        for name in ("repo-owner", "j.kim", "reviewer-2", ""):
            self.assertFalse(is_machine(name), name)

    def test_each_adjudicated_field_is_closed_to_a_machine(self):
        changes = {
            "statuses": self.base.statuses + (("clean", "nothing to report"),),
            "perspective_set": self.base.perspective_set + ("triage_bench",),
            "independence_threshold": 0.5,
            "construct_mapping": self.base.construct_mapping
            + (("confidence", "truth"),),
        }
        self.assertEqual(tuple(changes), ADJUDICATED_FIELDS)
        for field, value in changes.items():
            with self.subTest(field=field):
                new = replace(bumped(self.base, **{field: value}), ratified_by="machine")
                with self.assertRaises(AuthorityError):
                    self.register.adjudicate(
                        new, ratified_by="machine", rationale="x", at="2026-11-25"
                    )
                self.assertEqual(self.register.current, self.base)

    def test_machine_field_is_rejected_even_when_ratifier_is_human(self):
        new = replace(bumped(self.base, independence_threshold=0.5), ratified_by="machine")
        with self.assertRaises(AuthorityError):
            self.register.adjudicate(
                new, ratified_by="repo-owner", rationale="x", at="2026-11-25"
            )

    def test_status_names_match_the_frozen_supervisor(self):
        self.assertEqual(self.base.status_names(), STATUSES)


class FreezeTests(unittest.TestCase):
    def test_adjudication_is_refused_mid_evaluation(self):
        register = PolicyRegister()
        register.begin_evaluation()
        new = bumped(register.current, independence_threshold=0.5)
        with self.assertRaises(FrozenPolicyError):
            register.adjudicate(new, ratified_by="repo-owner", rationale="x", at="2026-11-25")
        self.assertEqual(register.current.version, 1)

    def test_authority_is_reported_before_the_freeze(self):
        register = PolicyRegister()
        register.begin_evaluation()
        new = replace(bumped(register.current, independence_threshold=0.5), ratified_by="machine")
        with self.assertRaises(AuthorityError):
            register.adjudicate(new, ratified_by="machine", rationale="x", at="2026-11-25")

    def test_adjudication_works_once_the_window_closes(self):
        register = PolicyRegister()
        register.begin_evaluation()
        register.end_evaluation()
        new = bumped(register.current, independence_threshold=0.5)
        register.adjudicate(new, ratified_by="repo-owner", rationale="x", at="2026-11-25")
        self.assertEqual(register.current.version, 2)
        self.assertEqual(len(register.history), 2)

    def test_nested_windows_are_refused(self):
        register = PolicyRegister()
        register.begin_evaluation()
        with self.assertRaises(FrozenPolicyError):
            register.begin_evaluation()


class VersionTests(unittest.TestCase):
    def test_versions_are_consecutive(self):
        register = PolicyRegister()
        new = replace(register.current, version=3, independence_threshold=0.5)
        with self.assertRaises(ValueError):
            register.adjudicate(new, ratified_by="repo-owner", rationale="x", at="2026-11-25")

    def test_a_no_op_is_not_a_version(self):
        register = PolicyRegister()
        new = replace(register.current, version=2)
        with self.assertRaises(ValueError):
            register.adjudicate(new, ratified_by="repo-owner", rationale="x", at="2026-11-25")

    def test_diff_names_every_changed_field(self):
        base = frozen_policy_v1()
        cases = {
            "statuses": base.statuses[:-1],
            "perspective_set": base.perspective_set[:3],
            "independence_threshold": 0.75,
            "construct_mapping": base.construct_mapping[:1],
        }
        for field, value in cases.items():
            with self.subTest(field=field):
                self.assertEqual(diff(base, replace(base, **{field: value})), (field,))
        self.assertEqual(diff(base, base), ())

    def test_an_adjudication_needs_a_rationale_date_and_ratifier(self):
        register = PolicyRegister()
        base = register.current
        for kwargs in (
            {"rationale": "  "},
            {"at": ""},
            {"ratified_by": "  "},
        ):
            args = {"ratified_by": "repo-owner", "rationale": "why", "at": "2026-11-25"}
            args.update(kwargs)
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                register.adjudicate(
                    bumped(base, independence_threshold=0.5), **args
                )
            self.assertEqual(register.current, base)

    def test_history_is_append_only(self):
        register = PolicyRegister()
        first = register.current
        register.adjudicate(
            bumped(first, independence_threshold=0.8),
            ratified_by="repo-owner",
            rationale="tighten",
            at="2026-11-25",
        )
        self.assertEqual(register.history[0], first)
        self.assertEqual([p.version for p in register.history], [1, 2])


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.policy = frozen_policy_v1()
        self.ledger = StatusLedger(self.policy)
        self.proposal = StatusProposal(
            claim_id="sink-3",
            status="partial",
            basis="1 of 3 upstream sources reviewed",
            policy_version=self.policy.version,
        )

    def test_a_machine_may_not_ratify(self):
        with self.assertRaises(AuthorityError):
            self.ledger.ratify(self.proposal, ratified_by="machine", at="2026-11-25")
        self.assertEqual(self.ledger.claims(), ())

    def test_an_unlisted_status_is_not_admissible(self):
        bad = replace(self.proposal, status="clean")
        with self.assertRaises(LedgerError):
            self.ledger.ratify(bad, ratified_by="repo-owner", at="2026-11-25")

    def test_a_proposal_from_another_policy_version_is_refused(self):
        stale = replace(self.proposal, policy_version=self.policy.version + 1)
        with self.assertRaises(LedgerError):
            self.ledger.ratify(stale, ratified_by="repo-owner", at="2026-11-25")

    def test_ratification_is_versioned_and_supersedes(self):
        first = self.ledger.ratify(self.proposal, ratified_by="repo-owner", at="2026-11-25")
        second = self.ledger.ratify(
            replace(self.proposal, status="inspected", basis="3 of 3 reviewed"),
            ratified_by="repo-owner",
            at="2026-11-26",
        )
        self.assertEqual((first.version, second.version), (1, 2))
        self.assertEqual(self.ledger.latest("sink-3").status, "inspected")
        self.assertEqual(len(self.ledger.history("sink-3")), 2)
        self.assertEqual(self.ledger.statuses(), {"sink-3": "inspected"})

    def test_the_earlier_row_is_untouched(self):
        first = self.ledger.ratify(self.proposal, ratified_by="repo-owner", at="2026-11-25")
        self.ledger.ratify(
            replace(self.proposal, status="inspected"),
            ratified_by="repo-owner",
            at="2026-11-26",
        )
        self.assertEqual(self.ledger.history("sink-3")[0], first)
        self.assertEqual(first.status, "partial")

    def test_unknown_claim_has_no_status(self):
        self.assertIsNone(self.ledger.latest("sink-9"))
        self.assertEqual(self.ledger.statuses(), {})


class FingerprintTests(unittest.TestCase):
    def test_fingerprint_carries_version_and_all_four_objects(self):
        text = frozen_policy_v1().fingerprint()
        self.assertTrue(text.startswith("v1:"))
        for part in ("p_catch>=0.90", "statuses=4", "perspectives=6", "constructs=2"):
            self.assertIn(part, text)


if __name__ == "__main__":
    unittest.main()
