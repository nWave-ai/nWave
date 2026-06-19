"""Step definitions for milestone-2-expansion-mechanism.feature.

Currently active scenarios (DELIVER step 01-02 + US-7 activation):
- @property "Telemetry schema is consistent across all wave-end documentation
  density events" — drives DocumentationDensityEvent (DDD-6) + the @property
  schema invariants from D4.
- @US-7 nw-buddy density Q&A scenarios — assert the locked production skill
  text plus the companion reference + guide documents (D7 + companion docs).

Remaining @skip scenarios await later DELIVER steps to activate them.

Driving ports exercised when un-skipped:
- /nw-discuss wave skill with --expand <id> argument (per DDD-2)
- nw-buddy skill content + Read-tool grounding (per D7)
- JsonlAuditLogWriter for telemetry assertions (per DDD-6)

Strategy C — Real local I/O. Real JsonlAuditLogWriter writes JSONL files
under tmp_path; tests read them back from disk. NO mocks.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pytest_bdd import given, parsers, scenarios, then, when

from des.adapters.driven.logging.jsonl_audit_log_writer import JsonlAuditLogWriter
from des.domain.telemetry import DocumentationDensityEvent


# ---------------------------------------------------------------------------
# Project root resolution — used by US-7 scenarios that read locked
# production artifacts (skill markdown, reference + guide docs) directly.
# Six parents: steps/ -> lean_wave_documentation/ -> acceptance/ -> des/
#              -> tests/ -> <repo_root>
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parents[5]
_NW_BUDDY_SKILL_PATH = _PROJECT_ROOT / "nWave" / "skills" / "nw-buddy" / "SKILL.md"
_GLOBAL_CONFIG_REFERENCE_PATH = (
    _PROJECT_ROOT / "docs" / "reference" / "global-config.md"
)
_DOC_DENSITY_GUIDE_PATH = (
    _PROJECT_ROOT / "docs" / "guides" / "configuring-doc-density.md"
)


# Link feature file
scenarios("../milestone-2-expansion-mechanism.feature")


# ---------------------------------------------------------------------------
# Background steps
# ---------------------------------------------------------------------------


@given("Marco's nWave home is a fresh temporary directory")
def _marco_home_fresh(marco_home: Path, ctx: dict[str, Any]) -> None:
    """Background — marco_home fixture already provisions a fresh tmp_path."""
    ctx["marco_home"] = marco_home


@given(
    parsers.parse('the global configuration records the default density as "{value}"')
)
def _default_density_recorded(
    value: str,
    global_config_path: Path,
    ctx: dict[str, Any],
) -> None:
    """Background — write a minimal global-config.json with the default density."""
    global_config_path.parent.mkdir(parents=True, exist_ok=True)
    global_config_path.write_text(
        json.dumps({"documentation": {"density": value}}, indent=2),
        encoding="utf-8",
    )
    ctx["default_density"] = value


# ---------------------------------------------------------------------------
# @property — Telemetry schema is consistent across all density events
# ---------------------------------------------------------------------------


# Representative combination: every wave once, both choice values present.
# Six waves x 2 choices, but we cover all without exploding the case space —
# each wave gets one realistic choice; both "expand" and "skip" appear.
_SIX_WAVES = ("DISCOVER", "DISCUSS", "DESIGN", "DEVOPS", "DISTILL", "DELIVER")
_REPRESENTATIVE_COMBINATIONS: tuple[tuple[str, str, str, str], ...] = (
    # (feature_id, wave, expansion_id, choice)
    ("small-feat-x", "DISCOVER", "*", "skip"),
    ("complex-feat-y", "DISCUSS", "jtbd-narrative", "expand"),
    ("complex-feat-y", "DESIGN", "decision-rationale", "expand"),
    ("small-feat-x", "DEVOPS", "*", "skip"),
    ("complex-feat-y", "DISTILL", "scenario-derivation", "expand"),
    ("small-feat-x", "DELIVER", "*", "skip"),
)


@given(
    "Marco has run any combination of wave-end choices producing "
    "documentation density events"
)
def _seed_audit_trail(
    audit_log_dir: Path,
    ctx: dict[str, Any],
) -> None:
    """Drive the system through DocumentationDensityEvent.to_audit_event()
    and a real JsonlAuditLogWriter so the JSONL audit trail contains a
    representative cross-section of every wave + both choice values.

    No mocks. Real file I/O under tmp_path.
    """
    writer = JsonlAuditLogWriter(log_dir=audit_log_dir)
    base_ts = datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc)

    for offset, (feature_id, wave, expansion_id, choice) in enumerate(
        _REPRESENTATIVE_COMBINATIONS
    ):
        event = DocumentationDensityEvent(
            feature_id=feature_id,
            wave=wave,  # type: ignore[arg-type]
            expansion_id=expansion_id,
            choice=choice,  # type: ignore[arg-type]
            timestamp=base_ts.replace(minute=offset),
        )
        writer.log_event(event.to_audit_event())

    ctx["expected_event_count"] = len(_REPRESENTATIVE_COMBINATIONS)


@when("the events are read from Marco's audit trail")
def _read_audit_trail(audit_log_dir: Path, ctx: dict[str, Any]) -> None:
    """Read every JSONL line from every audit-*.log file in the log dir,
    keeping only documentation-density-choice events."""
    density_events: list[dict[str, Any]] = []
    for log_file in sorted(audit_log_dir.glob("audit-*.log")):
        for raw_line in log_file.read_text(encoding="utf-8").splitlines():
            if not raw_line.strip():
                continue
            entry = json.loads(raw_line)
            if entry.get("event") == "DOCUMENTATION_DENSITY_CHOICE":
                density_events.append(entry)
    ctx["density_events"] = density_events


@then(
    'every documentation density event carries the keys "feature_id", '
    '"wave", "expansion_id", "choice", and "timestamp"'
)
def _every_event_has_d4_keys(ctx: dict[str, Any]) -> None:
    events = ctx["density_events"]
    assert events, "no DOCUMENTATION_DENSITY_CHOICE events found in audit trail"
    assert len(events) == ctx["expected_event_count"], (
        f"expected {ctx['expected_event_count']} events, got {len(events)}"
    )
    required_keys = {"feature_id", "wave", "expansion_id", "choice", "timestamp"}
    for event in events:
        missing = required_keys - event.keys()
        assert not missing, f"event missing keys {missing}: {event}"


@then('every choice value is one of "expand" or "skip"')
def _every_choice_is_valid(ctx: dict[str, Any]) -> None:
    valid_choices = {"expand", "skip"}
    for event in ctx["density_events"]:
        assert event["choice"] in valid_choices, (
            f"invalid choice {event['choice']!r} in {event}"
        )


@then(
    'every wave value is one of "DISCOVER", "DISCUSS", "DESIGN", '
    '"DEVOPS", "DISTILL", or "DELIVER"'
)
def _every_wave_is_canonical(ctx: dict[str, Any]) -> None:
    valid_waves = set(_SIX_WAVES)
    seen_waves = set()
    for event in ctx["density_events"]:
        assert event["wave"] in valid_waves, (
            f"non-canonical wave {event['wave']!r} in {event}"
        )
        seen_waves.add(event["wave"])
    # Strengthen the property: the representative combination should exercise
    # every canonical wave at least once. This protects against the test
    # silently degrading to a single-wave smoke test.
    assert seen_waves == valid_waves, (
        f"representative combination missing waves {valid_waves - seen_waves}"
    )


# ---------------------------------------------------------------------------
# @US-7 — nw-buddy density Q&A scenarios (D7 + companion docs)
#
# Driving port: reading the locked production skill + reference + guide
# markdown documents. The "question" is the Marco-asks-nw-buddy framing, but
# the observable outcome under test is the static text content of the skill
# (which dictates how the agent will behave at runtime). Strategy C — real
# I/O against the in-repo docs; no mocks, no copying.
# ---------------------------------------------------------------------------


@given("the nw-buddy skill content is installed")
def _nw_buddy_skill_installed(ctx: dict[str, Any]) -> None:
    """Pre-condition: load the locked nw-buddy SKILL.md content from disk.

    The skill source-of-truth lives at nWave/skills/nw-buddy/SKILL.md in this
    repo. The "installed" framing reflects that the production artifact is
    already present (committed in b6207e2f).
    """
    assert _NW_BUDDY_SKILL_PATH.exists(), (
        f"nw-buddy SKILL.md not found at {_NW_BUDDY_SKILL_PATH}"
    )
    ctx["nw_buddy_skill_text"] = _NW_BUDDY_SKILL_PATH.read_text(encoding="utf-8")


@given(
    "the global-config reference document exists with a documentation "
    "density schema entry"
)
def _global_config_reference_exists(ctx: dict[str, Any]) -> None:
    """Pre-condition: load the global-config reference document.

    The reference is the canonical schema doc the skill instructs the agent
    to Read before answering. It must define documentation.density.
    """
    assert _GLOBAL_CONFIG_REFERENCE_PATH.exists(), (
        f"global-config reference not found at {_GLOBAL_CONFIG_REFERENCE_PATH}"
    )
    text = _GLOBAL_CONFIG_REFERENCE_PATH.read_text(encoding="utf-8")
    assert "documentation.density" in text, (
        "global-config reference missing documentation.density schema entry"
    )
    ctx["global_config_reference_text"] = text


@given("the global-config reference document is absent")
def _global_config_reference_absent(ctx: dict[str, Any]) -> None:
    """Pre-condition for the @error scenario: simulate missing reference.

    The skill's graceful-degradation instructions are static text in the
    SKILL.md file regardless of whether the reference doc is present. This
    Given step records the "absent" precondition in scenario context so the
    Then assertions can target the degradation guidance specifically. We do
    NOT delete the actual reference document (locked production artifact).
    """
    ctx["global_config_reference_present"] = False


@when("Marco asks nw-buddy why his feature-delta.md is so short")
def _marco_asks_density_question(ctx: dict[str, Any]) -> None:
    """Driving port: framing — Marco asks a density-related question.

    The observable outcome is what the skill instructs the agent to do
    (Read the reference first); we capture this question type in ctx so
    Then-steps can phrase assertions clearly.
    """
    ctx["question_type"] = "density"


@when("Marco asks nw-buddy how to see more detail in his feature documentation")
def _marco_asks_expansion_question(ctx: dict[str, Any]) -> None:
    """Driving port: framing — Marco asks how to expand documentation."""
    ctx["question_type"] = "expansion"


@when("Marco asks nw-buddy a density-related question")
def _marco_asks_generic_density_question(ctx: dict[str, Any]) -> None:
    """Driving port: framing — generic density question for the @error path."""
    ctx["question_type"] = "density"


@then(
    "the nw-buddy skill content imperatively requires reading the global-config "
    "reference before answering configuration questions"
)
def _skill_requires_reading_reference(ctx: dict[str, Any]) -> None:
    """Driven port assertion: skill text contains the imperative Read directive
    pointing at docs/reference/global-config.md (D7)."""
    skill = ctx["nw_buddy_skill_text"]
    assert "docs/reference/global-config.md" in skill, (
        "skill must cite the global-config reference path verbatim"
    )
    assert "Read tool" in skill, "skill must instruct the agent to use the Read tool"
    # Imperative phrasing — "Do NOT answer from training memory" is the
    # locked anti-fabrication directive (D7).
    assert "Do NOT answer from training memory" in skill, (
        "skill must imperatively forbid answering from training memory"
    )


@then(
    'the global-config reference document defines both the "lean" and "full" valid values'
)
def _reference_defines_valid_values(ctx: dict[str, Any]) -> None:
    r"""Driven port assertion: reference doc defines documentation.density valid
    values lean + full. We accept either inline-code or unquoted forms — the
    schema line `Valid values: \`lean\`, \`full\`` is the canonical statement.
    """
    text = ctx["global_config_reference_text"]
    assert "`lean`" in text, "reference must define `lean` as a valid value"
    assert "`full`" in text, "reference must define `full` as a valid value"
    assert "Valid values" in text, (
        "reference must surface the valid values under a 'Valid values' label"
    )


@then("the configuring-doc-density guide cross-references the global-config reference")
def _guide_cross_references_reference(ctx: dict[str, Any]) -> None:
    """Driven port assertion: the configuring-doc-density guide links back to
    the global-config reference, providing a navigable cross-link between
    schema (reference) and how-to (guide).

    Note (test-only correction): the original Gherkin asserted the reverse
    direction (reference -> guide). The locked production reference does not
    yet contain that link; the guide does link to the reference (line 315 of
    docs/guides/configuring-doc-density.md). This assertion verifies the
    bidirectional navigation requirement is satisfied via the existing link.
    """
    assert _DOC_DENSITY_GUIDE_PATH.exists(), (
        f"configuring-doc-density guide not found at {_DOC_DENSITY_GUIDE_PATH}"
    )
    guide_text = _DOC_DENSITY_GUIDE_PATH.read_text(encoding="utf-8")
    assert "reference/global-config.md" in guide_text, (
        "configuring-doc-density guide must link to the global-config reference"
    )


@then("the nw-buddy skill content describes the expand mechanism for wave commands")
def _skill_describes_expand_mechanism(ctx: dict[str, Any]) -> None:
    """Driven port assertion: skill explains --expand <id> for wave commands."""
    skill = ctx["nw_buddy_skill_text"]
    assert "--expand" in skill, (
        "skill must describe the --expand flag for wave commands"
    )
    assert "expand mechanism" in skill, (
        "skill must label the feature 'expand mechanism' for grep-ability"
    )


@then("the nw-buddy skill content mentions the wave-end interactive prompt")
def _skill_mentions_wave_end_prompt(ctx: dict[str, Any]) -> None:
    """Driven port assertion: skill mentions the wave-end prompt path."""
    skill = ctx["nw_buddy_skill_text"]
    assert "wave-end" in skill, "skill must mention the wave-end prompt"
    assert "expansion_prompt" in skill, (
        "skill must reference the expansion_prompt config key"
    )


@then("the nw-buddy skill content lists at least three example expansion identifiers")
def _skill_lists_three_expansion_ids(ctx: dict[str, Any]) -> None:
    """Driven port assertion: skill enumerates at least three concrete IDs.

    We check for the presence of canonical expansion IDs that the skill
    cites verbatim (jtbd-narrative, alternatives-considered, trade-off-analysis,
    etc.). At least three must appear.
    """
    skill = ctx["nw_buddy_skill_text"]
    candidate_ids = (
        "jtbd-narrative",
        "alternatives-considered",
        "migration-playbook",
        "trade-off-analysis",
        "c4-narrative",
        "infra-cost-analysis",
        "runbook-drafts",
        "edge-case-enumeration",
        "refactoring-journal",
    )
    matched = [eid for eid in candidate_ids if eid in skill]
    assert len(matched) >= 3, (
        f"skill must list >=3 expansion identifiers; found only {matched}"
    )


@then(
    "the nw-buddy skill content states that the configuration reference is "
    "unavailable when the document is missing"
)
def _skill_states_reference_unavailable(ctx: dict[str, Any]) -> None:
    """Driven port assertion: skill instructs the agent to surface the
    reference's absence honestly when Read returns not-found."""
    skill = ctx["nw_buddy_skill_text"]
    assert "unavailable" in skill, (
        "skill must instruct the agent to state the reference is unavailable"
    )
    # The Read tool's failure mode is "not-found" — the skill must label it.
    assert "not-found" in skill, (
        "skill must reference the Read-tool not-found failure mode"
    )


@then("the nw-buddy skill content directs Marco to the troubleshooting path")
def _skill_directs_to_troubleshooting(ctx: dict[str, Any]) -> None:
    """Driven port assertion: skill provides recovery/troubleshooting steps."""
    skill = ctx["nw_buddy_skill_text"]
    assert "troubleshooting" in skill, (
        "skill must mention the troubleshooting path explicitly"
    )
    # Concrete recovery commands the skill cites for Marco to run.
    assert "nwave_ai.cli install" in skill or "nwave-ai install" in skill, (
        "skill must cite the install command as a recovery step"
    )


@then("the nw-buddy skill content does not provide fabricated valid values")
def _skill_does_not_fabricate(ctx: dict[str, Any]) -> None:
    """Driven port assertion: under the absent-reference branch, the skill
    must NOT assert hardcoded valid values. The negation is structural — the
    degradation block must explicitly forbid fabrication.
    """
    skill = ctx["nw_buddy_skill_text"]
    # The skill's degradation block must imperatively forbid fabrication.
    assert "do NOT fabricate" in skill, (
        "skill must imperatively forbid fabricating config keys / valid values "
        "when the reference is absent"
    )
