"""Tier-A step definitions for the commit-author-identity acceptance suite.

Mandate-12: every step body is ≤2 statements, the final action statement is a
``composition.<method>(...)`` call (or a single observable assertion), and no
control flow appears in any body. The DSL emerges from typed ``parsers.parse``
converters over the ``domain_types`` enums — a handful of parameterized
decorators cover the whole literal space instead of a decorator-per-literal
explosion.

Pillar 3: the ``IdentityComposition`` builds the SUT from the production
validator entries (the pure functions + the three ``main()`` subprocess entries)
over a real isolated git repo. Pillar 2: the ``Given a fresh repository`` step is
reused across every enforcement-layer scenario (chained narrative via step
reuse, never copy-pasted fixture setup).

Layer split (Mandate 9 + 11):
- validator-core scenarios run at layer 1/2 (pure, direct call) and carry the
  ``@property`` PBT scenarios — Hypothesis ``@given`` is wired in the companion
  ``test_identity_core_properties.py`` module (this file holds the example-based
  Scenario Outlines; pytest-bdd binds the ``@property`` Gherkin scenarios to the
  same step vocabulary).
- enforcement-layer scenarios run at layer 3 (real git subprocess) and are
  example-only — no Hypothesis here.

All slices have landed (``conftest._PENDING_SLICE_TAGS`` is empty), so every
scenario in this directory runs against the real validator — nothing here is
skipped. This module holds no scenarios itself; it is the shared step library
imported by the sibling ``test_*.py`` binding modules.
"""

from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, then, when

from tests.des.acceptance.commit_author_identity.steps.composition import (
    IdentityComposition,
)
from tests.des.acceptance.commit_author_identity.steps.domain_types import (
    CommitBypass,
    EmailClass,
    IdentityRole,
    NameClass,
    PushRangeShape,
    Verdict,
)


# Note: ``scenarios(...)`` is NOT called here. pytest collects test functions
# from ``test_*.py`` modules only (default ``python_files``), so the Gherkin
# bindings live in the sibling ``test_*.py`` files which ``import *`` this
# vocabulary. This module is the shared step library (Pillar 2 + Mandate-12
# single vocabulary), imported by every binding module and by any Tier B state
# machine.


# ---------------------------------------------------------------------------
# Parser converters — coerce Gherkin enum-member NAMEs to typed enums.
# One typed decorator per enum covers the whole literal space (DSL emergence).
# ---------------------------------------------------------------------------

_ENUM_TOKEN = r"[A-Za-z0-9_-]+"


def _by_name(enum_cls):
    def convert(text: str):
        return enum_cls[text]

    convert.pattern = _ENUM_TOKEN
    convert.__name__ = f"convert_{enum_cls.__name__}"
    return convert


_EXTRA = {
    "EmailClass": _by_name(EmailClass),
    "NameClass": _by_name(NameClass),
}


# ---------------------------------------------------------------------------
# Fixtures — one composition per scenario (fresh world; Pillar 2 chaining is
# via step reuse within a scenario, not shared state across scenarios).
# ---------------------------------------------------------------------------


@pytest.fixture
def composition() -> IdentityComposition:
    return IdentityComposition()


# ---------------------------------------------------------------------------
# Given — preconditions (input state only; never the expected output)
# ---------------------------------------------------------------------------


@given("the maintainer is reviewing commit identities")
def given_reviewing_identities(composition: IdentityComposition) -> None:
    # Pure validator core needs no repo — the review context is a no-op marker
    # so the Gherkin reads as a complete sentence (Pillar 1).
    composition.world.captured_output = ""


@given("a fresh repository")
def given_fresh_repository(composition: IdentityComposition, tmp_path) -> None:
    composition.given_a_fresh_repository(tmp_path)


# ---------------------------------------------------------------------------
# When — validator-core driving port (layer 1/2, pure)
# ---------------------------------------------------------------------------


@when(
    parsers.parse(
        'the validator judges an email of class "{email_class:EmailClass}"',
        extra_types=_EXTRA,
    )
)
def when_judge_email(composition: IdentityComposition, email_class: EmailClass) -> None:
    composition.validate_email_of_class(email_class)


@when(
    parsers.parse(
        'the validator judges a name of class "{name_class:NameClass}"',
        extra_types=_EXTRA,
    )
)
def when_judge_name(composition: IdentityComposition, name_class: NameClass) -> None:
    composition.validate_name_of_class(name_class)


@when("the validator judges any GitHub no-reply address")
def when_judge_any_noreply(composition: IdentityComposition) -> None:
    # Representative member of the allowlisted class — the unbounded universal
    # invariant ("every no-reply address is accepted") is exercised by the PBT
    # module test_identity_core_properties.py; this example pins the canonical case.
    composition.validate_email_of_class(EmailClass.NOREPLY_NUMERIC)


@when("the validator judges a placeholder address paired with any name")
def when_judge_placeholder_with_any_name(composition: IdentityComposition) -> None:
    composition.validate_email_of_class(EmailClass.PLACEHOLDER_TEST_EXAMPLE)


# ---------------------------------------------------------------------------
# When — pre-commit driving port (layer 3, real git)
# ---------------------------------------------------------------------------


@when(
    parsers.parse(
        'a contributor commits with a "{email_class:EmailClass}" author',
        extra_types=_EXTRA,
    )
)
def when_commit_with_author(
    composition: IdentityComposition, email_class: EmailClass
) -> None:
    composition.commit_with_identity(email_class, IdentityRole.AUTHOR)


@when(
    parsers.parse(
        'a contributor commits with a "{email_class:EmailClass}" committer',
        extra_types=_EXTRA,
    )
)
def when_commit_with_committer(
    composition: IdentityComposition, email_class: EmailClass
) -> None:
    composition.commit_with_identity(email_class, IdentityRole.COMMITTER)


@when(
    parsers.parse(
        'a contributor commits under the author name class "{name_class:NameClass}"',
        extra_types=_EXTRA,
    )
)
def when_commit_with_author_name(
    composition: IdentityComposition, name_class: NameClass
) -> None:
    composition.commit_with_author_name_of_class(name_class)


@when("the contributor has no resolvable commit identity")
def when_no_resolvable_identity(composition: IdentityComposition) -> None:
    composition.make_identity_unresolvable()


@when("the pre-commit identity gate runs")
def when_run_precommit(composition: IdentityComposition) -> None:
    composition.run_precommit_gate()


# ---------------------------------------------------------------------------
# When — pre-push driving port (layer 3, real git range)
# ---------------------------------------------------------------------------


@when("a placeholder-authored commit reaches the range by skipping the commit gate")
def when_bypassed_placeholder_in_range(composition: IdentityComposition) -> None:
    composition.add_range_commit(
        EmailClass.PLACEHOLDER_TEST_EXAMPLE, IdentityRole.AUTHOR, CommitBypass.NO_VERIFY
    )


@when("a clean commit is added to the range")
def when_clean_commit_in_range(composition: IdentityComposition) -> None:
    composition.add_range_commit(
        EmailClass.NOREPLY_PLAIN, IdentityRole.AUTHOR, CommitBypass.NORMAL
    )


@when("a placeholder commit is already published on another branch")
def when_placeholder_also_on_another_remote(
    composition: IdentityComposition,
) -> None:
    composition.add_bypassed_commit_already_on_another_remote(
        EmailClass.PLACEHOLDER_TEST_EXAMPLE, IdentityRole.AUTHOR
    )


@when("a contributor hides a placeholder author email behind a tab in the name")
def when_tab_in_author_name(composition: IdentityComposition) -> None:
    composition.add_commit_with_tab_in_author_name()


@when(
    parsers.parse(
        'a commit under the author name class "{name_class:NameClass}" reaches the range',
        extra_types=_EXTRA,
    )
)
def when_author_name_commit_in_range(
    composition: IdentityComposition, name_class: NameClass
) -> None:
    composition.add_range_commit_with_name_of_class(name_class, IdentityRole.AUTHOR)


@when(
    parsers.parse(
        'a commit under the committer name class "{name_class:NameClass}" reaches the range',
        extra_types=_EXTRA,
    )
)
def when_committer_name_commit_in_range(
    composition: IdentityComposition, name_class: NameClass
) -> None:
    composition.add_range_commit_with_name_of_class(name_class, IdentityRole.COMMITTER)


@when("a contributor hides a placeholder author name behind a tab in the name")
def when_tab_hides_placeholder_name(composition: IdentityComposition) -> None:
    composition.add_range_commit_with_tab_in_name_hiding_placeholder_name()


@when("a contributor hides a placeholder author email behind a tab in the range name")
def when_tab_hides_placeholder_email_in_range(
    composition: IdentityComposition,
) -> None:
    composition.add_range_commit_with_tab_in_name_hiding_placeholder_email()


@when(
    parsers.parse(
        'a commit with a "{email_class:EmailClass}" committer reaches the range',
        extra_types=_EXTRA,
    )
)
def when_committer_commit_in_range(
    composition: IdentityComposition, email_class: EmailClass
) -> None:
    composition.add_range_commit(
        email_class, IdentityRole.COMMITTER, CommitBypass.NORMAL
    )


@when("the pre-push identity gate inspects an existing upstream range")
def when_prepush_existing(composition: IdentityComposition) -> None:
    composition.run_prepush_gate(PushRangeShape.EXISTING_UPSTREAM)


@when("the pre-push identity gate inspects a brand-new branch with no upstream")
def when_prepush_new_branch(composition: IdentityComposition) -> None:
    composition.run_prepush_gate(PushRangeShape.NEW_BRANCH_ZERO_SHA)


@when(
    "the pre-push identity gate inspects a new branch with no default branch to compare against"
)
def when_prepush_no_default_base(composition: IdentityComposition) -> None:
    composition.run_prepush_gate_with_no_resolvable_default_base()


# ---------------------------------------------------------------------------
# When — authoritative CI driving port (layer 3, range over argv)
# ---------------------------------------------------------------------------


@when("the authoritative gate inspects the whole change set")
def when_ci_inspects(composition: IdentityComposition) -> None:
    composition.run_ci_check_over_range()


@when("a change set equivalent to the eight placeholder-authored commits is proposed")
def when_pr42_range(composition: IdentityComposition) -> None:
    composition.run_ci_check_over_pr42_equivalent_range()


@when(
    parsers.parse(
        'a single "{email_class:EmailClass}" commit is pushed with no range',
        extra_types=_EXTRA,
    )
)
def when_push_head_only(
    composition: IdentityComposition, email_class: EmailClass
) -> None:
    composition.run_ci_check_over_head_only(email_class)


@when("a change set whose first commit is clean but a later commit is a placeholder")
def when_clean_first_placeholder_later(composition: IdentityComposition) -> None:
    composition.run_ci_check_over_clean_first_then_placeholder_range()


@when(
    parsers.parse(
        'a single commit under the author name class "{name_class:NameClass}" '
        "is pushed with no range",
        extra_types=_EXTRA,
    )
)
def when_push_head_only_name(
    composition: IdentityComposition, name_class: NameClass
) -> None:
    composition.run_ci_check_over_head_only_name(name_class)


# ---------------------------------------------------------------------------
# Then — validator-core observables (single port observable per assertion)
# ---------------------------------------------------------------------------


@then("the email is rejected")
def then_email_rejected(composition: IdentityComposition) -> None:
    assert composition.world.email_ruling.verdict is Verdict.REJECTED


@then("the email is accepted")
def then_email_accepted(composition: IdentityComposition) -> None:
    assert composition.world.email_ruling.verdict is Verdict.ACCEPTED


@then("the email is always accepted")
def then_email_always_accepted(composition: IdentityComposition) -> None:
    assert composition.world.email_ruling.verdict is Verdict.ACCEPTED


@then("the email is always rejected")
def then_email_always_rejected(composition: IdentityComposition) -> None:
    assert composition.world.email_ruling.verdict is Verdict.REJECTED


@then("the name is rejected")
def then_name_rejected(composition: IdentityComposition) -> None:
    assert composition.world.name_ruling.verdict is Verdict.REJECTED


@then("the name is accepted")
def then_name_accepted(composition: IdentityComposition) -> None:
    assert composition.world.name_ruling.verdict is Verdict.ACCEPTED


@then("the rejection names a reason the maintainer can act on")
def then_rejection_has_reason(composition: IdentityComposition) -> None:
    assert composition.world.email_ruling.reason.strip() != ""


# ---------------------------------------------------------------------------
# Then — enforcement-layer observables (exit-code via GateOutcome)
# ---------------------------------------------------------------------------


@then("the commit is refused")
def then_commit_refused(composition: IdentityComposition) -> None:
    assert composition.world.exit_code != 0


@then("the commit is allowed")
def then_commit_allowed(composition: IdentityComposition) -> None:
    assert composition.world.exit_code == 0


@then("the contributor is told which identity field was rejected")
def then_field_named(composition: IdentityComposition) -> None:
    assert composition.world.captured_output.strip() != ""


@then("the push is refused")
def then_push_refused(composition: IdentityComposition) -> None:
    assert composition.world.exit_code != 0


@then("the push is allowed")
def then_push_allowed(composition: IdentityComposition) -> None:
    assert composition.world.exit_code == 0


@then("the change set is flagged")
def then_change_set_flagged(composition: IdentityComposition) -> None:
    assert composition.world.exit_code != 0


@then("the change set is cleared")
def then_change_set_cleared(composition: IdentityComposition) -> None:
    assert composition.world.exit_code == 0


@then("every offending commit in the change set is named in the report")
def then_every_offending_commit_named(composition: IdentityComposition) -> None:
    # H1: the report must list EVERY offending commit by its short SHA — not just
    # the first. A `rows[:1]`-style regression would name fewer than all of them.
    out = composition.world.captured_output
    short_shas = [sha[:8] for sha in composition.world.range_commit_shas]
    assert short_shas and all(short in out for short in short_shas)


@then("the rejection names the placeholder author name as a placeholder")
def then_rejection_names_placeholder_name(
    composition: IdentityComposition,
) -> None:
    # R3-F1: the offending author NAME must be reported AS a placeholder name on
    # the author field. Today the push/CI runners read only emails (no %an/%cn),
    # so the placeholder name is never seen and never reported. After the crafter
    # adds NUL-separated %an/%cn + is_valid_author_name, the rejection names it.
    out = composition.world.captured_output
    assert "placeholder name" in out and "author" in out


@then("the rejection names the placeholder author email as a placeholder")
def then_rejection_names_placeholder_author(
    composition: IdentityComposition,
) -> None:
    # M2: the offending author email must be reported AS a placeholder, on the
    # author field. Today the tab misaligns the columns: the runner reads a
    # clean name fragment as the author email and only trips over the
    # placeholder as whitespace in the (garbled) committer column — so the
    # placeholder author email is never named as a placeholder. After the
    # crafter switches to a tab-proof split (drop %an / NUL separators) the
    # rejection will correctly name it.
    out = composition.world.captured_output
    assert "known placeholder" in out and composition.world.staged_author_email in out
