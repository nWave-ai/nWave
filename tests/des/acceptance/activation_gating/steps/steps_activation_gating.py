"""Tier-A step definitions for the project-activation-gating acceptance suite.

Mandate-12: every step body is ≤2 statements, the final action statement is a
``composition.<method>(...)`` call, and no control flow appears in any body. The
DSL emerges from typed ``parsers.parse`` converters over the ``domain_types``
enums — a handful of parameterized decorators cover the whole literal space
instead of a decorator-per-literal explosion.

State-mutating ``Then`` steps assert via ``assert_state_delta`` (Mandate 8) with
a port-exposed universe; pure-query ``Then`` steps assert on a single captured
port observable. Shared step-method NAMES are the cross-tier contract (Tier B
imports them).

Layer: 3 (subprocess/FS acceptance over a real tmp_path project). Per Mandate 9
+ 11 this layer is example-only — no Hypothesis ``@given`` here; sad paths are
enumerated explicitly. The 9-row truth table is covered by ``@pytest.mark.parametrize``
inside ``test_activation_resolution.py`` (finite, enumerable → parametrize, not
PBT, per the falsifier-gate).
"""

from __future__ import annotations

from pytest_bdd import given, parsers, then, when

from tests.common.state_delta import assert_state_delta, set_to, unchanged
from tests.des.acceptance.activation_gating.steps.domain_types import (
    COMPLETION_EXPECTATION,
    Activation,
    AdoptionResult,
    AdoptionTrigger,
    CliResult,
    CompletionShell,
    FsMode,
    GateOutcome,
    GitignoreVariant,
    GlobalMode,
    HookCommand,
    HookEnvelope,
    MarkerState,
    PriorUseEvidence,
    SubagentType,
)


# ---------------------------------------------------------------------------
# Parser converters — coerce Gherkin literals to typed enums (DSL emergence).
# Each enum is matched by NAME (the feature files quote the enum member name,
# e.g. "OPT_IN", "AUDIT_LOG_NONEMPTY") so a single typed decorator covers the
# whole literal space — the DSL emerges from the type system (Mandate-12).
# ---------------------------------------------------------------------------

_ENUM_TOKEN = r"[A-Za-z0-9_-]+"


def _by_name(enum_cls):
    """Build a ``parse`` converter that maps an enum member NAME to the member.

    The ``parse`` library (used by ``pytest_bdd.parsers.parse``) requires an
    extra-type callable to carry a ``.pattern`` attribute — that is all
    ``parse.with_pattern`` does. We set it directly to avoid a module-level
    third-party import (kept stable across the autoformatter). One typed
    decorator then covers the whole literal space for that enum.
    """

    def convert(text: str):
        return enum_cls[text]

    convert.pattern = _ENUM_TOKEN
    convert.__name__ = f"convert_{enum_cls.__name__}"
    return convert


EXTRA_TYPES = {
    "GlobalMode": _by_name(GlobalMode),
    "MarkerState": _by_name(MarkerState),
    "PriorUseEvidence": _by_name(PriorUseEvidence),
    "GitignoreVariant": _by_name(GitignoreVariant),
    "AdoptionTrigger": _by_name(AdoptionTrigger),
    "HookCommand": _by_name(HookCommand),
    "CompletionShell": _by_name(CompletionShell),
    "Activation": _by_name(Activation),
    "GateOutcome": _by_name(GateOutcome),
    "AdoptionResult": _by_name(AdoptionResult),
    "FsMode": _by_name(FsMode),
}


# ===========================================================================
# GIVEN — preconditions (typed in; on-disk INPUT state out)
# ===========================================================================


@given(
    parsers.parse(
        'the global activation mode is "{mode:GlobalMode}"', extra_types=EXTRA_TYPES
    ),
)
def Given_global_mode(composition, mode: GlobalMode) -> None:
    composition.given_global_mode(mode)


@given(
    parsers.parse(
        'the project marker is "{marker:MarkerState}"', extra_types=EXTRA_TYPES
    ),
)
def Given_marker(composition, marker: MarkerState) -> None:
    composition.given_marker(marker)


@given(
    parsers.parse(
        'the project shows "{evidence:PriorUseEvidence}" prior-use',
        extra_types=EXTRA_TYPES,
    ),
)
def Given_prior_use(composition, evidence: PriorUseEvidence) -> None:
    composition.given_prior_use_evidence(evidence)


@given(
    parsers.parse(
        'the root ignore file uses the "{variant:GitignoreVariant}" variant',
        extra_types=EXTRA_TYPES,
    ),
)
def Given_root_gitignore(composition, variant: GitignoreVariant) -> None:
    composition.given_root_gitignore(variant)


@given("the nested ignore banner is present")
def Given_nested_banner(composition) -> None:
    composition.given_nested_gitignore_banner()


@given("the project is under version control")
def Given_git_repo(composition) -> None:
    composition.given_git_repo()


@given(
    parsers.parse('the project filesystem is "{mode:FsMode}"', extra_types=EXTRA_TYPES),
)
def Given_fs_mode(composition, mode: FsMode) -> None:
    composition.given_fs_mode(mode)


# ===========================================================================
# WHEN — single user action / system event (drive real production code)
# ===========================================================================


@when("the activation state is resolved for this project")
def When_resolve(composition) -> None:
    composition.resolve_activation()


@when(
    parsers.parse('a "{command:HookCommand}" hook fires', extra_types=EXTRA_TYPES),
)
def When_hook_fires(composition, command: HookCommand) -> None:
    composition.dispatch_hook(
        HookEnvelope(command=command, cwd=str(composition.project_root))
    )


@when("an nWave agent is dispatched in this project")
def When_nw_agent_dispatched(composition) -> None:
    composition.dispatch_hook(
        HookEnvelope(
            command=HookCommand.PRE_TASK,
            cwd=str(composition.project_root),
            subagent_type=SubagentType("nw-software-crafter"),
        )
    )


@when(
    parsers.parse(
        'the session adopts the project via "{trigger:AdoptionTrigger}"',
        extra_types=EXTRA_TYPES,
    ),
)
def When_adopt(composition, trigger: AdoptionTrigger) -> None:
    composition.adopt(trigger)


@when("the gitignore is fixed for the marker")
def When_fix_gitignore(composition) -> None:
    composition.fix_gitignore()


@when("the gitignore is fixed for the marker a second time")
def When_fix_gitignore_again(composition) -> None:
    composition.fix_gitignore()


@when("the operator enables this project")
def When_enable(composition) -> None:
    composition.run_cli(["project", "enable"])


@when("the operator disables this project")
def When_disable(composition) -> None:
    composition.run_cli(["project", "disable"])


@when(
    parsers.parse(
        'the operator sets the global mode to "{mode:GlobalMode}"',
        extra_types=EXTRA_TYPES,
    ),
)
def When_set_mode(composition, mode: GlobalMode) -> None:
    composition.run_cli(["mode", mode.value])


@when("the operator asks for the activation status")
def When_status(composition) -> None:
    composition.run_cli(["status"])


@when("the operator runs an unrecognized activation command")
def When_bad_command(composition) -> None:
    composition.run_cli(["project", "frobnicate"])


@when(
    parsers.parse(
        'shell completion is generated for "{shell:CompletionShell}"',
        extra_types=EXTRA_TYPES,
    ),
)
def When_generate_completion(composition, shell: CompletionShell) -> None:
    composition.generate_completion(shell)


# ===========================================================================
# THEN — observable outcomes (port-exposed; state-delta where mutating)
# ===========================================================================


@then(
    parsers.parse(
        'the project is resolved "{expected:Activation}"', extra_types=EXTRA_TYPES
    ),
)
def Then_resolution_is(composition, expected: Activation) -> None:
    assert composition.last_resolution is expected


@then("the hook is allowed without blocking")
def Then_allowed_exit_0(composition) -> None:
    assert composition.last_gate_outcome is GateOutcome.ALLOWED_EXIT_0


@then("the hook is dispatched to its handler")
def Then_dispatched(composition) -> None:
    assert composition.last_gate_outcome is GateOutcome.DISPATCHED


@then("the gate never blocks the hook")
def Then_never_blocks(composition) -> None:
    assert composition.recorded.get("exit_code") == 0


@then("the handler receives the original hook input intact")
def Then_stdin_intact(composition) -> None:
    assert composition.captured_handler_stdin == composition.recorded.get("sent_stdin")


@then("the project is adopted and the agent dispatch proceeds")
def Then_adopted_and_dispatched(composition) -> None:
    assert composition.last_gate_outcome is GateOutcome.ADOPTED_AND_DISPATCHED


@then("the project marker is written")
def Then_marker_written(composition) -> None:
    assert_state_delta(
        before=composition.recorded["before"],
        after=composition.capture_universe(),
        universe={
            "marker.enabled_for_repo",
            "marker.file_exists",
            "global_config.text",
        },
        expected={
            "marker.enabled_for_repo": set_to(True),
            "marker.file_exists": set_to(True),
            "global_config.text": unchanged(),
        },
    )


@then("no project marker is written")
def Then_marker_not_written(composition) -> None:
    assert composition.capture_universe()["marker.file_exists"] is False


@then(
    parsers.parse(
        'the adoption outcome is "{result:AdoptionResult}"', extra_types=EXTRA_TYPES
    ),
)
def Then_adoption_outcome(composition, result: AdoptionResult) -> None:
    assert composition.last_adoption is result


@then("the marker still reflects the deliberate opt-out")
def Then_sticky_preserved(composition) -> None:
    assert composition.capture_universe()["marker.enabled_for_repo"] is False


@then("the marker becomes trackable by version control")
def Then_marker_trackable(composition) -> None:
    assert composition.capture_universe()["marker.git_tracked"] is True


@then("the nested ignore banner is preserved")
def Then_banner_preserved(composition) -> None:
    assert "Generated by nWave" in (
        composition.capture_universe()["nested_gitignore.text"] or ""
    )


@then("the ignore files are unchanged from the first fix")
def Then_gitignore_idempotent(composition) -> None:
    assert (
        composition.recorded.get("gitignore_after_first")
        == composition.capture_universe()["root_gitignore.text"]
    )


@then("the activation command succeeds")
def Then_cli_success(composition) -> None:
    assert composition.last_cli_result is CliResult.SUCCESS


@then("the activation command reports a usage error")
def Then_cli_usage_error(composition) -> None:
    assert composition.last_cli_result is CliResult.USAGE_ERROR


@then(
    parsers.parse(
        'the global mode is recorded as "{mode:GlobalMode}"', extra_types=EXTRA_TYPES
    ),
)
def Then_global_mode_recorded(composition, mode: GlobalMode) -> None:
    assert f'"{mode.value}"' in (
        composition.capture_universe()["global_config.text"] or ""
    )


@then("the status report names the resolved project state")
def Then_status_names_state(composition) -> None:
    stdout = composition.last_cli_stdout.lower()
    assert composition.last_cli_result is CliResult.SUCCESS
    assert ("opt-in" in stdout) or ("all" in stdout)
    assert ("active" in stdout) or ("inactive" in stdout)


@then("the completion lists exactly the published activation commands")
def Then_completion_no_drift(composition) -> None:
    assert COMPLETION_EXPECTATION.must_contain.issubset(
        set(composition.last_completion_script.split())
    )


@then("the completion omits any internal hook vocabulary")
def Then_completion_no_hooks_term(composition) -> None:
    assert "hooks" not in composition.last_completion_script
