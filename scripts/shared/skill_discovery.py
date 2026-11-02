"""Discover skill entry points without treating their reference assets as skills."""

from pathlib import Path


def skill_entrypoints(skills_dir: Path) -> list[Path]:
    return (
        sorted(
            path
            for directory in skills_dir.iterdir()
            if directory.is_dir()
            for path in (
                [directory / "SKILL.md"]
                if (directory / "SKILL.md").is_file()
                else directory.glob("*.md")
            )
        )
        if skills_dir.is_dir()
        else []
    )
