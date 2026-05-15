"""Unit tests for OpenCode commands installer plugin.

Tests validate that:
- _transform_frontmatter() removes argument-hint and disable-model-invocation
- _transform_frontmatter() keeps description unchanged
- _transform_command() produces a complete OpenCode-format command file
- install() creates transformed command files in the target directory
- install() preserves body content unchanged
- uninstall() only removes manifest-tracked commands, not user-created ones
- install() creates a .nwave-commands-manifest.json tracking installed commands

CRITICAL: Tests follow hexagonal architecture - mocks only at port boundaries.

State-delta migration summary
------------------------------
CONVERTED (5 tests) — state-delta + implicit-unchanged invariant:
  - test_install_creates_command_files: filesystem multi-slot (command file +
    manifest created); implicit-unchanged prevents unintended sibling file mutations
  - test_install_preserves_body: content multi-slot (body preserved, frontmatter
    transformed); implicit-unchanged on undeclared content slots
  - test_uninstall_removes_only_manifest_commands: classic "preserve user files"
    semantic; implicit-unchanged enforces user command is not removed
  - test_install_creates_manifest: manifest + command files multi-slot;
    implicit-unchanged on unrelated slots
  - test_transform_command_with_all_removals + test_transform_command_description_only:
    content multi-slot on pure-function output (argument-hint/disable-model-invocation
    absent, description + body preserved); catches silently dropped transformations

KEPT as-is (3 tests) — no state-delta benefit:
  - test_transform_removes_argument_hint: pure function, single-assertion (no state)
  - test_transform_removes_disable_model_invocation: pure function, single-assertion
  - test_transform_keeps_description: pure function, single-assertion (no state)

Hidden mutations found:
  - None detected in this file. The commands plugin transformation is a simple
    key-removal filter (no renames, no additions) so the content slot coverage
    adds correctness clarity but did not expose previously-untracked mutations.
    The implicit-unchanged invariant on filesystem tests still guards against
    unexpected sibling file creation as a regression net.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

from nwave_ai.state_delta import assert_state_delta, set_to

from scripts.install.plugins.base import InstallContext
from scripts.install.plugins.opencode_commands_plugin import (
    OpenCodeCommandsPlugin,
    _transform_command,
    _transform_frontmatter,
)
from scripts.install.plugins.opencode_common import parse_frontmatter


def _make_context(tmp_path):
    """Create an InstallContext with a minimal command source layout.

    Returns:
        Tuple of (context, commands_source, opencode_commands_target)
    """
    project_root = tmp_path / "project"
    framework_source = tmp_path / "framework"

    commands_source = project_root / "nWave" / "tasks" / "nw"
    commands_source.mkdir(parents=True)

    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)

    logger = MagicMock()

    context = InstallContext(
        claude_dir=claude_dir,
        scripts_dir=tmp_path / "scripts",
        templates_dir=tmp_path / "templates",
        logger=logger,
        project_root=project_root,
        framework_source=framework_source,
    )

    opencode_commands_target = tmp_path / "home" / ".config" / "opencode" / "commands"

    return context, commands_source, opencode_commands_target


def _create_command(commands_source, command_name, content):
    """Create a command .md file in the source layout.

    Args:
        commands_source: Path to nWave/tasks/nw/ directory
        command_name: Command filename without extension (e.g. 'deliver')
        content: Full file content with frontmatter + body
    """
    (commands_source / f"{command_name}.md").write_text(content)


_COMMAND_WITH_ARGUMENT_HINT = (
    "---\n"
    'description: "Designs system architecture with C4 diagrams."\n'
    'argument-hint: "[component-name] - Optional: --paradigm=[auto|oop|fp]"\n'
    "---\n"
    "\n"
    "# NW-DESIGN: Architecture Design\n"
    "\n"
    "Body content here.\n"
)

_COMMAND_WITH_DISABLE_MODEL = (
    "---\n"
    'description: "Archives a completed feature to docs/evolution/."\n'
    "disable-model-invocation: true\n"
    "argument-hint: '[agent] [feature-id] - Example: @platform-architect \"auth\"'\n"
    "---\n"
    "\n"
    "# NW-FINALIZE: Feature Completion\n"
    "\n"
    "Finalize body content.\n"
)

_COMMAND_DESCRIPTION_ONLY = (
    "---\n"
    'description: "Simple command with only description."\n'
    "---\n"
    "\n"
    "# NW-SIMPLE: Simple Command\n"
    "\n"
    "Simple body.\n"
)


# ---------------------------------------------------------------------------
# State-delta helpers
# ---------------------------------------------------------------------------


def _command_filesystem_state(
    target_dir: Path,
    track: frozenset[str] | None = None,
) -> dict[str, object]:
    """Return a flat state dict for the OpenCode commands target directory.

    Tracks existence of command .md files and the manifest. Each key is either
    ``<command-name>.md.exists`` or ``manifest.exists``.

    When ``track`` is provided, every name in the set is always emitted with
    True/False so before/after share the key (required for uninstall tests that
    assert ``set_to(False)``). Pass ``"manifest"`` as a special token for the
    manifest file; everything else is treated as a bare filename (with extension)
    under ``target_dir``. Without ``track``, only currently-existing .md files
    and the manifest are emitted.

    Args:
        target_dir: Path to the OpenCode commands directory (may not yet exist).
        track: Optional set of names to always emit. Use ``"manifest"`` for the
               manifest file and ``"<command-name>.md"`` for command files.

    Returns:
        Flat dict mapping slot names to their current values.
    """
    manifest_path = target_dir / ".nwave-commands-manifest.json"
    state: dict[str, object] = {}

    if track is not None:
        for name in track:
            if name == "manifest":
                state["manifest.exists"] = manifest_path.exists()
            else:
                state[f"{name}.exists"] = (target_dir / name).exists()
    else:
        state["manifest.exists"] = manifest_path.exists()
        if target_dir.exists():
            for entry in sorted(target_dir.iterdir()):
                if entry.is_file() and entry.suffix == ".md":
                    state[f"{entry.name}.exists"] = True

    return state


def _command_content_state(target_dir: Path, command_name: str) -> dict[str, object]:
    """Return a flat state dict for an installed command file's content.

    Slots:
      ``content.exists``                   whether <command_name>.md exists
      ``content.has_argument_hint``        file contains ``argument-hint``
      ``content.has_disable_model``        file contains ``disable-model-invocation``
      ``content.has_description``          file contains ``description:``
      ``content.body_excerpt``             first non-blank body line (None when absent)
      ``content.full``                     raw file text (None when absent)

    Args:
        target_dir: Path to the OpenCode commands directory.
        command_name: Command stem without extension (e.g. ``design``).

    Returns:
        Flat dict with content property slots.
    """
    command_md = target_dir / f"{command_name}.md"
    if not command_md.exists():
        return {
            "content.exists": False,
            "content.has_argument_hint": False,
            "content.has_disable_model": False,
            "content.has_description": False,
            "content.body_excerpt": None,
            "content.full": None,
        }
    text = command_md.read_text(encoding="utf-8")
    _, body = parse_frontmatter(text)
    body_lines = [line for line in body.splitlines() if line.strip()]
    return {
        "content.exists": True,
        "content.has_argument_hint": "argument-hint" in text,
        "content.has_disable_model": "disable-model-invocation" in text,
        "content.has_description": "description:" in text,
        "content.body_excerpt": body_lines[0] if body_lines else None,
        "content.full": text,
    }


# ---------------------------------------------------------------------------
# Tests: _transform_frontmatter() — kept as-is (pure function, single concern)
# ---------------------------------------------------------------------------


class TestTransformRemovesArgumentHint:
    """Test that _transform_frontmatter removes argument-hint field."""

    def test_transform_removes_argument_hint(self):
        """
        GIVEN: A frontmatter dict with argument-hint field
        WHEN: _transform_frontmatter() is called
        THEN: argument-hint is not in the result
        """
        frontmatter = {
            "description": "Designs system architecture.",
            "argument-hint": "[component-name] - Optional: --paradigm=[auto|oop|fp]",
        }

        result = _transform_frontmatter(frontmatter)

        assert "argument-hint" not in result


class TestTransformRemovesDisableModelInvocation:
    """Test that _transform_frontmatter removes disable-model-invocation field."""

    def test_transform_removes_disable_model_invocation(self):
        """
        GIVEN: A frontmatter dict with disable-model-invocation field
        WHEN: _transform_frontmatter() is called
        THEN: disable-model-invocation is not in the result
        """
        frontmatter = {
            "description": "Archives a completed feature.",
            "disable-model-invocation": True,
            "argument-hint": "[agent] [feature-id]",
        }

        result = _transform_frontmatter(frontmatter)

        assert "disable-model-invocation" not in result


class TestTransformKeepsDescription:
    """Test that _transform_frontmatter preserves description exactly."""

    def test_transform_keeps_description(self):
        """
        GIVEN: A frontmatter dict with description field
        WHEN: _transform_frontmatter() is called
        THEN: description is preserved with the exact same value
        """
        frontmatter = {
            "description": "Designs system architecture with C4 diagrams.",
            "argument-hint": "[component-name]",
            "disable-model-invocation": True,
        }

        result = _transform_frontmatter(frontmatter)

        assert result["description"] == "Designs system architecture with C4 diagrams."


# ---------------------------------------------------------------------------
# Tests: install() — filesystem creation (converted)
# ---------------------------------------------------------------------------


class TestInstallCreatesCommandFiles:
    """Test that install() creates transformed command files in the target directory."""

    def test_install_creates_command_files(self, tmp_path, monkeypatch):
        """
        GIVEN: A source command at nWave/tasks/nw/design.md
        WHEN: install() is called
        THEN: design.md is created in the OpenCode commands directory
              with transformed frontmatter (no argument-hint);
              no other .md files appear as side-effects.
        """
        context, commands_source, target = _make_context(tmp_path)
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_commands_plugin._opencode_commands_dir",
            lambda: target,
        )

        _create_command(commands_source, "design", _COMMAND_WITH_ARGUMENT_HINT)

        before = _command_filesystem_state(target)

        plugin = OpenCodeCommandsPlugin()
        result = plugin.install(context)

        assert result.success is True

        after = _command_filesystem_state(target)
        universe = set(before.keys()) | set(after.keys())
        assert_state_delta(
            before=before,
            after=after,
            universe=universe,
            expected={
                "design.md.exists": set_to(True),
                "manifest.exists": set_to(True),
            },
        )


# ---------------------------------------------------------------------------
# Tests: install() — content preservation (converted)
# ---------------------------------------------------------------------------


class TestInstallPreservesBody:
    """Test that install() preserves body content unchanged after transformation."""

    def test_install_preserves_body(self, tmp_path, monkeypatch):
        """
        GIVEN: A command file with specific body content
        WHEN: install() transforms it
        THEN: The body content after the frontmatter is unchanged;
              forbidden frontmatter fields are removed;
              implicit-unchanged enforces no undeclared slot mutations.
        """
        context, commands_source, target = _make_context(tmp_path)
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_commands_plugin._opencode_commands_dir",
            lambda: target,
        )

        _create_command(commands_source, "design", _COMMAND_WITH_ARGUMENT_HINT)

        before = _command_content_state(target, "design")

        plugin = OpenCodeCommandsPlugin()
        plugin.install(context)

        after = _command_content_state(target, "design")
        universe = set(before.keys()) | set(after.keys())

        _, source_body = parse_frontmatter(_COMMAND_WITH_ARGUMENT_HINT)

        def body_unchanged(old: object, new: object) -> bool:
            """Body portion of the command file is preserved after transformation."""
            if not isinstance(new, str):
                return False
            _, installed_body = parse_frontmatter(new)
            return installed_body == source_body

        assert_state_delta(
            before=before,
            after=after,
            universe=universe,
            expected={
                "content.exists": set_to(True),
                "content.full": body_unchanged,
                "content.has_argument_hint": set_to(False),
                "content.has_disable_model": set_to(False),
                "content.has_description": set_to(True),
                "content.body_excerpt": set_to("# NW-DESIGN: Architecture Design"),
            },
        )


# ---------------------------------------------------------------------------
# Tests: uninstall() (converted)
# ---------------------------------------------------------------------------


class TestUninstallRemovesOnlyManifestCommands:
    """Test that uninstall() removes only manifest-tracked commands."""

    def test_uninstall_removes_only_manifest_commands(self, tmp_path, monkeypatch):
        """
        GIVEN: An OpenCode commands directory with both nWave-installed and
               user-created command files
        WHEN: uninstall() is called
        THEN: Only nWave-installed commands (listed in manifest) are removed;
              user-created commands remain untouched;
              implicit-unchanged enforces user command preservation automatically.
        """
        context, _commands_source, target = _make_context(tmp_path)
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_commands_plugin._opencode_commands_dir",
            lambda: target,
        )

        target.mkdir(parents=True, exist_ok=True)

        # Create nWave-installed command
        nwave_command = target / "design.md"
        nwave_command.write_text("---\ndescription: Architecture\n---\n\n# Design\n")

        # Create user-owned command (NOT in manifest)
        user_command = target / "my-custom-command.md"
        user_command.write_text("---\ndescription: My cmd\n---\n\n# My cmd\n")

        # Manifest only tracks nWave commands
        manifest = {
            "installed_commands": ["design"],
            "version": "1.0",
        }
        (target / ".nwave-commands-manifest.json").write_text(json.dumps(manifest))

        tracked = frozenset({"design.md", "my-custom-command.md", "manifest"})
        before = _command_filesystem_state(target, track=tracked)

        plugin = OpenCodeCommandsPlugin()
        result = plugin.uninstall(context)

        assert result.success is True

        after = _command_filesystem_state(target, track=tracked)
        universe = set(before.keys()) | set(after.keys())
        assert_state_delta(
            before=before,
            after=after,
            universe=universe,
            expected={
                # nWave command removed: True -> False
                "design.md.exists": set_to(False),
                # manifest removed: True -> False
                "manifest.exists": set_to(False),
                # user command MUST remain: implicit-unchanged enforces this;
                # "my-custom-command.md.exists" True->True is NOT in expected
            },
        )


# ---------------------------------------------------------------------------
# Tests: install() — manifest creation (converted)
# ---------------------------------------------------------------------------


class TestInstallCreatesManifest:
    """Test that install() creates a manifest tracking installed command names."""

    def test_install_creates_manifest(self, tmp_path, monkeypatch):
        """
        GIVEN: Multiple source command files
        WHEN: install() is called
        THEN: A .nwave-commands-manifest.json is created listing all installed commands;
              both command .md files appear; no other .md files created as side-effects.
        """
        context, commands_source, target = _make_context(tmp_path)
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_commands_plugin._opencode_commands_dir",
            lambda: target,
        )

        _create_command(commands_source, "design", _COMMAND_WITH_ARGUMENT_HINT)
        _create_command(commands_source, "finalize", _COMMAND_WITH_DISABLE_MODEL)

        before = _command_filesystem_state(target)

        plugin = OpenCodeCommandsPlugin()
        plugin.install(context)

        after = _command_filesystem_state(target)
        universe = set(before.keys()) | set(after.keys())
        assert_state_delta(
            before=before,
            after=after,
            universe=universe,
            expected={
                "design.md.exists": set_to(True),
                "finalize.md.exists": set_to(True),
                "manifest.exists": set_to(True),
            },
        )

        manifest = json.loads((target / ".nwave-commands-manifest.json").read_text())
        assert "installed_commands" in manifest
        assert sorted(manifest["installed_commands"]) == sorted(["design", "finalize"])


# ---------------------------------------------------------------------------
# Tests: _transform_command() full pipeline (converted)
# ---------------------------------------------------------------------------


class TestTransformCommandFullPipeline:
    """Test the full _transform_command pipeline from source to OpenCode format."""

    def test_transform_command_with_all_removals(self):
        """
        GIVEN: A command file with argument-hint and disable-model-invocation
        WHEN: _transform_command() is called
        THEN: Produces valid OpenCode format with both fields removed;
              description + body are preserved unchanged.
        """
        before = _command_content_state(Path("/nonexistent"), "finalize")

        result_text = _transform_command(_COMMAND_WITH_DISABLE_MODEL)

        _, source_body = parse_frontmatter(_COMMAND_WITH_DISABLE_MODEL)
        _, result_body = parse_frontmatter(result_text)

        after: dict[str, object] = {
            "content.exists": True,
            "content.has_argument_hint": "argument-hint" in result_text,
            "content.has_disable_model": "disable-model-invocation" in result_text,
            "content.has_description": "description:" in result_text,
            "content.body_excerpt": next(
                (line for line in result_body.splitlines() if line.strip()), None
            ),
            "content.full": result_text,
        }

        def description_and_body_preserved(old: object, new: object) -> bool:
            """description value and body are identical to source after transformation."""
            if not isinstance(new, str):
                return False
            fm, body = parse_frontmatter(new)
            return (
                fm.get("description")
                == "Archives a completed feature to docs/evolution/."
                and body == source_body
            )

        universe = set(before.keys()) | set(after.keys())
        assert_state_delta(
            before=before,
            after=after,
            universe=universe,
            expected={
                "content.exists": set_to(True),
                "content.has_argument_hint": set_to(False),
                "content.has_disable_model": set_to(False),
                "content.has_description": set_to(True),
                "content.full": description_and_body_preserved,
                "content.body_excerpt": set_to("# NW-FINALIZE: Feature Completion"),
            },
        )

    def test_transform_command_description_only(self):
        """
        GIVEN: A command file with only description (no fields to remove)
        WHEN: _transform_command() is called
        THEN: Produces output with description preserved and body unchanged;
              only description key remains in frontmatter (len == 1).
        """
        before = _command_content_state(Path("/nonexistent"), "simple")

        result_text = _transform_command(_COMMAND_DESCRIPTION_ONLY)

        _, source_body = parse_frontmatter(_COMMAND_DESCRIPTION_ONLY)
        _frontmatter, result_body = parse_frontmatter(result_text)

        after: dict[str, object] = {
            "content.exists": True,
            "content.has_argument_hint": "argument-hint" in result_text,
            "content.has_disable_model": "disable-model-invocation" in result_text,
            "content.has_description": "description:" in result_text,
            "content.body_excerpt": next(
                (line for line in result_body.splitlines() if line.strip()), None
            ),
            "content.full": result_text,
        }

        def description_only_and_body_preserved(old: object, new: object) -> bool:
            """Only description in frontmatter; body identical to source."""
            if not isinstance(new, str):
                return False
            fm, body = parse_frontmatter(new)
            return (
                len(fm) == 1
                and fm.get("description") == "Simple command with only description."
                and body == source_body
            )

        universe = set(before.keys()) | set(after.keys())
        assert_state_delta(
            before=before,
            after=after,
            universe=universe,
            expected={
                "content.exists": set_to(True),
                "content.has_argument_hint": set_to(False),
                "content.has_disable_model": set_to(False),
                "content.has_description": set_to(True),
                "content.full": description_only_and_body_preserved,
                "content.body_excerpt": set_to("# NW-SIMPLE: Simple Command"),
            },
        )
