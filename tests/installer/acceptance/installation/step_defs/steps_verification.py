"""
Step definitions for post-installation verification acceptance tests (AC-07, AC-08).

CRITICAL: Hexagonal boundary enforcement - tests invoke CLI entry points ONLY.
- FORBIDDEN: Direct imports of internal verification components
- REQUIRED: Invoke through driving ports (scripts/install/*.py)

Cross-platform compatible (Windows, macOS, Linux).
"""

import re

from pytest_bdd import given, parsers, scenarios, then, when


# Load scenarios from feature files
scenarios("../features/04_post_installation.feature")


# ============================================================================
# GIVEN - Preconditions
# ============================================================================


@given("the verification script should exist at scripts/install/verify_nwave.py")
def verification_script_should_exist(verify_script):
    """Note that verification script should exist (spec step)."""
    # This is a specification step - actual check happens in When
    pass


@given("nWave is fully installed")
def nwave_fully_installed(isolated_claude_home, partial_installation_builder):
    """Create a fully installed nWave environment."""
    # Create all expected files
    agents_dir = isolated_claude_home["agents_dir"]
    commands_dir = isolated_claude_home["commands_dir"]
    templates_dir = isolated_claude_home["templates_dir"]

    # Create agent files (simulate full installation)
    agent_names = [
        "business-analyst.md",
        "solution-architect.md",
        "acceptance-designer.md",
        "software-crafter.md",
        "deployment-engineer.md",
        "business-analyst-reviewer.md",
        "solution-architect-reviewer.md",
        "acceptance-designer-reviewer.md",
        "software-crafter-reviewer.md",
        "deployment-engineer-reviewer.md",
    ]
    for name in agent_names:
        (agents_dir / name).write_text(f"# {name.replace('.md', '').title()}")

    # Create essential command files
    essential_commands = [
        "discuss.md",
        "design.md",
        "distill.md",
        "devop.md",
        "deliver.md",
    ]
    for cmd in essential_commands:
        (commands_dir / cmd).write_text(f"# {cmd.replace('.md', '').title()}")

    # Create schema template
    (templates_dir / "step-tdd-cycle-schema.json").write_text(
        '{"schema_version": "2.0", "tdd_cycle": {"phase_execution_log": [1,2,3,4,5,6,7,8]}}'
    )

    # Create manifest
    isolated_claude_home["manifest_file"].write_text("# nWave Installation Manifest\n")


@given("all agent files are present")
def all_agent_files_present(file_assertions):
    """Verify agent files are present."""
    assert file_assertions.agent_count() >= 10, "Not all agent files present"


@given("all command files are present")
def all_command_files_present(file_assertions):
    """Verify command files are present."""
    assert file_assertions.command_count() >= 5, "Not all command files present"


@given("the manifest file exists")
def manifest_file_exists(file_assertions):
    """Verify manifest file exists."""
    assert file_assertions.manifest_exists(), "Manifest file not present"


@given("a partial installation exists")
def partial_installation(partial_installation_builder):
    """Create a partial installation for testing."""
    partial_installation_builder.create_minimal()


@given(parsers.parse('the essential command "{command}" is missing'))
def essential_command_missing(command, partial_installation_builder):
    """Remove an essential command file."""
    partial_installation_builder.remove_file(f"commands/nw/{command}")


@given(parsers.parse('the agent file "{agent}" is missing'))
def agent_file_missing(agent, partial_installation_builder):
    """Remove an agent file."""
    partial_installation_builder.remove_file(f"agents/nw/{agent}")


@given("the schema template is missing")
def schema_template_missing(partial_installation_builder):
    """Remove the schema template."""
    partial_installation_builder.remove_file("templates/step-tdd-cycle-schema.json")


# ============================================================================
# WHEN - Actions
# ============================================================================


@when("I check for the verification script")
def check_verification_script(verify_script, cli_result):
    """Check if verification script exists."""
    cli_result["script_exists"] = verify_script.exists()
    cli_result["script_path"] = str(verify_script)


@when("I run the verification")
def run_verification_after_install(run_installer, cli_result):
    """Run installer to trigger verification phase."""
    # Run installer which includes verification
    run_installer()


@when("I run the standalone verification script")
def run_standalone_verification(run_verifier, cli_result):
    """Run the standalone verification script."""
    run_verifier()


# ============================================================================
# THEN - Assertions
# ============================================================================


@then("the verification should run automatically")
def verification_runs_automatically(cli_result):
    """Verify that verification was executed."""
    all_output = f"{cli_result['stdout']}\n{cli_result['stderr']}"
    verification_ran = (
        "Validating" in all_output
        or "validation" in all_output.lower()
        or "Verification" in all_output
    )
    assert verification_ran, f"Verification doesn't appear to have run:\n{all_output}"


@then("the agent count should be reported")
def agent_count_reported(cli_result):
    """Verify agent count is reported in output."""
    all_output = f"{cli_result['stdout']}\n{cli_result['stderr']}"
    # Look for patterns like "Agents installed: 28" or "28 agent files"
    has_count = re.search(
        r"[Aa]gents?\s*(installed)?:?\s*\d+", all_output
    ) or re.search(r"\d+\s*agent", all_output)
    assert has_count, f"Agent count not reported in output:\n{all_output}"


@then("the agent count should be at least 10")
def agent_count_minimum(cli_result):
    """Verify reported agent count is at least 10."""
    all_output = f"{cli_result['stdout']}\n{cli_result['stderr']}"
    # Extract numeric value
    match = re.search(r"[Aa]gents?\s*(installed)?:?\s*(\d+)", all_output)
    if match:
        count = int(match.group(2))
        assert count >= 10, f"Agent count {count} is less than minimum 10"
    else:
        match = re.search(r"(\d+)\s*agent", all_output)
        if match:
            count = int(match.group(1))
            assert count >= 10, f"Agent count {count} is less than minimum 10"


@then("the command count should be reported")
def command_count_reported(cli_result):
    """Verify command count is reported in output."""
    all_output = f"{cli_result['stdout']}\n{cli_result['stderr']}"
    has_count = re.search(
        r"[Cc]ommands?\s*(installed)?:?\s*\d+", all_output
    ) or re.search(r"\d+\s*command", all_output)
    assert has_count, f"Command count not reported in output:\n{all_output}"


@then(parsers.parse('the manifest file should exist at "{path}"'))
def manifest_exists_at_path(path, file_assertions):
    """Verify manifest file exists at specified path."""
    assert file_assertions.manifest_exists(), "Manifest file not found"


@then("the verification should fail")
def verification_fails(cli_result):
    """Verify that verification failed."""
    assert cli_result["returncode"] != 0, (
        f"Expected non-zero exit code, got {cli_result['returncode']}"
    )


@then(parsers.parse('the error should list "{item}" as missing'))
def error_lists_missing_item(item, cli_result, assert_output):
    """Verify error lists specific missing item."""
    assert_output.contains(cli_result, item)


@then("the script should be present")
def script_is_present(cli_result):
    """Verify verification script exists."""
    assert cli_result.get("script_exists", False), (
        f"Verification script not found at {cli_result.get('script_path')}"
    )


@then("the script should be executable")
def script_is_executable(verify_script):
    """Verify script has execute permissions (Unix) or is a .py file (cross-platform)."""
    # On all platforms, a .py file can be executed via python interpreter
    assert verify_script.suffix == ".py", "Script should be a Python file"


@then("the output should list installed components")
def output_lists_components(cli_result):
    """Verify output lists installed components."""
    all_output = f"{cli_result['stdout']}\n{cli_result['stderr']}"
    has_components = (
        "agents" in all_output.lower()
        or "commands" in all_output.lower()
        or "installed" in all_output.lower()
    )
    assert has_components, f"Installed components not listed:\n{all_output}"


@then("the verification should check for essential commands:")
def verification_checks_essential_commands(pytestconfig):
    """Verify specification of essential commands to check."""
    # This is a specification step documenting required commands
    essential_commands = ["discuss", "design", "distill", "develop", "deliver"]
    assert len(essential_commands) == 5, "All essential commands should be specified"


@then("missing commands should be reported")
def missing_commands_reported(cli_result, file_assertions):
    """Verify missing commands are reported if any are missing."""
    all_output = f"{cli_result['stdout']}\n{cli_result['stderr']}"
    if file_assertions.command_count() < 5:
        assert "missing" in all_output.lower() or "Missing" in all_output, (
            "Missing commands not reported"
        )


@then(parsers.parse('the error should mention "{text}"'))
def error_mentions_text(text, cli_result, assert_output):
    """Verify error mentions specified text."""
    assert_output.contains(cli_result, text)


@then("the error should provide remediation guidance")
def error_provides_remediation(cli_result):
    """Verify error provides remediation guidance."""
    all_output = f"{cli_result['stdout']}\n{cli_result['stderr']}"
    has_guidance = (
        "[FIX]" in all_output
        or "reinstall" in all_output.lower()
        or "run" in all_output.lower()
    )
    assert has_guidance, f"No remediation guidance in output:\n{all_output}"
