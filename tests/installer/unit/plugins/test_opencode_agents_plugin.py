"""Unit tests for OpenCode agents installer plugin.

Tests validate that:
- _parse_tools() normalizes CSV strings and YAML arrays to lowercase lists
- _transform_frontmatter() removes name/model/skills, renames maxTurns, adds mode
- _transform_agent() produces a complete OpenCode-format agent file
- install() creates transformed agent files in the target directory
- install() preserves body content unchanged
- verify() checks that installed agent files exist
- uninstall() only removes manifest-tracked agents, not user-created ones
- install() creates a .nwave-agents-manifest.json tracking installed agents

CRITICAL: Tests follow hexagonal architecture - mocks only at port boundaries.

State-delta migration summary
------------------------------
CONVERTED (7 tests) — state-delta + implicit-unchanged invariant:
  - test_install_creates_agent_files: multi-slot (agent file + manifest created);
    implicit-unchanged prevents unintended sibling file mutations
  - test_install_preserves_body: content multi-slot (body preserved, frontmatter
    transformed); implicit-unchanged on undeclared content slots
  - test_uninstall_removes_only_manifest_agents: classic "preserve user files"
    semantic; implicit-unchanged enforces user agent is not removed
  - test_install_creates_manifest: manifest + agent files multi-slot;
    implicit-unchanged on unrelated slots
  - test_transform_agent_csv_tools: pure-function content multi-slot (frontmatter
    presence/absence + permission block); merges task_permission test;
    catches silently dropped transformations
  - test_transform_agent_array_tools: pure-function content multi-slot variant;
    distinct input (array tools) producing distinct permission output
  - test_transform_frontmatter_uses_permission_key_not_tools: dict-level
    multi-slot (permission present, tools absent, value correct)

KEPT as-is (7 tests) — no state-delta benefit:
  - test_transform_tools_csv_to_object: single return value from pure function
  - test_transform_tools_array_to_object: single return value from pure function
  - test_transform_removes_name_and_model: pure function, 2-assertion (no state)
  - test_transform_removes_skills: pure function, single-assertion (no state)
  - test_transform_renames_maxturns_to_steps: pure function, 2-assertion (no state)
  - test_transform_adds_mode_subagent: pure function, single-assertion (no state)
  - test_parse_tools_returns_allow_strings_not_booleans: type guard loop on pure fn

Hidden mutations found:
  - content.has_permission transitions False -> True during install(); the original
    test_install_creates_agent_files only checked string fragments in the raw content,
    missing the tools->permission key rename as a declared mutation. Now visible via
    content.has_tools_key + content.has_permission slots in the content helper.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

from nwave_ai.state_delta import assert_state_delta, set_to

from scripts.install.plugins.base import InstallContext
from scripts.install.plugins.opencode_agents_plugin import (
    OpenCodeAgentsPlugin,
    _parse_tools,
    _transform_agent,
    _transform_frontmatter,
)
from scripts.install.plugins.opencode_common import parse_frontmatter


def _make_context(tmp_path):
    """Create an InstallContext with a minimal agent source layout.

    Returns:
        Tuple of (context, agents_source, opencode_agents_target)
    """
    project_root = tmp_path / "project"
    framework_source = tmp_path / "framework"

    agents_source = project_root / "nWave" / "agents"
    agents_source.mkdir(parents=True)

    # Create minimal framework-catalog.yaml so load_public_agents(strict=True)
    # does not raise CatalogNotFoundError. Empty agents section means all
    # agents are treated as public (backward compatibility).
    (project_root / "nWave" / "framework-catalog.yaml").write_text(
        "agents: {}\n",
    )

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

    opencode_agents_target = tmp_path / "home" / ".config" / "opencode" / "agents"

    return context, agents_source, opencode_agents_target


def _create_agent(agents_source, agent_name, content):
    """Create an agent .md file in the source layout.

    Args:
        agents_source: Path to nWave/agents/ directory
        agent_name: Agent filename without extension (e.g. 'nw-software-crafter')
        content: Full file content with frontmatter + body
    """
    (agents_source / f"{agent_name}.md").write_text(content)


_CSV_TOOLS_AGENT = (
    "---\n"
    "name: nw-software-crafter\n"
    "description: DELIVER wave - Outside-In TDD\n"
    "model: inherit\n"
    "tools: Read, Write, Edit, Bash, Glob, Grep, Task\n"
    "maxTurns: 50\n"
    "skills:\n"
    "  - tdd-methodology\n"
    "  - progressive-refactoring\n"
    "---\n"
    "\n"
    "# nw-software-crafter\n"
    "\n"
    "Body content here.\n"
)

_ARRAY_TOOLS_AGENT = (
    "---\n"
    "name: nw-documentarist-reviewer\n"
    "description: Documentation quality reviewer\n"
    "model: haiku\n"
    "tools: [Read, Glob, Grep]\n"
    "maxTurns: 25\n"
    "skills:\n"
    "  - review-criteria\n"
    "---\n"
    "\n"
    "# nw-documentarist-reviewer\n"
    "\n"
    "Reviewer body content.\n"
)


# ---------------------------------------------------------------------------
# State-delta helpers
# ---------------------------------------------------------------------------


def _agent_filesystem_state(
    target_dir: Path,
    track: frozenset[str] | None = None,
) -> dict[str, object]:
    """Return a flat state dict for the OpenCode agents target directory.

    Tracks existence of agent .md files and the manifest. Each key is either
    ``<agent-name>.md.exists`` or ``manifest.exists``.

    When ``track`` is provided, every name in the set is always emitted with
    True/False so before/after share the key (required for uninstall tests that
    assert ``set_to(False)``). Pass ``"manifest"`` as a special token for the
    manifest file; everything else is treated as a bare filename (with extension)
    under ``target_dir``. Without ``track``, only currently-existing .md files
    and the manifest are emitted.

    Args:
        target_dir: Path to the OpenCode agents directory (may not yet exist).
        track: Optional set of names to always emit. Use ``"manifest"`` for the
               manifest file and ``"<agent-name>.md"`` for agent files.

    Returns:
        Flat dict mapping slot names to their current values.
    """
    manifest_path = target_dir / ".nwave-agents-manifest.json"
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


def _agent_content_state(target_dir: Path, agent_name: str) -> dict[str, object]:
    """Return a flat state dict for an installed agent file's content.

    Slots:
      ``content.exists``         whether <agent_name>.md exists
      ``content.has_mode``       file contains ``mode:``
      ``content.has_steps``      file contains ``steps:``
      ``content.has_name``       file contains ``\\nname:`` (frontmatter key)
      ``content.has_model``      file contains ``model:``
      ``content.has_skills``     file contains ``skills:``
      ``content.has_maxturns``   file contains ``maxTurns:``
      ``content.has_tools_key``  file contains ``\\ntools:``
      ``content.has_permission`` file contains ``permission:``
      ``content.body_excerpt``   first non-blank body line (None when absent)
      ``content.full``           raw file text (None when absent)

    Args:
        target_dir: Path to the OpenCode agents directory.
        agent_name: Agent stem without extension (e.g. ``nw-software-crafter``).

    Returns:
        Flat dict with content property slots.
    """
    agent_md = target_dir / f"{agent_name}.md"
    if not agent_md.exists():
        return {
            "content.exists": False,
            "content.has_mode": False,
            "content.has_steps": False,
            "content.has_name": False,
            "content.has_model": False,
            "content.has_skills": False,
            "content.has_maxturns": False,
            "content.has_tools_key": False,
            "content.has_permission": False,
            "content.body_excerpt": None,
            "content.full": None,
        }
    text = agent_md.read_text(encoding="utf-8")
    _, body = parse_frontmatter(text)
    body_lines = [line for line in body.splitlines() if line.strip()]
    return {
        "content.exists": True,
        "content.has_mode": "mode:" in text,
        "content.has_steps": "steps:" in text,
        "content.has_name": "\nname:" in text,
        "content.has_model": "model:" in text,
        "content.has_skills": "skills:" in text,
        "content.has_maxturns": "maxTurns:" in text,
        "content.has_tools_key": "\ntools:" in text,
        "content.has_permission": "permission:" in text,
        "content.body_excerpt": body_lines[0] if body_lines else None,
        "content.full": text,
    }


# ---------------------------------------------------------------------------
# Tests: _parse_tools() — kept as-is (pure function, single return value)
# ---------------------------------------------------------------------------


class TestParseToolsCsvToObject:
    """Test that _parse_tools normalizes CSV string to lowercase list."""

    def test_transform_tools_csv_to_object(self):
        """
        GIVEN: A tools value as CSV string "Read, Write, Edit"
        WHEN: _parse_tools() is called
        THEN: Returns {"read": "allow", "write": "allow", "edit": "allow"}
        """
        result = _parse_tools("Read, Write, Edit")

        assert result == {"read": "allow", "write": "allow", "edit": "allow"}


class TestParseToolsArrayToObject:
    """Test that _parse_tools normalizes YAML array to lowercase list."""

    def test_transform_tools_array_to_object(self):
        """
        GIVEN: A tools value as list ["Read", "Glob", "Grep"]
        WHEN: _parse_tools() is called
        THEN: Returns {"read": "allow", "glob": "allow", "grep": "allow"}
        """
        result = _parse_tools(["Read", "Glob", "Grep"])

        assert result == {"read": "allow", "glob": "allow", "grep": "allow"}


# ---------------------------------------------------------------------------
# Tests: _transform_frontmatter() — kept as-is (pure function, single concern)
# ---------------------------------------------------------------------------


class TestTransformRemovesNameAndModel:
    """Test that _transform_frontmatter removes name and model fields."""

    def test_transform_removes_name_and_model(self):
        """
        GIVEN: A frontmatter dict with name, model, and other fields
        WHEN: _transform_frontmatter() is called
        THEN: name and model are not in the result
        """
        frontmatter = {
            "name": "nw-software-crafter",
            "description": "DELIVER wave",
            "model": "inherit",
            "tools": "Read, Write",
            "maxTurns": 50,
        }

        result = _transform_frontmatter(frontmatter)

        assert "name" not in result
        assert "model" not in result


class TestTransformRemovesSkills:
    """Test that _transform_frontmatter removes skills field."""

    def test_transform_removes_skills(self):
        """
        GIVEN: A frontmatter dict with a skills list
        WHEN: _transform_frontmatter() is called
        THEN: skills is not in the result
        """
        frontmatter = {
            "name": "nw-software-crafter",
            "description": "DELIVER wave",
            "model": "inherit",
            "tools": "Read, Write",
            "maxTurns": 50,
            "skills": ["tdd-methodology", "progressive-refactoring"],
        }

        result = _transform_frontmatter(frontmatter)

        assert "skills" not in result


class TestTransformRenamesMaxTurnsToSteps:
    """Test that _transform_frontmatter renames maxTurns to steps."""

    def test_transform_renames_maxturns_to_steps(self):
        """
        GIVEN: A frontmatter dict with maxTurns: 50
        WHEN: _transform_frontmatter() is called
        THEN: Result has steps: 50 and no maxTurns
        """
        frontmatter = {
            "name": "nw-software-crafter",
            "description": "DELIVER wave",
            "model": "inherit",
            "tools": "Read, Write",
            "maxTurns": 50,
        }

        result = _transform_frontmatter(frontmatter)

        assert result["steps"] == 50
        assert "maxTurns" not in result


class TestTransformAddsSubagentMode:
    """Test that _transform_frontmatter adds mode: subagent."""

    def test_transform_adds_mode_subagent(self):
        """
        GIVEN: A frontmatter dict without mode
        WHEN: _transform_frontmatter() is called
        THEN: Result has mode: "subagent"
        """
        frontmatter = {
            "name": "nw-software-crafter",
            "description": "DELIVER wave",
            "model": "inherit",
            "tools": "Read, Write",
            "maxTurns": 50,
        }

        result = _transform_frontmatter(frontmatter)

        assert result["mode"] == "subagent"


# ---------------------------------------------------------------------------
# Tests: install() — filesystem creation (converted)
# ---------------------------------------------------------------------------


class TestInstallCreatesAgentFiles:
    """Test that install() creates transformed agent files in the target directory."""

    def test_install_creates_agent_files(self, tmp_path, monkeypatch):
        """
        GIVEN: A source agent at nWave/agents/nw-software-crafter.md
        WHEN: install() is called
        THEN: nw-software-crafter.md is created in the OpenCode agents directory;
              manifest is created; no other .md files appear as side-effects.
        """
        context, agents_source, target = _make_context(tmp_path)
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_agents_plugin._opencode_agents_dir",
            lambda: target,
        )

        _create_agent(agents_source, "nw-software-crafter", _CSV_TOOLS_AGENT)

        before = _agent_filesystem_state(target)

        plugin = OpenCodeAgentsPlugin()
        result = plugin.install(context)

        assert result.success is True

        after = _agent_filesystem_state(target)
        universe = set(before.keys()) | set(after.keys())
        assert_state_delta(
            before=before,
            after=after,
            universe=universe,
            expected={
                "nw-software-crafter.md.exists": set_to(True),
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
        GIVEN: An agent file with specific body content
        WHEN: install() transforms it
        THEN: The body content after the frontmatter is unchanged;
              frontmatter transformation slots (mode, steps, permission) declared;
              implicit-unchanged enforces no undeclared slot mutations.
        """
        context, agents_source, target = _make_context(tmp_path)
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_agents_plugin._opencode_agents_dir",
            lambda: target,
        )

        _create_agent(agents_source, "nw-software-crafter", _CSV_TOOLS_AGENT)

        before = _agent_content_state(target, "nw-software-crafter")

        plugin = OpenCodeAgentsPlugin()
        plugin.install(context)

        after = _agent_content_state(target, "nw-software-crafter")
        universe = set(before.keys()) | set(after.keys())

        _, source_body = parse_frontmatter(_CSV_TOOLS_AGENT)

        def body_unchanged(old: object, new: object) -> bool:
            """Body portion of the agent file is preserved after transformation."""
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
                "content.has_mode": set_to(True),
                "content.has_steps": set_to(True),
                "content.has_name": set_to(False),
                "content.has_model": set_to(False),
                "content.has_skills": set_to(False),
                "content.has_maxturns": set_to(False),
                # tools -> permission: both key-presence slots transition
                "content.has_tools_key": set_to(False),
                "content.has_permission": set_to(True),
                # body_excerpt: None -> first body headline
                "content.body_excerpt": set_to("# nw-software-crafter"),
            },
        )


# ---------------------------------------------------------------------------
# Tests: uninstall() (converted)
# ---------------------------------------------------------------------------


class TestUninstallRemovesOnlyManifestAgents:
    """Test that uninstall() removes only manifest-tracked agents."""

    def test_uninstall_removes_only_manifest_agents(self, tmp_path, monkeypatch):
        """
        GIVEN: An OpenCode agents directory with both nWave-installed and
               user-created agent files plus a manifest
        WHEN: uninstall() is called
        THEN: Only nWave-installed agents (listed in manifest) are removed;
              user-created agents remain untouched;
              implicit-unchanged enforces user agent preservation automatically.
        """
        context, _agents_source, target = _make_context(tmp_path)
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_agents_plugin._opencode_agents_dir",
            lambda: target,
        )

        target.mkdir(parents=True, exist_ok=True)

        # Create nWave-installed agent
        nwave_agent = target / "nw-software-crafter.md"
        nwave_agent.write_text("---\nmode: subagent\n---\n\n# Agent\n")

        # Create user-owned agent (NOT in manifest)
        user_agent = target / "my-custom-agent.md"
        user_agent.write_text("---\nmode: subagent\n---\n\n# My agent\n")

        # Manifest only tracks nWave agents
        manifest = {
            "installed_agents": ["nw-software-crafter"],
            "version": "1.0",
        }
        (target / ".nwave-agents-manifest.json").write_text(json.dumps(manifest))

        tracked = frozenset(
            {"nw-software-crafter.md", "my-custom-agent.md", "manifest"}
        )
        before = _agent_filesystem_state(target, track=tracked)

        plugin = OpenCodeAgentsPlugin()
        result = plugin.uninstall(context)

        assert result.success is True

        after = _agent_filesystem_state(target, track=tracked)
        universe = set(before.keys()) | set(after.keys())
        assert_state_delta(
            before=before,
            after=after,
            universe=universe,
            expected={
                # nWave agent removed: True -> False
                "nw-software-crafter.md.exists": set_to(False),
                # manifest removed: True -> False
                "manifest.exists": set_to(False),
                # user agent MUST remain: implicit-unchanged enforces this;
                # "my-custom-agent.md.exists" True->True is NOT in expected
            },
        )


# ---------------------------------------------------------------------------
# Tests: install() — manifest creation (converted)
# ---------------------------------------------------------------------------


class TestInstallCreatesManifest:
    """Test that install() creates a manifest tracking installed agent names."""

    def test_install_creates_manifest(self, tmp_path, monkeypatch):
        """
        GIVEN: Multiple source agent files
        WHEN: install() is called
        THEN: A .nwave-agents-manifest.json is created listing all installed agents;
              both agent .md files appear; no other .md files created as side-effects.
        """
        context, agents_source, target = _make_context(tmp_path)
        monkeypatch.setattr(
            "scripts.install.plugins.opencode_agents_plugin._opencode_agents_dir",
            lambda: target,
        )

        _create_agent(agents_source, "nw-software-crafter", _CSV_TOOLS_AGENT)
        _create_agent(agents_source, "nw-documentarist-reviewer", _ARRAY_TOOLS_AGENT)

        before = _agent_filesystem_state(target)

        plugin = OpenCodeAgentsPlugin()
        plugin.install(context)

        after = _agent_filesystem_state(target)
        universe = set(before.keys()) | set(after.keys())
        assert_state_delta(
            before=before,
            after=after,
            universe=universe,
            expected={
                "nw-software-crafter.md.exists": set_to(True),
                "nw-documentarist-reviewer.md.exists": set_to(True),
                "manifest.exists": set_to(True),
            },
        )

        manifest = json.loads((target / ".nwave-agents-manifest.json").read_text())
        assert "installed_agents" in manifest
        assert sorted(manifest["installed_agents"]) == sorted(
            ["nw-software-crafter", "nw-documentarist-reviewer"]
        )


# ---------------------------------------------------------------------------
# Tests: _transform_agent() full pipeline (converted)
# ---------------------------------------------------------------------------


class TestTransformAgentFullPipeline:
    """Test the full _transform_agent pipeline from source to OpenCode format."""

    def test_transform_agent_csv_tools(self):
        """
        GIVEN: A full agent file with CSV tools format
        WHEN: _transform_agent() is called
        THEN: Produces valid OpenCode format with all transformations applied;
              permission uses 'allow' strings including task (sub-agent invocation);
              body content is preserved unchanged.

        Merges: test_task_permission_present_in_full_agent_transform (same pipeline,
        same input, overlapping assertions unified into permission_includes_task).
        """
        before = _agent_content_state(Path("/nonexistent"), "nw-software-crafter")

        result_text = _transform_agent(_CSV_TOOLS_AGENT)

        frontmatter, body = parse_frontmatter(result_text)
        _, source_body = parse_frontmatter(_CSV_TOOLS_AGENT)

        after: dict[str, object] = {
            "content.exists": True,
            "content.has_mode": "mode:" in result_text,
            "content.has_steps": "steps:" in result_text,
            "content.has_name": "\nname:" in result_text,
            "content.has_model": "model:" in result_text,
            "content.has_skills": "skills:" in result_text,
            "content.has_maxturns": "maxTurns:" in result_text,
            "content.has_tools_key": "\ntools:" in result_text,
            "content.has_permission": "permission:" in result_text,
            "content.body_excerpt": next(
                (line for line in body.splitlines() if line.strip()), None
            ),
            "content.full": result_text,
        }

        def permission_includes_task(old: object, new: object) -> bool:
            """Permission dict uses 'allow' strings for all tools including task."""
            fm, _ = parse_frontmatter(new)  # type: ignore[arg-type]
            perm = fm.get("permission", {})
            expected_tools = {
                "read",
                "write",
                "edit",
                "bash",
                "glob",
                "grep",
                "task",
            }
            return set(perm.keys()) == expected_tools and all(
                v == "allow" for v in perm.values()
            )

        def body_preserved(old: object, new: object) -> bool:
            """Body portion is identical to source after transformation."""
            _, installed_body = parse_frontmatter(new)  # type: ignore[arg-type]
            return installed_body == source_body

        universe = set(before.keys()) | set(after.keys())
        assert_state_delta(
            before=before,
            after=after,
            universe=universe,
            expected={
                "content.exists": set_to(True),
                "content.has_mode": set_to(True),
                "content.has_steps": set_to(True),
                "content.has_name": set_to(False),
                "content.has_model": set_to(False),
                "content.has_skills": set_to(False),
                "content.has_maxturns": set_to(False),
                "content.has_tools_key": set_to(False),
                "content.has_permission": set_to(True),
                "content.full": permission_includes_task,
                # body_excerpt: None -> first body headline
                "content.body_excerpt": set_to("# nw-software-crafter"),
            },
        )

        assert body_preserved(None, result_text), (
            "Body content must be unchanged after transformation"
        )
        assert frontmatter["description"] == "DELIVER wave - Outside-In TDD"
        assert frontmatter["steps"] == 50

    def test_transform_agent_array_tools(self):
        """
        GIVEN: A full agent file with array-style tools format
        WHEN: _transform_agent() is called
        THEN: Produces valid OpenCode format with permission from array;
              steps matches maxTurns; body content is preserved.
        """
        before = _agent_content_state(Path("/nonexistent"), "nw-documentarist-reviewer")

        result_text = _transform_agent(_ARRAY_TOOLS_AGENT)

        frontmatter, body = parse_frontmatter(result_text)
        _, source_body = parse_frontmatter(_ARRAY_TOOLS_AGENT)

        after: dict[str, object] = {
            "content.exists": True,
            "content.has_mode": "mode:" in result_text,
            "content.has_steps": "steps:" in result_text,
            "content.has_name": "\nname:" in result_text,
            "content.has_model": "model:" in result_text,
            "content.has_skills": "skills:" in result_text,
            "content.has_maxturns": "maxTurns:" in result_text,
            "content.has_tools_key": "\ntools:" in result_text,
            "content.has_permission": "permission:" in result_text,
            "content.body_excerpt": next(
                (line for line in body.splitlines() if line.strip()), None
            ),
            "content.full": result_text,
        }

        def array_permission_correct(old: object, new: object) -> bool:
            """Permission dict from array tools maps to 'allow' strings."""
            fm, _ = parse_frontmatter(new)  # type: ignore[arg-type]
            perm = fm.get("permission", {})
            return perm == {"read": "allow", "glob": "allow", "grep": "allow"}

        universe = set(before.keys()) | set(after.keys())
        assert_state_delta(
            before=before,
            after=after,
            universe=universe,
            expected={
                "content.exists": set_to(True),
                "content.has_mode": set_to(True),
                "content.has_steps": set_to(True),
                "content.has_name": set_to(False),
                "content.has_model": set_to(False),
                "content.has_skills": set_to(False),
                "content.has_maxturns": set_to(False),
                "content.has_tools_key": set_to(False),
                "content.has_permission": set_to(True),
                "content.full": array_permission_correct,
                # body_excerpt: None -> first body headline
                "content.body_excerpt": set_to("# nw-documentarist-reviewer"),
            },
        )

        assert frontmatter["steps"] == 25
        assert body.strip().startswith("# nw-documentarist-reviewer")
        assert source_body == body


# ---------------------------------------------------------------------------
# Tests: OpenCode permission format (mixed: 1 converted, 1 kept)
# ---------------------------------------------------------------------------


class TestOpenCodePermissionFormat:
    """OpenCode agents must use 'permission: {tool: allow}' format, not 'tools: {tool: true}'.

    OpenCode markdown agents require the 'permission' key with string values
    ('allow', 'deny', 'ask'). The legacy 'tools' key with boolean values is
    ignored in markdown frontmatter, causing Task tool invocation to fail with
    TypeError: undefined is not an object (evaluating 'input.prompt').

    See: docs/analysis/rca-opencode-task-tool-typeerror.md
    """

    def test_parse_tools_returns_allow_strings_not_booleans(self):
        """
        GIVEN: A tools value as CSV string "Read, Write, Task"
        WHEN: _parse_tools() is called
        THEN: Returns mapping with "allow" string values, not boolean True
        """
        result = _parse_tools("Read, Write, Task")

        assert result == {"read": "allow", "write": "allow", "task": "allow"}
        for tool_name, value in result.items():
            assert isinstance(value, str), (
                f"Permission for '{tool_name}' must be string 'allow', "
                f"got {type(value).__name__}"
            )

    def test_transform_frontmatter_uses_permission_key_not_tools(self):
        """
        GIVEN: A frontmatter dict with tools: "Read, Write, Edit, Bash, Task"
        WHEN: _transform_frontmatter() is called
        THEN: Result has 'permission' key (not 'tools') with 'allow' string values;
              implicit-unchanged catches any undeclared key mutations.
        """
        frontmatter = {
            "name": "nw-software-crafter",
            "description": "DELIVER wave",
            "model": "inherit",
            "tools": "Read, Write, Edit, Bash, Task",
            "maxTurns": 50,
        }

        result = _transform_frontmatter(frontmatter)

        # State-delta on a synthetic dict derived from the pure-function output.
        before: dict[str, object] = {
            "has_permission": False,
            "has_tools": True,
            "permission_value": None,
        }
        after: dict[str, object] = {
            "has_permission": "permission" in result,
            "has_tools": "tools" in result,
            "permission_value": result.get("permission"),
        }
        universe = set(before.keys()) | set(after.keys())

        def permission_is_allow_mapping(old: object, new: object) -> bool:
            """Permission dict maps expected tools to 'allow' strings."""
            if not isinstance(new, dict):
                return False
            expected_tools = {"read", "write", "edit", "bash", "task"}
            return set(new.keys()) == expected_tools and all(
                v == "allow" for v in new.values()
            )

        assert_state_delta(
            before=before,
            after=after,
            universe=universe,
            expected={
                "has_permission": set_to(True),
                "has_tools": set_to(False),
                "permission_value": permission_is_allow_mapping,
            },
        )
