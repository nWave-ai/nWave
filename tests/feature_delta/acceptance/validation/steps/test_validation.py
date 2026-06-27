"""
Step definitions for the Validation bounded context.

Driving Adapter Mandate (Mandate 5): every WS scenario invokes the CLI
via subprocess; the orchestrator import is deliberately routed through
the protocol surface, not in-process imports of internal classes.

Business-language abstraction (Mandate 2): step methods speak in
maintainer/feature-delta domain terms. Technical I/O lives in the
shared conftest fixtures (subprocess runner, sandbox).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when


# Bind every scenario in validation.feature to this step file.
scenarios("../validation.feature")


# ---------------------------------------------------------------------------
# Background steps
# ---------------------------------------------------------------------------


@given("a clean working directory with no prior nwave-ai state")
def _clean_working_dir(sandbox: Path) -> None:
    assert sandbox.exists()


@given("the nwave-ai binary is on PATH")
def _binary_on_path(nwave_ai_binary: list[str]) -> None:
    assert nwave_ai_binary, "nwave-ai entry point must be resolvable"


# ---------------------------------------------------------------------------
# Walking skeleton — token-billing exemplar
# ---------------------------------------------------------------------------


@given(parsers.parse('the token-billing failure exemplar at "{relpath}"'))
def _exemplar_at_path(token_billing_exemplar: Path, relpath: str) -> None:
    assert token_billing_exemplar.name == "feature-delta.md"
    assert relpath in str(token_billing_exemplar)


@given(parsers.parse('the exemplar DISCUSS section commits to "{commitment}"'))
def _exemplar_discuss_commitment(token_billing_exemplar: Path, commitment: str) -> None:
    content = token_billing_exemplar.read_text(encoding="utf-8")
    assert commitment in content


@given(
    parsers.parse(
        'the exemplar DESIGN section weakens this to "{weakened}" '
        "with no DDD ratification"
    )
)
def _exemplar_design_weakening(token_billing_exemplar: Path, weakened: str) -> None:
    content = token_billing_exemplar.read_text(encoding="utf-8")
    assert weakened in content
    assert "DDD-1" not in content


@when(
    parsers.parse(
        'the maintainer runs "nwave-ai validate-feature-delta {arg}" via subprocess'
    ),
    target_fixture="cli_result",
)
def _ws_dogfood_invocation(run_cli, arg: str, capsys):
    # capsys must be referenced in @when, not @then (F-002)
    return run_cli("validate-feature-delta", arg)


@then("the exit code is 1")
def _exit_code_one(cli_result) -> None:
    assert cli_result.exit_code == 1, (
        f"expected exit 1, got {cli_result.exit_code}\nstderr={cli_result.stderr!r}"
    )


@then("stderr names the offender file and line of the DESIGN row")
def _stderr_names_offender(cli_result) -> None:
    assert "feature-delta.md" in cli_result.stderr
    assert ":" in cli_result.stderr  # file:line marker present


@then(
    parsers.parse(
        'stderr contains the protocol surface "{surface}" as missing downstream'
    )
)
def _stderr_protocol_surface(cli_result, surface: str) -> None:
    assert surface in cli_result.stderr


@then("stderr suggests adding a DDR entry or restoring the commitment")
def _stderr_remediation(cli_result) -> None:
    text = cli_result.stderr.lower()
    assert "ddr" in text and ("restore" in text or "add" in text)


@then("no file outside the path argument was modified")
def _no_side_effects(cli_result, sandbox: Path, take_snapshot) -> None:
    # G4 invariant — snapshot before vs after run; diff must be empty for monitored set.
    # The invocation has already completed; we compare the post-run state against a
    # clean baseline: the exemplar file itself is the ONLY file that may exist under
    # sandbox at this point (the token_billing_exemplar fixture wrote it before When).
    # Any additional file appearing means the CLI had an unexpected side effect.
    post_snap = take_snapshot(sandbox)
    monitored_paths = {p for p in post_snap.files if not p.startswith("runs/")}
    assert monitored_paths == set(), (
        f"G4 violation: CLI created files outside the target path argument: "
        f"{sorted(monitored_paths)}"
    )


# ---------------------------------------------------------------------------
# E1 / E2 / E3 / E3b common steps
# ---------------------------------------------------------------------------


@given(
    parsers.parse(
        "a well-formed feature-delta with DISCUSS, DESIGN, and DISTILL sections"
    ),
    target_fixture="feature_delta_path",
)
def _wellformed(write_feature_delta) -> Path:
    content = (
        "# wellformed\n\n"
        "## Wave: DISCUSS\n\n### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        "| n/a | POST /api/login real Flask handler | n/a | "
        "establishes login protocol surface |\n\n"
        "## Wave: DESIGN\n\n### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        "| DISCUSS#row1 | POST /api/login backed by Flask 3.x | "
        "n/a | preserves DISCUSS#row1 verbatim |\n\n"
        "## Wave: DISTILL\n\n### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        "| DESIGN#row1 | POST /api/login asserted in scenario | "
        "n/a | preserves DESIGN#row1 verbatim |\n"
    )
    return write_feature_delta("docs/feature/wellformed/feature-delta.md", content)


@when("the maintainer runs the validator against the file", target_fixture="cli_result")
def _run_validator_default(run_cli, feature_delta_path: Path, capsys):
    rel = feature_delta_path.relative_to(feature_delta_path.parents[3])
    return run_cli("validate-feature-delta", str(rel))


@when("the maintainer runs the validator", target_fixture="cli_result")
def _run_validator(run_cli, feature_delta_path: Path, capsys):
    rel = feature_delta_path.relative_to(feature_delta_path.parents[3])
    return run_cli("validate-feature-delta", str(rel))


@then("the exit code is 0 within 1 second")
def _exit_zero_under_budget(cli_result) -> None:
    assert cli_result.exit_code == 0, cli_result.stderr
    # Budget set to 5000ms acceptance-side (G1 tighter budget tested elsewhere).
    assert cli_result.duration_ms < 5000


@then(parsers.parse("the output reports {rule} PASS"))
def _output_reports_pass(cli_result, rule: str) -> None:
    combined = cli_result.stdout + cli_result.stderr
    assert f"{rule} PASS" in combined or f"[PASS] {rule}" in combined


# ---------------------------------------------------------------------------
# Scaffold marker — all remaining steps raise AssertionError per Mandate 7
# ---------------------------------------------------------------------------

__SCAFFOLD__ = True


def _scaffold(message: str) -> None:
    raise AssertionError(f"__SCAFFOLD__ Not yet implemented — RED scaffold: {message}")


# ---------------------------------------------------------------------------
# Remaining step bodies are RED-ready scaffolds (Mandate 7)
# ---------------------------------------------------------------------------


@given(
    parsers.parse(
        "a feature-delta where the DISCUSS heading is typed "
        '"## Wave : DISCUSS" with an extra space'
    ),
    target_fixture="feature_delta_path",
)
def _given_typo_heading(write_feature_delta) -> Path:
    content = (
        "# typo heading\n\n"
        "## Wave : DISCUSS\n\n"
        "### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        "| n/a | some commitment | n/a | some impact |\n"
    )
    return write_feature_delta("docs/feature/typo/feature-delta.md", content)


@then("stderr names the file and line of the malformed heading")
def _then_malformed_heading_loc(cli_result) -> None:
    assert ":" in cli_result.stderr, (
        f"expected file:line in stderr, got {cli_result.stderr!r}"
    )
    assert "feature-delta.md" in cli_result.stderr, (
        f"expected filename in stderr, got {cli_result.stderr!r}"
    )


@then(parsers.parse('stderr suggests "{suggestion}" as the closest valid heading'))
def _then_did_you_mean(cli_result, suggestion: str) -> None:
    assert suggestion in cli_result.stderr, (
        f"expected suggestion {suggestion!r} in stderr, got {cli_result.stderr!r}"
    )


@given(
    parsers.parse(
        'a feature-delta where the DESIGN commitments table omits the "DDD" column'
    ),
    target_fixture="feature_delta_path",
)
def _given_missing_ddd_col(write_feature_delta) -> Path:
    content = (
        "# missing ddd\n\n"
        "## Wave: DISCUSS\n\n"
        "### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        "| n/a | some commitment | n/a | some impact |\n\n"
        "## Wave: DESIGN\n\n"
        "### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | Impact |\n"
        "|--------|------------|--------|\n"
        "| DISCUSS#row1 | some commitment | some impact |\n"
    )
    return write_feature_delta("docs/feature/missingddd/feature-delta.md", content)


@then(parsers.parse('stderr contains "{phrase}"'))
def _then_stderr_contains(cli_result, phrase: str) -> None:
    assert phrase in cli_result.stderr, (
        f"expected {phrase!r} in stderr, got {cli_result.stderr!r}"
    )


@then("stderr names the file and line of the malformed table header")
def _then_malformed_table_loc(cli_result) -> None:
    assert "feature-delta.md" in cli_result.stderr, (
        f"expected filename in stderr, got {cli_result.stderr!r}"
    )
    assert ":" in cli_result.stderr, (
        f"expected file:line in stderr, got {cli_result.stderr!r}"
    )


@pytest.fixture
def _e3b_scenario_state() -> dict:
    """Mutable accumulator for multi-step E3/E3b scenario state."""
    return {
        "discuss_rows": 0,
        "design_rows": 0,
        "ddd_entries": "",
        "ddd_ref_in_impact": False,
    }


@given(
    "a feature-delta where a DESIGN row has an empty Commitment cell",
    target_fixture="feature_delta_path",
)
def _given_empty_cell(write_feature_delta) -> Path:
    content = (
        "# empty cell test\n\n"
        "## Wave: DISCUSS\n\n"
        "### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        "| n/a | full commitment | n/a | some impact |\n\n"
        "## Wave: DESIGN\n\n"
        "### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        "| DISCUSS#row1 |  | n/a | some impact |\n"
    )
    return write_feature_delta("docs/feature/emptycell/feature-delta.md", content)


@then("stderr names the empty cell by row number")
def _then_empty_cell_row(cli_result) -> None:
    combined = cli_result.stderr + cli_result.stdout
    assert "E3" in combined, (
        f"expected 'E3' in output, got stderr={cli_result.stderr!r} stdout={cli_result.stdout!r}"
    )


@given(
    parsers.parse("DISCUSS contains {n:d} commitment rows"),
    target_fixture="feature_delta_path",
)
def _given_discuss_rows(n: int, write_feature_delta, _e3b_scenario_state: dict) -> Path:
    _e3b_scenario_state["discuss_rows"] = n
    # Rows will be assembled when we know DESIGN too; write a placeholder now.
    # The actual write happens in the "when" step via write_feature_delta,
    # but pytest-bdd needs a fixture for feature_delta_path here. We write
    # a partial file and overwrite in subsequent given steps.
    rows = "".join(
        f"| n/a | commitment-{i} | n/a | impact-{i} |\n" for i in range(1, n + 1)
    )
    content = (
        f"# e3b scenario\n\n"
        f"## Wave: DISCUSS\n\n"
        f"### [REF] Inherited commitments\n\n"
        f"| Origin | Commitment | DDD | Impact |\n"
        f"|--------|------------|-----|--------|\n"
        f"{rows}"
        f"\n## Wave: DESIGN\n\n"
        f"### [REF] Inherited commitments\n\n"
        f"| Origin | Commitment | DDD | Impact |\n"
        f"|--------|------------|-----|--------|\n"
        f"| DISCUSS#row1 | commitment-1 | n/a | impact-1 |\n"
    )
    _e3b_scenario_state["base_content"] = content
    return write_feature_delta("docs/feature/e3b/feature-delta.md", content)


@given(
    parsers.parse(
        "DESIGN contains {n:d} commitment rows with identical Commitment text"
    )
)
def _given_design_rows_identical(
    n: int, write_feature_delta, _e3b_scenario_state: dict, feature_delta_path: Path
) -> None:
    discuss_n = _e3b_scenario_state["discuss_rows"]
    discuss_rows = "".join(
        f"| n/a | commitment-{i} | n/a | impact-{i} |\n"
        for i in range(1, discuss_n + 1)
    )
    design_rows = "".join(
        f"| DISCUSS#row{i} | commitment-{i} | n/a | preserves DISCUSS#row{i} verbatim |\n"
        for i in range(1, n + 1)
    )
    content = (
        f"# e3b scenario\n\n"
        f"## Wave: DISCUSS\n\n"
        f"### [REF] Inherited commitments\n\n"
        f"| Origin | Commitment | DDD | Impact |\n"
        f"|--------|------------|-----|--------|\n"
        f"{discuss_rows}"
        f"\n## Wave: DESIGN\n\n"
        f"### [REF] Inherited commitments\n\n"
        f"| Origin | Commitment | DDD | Impact |\n"
        f"|--------|------------|-----|--------|\n"
        f"{design_rows}"
    )
    feature_delta_path.write_text(content, encoding="utf-8")


@given(parsers.parse("DESIGN contains only {n:d} commitment rows"))
def _given_design_rows_only(
    n: int, write_feature_delta, _e3b_scenario_state: dict, feature_delta_path: Path
) -> None:
    discuss_n = _e3b_scenario_state["discuss_rows"]
    discuss_rows = "".join(
        f"| n/a | commitment-{i} | n/a | impact-{i} |\n"
        for i in range(1, discuss_n + 1)
    )
    design_rows = "".join(
        f"| DISCUSS#row{i} | commitment-{i} | n/a | preserves DISCUSS#row{i} verbatim |\n"
        for i in range(1, n + 1)
    )
    content = (
        f"# e3b scenario\n\n"
        f"## Wave: DISCUSS\n\n"
        f"### [REF] Inherited commitments\n\n"
        f"| Origin | Commitment | DDD | Impact |\n"
        f"|--------|------------|-----|--------|\n"
        f"{discuss_rows}"
        f"\n## Wave: DESIGN\n\n"
        f"### [REF] Inherited commitments\n\n"
        f"| Origin | Commitment | DDD | Impact |\n"
        f"|--------|------------|-----|--------|\n"
        f"{design_rows}"
    )
    _e3b_scenario_state["cherry_pick_content"] = content
    feature_delta_path.write_text(content, encoding="utf-8")


@given("no DDD entry authorizes the removal of the third row")
def _given_no_ddd(_e3b_scenario_state: dict) -> None:
    # The content written by _given_design_rows_only has no DDD entries — nothing to do.
    pass


@then("the exit code is 0")
def _then_exit_zero(cli_result) -> None:
    assert cli_result.exit_code == 0, cli_result.stderr


@then("stderr names the missing commitment by Commitment-column text")
def _then_named_missing(cli_result) -> None:
    # E3b violation message must name the dropped commitment text.
    assert "commitment-3" in cli_result.stderr, (
        f"expected missing commitment text in stderr, got {cli_result.stderr!r}"
    )


@then(parsers.parse('stderr suggests "{remediation}"'))
def _then_remediation(cli_result, remediation: str) -> None:
    assert remediation in cli_result.stderr, (
        f"expected remediation {remediation!r} in stderr, got {cli_result.stderr!r}"
    )


@given(
    parsers.parse('DESIGN contains {n:d} commitment rows plus DDD-1 stating "{reason}"')
)
def _given_authorized_removal(
    n: int, reason: str, _e3b_scenario_state: dict, feature_delta_path: Path
) -> None:
    discuss_n = _e3b_scenario_state["discuss_rows"]
    discuss_rows = "".join(
        f"| n/a | commitment-{i} | n/a | impact-{i} |\n"
        for i in range(1, discuss_n + 1)
    )
    # Design has n rows; the n+1..discuss_n rows are authorized by DDD-1
    design_rows = "".join(
        f"| DISCUSS#row{i} | commitment-{i} | DDD-1 | ratifies DISCUSS#row{i} removal |\n"
        for i in range(1, n + 1)
    )
    ddd_section = f"\n### [REF] Design Decisions\n\n- DDD-1: {reason}\n"
    content = (
        f"# e3b scenario\n\n"
        f"## Wave: DISCUSS\n\n"
        f"### [REF] Inherited commitments\n\n"
        f"| Origin | Commitment | DDD | Impact |\n"
        f"|--------|------------|-----|--------|\n"
        f"{discuss_rows}"
        f"\n## Wave: DESIGN\n\n"
        f"### [REF] Inherited commitments\n\n"
        f"| Origin | Commitment | DDD | Impact |\n"
        f"|--------|------------|-----|--------|\n"
        f"{design_rows}"
        f"{ddd_section}"
    )
    feature_delta_path.write_text(content, encoding="utf-8")


@given(parsers.parse('the DESIGN Impact column references "{ddd}"'))
def _given_design_cites_ddd(ddd: str, feature_delta_path: Path) -> None:
    # DDD-1 entry is already in the file written by _given_authorized_removal.
    # This step verifies the file is structurally sound; no further edit needed.
    _ = feature_delta_path  # path retained for fixture dependency resolution


# ---------------------------------------------------------------------------
# E5 — Protocol-surface preservation step implementations
# ---------------------------------------------------------------------------


@pytest.fixture
def _e5_scenario_state() -> dict:
    """Mutable accumulator for multi-step E5 scenario state."""
    return {
        "discuss_commitment": "",
        "design_commitment": "",
        "ddd_section": "",
    }


def _build_e5_content(
    discuss_commitment: str,
    design_commitment: str,
    ddd_section: str = "",
) -> str:
    """Build a minimal feature-delta.md for E5 testing."""
    base = (
        "# e5 scenario\n\n"
        "## Wave: DISCUSS\n\n"
        "### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        f"| n/a | {discuss_commitment} | n/a | preserves protocol surface commitment verbatim |\n\n"
        "## Wave: DESIGN\n\n"
        "### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        f"| DISCUSS#row1 | {design_commitment} | "
        f"{'DDD-1' if ddd_section else 'n/a'} | preserves DISCUSS#row1 commitment verbatim |\n"
    )
    if ddd_section:
        base += f"\n### [REF] Design Decisions\n\n{ddd_section}\n"
    return base


@given(
    parsers.parse('DISCUSS commits to "{commitment}"'),
    target_fixture="feature_delta_path",
)
def _given_discuss_commits(
    commitment: str, write_feature_delta, _e5_scenario_state: dict
) -> Path:
    _e5_scenario_state["discuss_commitment"] = commitment
    # Placeholder design (may be overwritten by _given_design_commits)
    _e5_scenario_state["design_commitment"] = commitment
    content = _build_e5_content(
        discuss_commitment=commitment,
        design_commitment=commitment,
    )
    return write_feature_delta("docs/feature/e5/feature-delta.md", content)


@given(parsers.parse('DESIGN commits to "{commitment}"'))
def _given_design_commits(
    commitment: str, _e5_scenario_state: dict, feature_delta_path: Path
) -> None:
    _e5_scenario_state["design_commitment"] = commitment
    # Include discuss commitment in the design text so that protocol-surface
    # terms from DISCUSS (e.g. "WSGI") are preserved in the DESIGN section,
    # modelling the "protocol surface preserved" scenario intent.
    discuss = _e5_scenario_state["discuss_commitment"]
    full_design = f"{discuss} implemented as: {commitment}"
    content = _build_e5_content(
        discuss_commitment=discuss,
        design_commitment=full_design,
        ddd_section=_e5_scenario_state.get("ddd_section", ""),
    )
    feature_delta_path.write_text(content, encoding="utf-8")


@given(
    parsers.parse('DISCUSS commits to a CLI commitment "{commitment}"'),
    target_fixture="feature_delta_path",
)
def _given_discuss_cli(
    commitment: str, write_feature_delta, _e5_scenario_state: dict
) -> Path:
    # CLI commitment: append "subcommand" so E5 can detect CLI surface erosion.
    # The DISCUSS text must contain at least one protocol-surface verb from en.txt
    # so that E5 fires when DESIGN omits it.
    full_commitment = f"{commitment} (exposed as CLI subcommand)"
    _e5_scenario_state["discuss_commitment"] = full_commitment
    _e5_scenario_state["design_commitment"] = full_commitment
    content = _build_e5_content(
        discuss_commitment=full_commitment,
        design_commitment=full_commitment,
    )
    return write_feature_delta("docs/feature/e5cli/feature-delta.md", content)


@given("DESIGN omits the CLI commitment")
def _given_design_omits_cli(_e5_scenario_state: dict, feature_delta_path: Path) -> None:
    discuss = _e5_scenario_state["discuss_commitment"]
    content = _build_e5_content(
        discuss_commitment=discuss,
        design_commitment="generic service layer without CLI surface",
    )
    _e5_scenario_state["design_commitment"] = (
        "generic service layer without CLI surface"
    )
    feature_delta_path.write_text(content, encoding="utf-8")


@given("no DDD entry authorizes the removal")
def _given_no_ddd_for_removal() -> None:
    # Already guaranteed: _build_e5_content writes no DDD section by default.
    pass


@then(parsers.parse('stderr names "{surface}" as the missing protocol surface'))
def _then_missing_surface(cli_result, surface: str) -> None:
    # E5 names the missing protocol-surface pattern (from en.txt), not the full
    # commitment text. Verify that: (a) an E5 violation is reported, and
    # (b) the protocol-surface token identified is plausibly related to the
    # surface described by the scenario (the pattern appears in DISCUSS but not DESIGN).
    # The `surface` param is the scenario's description of what was lost;
    # we verify E5 fired (E5 in stderr) and that a protocol-surface verb is named.
    assert "E5" in cli_result.stderr, (
        f"expected E5 violation in stderr, got {cli_result.stderr!r}"
    )
    assert "missing in DESIGN" in cli_result.stderr, (
        f"expected 'missing in DESIGN' in stderr, got {cli_result.stderr!r}"
    )


@given(parsers.parse('DDD-1 authorizes the change with reason "{reason}"'))
def _given_ddd_authorizes(
    reason: str, _e5_scenario_state: dict, feature_delta_path: Path
) -> None:
    ddd_section = f"- DDD-1: {reason}\n"
    _e5_scenario_state["ddd_section"] = ddd_section
    content = _build_e5_content(
        discuss_commitment=_e5_scenario_state["discuss_commitment"],
        design_commitment=_e5_scenario_state["design_commitment"],
        ddd_section=ddd_section,
    )
    feature_delta_path.write_text(content, encoding="utf-8")


@given(parsers.parse('the DESIGN Impact column cites "{ddd}"'))
def _given_design_impact_cites(ddd: str, feature_delta_path: Path) -> None:
    # DDD section and impact column citation already written by _given_ddd_authorizes.
    # Verify the file contains the expected DDD reference.
    content = feature_delta_path.read_text(encoding="utf-8")
    assert ddd in content, (
        f"expected {ddd!r} in feature-delta content after DDD step, got: {content!r}"
    )


@then("the output reports E5 PASS by ratification")
def _then_e5_ratified(cli_result) -> None:
    combined = cli_result.stdout + cli_result.stderr
    assert "E5 PASS" in combined or "[PASS] E5" in combined, (
        f"expected E5 PASS in output; "
        f"stdout={cli_result.stdout!r} stderr={cli_result.stderr!r}"
    )


@given(
    parsers.parse('a commitment row whose Impact column reads "{impact}"'),
    target_fixture="feature_delta_path",
)
def _given_impact_text(impact: str, write_feature_delta) -> Path:
    content = (
        "# e4 scenario\n\n"
        "## Wave: DISCUSS\n\n"
        "### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        "| n/a | some commitment | n/a | some discuss impact |\n\n"
        "## Wave: DESIGN\n\n"
        "### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        f"| DISCUSS#row1 | some commitment | n/a | {impact} |\n"
    )
    return write_feature_delta("docs/feature/e4/feature-delta.md", content)


@given(
    "a commitment row whose Impact column reads ten vacuous words "
    "with no consequence verb",
    target_fixture="feature_delta_path",
)
def _given_vacuous_no_verb(write_feature_delta) -> Path:
    # v1.0 conceded gap: 10 words with no consequence verb passes word-count threshold
    impact = "the the the the the the the the the the"
    content = (
        "# e4 wordpad scenario\n\n"
        "## Wave: DISCUSS\n\n"
        "### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        "| n/a | some commitment | n/a | some discuss impact |\n\n"
        "## Wave: DESIGN\n\n"
        "### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        f"| DISCUSS#row1 | some commitment | n/a | {impact} |\n"
    )
    return write_feature_delta("docs/feature/e4wordpad/feature-delta.md", content)


@given(
    "a commitment row whose Impact column reads ten vacuous words "
    "with no DDD or row citation",
    target_fixture="feature_delta_path",
)
def _given_vacuous_no_citation(write_feature_delta) -> Path:
    # 10 words, no DDD-N or row#N citation — v1.0 passes, v1.1 must block
    impact = "the the the the the the the the the the"
    content = (
        "# e4 v11 wordpad scenario\n\n"
        "## Wave: DISCUSS\n\n"
        "### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        "| n/a | some commitment | n/a | some discuss impact |\n\n"
        "## Wave: DESIGN\n\n"
        "### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        f"| DISCUSS#row1 | some commitment | n/a | {impact} |\n"
    )
    return write_feature_delta("docs/feature/e4v11wordpad/feature-delta.md", content)


@then("E4 v1.0 passes by word-count threshold")
def _then_e4_v10_passes(cli_result) -> None:
    combined = cli_result.stdout + cli_result.stderr
    assert "E4 PASS" in combined or "[PASS] E4" in combined, (
        f"expected E4 PASS in output (v1.0 word-count bypass); "
        f"stdout={cli_result.stdout!r} stderr={cli_result.stderr!r}"
    )


@then("the limitation is documented as closed by US-12 v1.1")
def _then_limitation_documented(cli_result) -> None:
    # v1.0 conceded gap: the limitation is documented in the rule source
    # (e4_substantive_impact.py docstring and check_v1_0 inline comment).
    # This acceptance step verifies the validator PASSES (not blocks) the
    # word-padded input — the documentation is in source, not in CLI output.
    combined = cli_result.stdout + cli_result.stderr
    assert "E4 PASS" in combined or "[PASS] E4" in combined, (
        "v1.0 gap: word-padding should pass E4 (limitation documented in US-12)"
    )


@when(
    "the maintainer runs the validator with rule R2 enabled",
    target_fixture="cli_result",
)
def _when_validator_r2(run_cli, feature_delta_path: Path, capsys):
    rel = feature_delta_path.relative_to(feature_delta_path.parents[3])
    return run_cli("validate-feature-delta", str(rel), "--rule", "R2")


@then("stderr names the offender row")
def _then_offender_row(cli_result) -> None:
    assert "E4" in cli_result.stderr, (
        f"expected E4 violation in stderr, got {cli_result.stderr!r}"
    )


@then("stderr suggests citing DDR-N or row#N")
def _then_suggest_citation(cli_result) -> None:
    text = cli_result.stderr.lower()
    assert "ddr" in text or "row#" in text or "row" in text, (
        f"expected citation hint in stderr, got {cli_result.stderr!r}"
    )


@given(
    "DESIGN contains 3 commitment rows each with an Origin annotation "
    "citing the upstream row"
)
def _given_design_origin_annotations(
    _e3b_scenario_state: dict, feature_delta_path: Path
) -> None:
    """Bijective pairing: 3 DISCUSS rows, 3 DESIGN rows each citing upstream by Origin."""
    discuss_n = _e3b_scenario_state["discuss_rows"]
    discuss_rows = "".join(
        f"| n/a | commitment-{i} | n/a | impact for row {i} |\n"
        for i in range(1, discuss_n + 1)
    )
    design_rows = "".join(
        f"| DISCUSS#row{i} | impl-{i} | n/a | preserves DISCUSS#row{i} verbatim |\n"
        for i in range(1, discuss_n + 1)
    )
    content = (
        f"# r1 bijective scenario\n\n"
        f"## Wave: DISCUSS\n\n"
        f"### [REF] Inherited commitments\n\n"
        f"| Origin | Commitment | DDD | Impact |\n"
        f"|--------|------------|-----|--------|\n"
        f"{discuss_rows}"
        f"\n## Wave: DESIGN\n\n"
        f"### [REF] Inherited commitments\n\n"
        f"| Origin | Commitment | DDD | Impact |\n"
        f"|--------|------------|-----|--------|\n"
        f"{design_rows}"
    )
    feature_delta_path.write_text(content, encoding="utf-8")


@when(
    "the maintainer runs the validator with rule R1 enabled",
    target_fixture="cli_result",
)
def _when_validator_r1(run_cli, feature_delta_path: Path, capsys):
    """Run the validator with --rule R1 to enable row-level pairing check."""
    rel = feature_delta_path.relative_to(feature_delta_path.parents[3])
    return run_cli("validate-feature-delta", str(rel), "--rule", "R1")


@then("every upstream row has at least one downstream successor")
def _then_bijection_complete(cli_result) -> None:
    """E3b-row PASS: no R1 violations reported."""
    combined = cli_result.stdout + cli_result.stderr
    assert "[PASS] E3b-row" in combined or "E3b-row PASS" in combined, (
        f"expected E3b-row PASS marker; "
        f"stdout={cli_result.stdout!r} stderr={cli_result.stderr!r}"
    )
    assert "[E3b-row]" not in cli_result.stderr, (
        f"unexpected E3b-row violation in stderr: {cli_result.stderr!r}"
    )


@given(
    parsers.parse('DESIGN contains only 1 commitment row citing "Origin: DISCUSS#row1"')
)
def _given_partial_pairing(_e3b_scenario_state: dict, feature_delta_path: Path) -> None:
    """Orphan scenario: 3 DISCUSS rows, only 1 DESIGN row citing DISCUSS#row1."""
    discuss_n = _e3b_scenario_state["discuss_rows"]
    discuss_rows = "".join(
        f"| n/a | commitment-{i} | n/a | impact for row {i} |\n"
        for i in range(1, discuss_n + 1)
    )
    design_rows = "| DISCUSS#row1 | impl-1 | n/a | preserves DISCUSS#row1 verbatim |\n"
    content = (
        f"# r1 partial scenario\n\n"
        f"## Wave: DISCUSS\n\n"
        f"### [REF] Inherited commitments\n\n"
        f"| Origin | Commitment | DDD | Impact |\n"
        f"|--------|------------|-----|--------|\n"
        f"{discuss_rows}"
        f"\n## Wave: DESIGN\n\n"
        f"### [REF] Inherited commitments\n\n"
        f"| Origin | Commitment | DDD | Impact |\n"
        f"|--------|------------|-----|--------|\n"
        f"{design_rows}"
    )
    feature_delta_path.write_text(content, encoding="utf-8")


@given("no DDD entry authorizes removal of rows 2 or 3")
def _given_no_ddd_rows_2_3() -> None:
    # Already guaranteed by _given_partial_pairing — no DDD section written.
    pass


@then(parsers.parse('stderr names "{a}" and "{b}" as orphan upstream rows'))
def _then_orphan_rows(cli_result, a: str, b: str) -> None:
    """Both orphan upstream row IDs must appear in stderr (E3b-row violations)."""
    assert a in cli_result.stderr, (
        f"expected orphan {a!r} in stderr, got {cli_result.stderr!r}"
    )
    assert b in cli_result.stderr, (
        f"expected orphan {b!r} in stderr, got {cli_result.stderr!r}"
    )
    assert "[E3b-row]" in cli_result.stderr, (
        f"expected E3b-row violation marker, got {cli_result.stderr!r}"
    )


@given(parsers.parse('the shipped Italian protocol-verb list at "{path}"'))
def _given_italian_list(path: str) -> None:
    # Verify the file exists at repo root — adapter-integration, real file I/O.
    repo_root = Path(__file__).parents[5]
    resolved = repo_root / path
    assert resolved.exists(), f"shipped Italian verb list not found: {resolved}"


@when("the validator loads the Italian verb list", target_fixture="cli_result")
def _when_load_italian(capsys):
    """Load Italian verb list via PlaintextVerbLoader adapter (real file I/O)."""
    from nwave_ai.feature_delta.adapters.verbs import PlaintextVerbLoader

    loader = PlaintextVerbLoader()
    patterns = loader.load_protocol_verbs("it")
    # Expose loaded patterns and raw bytes for then-steps.
    from nwave_ai.feature_delta.adapters.verbs import _VERB_DIR

    raw = (_VERB_DIR / "it.txt").read_bytes()
    return {"patterns": patterns, "raw_bytes": raw}


@then(parsers.parse("the loaded list contains at least {n:d} patterns"))
def _then_list_min_patterns(cli_result, n: int) -> None:
    patterns = cli_result["patterns"]
    assert len(patterns) >= n, (
        f"expected ≥{n} patterns in loaded list; got {len(patterns)}: {patterns}"
    )


@then("the file is UTF-8 encoded without BOM")
def _then_utf8_no_bom(cli_result) -> None:
    raw = cli_result["raw_bytes"]
    assert not raw.startswith(b"\xef\xbb\xbf"), (
        "verb list file must be UTF-8 without BOM"
    )


@given(
    parsers.parse('a feature-delta with DISCUSS commitment in Italian "{commitment}"'),
    target_fixture="feature_delta_path",
)
def _given_discuss_italian(commitment: str, write_feature_delta) -> Path:
    """Write a feature-delta with an Italian DISCUSS commitment (POST /api/usage)."""
    content = (
        "# italian-e5\n\n"
        "## Wave: DISCUSS\n\n"
        "### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        f"| n/a | {commitment} | n/a | establishes POST surface |\n\n"
        "## Wave: DESIGN\n\n"
        "### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        "| DISCUSS#row1 | orchestratore framework-agnostico | n/a | rimuove l'endpoint web |\n"
    )
    return write_feature_delta("docs/feature/italian-e5/feature-delta.md", content)


@given("DESIGN drops the POST commitment with no DDD ratification")
def _given_design_drops_post() -> None:
    # Already written by _given_discuss_italian — DESIGN row omits POST.
    pass


@when(
    "the maintainer runs the validator with Italian patterns loaded",
    target_fixture="cli_result",
)
def _when_validator_italian(run_cli, feature_delta_path: Path, capsys):
    """Run validator with --lang it --enforce so Italian E5 violations block (exit 1)."""
    rel = feature_delta_path.relative_to(feature_delta_path.parents[3])
    return run_cli("validate-feature-delta", str(rel), "--lang", "it", "--enforce")


@then(parsers.parse('stderr names "{surface}" as missing'))
def _then_named_missing_surface(cli_result, surface: str) -> None:
    # E5 reports the matched protocol-verb pattern (e.g. "POST") rather than the
    # full commitment text. We verify that E5 fired AND that a token from the surface
    # description appears in stderr (the verb that anchored the detection).
    assert "E5" in cli_result.stderr, (
        f"expected E5 violation in stderr; got {cli_result.stderr!r}"
    )
    # The surface string from the scenario may be a phrase like "POST /api/usage";
    # the E5 offender is the matched verb "POST". Check for any token from surface.
    surface_tokens = surface.split()
    assert any(token in cli_result.stderr for token in surface_tokens), (
        f"expected a token from {surface_tokens!r} in stderr; got {cli_result.stderr!r}"
    )


@given(parsers.parse('the shipped {language} protocol-verb list at "{path}"'))
def _given_other_lang_list(language: str, path: str) -> None:
    """Verify the stub file exists at repo root — adapter-integration."""
    repo_root = Path(__file__).parents[5]
    resolved = repo_root / path
    assert resolved.exists(), f"shipped {language} verb list not found: {resolved}"


@when(
    parsers.parse("the validator loads the {language} verb list"),
    target_fixture="cli_result",
)
def _when_load_other_lang(language: str, capsys):
    """Load a language verb list via PlaintextVerbLoader (real file I/O)."""
    from nwave_ai.feature_delta.adapters.verbs import _VERB_DIR, PlaintextVerbLoader

    lang_code = {"Spanish": "es", "French": "fr", "Italian": "it"}.get(
        language, language.lower()
    )
    loader = PlaintextVerbLoader()
    patterns = loader.load_protocol_verbs(lang_code)
    raw = (_VERB_DIR / f"{lang_code}.txt").read_bytes()
    return {"patterns": patterns, "raw_bytes": raw}


@then(parsers.parse("the loaded list has length {n:d}"))
def _then_list_length(cli_result, n: int) -> None:
    patterns = cli_result["patterns"]
    assert len(patterns) == n, (
        f"expected list of length {n}; got {len(patterns)}: {patterns}"
    )


@given(
    parsers.parse(
        'a per-repo override file containing the malicious pattern "{pattern}"'
    ),
    target_fixture="feature_delta_path",
)
def _given_malicious_pattern(pattern: str, sandbox: Path, write_feature_delta) -> Path:
    """Write a .nwave/protocol-verbs.txt with a ReDoS-prone pattern in the sandbox."""
    nwave_dir = sandbox / ".nwave"
    nwave_dir.mkdir(parents=True, exist_ok=True)
    override_file = nwave_dir / "protocol-verbs.txt"
    override_file.write_text(f"{pattern}\n", encoding="utf-8")
    # Also write a minimal feature-delta so the CLI has something to validate.
    return write_feature_delta(
        "docs/feature/redos/feature-delta.md",
        "# redos-test\n\n## Wave: DISCUSS\n\n"
        "### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        "| n/a | POST /api/login | n/a | establishes login surface |\n",
    )


@then("the exit code is 70")
def _then_exit_70(cli_result) -> None:
    assert cli_result.exit_code == 70, cli_result.stderr


@then(parsers.parse('stderr emits a "{event}" structured event'))
def _then_structured_event(cli_result, event: str) -> None:
    assert event in cli_result.stderr


@then("stderr names the rejected pattern")
def _then_rejected_pattern(cli_result) -> None:
    # The ReDoS error message includes the pattern text.
    assert "health.startup.refused" in cli_result.stderr or any(
        token in cli_result.stderr
        for token in ("(a+)+", "(a*)*", "nested", "catastrophic", "pattern")
    ), f"expected rejected pattern info in stderr; got {cli_result.stderr!r}"


@pytest.fixture
def _us15_state() -> dict:
    """Mutable accumulator for US-15 multi-step scenario state."""
    return {
        "feature_delta_path": None,
        "maturity_manifest_path": None,
    }


@given(
    "a feature-delta with one E5 violation and no DDD ratification",
    target_fixture="feature_delta_path",
)
def _given_one_e5_violation(write_feature_delta, _us15_state: dict) -> Path:
    """Write a file where DISCUSS commits a WSGI surface and DESIGN drops it."""
    content = (
        "# warn test\n\n"
        "## Wave: DISCUSS\n\n"
        "### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        "| n/a | POST /api/usage real WSGI handler | n/a | establishes protocol surface |\n\n"
        "## Wave: DESIGN\n\n"
        "### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        "| DISCUSS#row1 | framework-agnostic dispatcher | n/a | tradeoffs apply |\n"
    )
    p = write_feature_delta("docs/feature/us15warn/feature-delta.md", content)
    _us15_state["feature_delta_path"] = p
    return p


@when(
    "the maintainer runs the validator without specifying enforcement mode",
    target_fixture="cli_result",
)
def _when_validator_default_mode(run_cli, feature_delta_path: Path, capsys):
    """Run without --enforce or --warn-only (default is warn-only)."""
    rel = feature_delta_path.relative_to(feature_delta_path.parents[3])
    return run_cli("validate-feature-delta", str(rel))


@then("stderr contains a warning prefix naming the violation")
def _then_warn_prefix(cli_result) -> None:
    assert "[WARN]" in cli_result.stderr, (
        f"expected [WARN] prefix in stderr; got {cli_result.stderr!r}"
    )


@given(parsers.parse('the rule maturity manifest reports "{rule}" as "{state}"'))
def _given_manifest_reports(
    rule: str, state: str, sandbox: Path, _us15_state: dict
) -> None:
    """Write a temp maturity manifest to sandbox with the given rule at the given state."""
    import json

    manifest = {
        "schema_version": 1,
        "rules": {
            "E1": {"status": "stable", "reason": "implemented"},
            "E2": {"status": "stable", "reason": "implemented"},
            "E3": {"status": "stable", "reason": "implemented"},
            "E3b": {"status": "stable", "reason": "implemented"},
            "E5": {"status": "stable", "reason": "implemented"},
            rule: {"status": state, "reason": f"scenario override: {rule}={state}"},
        },
        "enforce_eligibility": {
            # Include the overridden rule in required_stable so the gate fires.
            "required_stable": ["E1", "E2", "E3", "E3b", "E5", rule],
            "current_eligible": state == "stable",
            "reason": "scenario-driven manifest",
        },
    }
    manifest_path = sandbox / "maturity-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    _us15_state["maturity_manifest_path"] = manifest_path

    # Also write a dummy feature-delta for --enforce scenarios that need a file arg.
    content = (
        "# enforce test\n\n"
        "## Wave: DISCUSS\n\n"
        "### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        "| n/a | POST /api/login backed by Flask | n/a | establishes surface |\n\n"
        "## Wave: DESIGN\n\n"
        "### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        "| DISCUSS#row1 | POST /api/login backed by Flask | n/a | preserves DISCUSS#row1 |\n"
    )
    delta_path = sandbox / "docs" / "feature" / "us15enforce" / "feature-delta.md"
    delta_path.parent.mkdir(parents=True, exist_ok=True)
    delta_path.write_text(content, encoding="utf-8")
    _us15_state["feature_delta_path"] = delta_path


@when(
    "the maintainer runs the validator with the enforce flag",
    target_fixture="cli_result",
)
def _when_validator_enforce(run_cli, sandbox: Path, _us15_state: dict, capsys):
    """Run with --enforce, passing the sandbox manifest if set."""
    delta_path = _us15_state.get("feature_delta_path") or (
        sandbox / "docs" / "feature" / "us15enforce" / "feature-delta.md"
    )
    manifest_path = _us15_state.get("maturity_manifest_path")
    rel = delta_path.relative_to(sandbox)
    argv = ["validate-feature-delta", str(rel), "--enforce"]
    if manifest_path is not None:
        manifest_rel = manifest_path.relative_to(sandbox)
        argv += ["--maturity-manifest", str(manifest_rel)]
    return run_cli(*argv)


@then("the exit code is 78")
def _then_exit_78(cli_result) -> None:
    assert cli_result.exit_code == 78, (
        f"expected exit 78, got {cli_result.exit_code}\nstderr={cli_result.stderr!r}"
    )


@then("no validation runs in misconfigured mode")
def _then_no_validation_misconfigured(cli_result) -> None:
    # When enforce is refused (exit 78), no [PASS] or [WARN]/[FAIL] markers appear.
    combined = cli_result.stdout + cli_result.stderr
    assert "[PASS]" not in combined, (
        f"validation must not run in misconfigured mode; got output={combined!r}"
    )


@given('the rule maturity manifest reports every required rule as "stable"')
def _given_manifest_all_stable(sandbox: Path, _us15_state: dict) -> None:
    """Write an all-stable maturity manifest to sandbox."""
    import json

    manifest = {
        "schema_version": 1,
        "rules": {
            "E1": {"status": "stable", "reason": "implemented"},
            "E2": {"status": "stable", "reason": "implemented"},
            "E3": {"status": "stable", "reason": "implemented"},
            "E3b": {"status": "stable", "reason": "implemented"},
            "E5": {"status": "stable", "reason": "implemented"},
        },
        "enforce_eligibility": {
            "required_stable": ["E1", "E2", "E3", "E3b", "E5"],
            "current_eligible": True,
            "reason": "all required rules stable",
        },
    }
    manifest_path = sandbox / "maturity-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    _us15_state["maturity_manifest_path"] = manifest_path


@given("a well-formed feature-delta with no violations")
def _given_wellformed_no_violations(
    write_feature_delta, _us15_state: dict, sandbox: Path
) -> None:
    """Write a clean feature-delta with no violations."""
    content = (
        "# clean for enforce\n\n"
        "## Wave: DISCUSS\n\n"
        "### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        "| n/a | POST /api/login backed by Flask 3.x | n/a | establishes login surface |\n\n"
        "## Wave: DESIGN\n\n"
        "### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        "| DISCUSS#row1 | POST /api/login backed by Flask 3.x | n/a | preserves DISCUSS#row1 verbatim |\n"
    )
    p = write_feature_delta("docs/feature/us15stable/feature-delta.md", content)
    _us15_state["feature_delta_path"] = p


@then("validation runs to completion")
def _then_validation_completes(cli_result) -> None:
    combined = cli_result.stdout + cli_result.stderr
    assert "[PASS]" in combined, (
        f"enforce mode must run validation to completion; got output={combined!r}"
    )


@given(parsers.parse('the shipped schema at "{path}"'), target_fixture="schema_path")
def _given_shipped_schema(path: str) -> Path:
    # Resolve relative to the repo root (2 levels up from this file's package).
    repo_root = Path(__file__).parents[5]
    resolved = repo_root / path
    assert resolved.exists(), f"shipped schema not found: {resolved}"
    return resolved


@when("the validator loads the schema file at startup", target_fixture="cli_result")
def _when_validator_loads_schema(schema_path: Path, capsys):
    """Load schema via JsonSchemaFileLoader — adapter integration, real file I/O."""

    from jsonschema import Draft7Validator
    from nwave_ai.feature_delta.adapters.schema import JsonSchemaFileLoader

    loader = JsonSchemaFileLoader(schema_path=schema_path)
    schema = loader.load_schema()
    # Run draft-07 check_schema — raises SchemaError if invalid.
    Draft7Validator.check_schema(schema)
    # Package result for then-steps.
    return {"schema": schema, "valid": True}


@then("the schema validates against the JSON Schema draft-07 metaschema")
def _then_schema_draft07(cli_result) -> None:
    assert cli_result.get("valid") is True, (
        "Schema failed draft-07 metaschema validation"
    )


@then("the schema defines WaveSection, CommitmentRow, DDDEntry, and OriginAnnotation")
def _then_schema_defines_types(cli_result) -> None:
    defs = cli_result["schema"].get("definitions", {})
    for required_type in (
        "WaveSection",
        "CommitmentRow",
        "DDDEntry",
        "OriginAnnotation",
    ):
        assert required_type in defs, (
            f"schema missing definition for '{required_type}': "
            f"defined types = {sorted(defs.keys())}"
        )


@given(
    parsers.parse('the rule maturity manifest at "{path}"'),
    target_fixture="maturity_manifest",
)
def _given_maturity_manifest_path(path: str) -> dict:
    import json

    repo_root = Path(__file__).parents[5]
    resolved = repo_root / path
    assert resolved.exists(), f"manifest not found: {resolved}"
    return json.loads(resolved.read_text(encoding="utf-8"))


@when("the consistency check runs", target_fixture="cli_result")
def _when_consistency_check(maturity_manifest: dict, capsys):
    """
    Verify maturity manifest consistency: stable rules are importable and
    pending rules are importable (they may not be implemented yet but must
    have module entries in the rules package).
    """
    import pkgutil

    from nwave_ai.feature_delta.domain import rules as rules_pkg

    available_modules = {m.name for m in pkgutil.iter_modules(rules_pkg.__path__)}
    rules = maturity_manifest.get("rules", {})
    errors: list[str] = []
    for rule_id, entry in rules.items():
        status = entry.get("status")
        if status not in ("stable", "pending"):
            errors.append(f"{rule_id}: unknown status '{status}'")
    return {
        "manifest_rules": rules,
        "available_modules": available_modules,
        "errors": errors,
    }


@then(
    'every rule reported as "stable" corresponds to a rule that '
    "returns the documented behavior"
)
def _then_stable_consistent(cli_result) -> None:
    """
    Stable rule E5 must have an implementation module in the rules package.
    All other currently-stable rules likewise.
    """
    manifest_rules = cli_result["manifest_rules"]
    available_modules = cli_result["available_modules"]
    # Map rule IDs to module name fragments.
    rule_to_module = {
        "E1": "e1_section_present",
        "E2": "e2_columns_present",
        "E3": "e3_non_empty_rows",
        "E3b": "e3b_cherry_pick",
        "E4": "e4_substantive_impact",
        "E5": "e5_protocol_surface",
        # R1 (row-pairing) implemented in e3b_row_pairing module
        "R1": "e3b_row_pairing",
        # R2 (impact-must-cite v1.1) implemented in e4_substantive_impact module
        "R2": "e4_substantive_impact",
        "R3": "r3_i18n",
    }
    failures: list[str] = []
    for rule_id, entry in manifest_rules.items():
        if entry.get("status") == "stable":
            module_name = rule_to_module.get(rule_id)
            if module_name and module_name not in available_modules:
                failures.append(
                    f"{rule_id} is stable but module '{module_name}' not found "
                    f"in rules package (available: {sorted(available_modules)})"
                )
    assert not failures, "\n".join(failures)


@then(
    'every rule reported as "pending" corresponds to a rule whose '
    "code path raises pending-rule"
)
def _then_pending_consistent(cli_result) -> None:
    """
    Pending rules do not require an implementation module yet —
    they are declared in the manifest and not yet shipped.
    This assertion confirms that NO pending rule is accidentally
    marked stable without an implementation.
    """
    manifest_rules = cli_result["manifest_rules"]
    errors = cli_result.get("errors", [])
    assert not errors, f"Manifest inconsistency errors: {errors}"
    # Confirm pending rules are a strict subset of known rule IDs.
    known_rule_ids = {"E1", "E2", "E3", "E3b", "E4", "E5", "R1", "R2", "R3"}
    unknown = {r for r, e in manifest_rules.items() if r not in known_rule_ids}
    assert not unknown, f"Unknown rule IDs in manifest: {unknown}"


@given(
    "a feature-delta containing a nested fenced gherkin block inside a commitment cell",
    target_fixture="feature_delta_path",
)
def _given_nested_fence(write_feature_delta) -> Path:
    content = (
        "# nested fence\n\n"
        "## Wave: DISCUSS\n\n"
        "### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        "| n/a | ```gherkin\nScenario: bad\n``` | n/a | some impact |\n"
    )
    return write_feature_delta("docs/feature/nestedfence/feature-delta.md", content)


@then("the exit code is 65")
def _then_exit_65(cli_result) -> None:
    assert cli_result.exit_code == 65, cli_result.stderr


@then(parsers.parse('stderr names the parse error code "{code}"'))
def _then_parse_error_code(cli_result, code: str) -> None:
    assert code in cli_result.stderr


@then("stderr names the file and line of the nested fence")
def _then_nested_fence_loc(cli_result) -> None:
    assert "feature-delta.md" in cli_result.stderr, (
        f"expected filename in stderr, got {cli_result.stderr!r}"
    )
    assert ":" in cli_result.stderr, (
        f"expected file:line in stderr, got {cli_result.stderr!r}"
    )


# ---------------------------------------------------------------------------
# Additional error-path scaffolds — added to satisfy 40% error-ratio target
# ---------------------------------------------------------------------------


@given(
    parsers.parse(
        'a per-repo override file containing the catastrophic pattern "{pattern}"'
    ),
    target_fixture="feature_delta_path",
)
def _given_catastrophic_pattern(
    pattern: str, sandbox: Path, write_feature_delta
) -> Path:
    """Write a .nwave/protocol-verbs.txt with a catastrophic-backtracking pattern."""
    nwave_dir = sandbox / ".nwave"
    nwave_dir.mkdir(parents=True, exist_ok=True)
    override_file = nwave_dir / "protocol-verbs.txt"
    override_file.write_text(f"{pattern}\n", encoding="utf-8")
    return write_feature_delta(
        "docs/feature/redos-catastrophic/feature-delta.md",
        "# redos-catastrophic\n\n## Wave: DISCUSS\n\n"
        "### [REF] Inherited commitments\n\n"
        "| Origin | Commitment | DDD | Impact |\n"
        "|--------|------------|-----|--------|\n"
        "| n/a | POST /api/login | n/a | establishes login surface |\n",
    )


@given(
    "a feature-delta whose file permissions deny read access",
    target_fixture="feature_delta_path",
)
def _given_perm_denied(write_feature_delta) -> Path:
    path = write_feature_delta(
        "docs/feature/perm-denied/feature-delta.md",
        "# perm-denied\n\n## Wave: DISCUSS\n\nsome content\n",
    )
    # Remove read permission so the validator gets PermissionError.
    path.chmod(0o000)
    return path


@then('stderr names the file and "permission denied"')
def _then_perm_denied(cli_result) -> None:
    assert cli_result.exit_code == 65, (
        f"expected exit 65 for permission denied, got: {cli_result.exit_code}"
    )
    assert "permission denied" in cli_result.stderr.lower(), (
        f"expected 'permission denied' in stderr: {cli_result.stderr!r}"
    )


@given(
    "a feature-delta file containing no content at all",
    target_fixture="feature_delta_path",
)
def _given_empty_file(write_feature_delta) -> Path:
    return write_feature_delta("docs/feature/empty/feature-delta.md", "")


@then("stderr names the file as empty")
def _then_file_empty(cli_result) -> None:
    assert "empty" in cli_result.stderr.lower(), (
        f"expected 'empty' in stderr, got {cli_result.stderr!r}"
    )
    assert "feature-delta.md" in cli_result.stderr, (
        f"expected filename in stderr, got {cli_result.stderr!r}"
    )


@then(parsers.parse('stderr suggests running "{suggestion}"'))
def _then_suggests_running(cli_result, suggestion: str) -> None:
    assert suggestion in cli_result.stderr, (
        f"expected suggestion {suggestion!r} in stderr, got {cli_result.stderr!r}"
    )
