"""FrameworkFilesCheck — verifies agents/ and skills/ are present and populated."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nwave_ai.common.check_result import CheckResult


if TYPE_CHECKING:
    from pathlib import Path

    from nwave_ai.doctor.context import DoctorContext


# commands/ is intentionally excluded: since v2.8.0 the framework delivers
# commands as skills under skills/nw-*/SKILL.md, and commands_plugin.py removes
# any legacy commands/nw/ directory on every install. Requiring commands/ here
# would yield a false-positive on every clean install.
REQUIRED_DIRS: tuple[str, ...] = ("agents", "skills")


def _count_markdown_files(directory: Path) -> int:
    """Count .md files recursively, excluding .md.bak backups.

    Args:
        directory: Directory to search recursively.

    Returns:
        Count of files with suffix exactly '.md'.
    """
    if not directory.is_dir():
        return 0
    return sum(1 for p in directory.rglob("*.md"))


class FrameworkFilesCheck:
    """Check that agents/ and skills/ exist and contain at least 1 .md file each.

    Uses recursive search to handle real install layouts:
    - agents/nw/*.md (nested under subdirectory)
    - skills/*/SKILL.md (each skill is a directory)
    """

    name: str = "framework_files"
    description: str = (
        "Framework directories (agents/, skills/) exist and are populated"
    )

    def run(self, context: DoctorContext) -> CheckResult:
        """Return passed=True when every required directory contains >= 1 .md file (recursive).

        Args:
            context: Filesystem roots — checks context.claude_dir subdirectories.

        Returns:
            CheckResult with per-directory recursive .md file counts in message.
        """
        counts: dict[str, int] = {}
        problems: list[str] = []

        for subdir in REQUIRED_DIRS:
            directory = context.claude_dir / subdir
            if not directory.exists():
                problems.append(f"{subdir}/: missing")
                counts[subdir] = 0
            else:
                file_count = _count_markdown_files(directory)
                counts[subdir] = file_count
                if file_count == 0:
                    problems.append(f"{subdir}/: empty (0 .md files)")

        count_str = ", ".join(f"{d}={counts.get(d, 0)}" for d in REQUIRED_DIRS)

        if problems:
            problem_str = "; ".join(problems)
            return CheckResult(
                passed=False,
                error_code="FRAMEWORK_DIRS_INCOMPLETE",
                message=f"Framework directory issues ({count_str}): {problem_str}",
                remediation=(
                    "Run `nwave-ai install` to deploy the nWave framework files, "
                    "or verify your installation completed without errors."
                ),
            )

        return CheckResult(
            passed=True,
            error_code=None,
            message=f"Framework directories populated: agents={counts['agents']}, "
            f"skills={counts['skills']}",
            remediation=None,
        )
