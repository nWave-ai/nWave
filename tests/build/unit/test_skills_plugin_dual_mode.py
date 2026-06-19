"""Tests for dual-mode SkillsPlugin: old hierarchical and new flat layouts.

Step 01-03: SkillsPlugin gains layout detection, installs from both
old nw/{agent}/ and new nw-*/SKILL.md source layouts. Cleans up old
~/.claude/skills/nw/ directory during upgrade. Preserves user custom skills.

Driving port: SkillsPlugin.install()
Test Budget: 4 behaviors x 2 = 8 max unit tests
"""

import logging
from pathlib import Path

import pytest

from scripts.install.plugins.base import InstallContext
from scripts.install.plugins.skills_plugin import SkillsPlugin


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def logger() -> logging.Logger:
    return logging.getLogger("test.skills-dual-mode")


@pytest.fixture
def claude_dir(tmp_path: Path) -> Path:
    d = tmp_path / ".claude"
    d.mkdir()
    return d


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


@pytest.fixture
def new_flat_source(tmp_path: Path) -> Path:
    """Source tree with nw-*/SKILL.md layout (NEW_FLAT)."""
    source = tmp_path / "source" / "skills"
    source.mkdir(parents=True)
    for name in ("nw-tdd-methodology", "nw-hexagonal-testing", "nw-quality-framework"):
        d = source / name
        d.mkdir()
        (d / "SKILL.md").write_text(f"# {name}\nContent.\n", encoding="utf-8")
    # Create minimal framework-catalog.yaml so load_public_agents(strict=True) works.
    # In _make_context, project_root = framework_source.parent = source.parent.parent
    # = tmp_path. So the catalog is at tmp_path/nWave/framework-catalog.yaml.
    nwave_dir = tmp_path / "nWave"
    nwave_dir.mkdir(parents=True, exist_ok=True)
    (nwave_dir / "framework-catalog.yaml").write_text(
        "agents: {}\n",
        encoding="utf-8",
    )
    return source


@pytest.fixture
def plugin() -> SkillsPlugin:
    return SkillsPlugin()


def _make_context(
    claude_dir: Path,
    framework_source: Path,
    project_root: Path,
    logger: logging.Logger,
) -> InstallContext:
    return InstallContext(
        claude_dir=claude_dir,
        scripts_dir=project_root / "scripts" / "install",
        templates_dir=project_root / "nWave" / "templates",
        logger=logger,
        project_root=framework_source.parent,
        framework_source=framework_source,
    )


# ---------------------------------------------------------------------------
# AC1: Installer detects and installs from new nw-*/SKILL.md layout
# ---------------------------------------------------------------------------


class TestInstallFromNewFlatLayout:
    """SkillsPlugin installs nw-*/SKILL.md directories to ~/.claude/skills/."""

    def test_install_copies_nw_prefixed_dirs_with_skill_md(
        self,
        plugin: SkillsPlugin,
        claude_dir: Path,
        new_flat_source: Path,
        project_root: Path,
        logger: logging.Logger,
    ) -> None:
        ctx = _make_context(claude_dir, new_flat_source.parent, project_root, logger)
        result = plugin.install(ctx)

        assert result.success, result.message
        for name in (
            "nw-tdd-methodology",
            "nw-hexagonal-testing",
            "nw-quality-framework",
        ):
            installed = claude_dir / "skills" / name / "SKILL.md"
            assert installed.exists(), f"{name}/SKILL.md not installed"


# ---------------------------------------------------------------------------
# AC2: Old nw/ directory removed during upgrade
# ---------------------------------------------------------------------------


class TestCleanupOldNamespace:
    """Old ~/.claude/skills/nw/ directory is removed during install."""

    def test_install_removes_old_nw_namespace_directory(
        self,
        plugin: SkillsPlugin,
        claude_dir: Path,
        new_flat_source: Path,
        project_root: Path,
        logger: logging.Logger,
    ) -> None:
        # Pre-condition: old nw/ dir exists from previous install
        old_nw = claude_dir / "skills" / "nw"
        old_nw.mkdir(parents=True)
        (old_nw / "software-crafter").mkdir()
        (old_nw / "software-crafter" / "tdd.md").write_text("old", encoding="utf-8")

        ctx = _make_context(claude_dir, new_flat_source.parent, project_root, logger)
        result = plugin.install(ctx)

        assert result.success, result.message
        assert not old_nw.exists(), "Old nw/ directory should be removed after install"


# ---------------------------------------------------------------------------
# AC3: User custom skills preserved
# ---------------------------------------------------------------------------


class TestPreserveCustomSkills:
    """User-owned skills without nw- prefix are never touched."""

    def test_install_preserves_custom_skill_directory(
        self,
        plugin: SkillsPlugin,
        claude_dir: Path,
        new_flat_source: Path,
        project_root: Path,
        logger: logging.Logger,
    ) -> None:
        # Pre-condition: user has custom skill
        custom = claude_dir / "skills" / "my-prompt-patterns"
        custom.mkdir(parents=True)
        (custom / "SKILL.md").write_text("# My Patterns\n", encoding="utf-8")

        ctx = _make_context(claude_dir, new_flat_source.parent, project_root, logger)
        result = plugin.install(ctx)

        assert result.success, result.message
        assert custom.exists(), "Custom skill directory should be preserved"
        assert (custom / "SKILL.md").read_text(encoding="utf-8") == "# My Patterns\n"


# ---------------------------------------------------------------------------
# AC4: Installation reports correct file count
# ---------------------------------------------------------------------------


class TestReportsCorrectCount:
    """Installation reports correct file count for both layouts."""

    def test_reports_count_for_new_flat_layout(
        self,
        plugin: SkillsPlugin,
        claude_dir: Path,
        new_flat_source: Path,
        project_root: Path,
        logger: logging.Logger,
    ) -> None:
        ctx = _make_context(claude_dir, new_flat_source.parent, project_root, logger)
        result = plugin.install(ctx)

        assert result.success, result.message
        assert len(result.installed_files) == 3
        assert "3" in result.message
