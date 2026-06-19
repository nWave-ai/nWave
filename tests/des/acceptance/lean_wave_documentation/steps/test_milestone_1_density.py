"""Step definitions for milestone-1-density-config.feature.

Scenarios are activated one at a time as DELIVER progresses; the rest stay
@skip until their owning step removes the tag. This module is the pytest-bdd
binding layer for the feature file.

Driving ports exercised:
- nwave-ai install (subprocess CLI) — first-run prompt + idempotent re-run
- nwave-ai doctor (subprocess CLI) — density display
- DISCOVER + DISCUSS wave skills — single-file layout enforcement
- validate_feature_delta.py (subprocess CLI) — schema validator
- scripts.shared.density_config.resolve_density() — shared utility (NOT internal
  DES component); pure-function entry exercised directly by US-3 cascade
  scenarios per D12 (rigor.profile → documentation.density override → default)

Tag-based skip is applied via the @skip Gherkin tag; see conftest.py at the
repo's pytest-bdd integration layer for the hook that maps @skip → pytest.skip.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from pytest_bdd import given, parsers, scenarios, then, when

from scripts.shared.density_config import Density, resolve_density


# Link feature file
scenarios("../milestone-1-density-config.feature")


# ---------------------------------------------------------------------------
# Subprocess helper for the doctor CLI driving port (D6 density display)
# ---------------------------------------------------------------------------


def _run_doctor(home_dir: Path) -> subprocess.CompletedProcess[str]:
    """Run `nwave-ai doctor` with HOME monkeypatched to a tmp directory.

    Driver port for the D12 inheritance scenarios: stdout must surface the
    resolved density mode + provenance label without leaking host state.

    Args:
        home_dir: tmp_path home for the subprocess (HOME env var)

    Returns:
        CompletedProcess with text-mode stdout/stderr.
    """
    project_root = Path(__file__).parent.parent.parent.parent.parent.parent
    cli_module = "nwave_ai.cli"

    env = os.environ.copy()
    env["HOME"] = str(home_dir)
    env["PYTHONPATH"] = (
        f"{project_root}{os.pathsep}{project_root / 'src'}"
        f"{os.pathsep}{env.get('PYTHONPATH', '')}"
    )

    return subprocess.run(
        [sys.executable, "-m", cli_module, "doctor"],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(project_root),
        timeout=30,
    )


# ---------------------------------------------------------------------------
# Subprocess helper for the install CLI driving port
# ---------------------------------------------------------------------------


def _run_install_with_density_only(
    home_dir: Path, stdin_text: str
) -> subprocess.CompletedProcess[str]:
    """Run the install CLI's density-prompt phase with HOME monkeypatched.

    The full install pipeline performs filesystem mutations on ~/.claude that
    are out of scope for the density-prompt scenario. This helper invokes the
    install entrypoint with --density-only, which exits immediately after the
    density-prompt branch — letting acceptance tests assert on
    ~/.nwave/global-config.json without spinning up plugins.

    Args:
        home_dir: tmp_path home for the subprocess (HOME env var)
        stdin_text: characters to send to stdin (the user's "lean"/"full" reply)

    Returns:
        CompletedProcess with text-mode stdout/stderr.
    """
    project_root = Path(__file__).parent.parent.parent.parent.parent.parent
    cli_module = "nwave_ai.cli"

    env = os.environ.copy()
    env["HOME"] = str(home_dir)
    env["PYTHONPATH"] = (
        f"{project_root}{os.pathsep}{project_root / 'src'}"
        f"{os.pathsep}{env.get('PYTHONPATH', '')}"
    )

    return subprocess.run(
        [sys.executable, "-m", cli_module, "install", "--density-only"],
        input=stdin_text,
        capture_output=True,
        text=True,
        env=env,
        cwd=str(project_root),
        timeout=30,
    )


# ---------------------------------------------------------------------------
# Background — shared by all scenarios in this feature
# ---------------------------------------------------------------------------


@given("Marco's nWave home is a fresh temporary directory")
def _marco_fresh_home(marco_home: Path) -> None:
    """Background step: marco_home fixture already provides a fresh tmp HOME."""
    assert marco_home.exists(), f"marco_home not created at {marco_home}"


# ---------------------------------------------------------------------------
# Scenario: First-install prompts once for density and persists Marco's choice
# ---------------------------------------------------------------------------


@given("the nWave global configuration file does not exist")
def _global_config_absent(global_config_path: Path) -> None:
    """Pre-condition: no ~/.nwave/global-config.json on disk."""
    assert not global_config_path.exists(), (
        f"Expected absent global-config.json, found one at {global_config_path}"
    )


@when(
    'Marco runs install interactively and answers "lean"',
    target_fixture="install_result",
)
def _install_interactive_answer_lean(
    marco_home: Path, ctx: dict[str, Any]
) -> subprocess.CompletedProcess[str]:
    """Drive the install CLI through stdin with the user's "lean" reply."""
    result = _run_install_with_density_only(marco_home, stdin_text="lean\n")
    ctx["first_run_stdout"] = result.stdout
    ctx["first_run_returncode"] = result.returncode
    return result


@then('the global configuration records the default density as "lean"')
def _density_persisted_lean(global_config_path: Path) -> None:
    """Driven port assertion: ~/.nwave/global-config.json has density=lean."""
    assert global_config_path.exists(), (
        f"Install did not create global-config.json at {global_config_path}"
    )
    payload = json.loads(global_config_path.read_text(encoding="utf-8"))
    documentation = payload.get("documentation", {})
    assert documentation.get("density") == "lean", (
        f"Expected documentation.density=='lean', got payload={payload!r}"
    )


@then(
    parsers.parse(
        'the global configuration records the expansion prompt as "{expected}"'
    )
)
def _expansion_prompt_persisted(global_config_path: Path, expected: str) -> None:
    payload = json.loads(global_config_path.read_text(encoding="utf-8"))
    documentation = payload.get("documentation", {})
    assert documentation.get("expansion_prompt") == expected, (
        f"Expected documentation.expansion_prompt=={expected!r}, got payload={payload!r}"
    )


@then("running install a second time does not prompt Marco again")
def _second_install_does_not_prompt(
    marco_home: Path, global_config_path: Path, ctx: dict[str, Any]
) -> None:
    """Idempotency: re-run with empty stdin must not block; config unchanged."""
    before = global_config_path.read_text(encoding="utf-8")

    # Empty stdin: if the prompt fires, typer blocks waiting for input and the
    # subprocess will hang; the timeout will trip and the test fails.
    second = _run_install_with_density_only(marco_home, stdin_text="")

    assert second.returncode == 0, (
        f"Second install failed: stdout={second.stdout!r} stderr={second.stderr!r}"
    )
    after = global_config_path.read_text(encoding="utf-8")
    assert before == after, "Second install rewrote global-config.json"

    # Heuristic: the prompt string MUST NOT appear in the second-run stdout.
    assert "Documentation density" not in second.stdout, (
        f"Second install re-prompted: stdout={second.stdout!r}"
    )


# ---------------------------------------------------------------------------
# D12 — rigor.profile inheritance scenarios (AC-3.f, AC-3.g)
# ---------------------------------------------------------------------------


def _write_global_config(global_config_path: Path, payload: dict[str, Any]) -> None:
    """Persist `payload` as `~/.nwave/global-config.json`, creating parents."""
    global_config_path.parent.mkdir(parents=True, exist_ok=True)
    global_config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


@given(
    parsers.parse(
        'Marco\'s `~/.nwave/global-config.json` has `rigor.profile = "{profile}"` set'
    )
)
def _global_config_with_rigor_profile(
    profile: str, global_config_path: Path, ctx: dict[str, Any]
) -> None:
    """Pre-condition: write rigor.profile only (no documentation block)."""
    _write_global_config(global_config_path, {"rigor": {"profile": profile}})
    ctx["rigor_profile"] = profile


@given("no `documentation.density` key is present in the config")
def _no_documentation_density(global_config_path: Path) -> None:
    """Sanity assertion: payload must NOT carry a documentation.density."""
    payload = json.loads(global_config_path.read_text(encoding="utf-8"))
    documentation = payload.get("documentation", {})
    assert documentation.get("density") is None, (
        f"Expected no documentation.density key, found {documentation!r}"
    )


@given("no `documentation.density` key is present")
def _no_documentation_density_short(global_config_path: Path) -> None:
    """Outline form: same precondition, alternate phrasing for the cascade rows."""
    _no_documentation_density(global_config_path)


@given(
    parsers.parse(
        'Marco\'s `~/.nwave/global-config.json` has `documentation.density = "{density}"`'
        ' AND `rigor.profile = "{profile}"` set'
    )
)
def _global_config_with_explicit_and_rigor(
    density: str,
    profile: str,
    global_config_path: Path,
    ctx: dict[str, Any],
) -> None:
    """Pre-condition: explicit override AND rigor.profile both present."""
    _write_global_config(
        global_config_path,
        {
            "documentation": {"density": density, "expansion_prompt": "ask"},
            "rigor": {"profile": profile},
        },
    )
    ctx["explicit_density"] = density
    ctx["rigor_profile"] = profile


@when("Marco runs `nwave-ai doctor`", target_fixture="doctor_result")
def _marco_runs_doctor(
    marco_home: Path, ctx: dict[str, Any]
) -> subprocess.CompletedProcess[str]:
    """Driving port: invoke the real `nwave-ai doctor` subprocess."""
    result = _run_doctor(marco_home)
    ctx["doctor_stdout"] = result.stdout
    ctx["doctor_returncode"] = result.returncode
    return result


@then(parsers.parse("stdout contains `{expected_line}`"))
def _doctor_stdout_contains(
    expected_line: str, doctor_result: subprocess.CompletedProcess[str]
) -> None:
    """Driven port assertion: doctor stdout surfaces the density line."""
    assert expected_line in doctor_result.stdout, (
        f"Expected line {expected_line!r} not in doctor stdout.\n"
        f"stdout={doctor_result.stdout!r}\nstderr={doctor_result.stderr!r}"
    )


# ---------------------------------------------------------------------------
# D12 — Scenario Outline: cascade matrix (pure-function port)
# ---------------------------------------------------------------------------


@when(
    "Marco's wave skill calls `density_config.resolve_density(global_config)`",
    target_fixture="resolved_density",
)
def _wave_skill_calls_resolve_density(global_config_path: Path) -> Density:
    """Driving port (domain scope): call resolve_density on the on-disk config."""
    payload = json.loads(global_config_path.read_text(encoding="utf-8"))
    return resolve_density(payload)


@then(parsers.parse('the returned density is "{expected_density}"'))
def _returned_density_matches(expected_density: str, resolved_density: Density) -> None:
    assert resolved_density.mode == expected_density, (
        f"Expected density.mode={expected_density!r}, got {resolved_density!r}"
    )


@then(parsers.parse('the returned expansion_prompt is "{expected_prompt}"'))
def _returned_expansion_prompt_matches(
    expected_prompt: str, resolved_density: Density
) -> None:
    assert resolved_density.expansion_prompt == expected_prompt, (
        f"Expected density.expansion_prompt={expected_prompt!r}, "
        f"got {resolved_density!r}"
    )


# ---------------------------------------------------------------------------
# US-5 / C14 — feature-delta schema validator (AC-5.c)
# ---------------------------------------------------------------------------


def _run_validator_subprocess(
    target: Path,
) -> subprocess.CompletedProcess[str]:
    """Invoke the validator script via subprocess; capture exit code + stdout.

    Driving port: the CLI shell at `scripts/validation/validate_feature_delta.py`.
    """
    project_root = Path(__file__).parent.parent.parent.parent.parent.parent
    script = project_root / "scripts" / "validation" / "validate_feature_delta.py"
    env = os.environ.copy()
    env["PYTHONPATH"] = (
        f"{project_root}{os.pathsep}{project_root / 'src'}"
        f"{os.pathsep}{env.get('PYTHONPATH', '')}"
    )
    return subprocess.run(
        [sys.executable, str(script), str(target)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(project_root),
        timeout=30,
    )


@given(
    parsers.parse(
        'Marco has a well-formed lean feature-delta.md for feature "{feature}"'
    ),
    target_fixture="feature_delta_path",
)
def _well_formed_feature_delta(
    feature: str, marco_repo: Path, ctx: dict[str, Any]
) -> Path:
    """Pre-condition: write a minimal lean-compliant feature-delta.md to disk.

    Real filesystem under tmp_path; every heading conforms to the D2 schema
    `## Wave: <NAME> / [REF|WHY|HOW] <Section>`.
    """
    feature_dir = marco_repo / "docs" / "feature" / feature
    feature_dir.mkdir(parents=True, exist_ok=True)
    target = feature_dir / "feature-delta.md"
    target.write_text(
        "# Feature delta\n"
        "\n"
        "## Wave: DISCUSS / [REF] Persona\n"
        "Marco solo dev.\n"
        "\n"
        "## Wave: DISCUSS / [REF] Job-to-be-done\n"
        "Lean wave outputs.\n"
        "\n"
        "## Wave: DESIGN / [WHY] Rationale\n"
        "Token-density rationale.\n"
        "\n"
        "## Wave: DELIVER / [HOW] Cookbook\n"
        "Subprocess CLI commands.\n",
        encoding="utf-8",
    )
    ctx["feature_delta_path"] = target
    return target


@given(
    parsers.parse(
        "Marco has a feature-delta.md containing a heading "
        '"{heading}" missing the schema prefix'
    ),
    target_fixture="feature_delta_path",
)
def _malformed_feature_delta(
    heading: str, marco_repo: Path, ctx: dict[str, Any]
) -> Path:
    """Pre-condition: write a feature-delta.md whose heading lacks the schema."""
    feature_dir = marco_repo / "docs" / "feature" / "broken-feat"
    feature_dir.mkdir(parents=True, exist_ok=True)
    target = feature_dir / "feature-delta.md"
    target.write_text(
        f"# Broken feature delta\n\n{heading}\nbody text\n",
        encoding="utf-8",
    )
    ctx["feature_delta_path"] = target
    ctx["malformed_heading"] = heading
    return target


@when(
    "Marco runs the feature-delta schema validator on it",
    target_fixture="validator_result",
)
def _run_validator_on_feature_delta(
    feature_delta_path: Path, ctx: dict[str, Any]
) -> subprocess.CompletedProcess[str]:
    """Driving port: invoke the validator CLI with the prepared delta path."""
    result = _run_validator_subprocess(feature_delta_path)
    ctx["validator_stdout"] = result.stdout
    ctx["validator_stderr"] = result.stderr
    ctx["validator_returncode"] = result.returncode
    return result


@then("the validator exits successfully")
def _validator_exits_zero(
    validator_result: subprocess.CompletedProcess[str],
) -> None:
    assert validator_result.returncode == 0, (
        f"Validator exited {validator_result.returncode}; "
        f"stdout={validator_result.stdout!r} stderr={validator_result.stderr!r}"
    )


@then("the validator reports the section count grouped by [REF], [WHY], and [HOW]")
def _validator_reports_section_count(
    validator_result: subprocess.CompletedProcess[str],
) -> None:
    """Driven port assertion: stdout names the wave-section count.

    Per AC-5.c the validator surfaces the count of validated wave sections
    (the schema groups by [REF]/[WHY]/[HOW] tokens and counts them together).
    """
    stdout = validator_result.stdout
    assert "Feature delta is valid" in stdout, (
        f"Expected success banner in stdout, got: {stdout!r}"
    )
    assert "wave sections checked" in stdout, (
        f"Expected wave-section count in stdout, got: {stdout!r}"
    )


@then("the validator exits non-zero")
def _validator_exits_nonzero(
    validator_result: subprocess.CompletedProcess[str],
) -> None:
    assert validator_result.returncode != 0, (
        f"Validator unexpectedly exited 0; stdout={validator_result.stdout!r}"
    )


@then(
    "Marco sees the malformed heading reported with its line number "
    "and the failing rule"
)
def _malformed_heading_reported(
    validator_result: subprocess.CompletedProcess[str], ctx: dict[str, Any]
) -> None:
    """Driven port assertion: stdout names the offending line + rule."""
    stdout = validator_result.stdout
    heading = ctx["malformed_heading"]
    assert "malformed headings" in stdout, (
        f"Expected failure banner in stdout, got: {stdout!r}"
    )
    assert heading in stdout, (
        f"Expected offending heading {heading!r} in stdout, got: {stdout!r}"
    )
    assert "line " in stdout, (
        f"Expected explicit line-number reference in stdout, got: {stdout!r}"
    )
    assert "missing schema prefix" in stdout, (
        f"Expected failing-rule reason in stdout, got: {stdout!r}"
    )


# ---------------------------------------------------------------------------
# Scenario: Non-interactive install defaults to lean density (US-3)
# ---------------------------------------------------------------------------


@given(
    "a continuous-integration host with no terminal and no existing "
    "global configuration"
)
def _ci_host_no_config(global_config_path: Path) -> None:
    """Pre-condition: a CI host starts with no global-config.json on disk."""
    assert not global_config_path.exists(), (
        f"Expected absent global-config.json, found one at {global_config_path}"
    )


@when(
    "the pipeline runs install in non-interactive mode",
    target_fixture="install_result",
)
def _install_non_interactive(
    marco_home: Path, ctx: dict[str, Any]
) -> subprocess.CompletedProcess[str]:
    """Drive install with a piped (non-TTY) stdin -> the non_interactive branch.

    The install CLI promotes a non-TTY stdin to non_interactive mode
    (`cli.py` — `not sys.stdin.isatty()`), so a piped empty stdin reproduces a
    CI host: `handle_install_density_prompt` writes the silent lean default.
    """
    result = _run_install_with_density_only(marco_home, stdin_text="")
    ctx["install_stdout"] = result.stdout
    ctx["install_returncode"] = result.returncode
    return result


@then("the install completes without prompting")
def _install_completes_without_prompting(
    install_result: subprocess.CompletedProcess[str],
) -> None:
    """Driven assertion: exit 0 and the interactive prompt string never appears."""
    assert install_result.returncode == 0, (
        f"Install failed: stdout={install_result.stdout!r} "
        f"stderr={install_result.stderr!r}"
    )
    assert "lean (experienced)" not in install_result.stdout, (
        f"Non-interactive install unexpectedly prompted: "
        f"stdout={install_result.stdout!r}"
    )


# ---------------------------------------------------------------------------
# Scenario: Upgrade path writes lean default silently with one notice (US-3)
# ---------------------------------------------------------------------------


@given("an existing global configuration without a documentation block")
def _existing_config_without_documentation(global_config_path: Path) -> None:
    """Pre-condition: a config file that exists but carries no documentation key."""
    global_config_path.parent.mkdir(parents=True, exist_ok=True)
    global_config_path.write_text(
        json.dumps({"attribution": {"enabled": False}}, indent=2), encoding="utf-8"
    )


@when("Marco runs install interactively", target_fixture="install_result")
def _install_interactive_over_existing(
    marco_home: Path, ctx: dict[str, Any]
) -> subprocess.CompletedProcess[str]:
    """Run install over an existing doc-less config -> the upgrade-silent branch.

    Case 2 of `handle_install_density_prompt` (config exists, no documentation
    block) fires before the interactivity check, so the lean default is written
    silently regardless of the (piped) stdin.
    """
    result = _run_install_with_density_only(marco_home, stdin_text="")
    ctx["install_stdout"] = result.stdout
    ctx["install_returncode"] = result.returncode
    return result


@then("Marco does not see an interactive density prompt")
def _no_interactive_density_prompt(
    install_result: subprocess.CompletedProcess[str],
) -> None:
    assert "lean (experienced)" not in install_result.stdout, (
        f"Upgrade path unexpectedly prompted: stdout={install_result.stdout!r}"
    )


@then(
    "Marco sees exactly one informational line referencing the global "
    "configuration path"
)
def _one_info_line_referencing_config(
    install_result: subprocess.CompletedProcess[str],
) -> None:
    """Driven assertion: the upgrade notice names the config file exactly once."""
    info_lines = [
        line
        for line in install_result.stdout.splitlines()
        if "global-config.json" in line
    ]
    assert len(info_lines) == 1, (
        f"Expected exactly one info line referencing global-config.json, got "
        f"{info_lines!r} from stdout={install_result.stdout!r}"
    )


# ---------------------------------------------------------------------------
# Scenario: Doctor falls back to lean default, surfaces no-config provenance (US-6)
# ---------------------------------------------------------------------------


@when("Marco runs doctor", target_fixture="doctor_result")
def _marco_runs_doctor_plain(
    marco_home: Path, ctx: dict[str, Any]
) -> subprocess.CompletedProcess[str]:
    """Driving port: invoke the real `nwave-ai doctor` subprocess (no-config)."""
    result = _run_doctor(marco_home)
    ctx["doctor_stdout"] = result.stdout
    ctx["doctor_returncode"] = result.returncode
    return result


@then(parsers.parse('Marco sees the line "{expected_line}"'))
def _marco_sees_line(
    expected_line: str, doctor_result: subprocess.CompletedProcess[str]
) -> None:
    """Driven assertion: the doctor density line appears verbatim in stdout."""
    assert expected_line in doctor_result.stdout, (
        f"Expected line {expected_line!r} not in doctor stdout.\n"
        f"stdout={doctor_result.stdout!r}\nstderr={doctor_result.stderr!r}"
    )
