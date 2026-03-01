"""Tests for wizard command files (new, continue, fast-forward).

Validates that:
- All 3 wizard command files exist with valid YAML frontmatter
- Commands reference shared rules file instead of inline duplication
- fast-forward uses correct naming (not ff)
- All 3 commands are registered in framework-catalog.yaml
"""

from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).parent.parent.parent
COMMANDS_DIR = PROJECT_ROOT / "nWave" / "tasks" / "nw"
CATALOG_PATH = PROJECT_ROOT / "nWave" / "framework-catalog.yaml"
SHARED_RULES_PATH = PROJECT_ROOT / "nWave" / "data" / "wizard-shared-rules.md"

WIZARD_COMMANDS = ["new", "continue", "fast-forward"]


def _parse_frontmatter(filepath: Path) -> dict | None:
    """Extract YAML frontmatter from a markdown file."""
    content = filepath.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        return None
    end_pos = content.index("\n---\n", 4) if "\n---\n" in content[4:] else None
    if end_pos is None:
        return None
    yaml_block = content[4:end_pos]
    return yaml.safe_load(yaml_block)


def _load_catalog_commands() -> dict:
    """Load command metadata from framework-catalog.yaml."""
    with open(CATALOG_PATH, encoding="utf-8") as f:
        catalog = yaml.safe_load(f)
    return catalog.get("commands", {})


class TestWizardCommandFiles:
    """Wizard command files exist with valid frontmatter."""

    def test_all_wizard_files_exist(self):
        """All 3 wizard command files must exist."""
        for cmd in WIZARD_COMMANDS:
            filepath = COMMANDS_DIR / f"{cmd}.md"
            assert filepath.exists(), f"Wizard command file missing: {filepath}"

    def test_all_wizard_files_have_frontmatter(self):
        """Every wizard command file must have YAML frontmatter with description."""
        for cmd in WIZARD_COMMANDS:
            filepath = COMMANDS_DIR / f"{cmd}.md"
            fm = _parse_frontmatter(filepath)
            assert fm is not None, f"{cmd}.md missing frontmatter"
            assert "description" in fm, f"{cmd}.md frontmatter missing description"

    def test_wizard_files_have_disable_model_invocation(self):
        """Wizard commands run in main instance, must have disable-model-invocation: true."""
        for cmd in WIZARD_COMMANDS:
            filepath = COMMANDS_DIR / f"{cmd}.md"
            fm = _parse_frontmatter(filepath)
            assert fm is not None, f"{cmd}.md missing frontmatter"
            assert fm.get("disable-model-invocation") is True, (
                f"{cmd}.md must have disable-model-invocation: true"
            )


class TestSharedRulesReferences:
    """Wizard commands reference shared rules instead of inline duplication."""

    def test_shared_rules_file_exists(self):
        """The shared rules file must exist."""
        assert SHARED_RULES_PATH.exists(), (
            f"Shared rules file missing: {SHARED_RULES_PATH}"
        )

    def test_shared_rules_has_feature_id_section(self):
        """Shared rules must contain Feature ID Derivation section."""
        content = SHARED_RULES_PATH.read_text(encoding="utf-8")
        assert "## Feature ID Derivation" in content

    def test_shared_rules_has_wave_detection_section(self):
        """Shared rules must contain Wave Detection Rules section."""
        content = SHARED_RULES_PATH.read_text(encoding="utf-8")
        assert "## Wave Detection Rules" in content

    def test_new_references_shared_rules(self):
        """new.md must reference shared rules for feature ID derivation."""
        content = (COMMANDS_DIR / "new.md").read_text(encoding="utf-8")
        assert "wizard-shared-rules.md" in content

    def test_continue_references_shared_rules(self):
        """continue.md must reference shared rules for wave detection."""
        content = (COMMANDS_DIR / "continue.md").read_text(encoding="utf-8")
        assert "wizard-shared-rules.md" in content

    def test_fast_forward_references_shared_rules(self):
        """fast-forward.md must reference shared rules."""
        content = (COMMANDS_DIR / "fast-forward.md").read_text(encoding="utf-8")
        assert "wizard-shared-rules.md" in content


class TestFastForwardNaming:
    """fast-forward uses correct naming (not ff)."""

    def test_no_ff_command_file(self):
        """ff.md must NOT exist — it was renamed to fast-forward.md."""
        assert not (COMMANDS_DIR / "ff.md").exists(), (
            "ff.md should not exist; use fast-forward.md"
        )

    def test_fast_forward_uses_correct_command_name(self):
        """fast-forward.md must reference /nw:fast-forward, not /nw:ff."""
        content = (COMMANDS_DIR / "fast-forward.md").read_text(encoding="utf-8")
        assert "/nw:fast-forward" in content
        assert "/nw:ff" not in content

    def test_fast_forward_uses_correct_header(self):
        """fast-forward.md must use NW-FAST-FORWARD header, not NW-FF."""
        content = (COMMANDS_DIR / "fast-forward.md").read_text(encoding="utf-8")
        assert "NW-FAST-FORWARD" in content


class TestCatalogRegistration:
    """All 3 wizard commands are registered in framework-catalog.yaml."""

    def test_all_wizard_commands_in_catalog(self):
        """All wizard commands must appear in the catalog."""
        catalog_commands = _load_catalog_commands()
        for cmd in WIZARD_COMMANDS:
            assert cmd in catalog_commands, (
                f"Wizard command '{cmd}' not found in catalog"
            )

    def test_wizard_commands_are_cross_wave(self):
        """Wizard commands must be CROSS_WAVE."""
        catalog_commands = _load_catalog_commands()
        for cmd in WIZARD_COMMANDS:
            assert catalog_commands[cmd].get("wave") == "CROSS_WAVE", (
                f"Wizard command '{cmd}' must be CROSS_WAVE"
            )

    def test_wizard_commands_have_no_agents(self):
        """Wizard commands run in main instance, agents list must be empty."""
        catalog_commands = _load_catalog_commands()
        for cmd in WIZARD_COMMANDS:
            assert catalog_commands[cmd].get("agents") == [], (
                f"Wizard command '{cmd}' must have empty agents list"
            )
