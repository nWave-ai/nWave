#!/usr/bin/env python3
"""Standalone verification script for nWave Framework installation.

This script provides an independent way to verify nWave installation status
without running the full installer. It checks:
- Agent file counts in ~/.claude/agents/nw/
- Command file counts in ~/.claude/commands/nw/
- Manifest existence at ~/.claude/nwave-manifest.txt
- Essential command files (review.md, devops.md, etc.)
- Skills file counts in ~/.claude/skills/nw/
- DES module presence in ~/.claude/lib/python/des/

The script supports multiple output modes:
- Terminal: Human-readable colored output (default)
- JSON: Machine-parseable output for Claude Code (--json flag)
- Verbose: Detailed information including counts (--verbose flag)

Exit codes:
- 0: Verification successful, all checks passed
- 1: Verification failed, missing files or manifest

Usage:
    # Default terminal output
    python verify_nwave.py

    # JSON output for automated tools
    python verify_nwave.py --json

    # Verbose terminal output
    python verify_nwave.py --verbose

    # Combined flags
    python verify_nwave.py --json --verbose
"""

import argparse
import json
import sys
from pathlib import Path


try:
    from scripts.install.context_detector import is_claude_code_context
    from scripts.install.install_nwave import print_logo
    from scripts.install.install_utils import Logger, PathUtils
    from scripts.install.installation_verifier import (
        InstallationVerifier,
        VerificationResult,
    )
except ImportError:
    from context_detector import is_claude_code_context
    from install_nwave import print_logo
    from install_utils import Logger, PathUtils
    from installation_verifier import (
        InstallationVerifier,
        VerificationResult,
    )


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        args: List of argument strings. If None, uses sys.argv.

    Returns:
        Parsed arguments namespace with json and verbose flags.
    """
    parser = argparse.ArgumentParser(
        description="Verify nWave Framework installation status.",
        epilog="Exit code 0 indicates success, non-zero indicates verification failure.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format for machine parsing",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Include detailed verification information",
    )
    return parser.parse_args(args)


def run_verification(claude_config_dir: Path | None = None) -> VerificationResult:
    """Run installation verification.

    This function delegates to InstallationVerifier to perform the actual
    verification checks.

    Args:
        claude_config_dir: Optional path to Claude config directory.
                          Defaults to ~/.claude via InstallationVerifier.

    Returns:
        VerificationResult containing all verification details.
    """
    verifier = InstallationVerifier(claude_config_dir=claude_config_dir)
    return verifier.run_verification()


def format_terminal_output(
    result: VerificationResult,
    verbose: bool = False,
) -> str:
    """Format verification result for terminal output.

    Args:
        result: VerificationResult from verification run.
        verbose: If True, include detailed counts and file information.

    Returns:
        Formatted string for terminal display.
    """
    lines = []

    if result.success:
        lines.append("  ✅ nWave installation verification passed")
    else:
        lines.append("  ❌ nWave installation verification failed")

    if verbose or not result.success:
        lines.append("")
        lines.append(f"    📦 Agent files: {result.agent_file_count}")
        lines.append(f"    📦 Command files: {result.command_file_count}")
        lines.append(
            f"    📦 Skill files: {result.skill_file_count} in {result.skill_group_count} groups"
        )
        des_icon = "✅" if result.des_installed else "❌"
        lines.append(f"    🔒 DES module: {des_icon}")
        manifest_icon = "✅" if result.manifest_exists else "❌"
        lines.append(f"    📄 Manifest: {manifest_icon}")

        if result.missing_essential_files:
            lines.append("")
            lines.append("    ⚠️ Missing essential files:")
            for filename in result.missing_essential_files:
                lines.append(f"      ❌ {filename}")
            lines.append("")
            lines.append("    💡 Re-run the nWave installer to restore missing files")

        if not result.manifest_exists:
            lines.append("")
            lines.append("    💡 Re-run the nWave installer to create the manifest")

    return "\n".join(lines)


def format_json_output(result: VerificationResult, verbose: bool = False) -> str:
    """Format verification result as JSON.

    Args:
        result: VerificationResult from verification run.
        verbose: If True, include all fields. If False, minimal output.

    Returns:
        JSON string representation of the verification result.
    """
    output = {
        "success": result.success,
        "agent_file_count": result.agent_file_count,
        "command_file_count": result.command_file_count,
        "skill_file_count": result.skill_file_count,
        "skill_group_count": result.skill_group_count,
        "des_installed": result.des_installed,
        "manifest_exists": result.manifest_exists,
        "missing_essential_files": result.missing_essential_files,
    }

    if result.error_code:
        output["error_code"] = result.error_code

    if not result.success:
        output["remediation"] = "Re-run the nWave installer to restore missing files."

    if verbose:
        output["message"] = result.message

    return json.dumps(output, indent=2)


def main(
    args: list[str] | None = None,
    claude_config_dir: Path | None = None,
) -> int:
    """Main entry point for standalone verification.

    Parses arguments, runs verification, and outputs results in the
    appropriate format based on context and flags.

    Args:
        args: Command line arguments. If None, uses sys.argv.
        claude_config_dir: Optional path to Claude config directory for testing.

    Returns:
        Exit code: 0 for success, 1 for verification failure.
    """
    parsed_args = parse_args(args)

    # Determine output mode early to configure logger appropriately
    use_json = parsed_args.json or is_claude_code_context()

    # Initialize logging to shared installation log file
    # In JSON mode, suppress console output to avoid polluting JSON output
    config_dir = claude_config_dir or PathUtils.get_claude_config_dir()
    log_file = config_dir / "nwave-install.log"
    logger = Logger(log_file=log_file, silent=use_json)

    if not use_json:
        print_logo(logger)
        logger.info("")
        logger.info("  🔍 nWave verification started")

    # Run verification
    result = run_verification(claude_config_dir=claude_config_dir)

    # Log verification results
    if result.success:
        logger.info(
            f"  ✅ Verification passed: {result.agent_file_count} agents, "
            f"{result.command_file_count} commands, "
            f"{result.skill_file_count} skills, DES installed"
        )
    else:
        logger.error(f"  ❌ Verification failed: {result.message}")
        if result.missing_essential_files:
            logger.error(f"    ⚠️ Missing: {', '.join(result.missing_essential_files)}")

    # Format and print output
    if use_json:
        output = format_json_output(result, verbose=parsed_args.verbose)
    else:
        output = format_terminal_output(result, verbose=parsed_args.verbose)

    print(output)

    # Return appropriate exit code
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
