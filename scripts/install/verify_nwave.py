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
- Codex DES hook, agents (181 skills, 36 agents) [--platform codex]
- Cursor DES hook [--platform cursor]
- Devin skills (181 skills) [--platform devin]

The script supports multiple output modes:
- Terminal: Human-readable colored output (default)
- JSON: Machine-parseable output for Claude Code (--json flag)
- Verbose: Detailed information including counts (--verbose flag)

Exit codes:
- 0: Verification successful, all checks passed; retired, in --retire-legacy-copy mode
- 1: Verification failed, missing files or manifest; legacy copy mismatch
- 2: Usage error, including a missing --against
- 3: Legacy copy refused, nothing compared or deleted

Usage:
    # Default terminal output (Claude Code only)
    python verify_nwave.py

    # Verify all supported platforms
    python verify_nwave.py --platform all

    # Verify a specific platform
    python verify_nwave.py --platform codex
    python verify_nwave.py --platform cursor
    python verify_nwave.py --platform devin

    # JSON output for automated tools
    python verify_nwave.py --json

    # Verbose terminal output
    python verify_nwave.py --verbose

    # Combined flags
    python verify_nwave.py --json --verbose
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


try:
    from scripts.install.context_detector import is_claude_code_context
    from scripts.install.install_nwave import print_logo
    from scripts.install.install_utils import PathUtils
    from scripts.install.installation_verifier import (
        InstallationVerifier,
        VerificationResult,
    )
    from scripts.install.plugins.base import InstallContext, PluginResult
    from scripts.install.plugins.codex_agents_plugin import CodexAgentsPlugin
    from scripts.install.plugins.codex_skills_plugin import CodexSkillsPlugin
    from scripts.install.plugins.devin_skills_plugin import DevinSkillsPlugin
    from scripts.install.plugins.nwave_hooks_plugin import HooksPlugin
    from scripts.install.rich_console import RichLogger
except ImportError:
    from context_detector import is_claude_code_context
    from install_nwave import print_logo
    from install_utils import PathUtils
    from installation_verifier import (
        InstallationVerifier,
        VerificationResult,
    )
    from plugins.base import InstallContext, PluginResult
    from plugins.codex_agents_plugin import CodexAgentsPlugin
    from plugins.codex_skills_plugin import CodexSkillsPlugin
    from plugins.devin_skills_plugin import DevinSkillsPlugin
    from plugins.nwave_hooks_plugin import HooksPlugin
    from rich_console import RichLogger


_NATIVE_PLATFORMS = ("codex", "cursor", "devin")


def _project_root() -> Path:
    """Return the nWave-experimental repo root (parent of scripts/install/)."""
    return Path(__file__).resolve().parent.parent.parent


def _make_verify_context(
    claude_dir: Path, platform: str, logger: object
) -> InstallContext:
    """Build a minimal InstallContext sufficient for plugin verify() calls."""
    repo_root = _project_root()
    # Mirror NWaveInstaller: prefer nWave/ (dev checkout), fall back to dist/
    framework_source = repo_root / "nWave"
    if not framework_source.exists():
        framework_source = repo_root / "dist"
    return InstallContext(
        claude_dir=claude_dir,
        scripts_dir=repo_root / "scripts",
        templates_dir=claude_dir / "templates",
        logger=logger,
        project_root=repo_root,
        framework_source=framework_source,
        target_platforms={platform},
    )


def verify_native_platform(
    platform: str,
    claude_dir: Path,
    logger: object,
) -> list[PluginResult]:
    """Run verify() for each plugin relevant to a native platform.

    Returns a list of PluginResult — one per plugin checked.
    """
    ctx = _make_verify_context(claude_dir, platform, logger)
    results: list[PluginResult] = []
    if platform == "codex":
        results.append(CodexSkillsPlugin().verify(ctx))
        results.append(CodexAgentsPlugin().verify(ctx))
        # The kept hook registrations replace the retired plugin checks:
        # nwave-hooks covers codex and cursor host files.
        results.append(HooksPlugin().verify(ctx))
    elif platform == "cursor":
        results.append(HooksPlugin().verify(ctx))
    elif platform == "devin":
        results.append(DevinSkillsPlugin().verify(ctx))
    return results


def format_native_results(
    platform: str, results: list[PluginResult], verbose: bool = False
) -> str:
    """Format native-platform plugin verify results for terminal output."""
    lines = [f"\n  Platform: {platform}"]
    all_ok = all(r.success for r in results)
    for r in results:
        icon = "✅" if r.success else "❌"
        lines.append(f"    {icon} {r.plugin_name}: {r.message}")
        if not r.success and r.errors:
            for e in r.errors:
                lines.append(f"        ⚠️  {e}")
    if all_ok:
        lines.append(f"  ✅ {platform} verification passed")
    else:
        lines.append(f"  ❌ {platform} verification failed")
    return "\n".join(lines)


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
    parser.add_argument(
        "--platform",
        choices=["claude-code", "codex", "cursor", "devin", "all"],
        default="claude-code",
        help=(
            "Platform to verify (default: claude-code). "
            "Use 'all' to verify every supported platform."
        ),
    )
    parser.add_argument(
        "--verify-legacy-copy",
        metavar="COPY",
        help="Compare a held legacy Codex dev copy with --against DECLARED; read-only.",
    )
    parser.add_argument(
        "--retire-legacy-copy",
        metavar="COPY",
        help="Compare the copy with --against DECLARED and delete it only when it passes.",
    )
    parser.add_argument(
        "--against",
        metavar="DECLARED",
        help="Folder holding the migrated assets, for the legacy copy modes.",
    )
    parsed = parser.parse_args(args)
    legacy_modes = [
        flag
        for flag in (parsed.verify_legacy_copy, parsed.retire_legacy_copy)
        if flag is not None
    ]
    if len(legacy_modes) > 1:
        parser.error(
            "--verify-legacy-copy and --retire-legacy-copy are alternatives; give one"
        )
    if legacy_modes and parsed.against is None:
        parser.error(
            "--against DECLARED is required with --verify-legacy-copy and --retire-legacy-copy"
        )
    if parsed.against is not None and not legacy_modes:
        parser.error(
            "--against DECLARED applies only with --verify-legacy-copy or --retire-legacy-copy"
        )
    return parsed


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

    lines.extend(_preserved_not_managed_lines(result.unaccounted_files))

    return "\n".join(lines)


def _preserved_not_managed_lines(unaccounted_files: dict[str, list[str]]) -> list[str]:
    """Informational listing of files preserved on disk, not managed by nWave.

    Provenance is unprovable (a user-created asset and a pre-manifest orphan
    are indistinguishable by record membership), so the listing is purely
    informational — never a deletion suggestion. Empty families render nothing.
    """
    families = {
        family: names for family, names in sorted(unaccounted_files.items()) if names
    }
    if not families:
        return []
    lines = ["", "    📄 Preserved, not managed by nWave:"]
    lines.extend(
        f"      {family}: {', '.join(names)}" for family, names in families.items()
    )
    return lines


def json_payload(result: VerificationResult, verbose: bool = False) -> dict:
    """Build the Claude Code verification result as a JSON-ready mapping.

    Args:
        result: VerificationResult from verification run.
        verbose: If True, include all fields. If False, minimal output.

    Returns:
        The mapping that ``format_json_output`` serializes.
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
        # Always present, even when empty: an absent listing is "no orphan
        # visibility", not a clean bill (informational, never a failure).
        "unaccounted_files": result.unaccounted_files,
    }

    if result.error_code:
        output["error_code"] = result.error_code

    if not result.success:
        output["remediation"] = "Re-run the nWave installer to restore missing files."

    if verbose:
        output["message"] = result.message

    return output


def format_json_output(result: VerificationResult, verbose: bool = False) -> str:
    """Format verification result as JSON."""
    return json.dumps(json_payload(result, verbose), indent=2)


# Legacy Codex dev copy comparison (U6b mechanism B). The comparison only reads. Retire
# deletes the copy itself, and only after a Passed outcome from the same invocation.
LEGACY_COPY_NAME = "legacy-codex-dev"
LEGACY_COPY_ENTRIES = frozenset({"skills", "agents", "receipt.json"})
LEGACY_COPY_SNAPSHOT_PREFIXES = ("nwave-", "legacy-hold-nwave-")
EXIT_PASSED = 0
EXIT_FAILED = 1
EXIT_REFUSED = 3


@dataclass(frozen=True)
class LegacyCopyOutcome:
    """The comparison of one legacy copy with one declared folder."""

    status: str
    assets: int = 0
    failed_assets: int = 0
    mismatches: tuple[str, ...] = ()
    reason: str = ""


class _Refused(Exception):
    """The copy or the declared folder admits no verdict; nothing is compared or deleted."""


def _check_copy_shape(copy: Path) -> None:
    """Refuse anything but a legacy-codex-dev directory in a snapshot under .nwave/backups."""
    path = copy.absolute()
    snapshot = path.parent
    if (
        path.name != LEGACY_COPY_NAME
        or not snapshot.name.startswith(LEGACY_COPY_SNAPSHOT_PREFIXES)
        or snapshot.parent.name != "backups"
        or snapshot.parent.parent.name != ".nwave"
    ):
        raise _Refused("the path is not a legacy-codex-dev copy inside .nwave/backups")
    if copy.is_symlink() or not copy.is_dir():
        raise _Refused("the legacy copy is not a directory")


def _refuse_if_inside(path: Path, resolved_copy: Path) -> None:
    """Refuse a path that resolves to the copy or into it, following symbolic links."""
    resolved = path.resolve()
    if resolved == resolved_copy or resolved_copy in resolved.parents:
        raise _Refused(f"{path} resolves into the legacy copy")


def _refuse_special_entries(root: Path) -> None:
    """Refuse a symbolic link or a non-regular file anywhere below a copy asset."""
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        here = Path(dirpath)
        for name in (*dirnames, *filenames):
            if (here / name).is_symlink():
                raise _Refused(
                    f"{here / name} is a symbolic link inside the legacy copy"
                )
        for name in filenames:
            if not (here / name).is_file():
                raise _Refused(f"{here / name} is not a regular file")


def _copy_assets(copy: Path) -> list[tuple[str, Path]]:
    """List the copy's assets, skills/<name> directories and agents/<name> files, or refuse."""
    entries = {entry.name: entry for entry in copy.iterdir()}
    for name, entry in sorted(entries.items()):
        if name not in LEGACY_COPY_ENTRIES:
            raise _Refused(f"the legacy copy holds the unexpected entry {name}")
        if entry.is_symlink():
            raise _Refused(f"{name} is a symbolic link inside the legacy copy")
    receipt = entries.get("receipt.json")
    if receipt is not None and not receipt.is_file():
        raise _Refused("receipt.json is not a regular file")
    assets: list[tuple[str, Path]] = []
    skills = entries.get("skills")
    if skills is not None:
        if not skills.is_dir():
            raise _Refused("skills is not a directory inside the legacy copy")
        for child in sorted(skills.iterdir()):
            if not child.is_dir() or child.is_symlink():
                raise _Refused(f"skills/{child.name} is not a directory")
            _refuse_special_entries(child)
            assets.append((child.name, child))
    agents = entries.get("agents")
    if agents is not None:
        if not agents.is_dir():
            raise _Refused("agents is not a directory inside the legacy copy")
        for child in sorted(agents.iterdir()):
            if not child.is_file() or child.is_symlink():
                raise _Refused(f"agents/{child.name} is not a regular file")
            assets.append((child.name, child))
    return assets


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _compare_file(
    copy_file: Path, dest: Path, label: str, resolved_copy: Path
) -> str | None:
    """One mismatch line for a copy file against its declared counterpart, or None."""
    _refuse_if_inside(dest, resolved_copy)
    if not dest.exists():
        return f"{label} missing in DECLARED"
    if dest.is_dir():
        return f"{label} kind mismatch in DECLARED (a folder where a file is expected)"
    if _digest(copy_file) != _digest(dest):
        return f"{label} digest differs in DECLARED"
    return None


def _asset_mismatches(
    asset_name: str, copy_asset: Path, declared: Path, resolved_copy: Path
) -> list[str]:
    """Mismatches of one asset against DECLARED/<asset_name>; a link into the copy refuses."""
    target = declared / asset_name
    label = f"{copy_asset.parent.name}/{asset_name}"
    _refuse_if_inside(target, resolved_copy)
    if not target.exists():
        return [f"{label} missing in DECLARED"]
    if not copy_asset.is_dir():
        problem = _compare_file(copy_asset, target, label, resolved_copy)
        return [problem] if problem else []
    if not target.is_dir():
        return [
            f"{label} kind mismatch in DECLARED (a file where a folder is expected)"
        ]
    problems: list[str] = []
    for copy_file in sorted(copy_asset.rglob("*")):
        if copy_file.is_file():
            relative = copy_file.relative_to(copy_asset).as_posix()
            problem = _compare_file(
                copy_file, target / relative, f"{label}/{relative}", resolved_copy
            )
            if problem:
                problems.append(problem)
    return problems


def compare_legacy_copy(copy: Path, declared: Path) -> LegacyCopyOutcome:
    """Compare a legacy copy with DECLARED. Reads only; the caller decides any deletion."""
    try:
        _check_copy_shape(copy)
        resolved_copy = copy.resolve()
        if declared.resolve() == resolved_copy:
            raise _Refused("--against names the legacy copy itself")
        assets = _copy_assets(copy)
        if not assets:
            raise _Refused("the legacy copy holds no assets to compare")
        per_asset = [
            _asset_mismatches(name, path, declared, resolved_copy)
            for name, path in assets
        ]
    except _Refused as refusal:
        return LegacyCopyOutcome("refused", reason=str(refusal))
    mismatches = tuple(problem for problems in per_asset for problem in problems)
    failed = sum(1 for problems in per_asset if problems)
    if mismatches:
        return LegacyCopyOutcome("failed", len(assets), failed, mismatches)
    return LegacyCopyOutcome("passed", len(assets))


def run_legacy_copy_mode(copy_arg: str, against: str, *, retire: bool) -> int:
    """Run the verify or retire mode for one legacy copy and return its exit code."""
    copy = Path(copy_arg)
    declared = Path(against)
    outcome = compare_legacy_copy(copy, declared)
    if outcome.status == "passed":
        if not retire:
            print(
                f"VERIFIED COPY: {outcome.assets} assets matched in {declared}; "
                "nothing was deleted."
            )
            return EXIT_PASSED
        try:
            shutil.rmtree(copy)
        except OSError as error:
            print(
                f"NOT RETIRED COPY: the legacy copy could not be deleted: {error}.",
                file=sys.stderr,
            )
            return EXIT_FAILED
        print(
            f"RETIRED COPY: {outcome.assets} assets matched in {declared}; "
            "the legacy copy was deleted."
        )
        return EXIT_PASSED
    prefix = "NOT RETIRED COPY" if retire else "NOT VERIFIED COPY"
    if outcome.status == "failed":
        detail = "; ".join(outcome.mismatches)
        print(
            f"{prefix}: {outcome.failed_assets} of {outcome.assets} assets did not match "
            f"in {declared}: {detail}. Nothing was deleted.",
            file=sys.stderr,
        )
        return EXIT_FAILED
    print(f"{prefix}: {outcome.reason}. Nothing was deleted.", file=sys.stderr)
    return EXIT_REFUSED


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
    if parsed_args.verify_legacy_copy is not None:
        return run_legacy_copy_mode(
            parsed_args.verify_legacy_copy, parsed_args.against, retire=False
        )
    if parsed_args.retire_legacy_copy is not None:
        return run_legacy_copy_mode(
            parsed_args.retire_legacy_copy, parsed_args.against, retire=True
        )

    # Determine output mode early to configure logger appropriately
    use_json = parsed_args.json or is_claude_code_context()

    # Initialize logging to shared installation log file
    # In JSON mode, suppress console output to avoid polluting JSON output
    config_dir = claude_config_dir or PathUtils.get_claude_config_dir()
    log_file = config_dir / "nwave-install.log"
    logger = RichLogger(log_file=log_file, silent=use_json)

    if not use_json:
        print_logo(logger)
        logger.info("")
        logger.info("  🔍 nWave verification started")

    platform = getattr(parsed_args, "platform", "claude-code")
    native_platforms = (
        list(_NATIVE_PLATFORMS)
        if platform == "all"
        else [platform]
        if platform in _NATIVE_PLATFORMS
        else []
    )
    run_claude_code = platform in ("claude-code", "all")

    overall_success = True
    document: dict = {}

    # Claude Code verification
    if run_claude_code:
        result = run_verification(claude_config_dir=claude_config_dir)
        if result.success:
            logger.info(
                f"  ✅ Verification passed: {result.agent_file_count} agents, "
                f"{result.command_file_count} commands, "
                f"{result.skill_file_count} skills, DES installed"
            )
        else:
            logger.error(f"  ❌ Verification failed: {result.message}")
            if result.missing_essential_files:
                logger.error(
                    f"    ⚠️ Missing: {', '.join(result.missing_essential_files)}"
                )
            overall_success = False

        if use_json:
            document.update(json_payload(result, verbose=parsed_args.verbose))
        else:
            print(format_terminal_output(result, verbose=parsed_args.verbose))

    # Native platform verification (Codex, Cursor, Devin)
    native_results: dict[str, list[PluginResult]] = {}
    for p in native_platforms:
        p_results = verify_native_platform(p, config_dir, logger)
        native_results[p] = p_results
        if not all(r.success for r in p_results):
            overall_success = False
        if not use_json:
            print(format_native_results(p, p_results, verbose=parsed_args.verbose))

    if use_json and native_results:
        document["platforms"] = {
            p: {
                "success": all(r.success for r in rs),
                "checks": [
                    {
                        "plugin": r.plugin_name,
                        "success": r.success,
                        "message": r.message,
                        "errors": r.errors,
                    }
                    for r in rs
                ],
            }
            for p, rs in native_results.items()
        }
    if use_json:
        print(json.dumps(document, indent=2))

    return 0 if overall_success else 1


if __name__ == "__main__":
    sys.exit(main())
