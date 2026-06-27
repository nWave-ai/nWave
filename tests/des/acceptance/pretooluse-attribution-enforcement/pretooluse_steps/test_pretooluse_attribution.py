"""Step definitions: PreToolUse deterministic commit attribution (ADR-CA-006).

Binds all four `.feature` files for the feature. Two driving surfaces, both
production-wired (Mandate 13 — driving-port-only):

  * the pure rewrite core via `CommitAttributionService.plan_rewrite`
    (Layer 3 composition, `@in-memory`) — the mutate/passthrough matrices;
  * the real `pre-tool-use` hook adapter via subprocess (Layer 4 wiring_e2e,
    `@real-io`) — the walking skeleton + adapter mutation contract.

Example-only, no PBT machinery (Mandate 9/11) — every shape is enumerated; the
generative idempotency/escaping PBT belongs to DELIVER unit tests. Step bodies
delegate to the composition roots and never inline business logic (Mandate-12
criterion 3): each body is a typed lookup plus a composition call.

Step-text is unique within this feature directory (S1): the `@in-memory` core
surface and the `@real-io` adapter surface use distinct Given/When/Then phrases
(`the rewrite core plans the attribution` vs `the attribution hook processes the
commit`), so no pytest-bdd registry collision is possible.

RED contract (Mandate 7): every scenario reaches a production scaffold that
raises AssertionError (`rewrite` / `plan_rewrite` /
`emit_commit_attribution_mutation`), so the pre-DELIVER gate classifies each as
RED (MISSING_FUNCTIONALITY), never BROKEN (ImportError).
"""

from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from .composition import (
    HookAdapterComposition,
    HookResult,
    RewriteComposition,
    RewriteResult,
)
from .domain_types import (
    COMMAND_BY_SHAPE,
    DUAL_TRAILER_BLOCK,
    SHAPE_BY_PHRASE,
    BashCommand,
    Decision,
    HookOutcome,
)


scenarios(
    "../walking-skeleton.feature",
    "../adapter-mutation-output.feature",
    "../mutate-matrix.feature",
    "../passthrough-matrix.feature",
    "../heredoc-mutate-matrix.feature",
    "../heredoc-passthrough-matrix.feature",
)


# ---------------------------------------------------------------------------
# Fixtures — one composition root per driving surface
# ---------------------------------------------------------------------------


@pytest.fixture
def rewrite_composition() -> RewriteComposition:
    """Production-wired composition over the pure rewrite service."""
    return RewriteComposition.build()


@pytest.fixture
def hook_composition() -> HookAdapterComposition:
    """Composition driving the real `pre-tool-use` hook subprocess."""
    return HookAdapterComposition.build()


@pytest.fixture
def box() -> dict[str, object]:
    """Carrier for the captured result(s) across When/Then steps."""
    return {}


# ===========================================================================
# Surface 1 — pure rewrite core (@in-memory)
# ===========================================================================


@given(parsers.parse("the rewrite core receives {command_shape}"))
def given_command_shape(box: dict[str, object], command_shape: str) -> None:
    box["command"] = BashCommand(COMMAND_BY_SHAPE[SHAPE_BY_PHRASE[command_shape]])


@when("the rewrite core plans the attribution")
def when_core_plans(
    box: dict[str, object], rewrite_composition: RewriteComposition
) -> None:
    result = rewrite_composition.plan_rewrite(box["command"])  # type: ignore[arg-type]
    box["result"] = result
    # Record the effective injected message so a later re-application (which
    # passes through, leaving box["result"].rewritten_command None) can still be
    # credit-checked against the message that actually carries the trailer.
    if result.rewritten_command is not None:
        box["effective_message"] = result.rewritten_command


@when("the rewrite core plans the attribution of the already-rewritten command")
def when_core_plans_again(
    box: dict[str, object], rewrite_composition: RewriteComposition
) -> None:
    first: RewriteResult = box["result"]  # type: ignore[assignment]
    box["result"] = rewrite_composition.plan_rewrite(
        BashCommand(first.rewritten_command or "")
    )


@then("the dual trailer is injected")
def then_dual_trailer_injected(box: dict[str, object]) -> None:
    assert _rewrite_result(box).decision is Decision.MUTATE


@then("the command runs unchanged")
def then_command_runs_unchanged(box: dict[str, object]) -> None:
    result = _rewrite_result(box)
    assert result.decision is Decision.PASSTHROUGH
    assert result.rewritten_command is None


@then("the planned message credits Claude and nWave exactly once")
def then_message_credits_once(box: dict[str, object]) -> None:
    # Effective message = the current rewrite if it mutated, else the message a
    # prior pass injected (re-application passes through — idempotency: the
    # trailer is present exactly once, never doubled).
    rewritten = _rewrite_result(box).rewritten_command or box.get("effective_message")
    assert rewritten is not None
    assert RewriteComposition.trailer_count(str(rewritten)) == 1


@then("removing the injected trailer restores the original command exactly")
def then_removing_trailer_restores_original(box: dict[str, object]) -> None:
    # Never-corrupt (fail-safe) property at example scope: the rewritten chain,
    # with the injected `-m <trailer>` argument removed, is byte-identical to the
    # original command — only the commit segment grew, the chain is preserved.
    original = str(box["command"])
    rewritten = _rewrite_result(box).rewritten_command
    assert rewritten is not None
    assert _strip_injected_trailer(rewritten) == original


@then("a declining reason is recorded")
def then_declining_reason_recorded(box: dict[str, object]) -> None:
    # Passthrough is never silent: the Plan records why it declined, so the
    # audit trail can distinguish "not a commit" from "ambiguous shell".
    assert _rewrite_result(box).plan.reason != ""


# ---------------------------------------------------------------------------
# Semantic placement invariant — the heredoc-body-skip correctness pin
# (ADR-CA-008 §8 Layer 2 / AB-14 / AB-15). `bash -n` syntax alone PASSES the
# body-`)` mis-split; these two Then steps assert the trailer landed as a real
# top-level `-m` argument on the commit, not swallowed into the heredoc body or
# a mis-delimited later segment.
# ---------------------------------------------------------------------------


@then("the original command is preserved as a prefix of the rewrite")
def then_original_is_byte_prefix(box: dict[str, object]) -> None:
    rewritten = _rewrite_result(box).rewritten_command
    assert rewritten is not None
    assert RewriteComposition.original_is_byte_prefix(str(box["command"]), rewritten)


@then("the trailer is the last argument of the rewritten commit")
def then_trailer_is_last_argument(box: dict[str, object]) -> None:
    rewritten = _rewrite_result(box).rewritten_command
    assert rewritten is not None
    assert RewriteComposition.last_argv_token(rewritten) == DUAL_TRAILER_BLOCK


@then("the rewritten command is syntactically valid bash")
def then_rewritten_is_valid_bash(box: dict[str, object]) -> None:
    rewritten = _rewrite_result(box).rewritten_command
    assert rewritten is not None
    assert RewriteComposition.is_syntactically_valid(rewritten)


# ===========================================================================
# Surface 2 — real PreToolUse hook adapter (@real-io)
# ===========================================================================


@given(parsers.parse("Claude is about to run {command_shape}"))
def given_claude_about_to_run(box: dict[str, object], command_shape: str) -> None:
    box["command"] = BashCommand(COMMAND_BY_SHAPE[SHAPE_BY_PHRASE[command_shape]])


@when("the attribution hook processes the commit")
def when_hook_processes(
    box: dict[str, object], hook_composition: HookAdapterComposition
) -> None:
    box["hook_result"] = hook_composition.invoke_pre_tool_use(box["command"])  # type: ignore[arg-type]


@then("the hook rewrites the command to carry the dual trailer")
def then_hook_rewrites(box: dict[str, object]) -> None:
    assert _hook_result(box).outcome is HookOutcome.REWRITES_COMMAND


@then("the agent's command runs unchanged")
def then_agents_command_unchanged(box: dict[str, object]) -> None:
    assert _hook_result(box).outcome is HookOutcome.RUNS_UNCHANGED


@then("the rewritten command credits Claude and nWave exactly once")
def then_hook_command_credits_once(box: dict[str, object]) -> None:
    rewritten = _hook_result(box).rewritten_command
    assert rewritten is not None
    assert RewriteComposition.trailer_count(rewritten) == 1


@then("the rewrite is granted without a permission prompt")
def then_rewrite_granted(box: dict[str, object]) -> None:
    # The mutation must pair the rewritten input with an explicit allow, or
    # Claude Code prompts the user instead of running the rewritten command.
    assert _hook_result(box).permission_decision == "allow"


@then("every field the agent supplied is preserved in the rewrite")
def then_fields_preserved(box: dict[str, object]) -> None:
    # Full-object replacement: the echoed updatedInput carries the original
    # `description` field, not just the rewritten `command`.
    keys = _hook_result(box).echoed_tool_input_keys
    assert {"command", "description"} <= keys


@then("the hook produces no output")
def then_hook_no_output(box: dict[str, object]) -> None:
    assert _hook_result(box).stdout == ""


# ---------------------------------------------------------------------------
# Result accessors (kept here so step bodies stay a single expression)
# ---------------------------------------------------------------------------


def _rewrite_result(box: dict[str, object]) -> RewriteResult:
    return box["result"]  # type: ignore[return-value]


def _hook_result(box: dict[str, object]) -> HookResult:
    return box["hook_result"]  # type: ignore[return-value]


def _strip_injected_trailer(rewritten_command: str) -> str:
    """Remove the single injected `-m '<dual trailer block>'` argument.

    The rewrite appends exactly one `-m <DUAL_TRAILER_BLOCK>` to the commit
    segment. Stripping it must restore the original command byte-for-byte
    (never-corrupt). The expected trailer block is a test-side observable
    (`DUAL_TRAILER_BLOCK`), not imported from the domain (S2 — driving-port-only).
    The rewrite appends the trailer as a raw ` -m <shlex-quoted block>` suffix to
    the commit segment, leaving the rest of the command byte-identical. So removing
    that exact injected substring (NOT a shlex round-trip, which would canonicalize
    the untouched parts and break the byte-for-byte comparison) restores the
    original. The expected injected string is a test-side observable
    (`DUAL_TRAILER_BLOCK`), not imported from the domain (S2 — driving-port-only).
    """
    import shlex

    injected = " -m " + shlex.quote(DUAL_TRAILER_BLOCK)
    return rewritten_command.replace(injected, "", 1)
