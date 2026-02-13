"""Tests for dist/ build system (build_dist.py).

Validates that build_dist.py produces the correct dist/ layout matching
the install target (~/.claude/). Adapted from old test_release_packaging.py
patterns (BuildValidator, VersionReader, VersionConsistency).
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest


# Project root (tests/build/unit/ → 3 levels up)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_project(tmp_path):
    """Create a minimal nWave project structure in tmp_path.

    Mirrors the real source layout so DistBuilder can assemble dist/.
    """
    # nWave/agents/ — agent markdown files
    agents_dir = tmp_path / "nWave" / "agents"
    agents_dir.mkdir(parents=True)
    for name in [
        "nw-solution-architect.md",
        "nw-software-crafter.md",
        "nw-researcher.md",
    ]:
        (agents_dir / name).write_text(f"# {name}\nAgent definition.")

    # nWave/tasks/nw/ — command markdown files
    commands_dir = tmp_path / "nWave" / "tasks" / "nw"
    commands_dir.mkdir(parents=True)
    for name in ["deliver.md", "design.md", "execute.md"]:
        (commands_dir / name).write_text(f"# {name}\nCommand definition.")

    # nWave/templates/ — schema and config templates
    templates_dir = tmp_path / "nWave" / "templates"
    templates_dir.mkdir(parents=True)
    (templates_dir / "step-tdd-cycle-schema.json").write_text('{"type": "object"}')
    (templates_dir / "roadmap-compact.yaml").write_text("roadmap: compact")

    # nWave/skills/ — skill group subdirectories
    for skill_group in ["software-crafter", "solution-architect"]:
        skill_dir = tmp_path / "nWave" / "skills" / skill_group
        skill_dir.mkdir(parents=True)
        (skill_dir / "overview.md").write_text(f"# {skill_group}\nSkill overview.")
        (skill_dir / "patterns.md").write_text(f"# {skill_group}\nPatterns.")

    # nWave/scripts/des/ — DES utility scripts
    des_scripts_dir = tmp_path / "nWave" / "scripts" / "des"
    des_scripts_dir.mkdir(parents=True)
    (des_scripts_dir / "check_stale_phases.py").write_text("# stale phases checker")
    (des_scripts_dir / "scope_boundary_check.py").write_text("# scope boundary check")

    # nWave/framework-catalog.yaml
    (tmp_path / "nWave" / "framework-catalog.yaml").write_text(
        'name: "nWave"\nversion: "2.13.3"\ndescription: "Test framework"\n'
    )

    # src/des/ — DES module with imports to rewrite
    des_module = tmp_path / "src" / "des"
    des_module.mkdir(parents=True)
    (des_module / "__init__.py").write_text('"""DES module."""\n')
    (des_module / "application").mkdir()
    (des_module / "application" / "__init__.py").write_text(
        "from src.des.application.orchestrator import DESOrchestrator\n"
    )
    (des_module / "application" / "orchestrator.py").write_text(
        "from src.des.adapters.driven.config import load_config\n"
        "\n"
        "class DESOrchestrator:\n"
        "    pass\n"
    )
    (des_module / "adapters").mkdir()
    (des_module / "adapters" / "__init__.py").write_text("")
    (des_module / "adapters" / "driven").mkdir()
    (des_module / "adapters" / "driven" / "__init__.py").write_text("")
    (des_module / "adapters" / "driven" / "config.py").write_text(
        "import src.des.adapters\n\ndef load_config():\n    return {}\n"
    )

    # pyproject.toml — version source
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "test"\nversion = "2.13.3"\n'
    )

    # scripts/ — utility scripts
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir(parents=True)
    (scripts_dir / "install_nwave_target_hooks.py").write_text(
        "# target hooks installer"
    )
    (scripts_dir / "validate_step_file.py").write_text("# step file validator")

    return tmp_path


@pytest.fixture()
def built_dist(mock_project):
    """Build dist/ from mock project and return dist path.

    Uses DistBuilder directly (not CLI) for fast test execution.
    """
    # Import from the real project's scripts/ directory
    real_scripts = str(PROJECT_ROOT / "scripts")
    sys.path.insert(0, real_scripts)
    try:
        from build_dist import DistBuilder

        builder = DistBuilder(project_root=mock_project)
        success = builder.run()
        assert success, "DistBuilder.run() failed"
    finally:
        sys.path.pop(0)

    return mock_project / "dist"


# ---------------------------------------------------------------------------
# 1. TestDistStructureValidator — adapted from old TestBuildValidator
# ---------------------------------------------------------------------------


class TestDistStructureValidator:
    """Validate that dist/ contains all required directories and files."""

    REQUIRED_DIRS = [
        "agents/nw",
        "commands/nw",
        "templates",
        "skills/nw",
        "scripts/des",
        "lib/python/des",
    ]

    REQUIRED_FILES = ["MANIFEST.json"]

    def test_dist_has_all_required_directories(self, built_dist):
        """Each required directory exists after build."""
        for dir_path in self.REQUIRED_DIRS:
            assert (built_dist / dir_path).is_dir(), f"Missing required dir: {dir_path}"

    def test_dist_has_agents(self, built_dist):
        """dist/agents/nw/ contains nw-*.md files."""
        agents = list((built_dist / "agents" / "nw").glob("nw-*.md"))
        assert len(agents) > 0, "No agent files in dist/agents/nw/"

    def test_dist_has_commands(self, built_dist):
        """dist/commands/nw/ contains *.md files."""
        commands = list((built_dist / "commands" / "nw").glob("*.md"))
        assert len(commands) > 0, "No command files in dist/commands/nw/"

    def test_dist_has_templates(self, built_dist):
        """dist/templates/ has schema and config files."""
        templates = list((built_dist / "templates").iterdir())
        assert len(templates) > 0, "No template files in dist/templates/"

    def test_dist_has_skills(self, built_dist):
        """dist/skills/nw/ has subdirectories with *.md files."""
        skills_dir = built_dist / "skills" / "nw"
        subdirs = [d for d in skills_dir.iterdir() if d.is_dir()]
        assert len(subdirs) > 0, "No skill groups in dist/skills/nw/"
        for subdir in subdirs:
            md_files = list(subdir.glob("*.md"))
            assert len(md_files) > 0, f"No .md files in skill group: {subdir.name}"

    def test_dist_has_des_scripts(self, built_dist):
        """dist/scripts/des/ has expected DES scripts."""
        des_scripts = built_dist / "scripts" / "des"
        assert (des_scripts / "check_stale_phases.py").exists()
        assert (des_scripts / "scope_boundary_check.py").exists()

    def test_dist_has_des_module(self, built_dist):
        """dist/lib/python/des/ has __init__.py (importable module)."""
        des_module = built_dist / "lib" / "python" / "des"
        assert (des_module / "__init__.py").exists()

    def test_dist_has_utility_scripts(self, built_dist):
        """dist/scripts/ has utility scripts."""
        scripts_dir = built_dist / "scripts"
        assert (scripts_dir / "install_nwave_target_hooks.py").exists()
        assert (scripts_dir / "validate_step_file.py").exists()

    def test_dist_has_manifest(self, built_dist):
        """dist/ has MANIFEST.json."""
        assert (built_dist / "MANIFEST.json").exists()

    def test_dist_missing_source_fails(self, tmp_path):
        """Build fails cleanly when nWave/ source is missing."""
        # Empty project — no nWave/ directory
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "test"\nversion = "1.0.0"\n'
        )

        real_scripts = str(PROJECT_ROOT / "scripts")
        sys.path.insert(0, real_scripts)
        try:
            from build_dist import DistBuilder

            builder = DistBuilder(project_root=tmp_path)
            success = builder.run()
            assert not success, "Build should fail when nWave/ is missing"
        finally:
            sys.path.pop(0)


# ---------------------------------------------------------------------------
# 2. TestDistDESImportRewriting
# ---------------------------------------------------------------------------


class TestDistDESImportRewriting:
    """Validate DES module import rewriting in dist/."""

    def test_no_src_des_imports(self, built_dist):
        """No 'from src.des.' or 'import src.des.' in dist DES module."""
        des_dir = built_dist / "lib" / "python" / "des"
        for py_file in des_dir.rglob("*.py"):
            content = py_file.read_text()
            assert "from src.des" not in content, (
                f"Found 'from src.des' in {py_file.relative_to(built_dist)}"
            )
            assert "import src.des" not in content, (
                f"Found 'import src.des' in {py_file.relative_to(built_dist)}"
            )
            assert "src.des." not in content, (
                f"Found 'src.des.' in {py_file.relative_to(built_dist)}"
            )

    def test_no_pycache(self, built_dist):
        """No __pycache__ directories in dist DES module."""
        des_dir = built_dist / "lib" / "python" / "des"
        pycache_dirs = list(des_dir.rglob("__pycache__"))
        assert len(pycache_dirs) == 0, (
            f"Found __pycache__ dirs: {[str(d) for d in pycache_dirs]}"
        )

    def test_des_imports_rewritten_correctly(self, built_dist):
        """Rewritten imports use 'des.' prefix (not 'src.des.')."""
        orchestrator = (
            built_dist / "lib" / "python" / "des" / "application" / "orchestrator.py"
        )
        content = orchestrator.read_text()
        assert "from des.adapters.driven.config" in content

        init = built_dist / "lib" / "python" / "des" / "application" / "__init__.py"
        content = init.read_text()
        assert "from des.application.orchestrator" in content


# ---------------------------------------------------------------------------
# 3. TestDistManifest — adapted from old TestVersionReader + VersionConsistency
# ---------------------------------------------------------------------------


class TestDistManifest:
    """Validate MANIFEST.json contents."""

    def test_manifest_is_valid_json(self, built_dist):
        """MANIFEST.json parses as valid JSON."""
        manifest_path = built_dist / "MANIFEST.json"
        manifest = json.loads(manifest_path.read_text())
        assert isinstance(manifest, dict)

    def test_manifest_has_version(self, built_dist):
        """Manifest version matches pyproject.toml version."""
        manifest = json.loads((built_dist / "MANIFEST.json").read_text())
        assert manifest["version"] == "2.13.3"

    def test_manifest_has_built_at(self, built_dist):
        """Manifest has valid ISO timestamp."""
        manifest = json.loads((built_dist / "MANIFEST.json").read_text())
        assert "built_at" in manifest
        # ISO format: YYYY-MM-DDTHH:MM:SS
        assert "T" in manifest["built_at"]

    def test_manifest_has_contents(self, built_dist):
        """Manifest has content counts for all artifact types."""
        manifest = json.loads((built_dist / "MANIFEST.json").read_text())
        contents = manifest["contents"]
        assert "agents" in contents
        assert "commands" in contents
        assert "templates" in contents
        assert "skills" in contents
        assert "des_module" in contents

    def test_manifest_counts_match_dist(self, built_dist):
        """Counts in manifest match actual files in dist/."""
        manifest = json.loads((built_dist / "MANIFEST.json").read_text())
        contents = manifest["contents"]

        actual_agents = len(list((built_dist / "agents" / "nw").glob("nw-*.md")))
        actual_commands = len(list((built_dist / "commands" / "nw").glob("*.md")))
        actual_templates = len(list((built_dist / "templates").iterdir()))

        assert contents["agents"] == actual_agents
        assert contents["commands"] == actual_commands
        assert contents["templates"] == actual_templates


# ---------------------------------------------------------------------------
# 4. TestDistConsistencyWithSource
# ---------------------------------------------------------------------------


class TestDistConsistencyWithSource:
    """Validate dist/ contents match source counts (no files lost)."""

    def test_agent_count_matches_source(self, mock_project, built_dist):
        """dist agents == nWave/agents/nw-*.md count."""
        source_count = len(list((mock_project / "nWave" / "agents").glob("nw-*.md")))
        dist_count = len(list((built_dist / "agents" / "nw").glob("nw-*.md")))
        assert dist_count == source_count

    def test_command_count_matches_source(self, mock_project, built_dist):
        """dist commands == nWave/tasks/nw/*.md count."""
        source_count = len(list((mock_project / "nWave" / "tasks" / "nw").glob("*.md")))
        dist_count = len(list((built_dist / "commands" / "nw").glob("*.md")))
        assert dist_count == source_count

    def test_template_files_match_source(self, mock_project, built_dist):
        """All nWave/templates/ files present in dist."""
        source_files = {
            f.name for f in (mock_project / "nWave" / "templates").iterdir()
        }
        dist_files = {f.name for f in (built_dist / "templates").iterdir()}
        assert source_files == dist_files

    def test_skill_groups_match_source(self, mock_project, built_dist):
        """All nWave/skills/ subdirs present in dist/skills/nw/."""
        source_groups = {
            d.name for d in (mock_project / "nWave" / "skills").iterdir() if d.is_dir()
        }
        dist_groups = {
            d.name for d in (built_dist / "skills" / "nw").iterdir() if d.is_dir()
        }
        assert source_groups == dist_groups

    def test_no_legacy_agents_in_dist(self, mock_project, built_dist):
        """legacy/ directory excluded from dist (if present in source)."""
        # Create a legacy dir in source
        legacy_dir = mock_project / "nWave" / "agents" / "legacy"
        legacy_dir.mkdir()
        (legacy_dir / "old-agent.md").write_text("# Old agent")

        # Rebuild
        real_scripts = str(PROJECT_ROOT / "scripts")
        sys.path.insert(0, real_scripts)
        try:
            from build_dist import DistBuilder

            builder = DistBuilder(project_root=mock_project)
            builder.run()
        finally:
            sys.path.pop(0)

        # legacy/ should not appear in dist
        assert not (built_dist / "agents" / "nw" / "legacy").exists()


# ---------------------------------------------------------------------------
# 5. TestBuildDistCLI — script invocation
# ---------------------------------------------------------------------------


class TestBuildDistCLI:
    """Test build_dist.py CLI invocation."""

    def test_build_creates_dist_directory(self, mock_project):
        """Running build_dist.py creates dist/ directory."""
        build_script = PROJECT_ROOT / "scripts" / "build_dist.py"
        result = subprocess.run(
            [sys.executable, str(build_script), "--project-root", str(mock_project)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"build_dist.py failed:\n{result.stderr}"
        assert (mock_project / "dist").is_dir()
        assert (mock_project / "dist" / "MANIFEST.json").exists()

    def test_build_always_cleans_first(self, mock_project):
        """Stale files in dist/ are removed before building."""
        # Create a stale file in dist/
        stale_dir = mock_project / "dist" / "stale_artifact"
        stale_dir.mkdir(parents=True)
        (stale_dir / "old_file.txt").write_text("stale content")

        build_script = PROJECT_ROOT / "scripts" / "build_dist.py"
        subprocess.run(
            [sys.executable, str(build_script), "--project-root", str(mock_project)],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Stale artifacts should be gone
        assert not (mock_project / "dist" / "stale_artifact").exists()
        # But dist/ itself should exist with fresh content
        assert (mock_project / "dist" / "MANIFEST.json").exists()

    def test_build_idempotent(self, mock_project):
        """Running twice produces same result."""
        build_script = PROJECT_ROOT / "scripts" / "build_dist.py"

        # First build
        subprocess.run(
            [sys.executable, str(build_script), "--project-root", str(mock_project)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        manifest1 = json.loads((mock_project / "dist" / "MANIFEST.json").read_text())
        files1 = sorted(
            str(f.relative_to(mock_project / "dist"))
            for f in (mock_project / "dist").rglob("*")
            if f.is_file()
        )

        # Second build
        subprocess.run(
            [sys.executable, str(build_script), "--project-root", str(mock_project)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        manifest2 = json.loads((mock_project / "dist" / "MANIFEST.json").read_text())
        files2 = sorted(
            str(f.relative_to(mock_project / "dist"))
            for f in (mock_project / "dist").rglob("*")
            if f.is_file()
        )

        # Same file counts
        assert manifest1["contents"] == manifest2["contents"]
        assert files1 == files2

    def test_build_preserves_releases(self, mock_project):
        """dist/releases/ is NOT cleaned (CI artifact preservation)."""
        # Create releases dir with CI artifact
        releases_dir = mock_project / "dist" / "releases"
        releases_dir.mkdir(parents=True)
        (releases_dir / "nwave-claude-code-2.13.3.tar.gz").write_text("ci artifact")

        build_script = PROJECT_ROOT / "scripts" / "build_dist.py"
        subprocess.run(
            [sys.executable, str(build_script), "--project-root", str(mock_project)],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # releases/ should be preserved
        assert (releases_dir / "nwave-claude-code-2.13.3.tar.gz").exists()
