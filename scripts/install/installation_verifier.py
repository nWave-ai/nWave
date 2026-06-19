"""Installation Verifier for nWave Framework.

This module provides post-installation verification to ensure all expected
files are present after the build process completes. It validates:
- Agent file counts in ~/.claude/agents/
- Essential command-skills in ~/.claude/skills/nw-{name}/
- Manifest existence at ~/.claude/nwave-manifest.txt
- Skills directory presence and file counts
- DES module presence (lib/python/des/)

Returns VERIFY_FAILED error code when verification fails.

Usage:
    from scripts.install.installation_verifier import InstallationVerifier

    verifier = InstallationVerifier()
    result = verifier.run_verification()
    if not result.success:
        print(f"Verification failed: {result.error_code}")
"""

from dataclasses import dataclass, field
from pathlib import Path

from scripts.shared.skill_distribution import (
    SCRIPTS_FAMILY_KEY,
    SKILLS_FAMILY_KEY,
    TEMPLATES_FAMILY_KEY,
    read_family_record,
    read_manifest,
    unaccounted_names,
)


try:
    from scripts.install.error_codes import VERIFY_FAILED
    from scripts.install.install_utils import PathUtils
except ImportError:
    from error_codes import VERIFY_FAILED
    from install_utils import PathUtils


@dataclass
class VerificationResult:
    """Result of installation verification.

    Attributes:
        success: True if verification passed, False otherwise.
        agent_file_count: Number of agent .md files found.
        command_file_count: Number of command-skill directories found.
        manifest_exists: True if nwave-manifest.txt exists.
        missing_essential_files: List of missing essential command-skill names.
        skill_file_count: Number of skill .md files found.
        skill_group_count: Number of skill group directories found.
        des_installed: True if DES module directory exists with files.
        unaccounted_files: Per manifest-bearing family directory, names on
            disk that no family record tracks — informational ("preserved,
            not managed by nWave"), never a verification failure. Always
            present, even when empty.
        error_code: VERIFY_FAILED if verification failed, None otherwise.
        message: Human-readable verification result message.
    """

    success: bool
    agent_file_count: int
    command_file_count: int
    manifest_exists: bool
    missing_essential_files: list[str]
    skill_file_count: int = 0
    skill_group_count: int = 0
    des_installed: bool = False
    unaccounted_files: dict[str, list[str]] = field(default_factory=dict)
    error_code: str | None = None
    message: str = ""


class InstallationVerifier:
    """Verifies post-installation file presence and completeness.

    This class provides verification methods to ensure the nWave framework
    installation completed successfully. It checks file counts, manifest
    existence, and essential command-skill presence.

    Attributes:
        claude_config_dir: Path to Claude config directory (~/.claude).
        agents_dir: Path to agents directory.
        skills_dir: Path to skills directory.
        manifest_path: Path to installation manifest file.
    """

    # Essential command-skills that must exist for a valid installation.
    # These are the core wave commands (migrated from commands/nw/ to skills/).
    ESSENTIAL_COMMAND_SKILLS: list[str] = [
        "nw-review",
        "nw-devops",
        "nw-discuss",
        "nw-design",
        "nw-distill",
        "nw-deliver",
    ]

    # The orphan report covers the manifest-bearing family directories:
    # (target directory name, the family's canonical manifest key).
    REPORT_FAMILY_DIRS: tuple[tuple[str, str], ...] = (
        ("scripts", SCRIPTS_FAMILY_KEY),
        ("templates", TEMPLATES_FAMILY_KEY),
        ("skills", SKILLS_FAMILY_KEY),
    )

    def __init__(self, claude_config_dir: Path | None = None):
        """Initialize InstallationVerifier.

        Args:
            claude_config_dir: Optional path to Claude config directory.
                              Defaults to ~/.claude via PathUtils.
        """
        self.claude_config_dir = claude_config_dir or PathUtils.get_claude_config_dir()
        self.agents_dir = self.claude_config_dir / "agents" / "nw"
        self.skills_dir = self.claude_config_dir / "skills"
        self.des_dir = self.claude_config_dir / "lib" / "python" / "des"
        self.manifest_path = self.claude_config_dir / "nwave-manifest.txt"

    def verify_agent_files(self) -> int:
        """Count agent markdown files in the agents directory.

        Returns:
            Number of .md files found in ~/.claude/agents/nw/.
            Returns 0 if directory does not exist.
        """
        return PathUtils.count_files(self.agents_dir, "*.md")

    def verify_command_skills(self) -> int:
        """Count command-skill directories (user-invocable skills).

        Counts nw-* directories in ~/.claude/skills/ that contain
        a SKILL.md with ``user-invocable:`` in the frontmatter.

        Returns:
            Number of command-skill directories found.
        """
        if not self.skills_dir.exists():
            return 0
        count = 0
        for d in self.skills_dir.iterdir():
            if not d.is_dir() or not d.name.startswith("nw-"):
                continue
            skill_file = d / "SKILL.md"
            if not skill_file.exists():
                continue
            try:
                text = skill_file.read_text(encoding="utf-8")
            except OSError:
                continue
            if text.startswith("---") and "user-invocable:" in text.split("\n---\n")[0]:
                count += 1
        return count

    def verify_manifest(self) -> bool:
        """Check if the installation manifest file exists.

        Returns:
            True if nwave-manifest.txt exists, False otherwise.
        """
        return self.manifest_path.exists()

    def verify_essential_commands(self) -> list[str]:
        """Check for missing essential command-skill directories.

        Looks for nw-{name}/SKILL.md in the skills directory.

        Returns:
            List of missing essential command-skill names.
            Empty list if all essential commands are present.
        """
        missing = []
        for skill_name in self.ESSENTIAL_COMMAND_SKILLS:
            skill_path = self.skills_dir / skill_name / "SKILL.md"
            if not skill_path.exists():
                missing.append(skill_name)
        return missing

    def verify_skills(self) -> tuple[int, int]:
        """Verify skills installation.

        Supports both new flat layout (skills/nw-{name}/SKILL.md) and
        old hierarchical layout (skills/nw/{agent}/*.md).

        Returns:
            Tuple of (skill_file_count, skill_group_count).
            Returns (0, 0) if skills directory does not exist.
        """
        if not self.skills_dir.exists():
            return 0, 0
        # New flat layout: nw-*/SKILL.md directories
        nw_dirs = [
            d
            for d in self.skills_dir.iterdir()
            if d.is_dir() and d.name.startswith("nw-")
        ]
        if nw_dirs:
            skill_files = [d / "SKILL.md" for d in nw_dirs if (d / "SKILL.md").exists()]
            return len(skill_files), len(nw_dirs)
        # Old layout fallback: nw/{agent}/*.md
        old_dir = self.skills_dir / "nw"
        if old_dir.exists():
            skill_files = list(old_dir.rglob("*.md"))
            skill_groups = [d for d in old_dir.iterdir() if d.is_dir()]
            return len(skill_files), len(skill_groups)
        return 0, 0

    def verify_des(self) -> bool:
        """Verify DES module installation.

        Returns:
            True if DES directory exists and contains Python files.
        """
        if not self.des_dir.exists():
            return False
        return len(list(self.des_dir.rglob("*.py"))) > 0

    def verify_unaccounted_files(self) -> dict[str, list[str]]:
        """Per manifest-bearing family directory, names no record tracks.

        Expected set per directory = union of the family records in that
        directory's shared ``.nwave-manifest.json`` (the manifest-based
        oracle). Directories without a manifest are out of report scope.
        Informational only ("preserved, not managed by nWave") — read-only,
        never affects the verification verdict, deterministic across runs.
        """
        report: dict[str, list[str]] = {}
        for family, family_key in self.REPORT_FAMILY_DIRS:
            directory = self.claude_config_dir / family
            if read_manifest(directory) is None:
                continue
            accounted = read_family_record(directory, key=family_key).accounted
            report[family] = unaccounted_names(
                directory, accounted=accounted, expected=frozenset()
            )
        return report

    def run_verification(self) -> VerificationResult:
        """Run complete installation verification.

        Performs all verification checks and returns a comprehensive result.

        Returns:
            VerificationResult with all verification details.
            success=True only if all checks pass.
        """
        agent_count = self.verify_agent_files()
        command_count = self.verify_command_skills()
        manifest_exists = self.verify_manifest()
        missing_essential = self.verify_essential_commands()
        skill_file_count, skill_group_count = self.verify_skills()
        des_installed = self.verify_des()
        unaccounted_files = self.verify_unaccounted_files()

        # Determine overall success
        # Verification fails if:
        # - Essential command-skills are missing
        # - Manifest does not exist
        # - Skills are not installed
        # - DES module is not installed
        success = (
            len(missing_essential) == 0
            and manifest_exists
            and skill_file_count > 0
            and des_installed
        )

        # Build result message
        if success:
            message = (
                f"Verification completed successfully. "
                f"Found {agent_count} agents, {command_count} commands, "
                f"{skill_file_count} skills in {skill_group_count} groups, "
                f"DES module installed."
            )
            error_code = None
        else:
            issues = []
            if missing_essential:
                issues.append(
                    f"missing essential commands: {', '.join(missing_essential)}"
                )
            if not manifest_exists:
                issues.append("manifest file not found")
            if skill_file_count == 0:
                issues.append("no skills installed")
            if not des_installed:
                issues.append("DES module not installed")
            message = f"Verification failed: {'; '.join(issues)}."
            error_code = VERIFY_FAILED

        return VerificationResult(
            success=success,
            agent_file_count=agent_count,
            command_file_count=command_count,
            manifest_exists=manifest_exists,
            missing_essential_files=missing_essential,
            skill_file_count=skill_file_count,
            skill_group_count=skill_group_count,
            des_installed=des_installed,
            unaccounted_files=unaccounted_files,
            error_code=error_code,
            message=message,
        )
