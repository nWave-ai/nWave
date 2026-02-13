"""Installation Verifier for nWave Framework.

This module provides post-installation verification to ensure all expected
files are present after the build process completes. It validates:
- Agent file counts in ~/.claude/agents/
- Command file counts in ~/.claude/commands/
- Manifest existence at ~/.claude/nwave-manifest.txt
- Essential command files (review.md, devops.md, etc.)
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

from dataclasses import dataclass
from pathlib import Path


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
        command_file_count: Number of command .md files found.
        manifest_exists: True if nwave-manifest.txt exists.
        missing_essential_files: List of missing essential command files.
        skill_file_count: Number of skill .md files found.
        skill_group_count: Number of skill group directories found.
        des_installed: True if DES module directory exists with files.
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
    error_code: str | None = None
    message: str = ""


class InstallationVerifier:
    """Verifies post-installation file presence and completeness.

    This class provides verification methods to ensure the nWave framework
    installation completed successfully. It checks file counts, manifest
    existence, and essential command presence.

    Attributes:
        claude_config_dir: Path to Claude config directory (~/.claude).
        agents_dir: Path to agents directory.
        commands_dir: Path to commands directory.
        manifest_path: Path to installation manifest file.
    """

    # Essential command files that must exist for a valid installation
    ESSENTIAL_COMMANDS: list[str] = [
        "review.md",
        "devops.md",
        "discuss.md",
        "design.md",
        "distill.md",
        "deliver.md",
    ]

    def __init__(self, claude_config_dir: Path | None = None):
        """Initialize InstallationVerifier.

        Args:
            claude_config_dir: Optional path to Claude config directory.
                              Defaults to ~/.claude via PathUtils.
        """
        self.claude_config_dir = claude_config_dir or PathUtils.get_claude_config_dir()
        self.agents_dir = self.claude_config_dir / "agents" / "nw"
        self.commands_dir = self.claude_config_dir / "commands" / "nw"
        self.skills_dir = self.claude_config_dir / "skills" / "nw"
        self.des_dir = self.claude_config_dir / "lib" / "python" / "des"
        self.manifest_path = self.claude_config_dir / "nwave-manifest.txt"

    def verify_agent_files(self) -> int:
        """Count agent markdown files in the agents directory.

        Returns:
            Number of .md files found in ~/.claude/agents/nw/.
            Returns 0 if directory does not exist.
        """
        return PathUtils.count_files(self.agents_dir, "*.md")

    def verify_command_files(self) -> int:
        """Count command markdown files in the commands directory.

        Returns:
            Number of .md files found in ~/.claude/commands/nw/.
            Returns 0 if directory does not exist.
        """
        return PathUtils.count_files(self.commands_dir, "*.md")

    def verify_manifest(self) -> bool:
        """Check if the installation manifest file exists.

        Returns:
            True if nwave-manifest.txt exists, False otherwise.
        """
        return self.manifest_path.exists()

    def verify_essential_commands(self) -> list[str]:
        """Check for missing essential command files.

        Returns:
            List of missing essential command filenames.
            Empty list if all essential commands are present.
        """
        missing = []
        for command_file in self.ESSENTIAL_COMMANDS:
            command_path = self.commands_dir / command_file
            if not command_path.exists():
                missing.append(command_file)
        return missing

    def verify_skills(self) -> tuple[int, int]:
        """Verify skills installation.

        Returns:
            Tuple of (skill_file_count, skill_group_count).
            Returns (0, 0) if skills directory does not exist.
        """
        if not self.skills_dir.exists():
            return 0, 0
        skill_files = list(self.skills_dir.rglob("*.md"))
        skill_groups = [d for d in self.skills_dir.iterdir() if d.is_dir()]
        return len(skill_files), len(skill_groups)

    def verify_des(self) -> bool:
        """Verify DES module installation.

        Returns:
            True if DES directory exists and contains Python files.
        """
        if not self.des_dir.exists():
            return False
        return len(list(self.des_dir.rglob("*.py"))) > 0

    def run_verification(self) -> VerificationResult:
        """Run complete installation verification.

        Performs all verification checks and returns a comprehensive result.

        Returns:
            VerificationResult with all verification details.
            success=True only if all checks pass.
        """
        agent_count = self.verify_agent_files()
        command_count = self.verify_command_files()
        manifest_exists = self.verify_manifest()
        missing_essential = self.verify_essential_commands()
        skill_file_count, skill_group_count = self.verify_skills()
        des_installed = self.verify_des()

        # Determine overall success
        # Verification fails if:
        # - Essential files are missing
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
                    f"missing essential files: {', '.join(missing_essential)}"
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
            error_code=error_code,
            message=message,
        )
