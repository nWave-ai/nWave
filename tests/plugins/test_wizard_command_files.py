"""Tests for wizard command task files (new.md, continue.md, ff.md).

Validates that the three wizard command files exist with correct frontmatter,
are registered in framework-catalog.yaml, contain consistent wave detection
rules, and document required behaviors per the wizard-commands requirements.
"""

from pathlib import Path

import pytest
import yaml


PROJECT_ROOT = Path(__file__).parent.parent.parent
COMMANDS_DIR = PROJECT_ROOT / "nWave" / "tasks" / "nw"
CATALOG_PATH = PROJECT_ROOT / "nWave" / "framework-catalog.yaml"

WIZARD_COMMANDS = ["new", "continue", "ff"]

# Wave detection artifact paths that must appear in both continue.md and ff.md.
# These are the canonical artifact paths from the requirements specification.
WAVE_DETECTION_ARTIFACTS = {
    "DISCOVER": "problem-validation.md",
    "DISCUSS": "requirements.md",
    "DESIGN": "architecture-design.md",
    "DEVOP": "platform-architecture.md",
    "DISTILL": "test-scenarios.md",
    "DELIVER": "execution-log.yaml",
}


def _parse_frontmatter(filepath: Path) -> dict | None:
    """Extract YAML frontmatter from a markdown file."""
    content = filepath.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        return None
    if "\n---\n" not in content[4:]:
        return None
    end_pos = content.index("\n---\n", 4)
    yaml_block = content[4:end_pos]
    return yaml.safe_load(yaml_block)


def _load_catalog_commands() -> dict:
    """Load command metadata from framework-catalog.yaml."""
    with open(CATALOG_PATH, encoding="utf-8") as f:
        catalog = yaml.safe_load(f)
    return catalog.get("commands", {})


def _read_file_content(filename: str) -> str:
    """Read the full text content of a command file."""
    filepath = COMMANDS_DIR / f"{filename}.md"
    return filepath.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Walking skeleton: wizard command files exist with valid frontmatter
# ---------------------------------------------------------------------------


class TestWizardCommandFilesExist:
    """Walking skeleton: all three wizard command files exist with frontmatter."""

    @pytest.mark.parametrize("cmd_name", WIZARD_COMMANDS)
    def test_wizard_command_file_exists(self, cmd_name):
        """Each wizard command file must exist under nWave/tasks/nw/."""
        filepath = COMMANDS_DIR / f"{cmd_name}.md"
        assert filepath.exists(), f"Wizard command file missing: {filepath}"

    @pytest.mark.parametrize("cmd_name", WIZARD_COMMANDS)
    def test_wizard_command_has_valid_frontmatter(self, cmd_name):
        """Each wizard command must have YAML frontmatter with description."""
        filepath = COMMANDS_DIR / f"{cmd_name}.md"
        fm = _parse_frontmatter(filepath)
        assert fm is not None, f"{cmd_name}.md has no YAML frontmatter"
        assert "description" in fm, f"{cmd_name}.md frontmatter missing 'description'"

    @pytest.mark.parametrize("cmd_name", WIZARD_COMMANDS)
    def test_wizard_command_has_argument_hint(self, cmd_name):
        """Each wizard command must have argument-hint in frontmatter."""
        filepath = COMMANDS_DIR / f"{cmd_name}.md"
        fm = _parse_frontmatter(filepath)
        assert fm is not None, f"{cmd_name}.md has no YAML frontmatter"
        assert "argument-hint" in fm, (
            f"{cmd_name}.md frontmatter missing 'argument-hint'"
        )


# ---------------------------------------------------------------------------
# Catalog registration
# ---------------------------------------------------------------------------


class TestWizardCatalogRegistration:
    """Wizard commands must be registered in framework-catalog.yaml."""

    @pytest.mark.parametrize("cmd_name", WIZARD_COMMANDS)
    def test_wizard_command_in_catalog(self, cmd_name):
        """Each wizard command must have an entry in the catalog commands section."""
        catalog_commands = _load_catalog_commands()
        # Catalog uses underscores; file names use hyphens
        catalog_key = cmd_name.replace("-", "_")
        assert catalog_key in catalog_commands, (
            f"Wizard command '{cmd_name}' not found in framework-catalog.yaml commands"
        )

    @pytest.mark.parametrize("cmd_name", WIZARD_COMMANDS)
    def test_wizard_catalog_description_matches_frontmatter(self, cmd_name):
        """Catalog description must match the frontmatter description."""
        catalog_commands = _load_catalog_commands()
        catalog_key = cmd_name.replace("-", "_")
        if catalog_key not in catalog_commands:
            pytest.skip(f"{cmd_name} not yet in catalog")

        filepath = COMMANDS_DIR / f"{cmd_name}.md"
        fm = _parse_frontmatter(filepath)
        assert fm is not None

        expected = catalog_commands[catalog_key].get("description", "")
        actual = fm.get("description", "")
        assert actual == expected, (
            f"{cmd_name}: catalog description '{expected}' != "
            f"frontmatter description '{actual}'"
        )


# ---------------------------------------------------------------------------
# Wave detection rule consistency (continue.md and ff.md)
# ---------------------------------------------------------------------------


class TestWaveDetectionRuleConsistency:
    """Wave detection artifact paths must be consistent across continue.md and ff.md."""

    @pytest.mark.parametrize("cmd_name", ["continue", "ff"])
    def test_command_mentions_all_six_waves(self, cmd_name):
        """Both continue.md and ff.md must reference all 6 wave names."""
        content = _read_file_content(cmd_name)
        for wave_name in WAVE_DETECTION_ARTIFACTS:
            assert wave_name in content, (
                f"{cmd_name}.md does not mention wave '{wave_name}'"
            )

    @pytest.mark.parametrize(
        "wave_name,artifact_path",
        list(WAVE_DETECTION_ARTIFACTS.items()),
        ids=list(WAVE_DETECTION_ARTIFACTS.keys()),
    )
    def test_continue_references_wave_artifact(self, wave_name, artifact_path):
        """continue.md must reference the canonical artifact path for each wave."""
        content = _read_file_content("continue")
        assert artifact_path in content, (
            f"continue.md missing artifact reference '{artifact_path}' "
            f"for wave {wave_name}"
        )

    @pytest.mark.parametrize(
        "wave_name,artifact_path",
        list(WAVE_DETECTION_ARTIFACTS.items()),
        ids=list(WAVE_DETECTION_ARTIFACTS.keys()),
    )
    def test_ff_references_wave_artifact(self, wave_name, artifact_path):
        """ff.md must reference the canonical artifact path for each wave."""
        content = _read_file_content("ff")
        assert artifact_path in content, (
            f"ff.md missing artifact reference '{artifact_path}' for wave {wave_name}"
        )

    def test_continue_references_execution_log_for_deliver_progress(self):
        """continue.md must reference execution-log.yaml for DELIVER step-level progress."""
        content = _read_file_content("continue")
        assert "execution-log.yaml" in content, (
            "continue.md must reference execution-log.yaml for DELIVER progress"
        )
        assert ".develop-progress.json" in content, (
            "continue.md must reference .develop-progress.json for DELIVER resume"
        )


# ---------------------------------------------------------------------------
# Project ID derivation specification (new.md)
# ---------------------------------------------------------------------------


class TestProjectIdDerivationSpec:
    """new.md must document the project ID derivation rules."""

    def test_new_documents_prefix_stripping(self):
        """new.md must mention stripping prefixes: implement, add, create, build."""
        content = _read_file_content("new")
        for prefix in ["implement", "add", "create", "build"]:
            assert prefix in content.lower(), (
                f"new.md missing prefix stripping instruction for '{prefix}'"
            )

    def test_new_documents_kebab_case(self):
        """new.md must mention kebab-case conversion."""
        content = _read_file_content("new")
        assert "kebab" in content.lower(), (
            "new.md must document kebab-case conversion for project ID"
        )

    def test_new_documents_segment_limit(self):
        """new.md must mention the 5-segment limit for project IDs."""
        content = _read_file_content("new")
        assert "5" in content, (
            "new.md must document the 5-segment limit for project IDs"
        )


# ---------------------------------------------------------------------------
# Fast-forward specific behaviors (ff.md)
# ---------------------------------------------------------------------------


class TestFastForwardBehaviorSpec:
    """ff.md must document fast-forward specific behaviors."""

    def test_ff_documents_discover_skip_by_default(self):
        """ff.md must document that DISCOVER is skipped by default."""
        content = _read_file_content("ff")
        content_lower = content.lower()
        assert "discover" in content_lower, "ff.md must mention DISCOVER wave"
        assert "skip" in content_lower, (
            "ff.md must document that DISCOVER is skipped by default"
        )

    def test_ff_documents_from_flag(self):
        """ff.md must document the --from flag for starting at a specific wave."""
        content = _read_file_content("ff")
        assert "--from" in content, "ff.md must document the --from flag"

    def test_ff_documents_failure_handling(self):
        """ff.md must document that failures stop the pipeline and suggest /nw:continue."""
        content = _read_file_content("ff")
        content_lower = content.lower()
        assert "fail" in content_lower or "error" in content_lower, (
            "ff.md must document failure handling"
        )
        assert "/nw:continue" in content or "nw:continue" in content, (
            "ff.md must suggest /nw:continue for recovery after failure"
        )


# ---------------------------------------------------------------------------
# Error handling specification coverage
# ---------------------------------------------------------------------------


class TestErrorHandlingSpecs:
    """Command files must document required error handling behaviors."""

    def test_new_documents_vague_description_handling(self):
        """new.md must document handling of vague or unclassifiable descriptions."""
        content = _read_file_content("new")
        content_lower = content.lower()
        assert (
            "vague" in content_lower
            or "follow-up" in content_lower
            or ("clarif" in content_lower)
        ), "new.md must document vague description handling"

    def test_new_documents_name_conflict_handling(self):
        """new.md must document name conflict detection and resolution."""
        content = _read_file_content("new")
        content_lower = content.lower()
        assert "conflict" in content_lower or "already exist" in content_lower, (
            "new.md must document name conflict handling"
        )

    def test_continue_documents_no_projects_scenario(self):
        """continue.md must document the no-projects-found scenario."""
        content = _read_file_content("continue")
        assert "/nw:new" in content or "nw:new" in content, (
            "continue.md must suggest /nw:new when no projects are found"
        )

    def test_continue_documents_skipped_waves_warning(self):
        """continue.md must document warning about non-adjacent wave artifacts."""
        content = _read_file_content("continue")
        content_lower = content.lower()
        assert (
            "skip" in content_lower
            or "non-adjacent" in content_lower
            or ("gap" in content_lower)
        ), "continue.md must document skipped waves warning"

    def test_continue_documents_corrupted_artifact_detection(self):
        """continue.md must document detection of empty or corrupted artifacts."""
        content = _read_file_content("continue")
        content_lower = content.lower()
        assert (
            "empty" in content_lower
            or "corrupt" in content_lower
            or ("0 byte" in content_lower)
        ), "continue.md must document corrupted artifact detection"
