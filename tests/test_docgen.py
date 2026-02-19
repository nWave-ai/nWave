"""Tests for nwave-docgen: deterministic documentation generator."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from scripts.docgen import (
    DocgenError,
    _infer_wave,
    check_pages,
    enrich,
    extract_agent,
    extract_all,
    extract_command,
    extract_skill,
    extract_template,
    parse_front_matter,
    render,
    run_pipeline,
    write_pages,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def nwave_tree(tmp_path: Path) -> Path:
    """Create a minimal nWave file tree for integration tests."""
    nw = tmp_path / "nWave"

    # Agent
    agents = nw / "agents"
    agents.mkdir(parents=True)
    (agents / "nw-crafter.md").write_text(
        textwrap.dedent("""\
        ---
        name: nw-crafter
        description: A test crafter agent
        model: sonnet
        tools: Read, Write, Edit
        maxTurns: 30
        skills:
          - tdd
          - refactoring
        ---
        # Body content
    """)
    )

    # Command
    cmds = nw / "tasks" / "nw"
    cmds.mkdir(parents=True)
    (cmds / "deliver.md").write_text(
        textwrap.dedent("""\
        ---
        description: "Execute the DELIVER wave"
        argument-hint: '[feature] - Example: "Add auth"'
        ---
        # Body
        Use nw-crafter to implement.
    """)
    )

    # Skills
    skill_dir = nw / "skills" / "crafter"
    skill_dir.mkdir(parents=True)
    (skill_dir / "tdd.md").write_text(
        textwrap.dedent("""\
        ---
        name: tdd
        description: TDD methodology knowledge
        ---
        # TDD
    """)
    )
    (skill_dir / "refactoring.md").write_text(
        textwrap.dedent("""\
        ---
        name: refactoring
        description: Progressive refactoring patterns
        ---
        # Refactoring
    """)
    )

    # Template
    templates = nw / "templates"
    templates.mkdir(parents=True)
    (templates / "deliver-tdd.yaml").write_text(
        textwrap.dedent("""\
        ---
        template_type: "deliver-tdd"
        description: "TDD template for DELIVER wave"
        version: "1.0.0"
        ---
    """)
    )

    return tmp_path


# ---------------------------------------------------------------------------
# parse_front_matter
# ---------------------------------------------------------------------------
class TestParseFrontMatter:
    def test_scalar_values(self, tmp_path: Path):
        f = tmp_path / "test.md"
        f.write_text("---\nname: foo\ndescription: bar baz\n---\n# Body")
        result = parse_front_matter(f)
        assert result == {"name": "foo", "description": "bar baz"}

    def test_list_values(self, tmp_path: Path):
        f = tmp_path / "test.md"
        f.write_text("---\nname: agent\nskills:\n  - alpha\n  - beta\n---\n")
        result = parse_front_matter(f)
        assert result["skills"] == ["alpha", "beta"]

    def test_quoted_values(self, tmp_path: Path):
        f = tmp_path / "test.md"
        f.write_text('---\ndescription: "A quoted value"\n---\n')
        result = parse_front_matter(f)
        assert result["description"] == "A quoted value"

    def test_missing_front_matter_raises(self, tmp_path: Path):
        f = tmp_path / "test.md"
        f.write_text("# No front matter here")
        with pytest.raises(DocgenError, match="Missing YAML front-matter"):
            parse_front_matter(f)


# ---------------------------------------------------------------------------
# Extract
# ---------------------------------------------------------------------------
class TestExtract:
    def test_extract_agent(self, nwave_tree: Path):
        path = nwave_tree / "nWave" / "agents" / "nw-crafter.md"
        agent = extract_agent(path)
        assert agent["name"] == "nw-crafter"
        assert agent["model"] == "sonnet"
        assert agent["tools"] == ["Read", "Write", "Edit"]
        assert agent["max_turns"] == 30
        assert agent["skills"] == ["tdd", "refactoring"]

    def test_extract_command(self, nwave_tree: Path):
        path = nwave_tree / "nWave" / "tasks" / "nw" / "deliver.md"
        cmd = extract_command(path)
        assert cmd["name"] == "deliver"
        assert "DELIVER" in cmd["description"]

    def test_extract_skill(self, nwave_tree: Path):
        path = nwave_tree / "nWave" / "skills" / "crafter" / "tdd.md"
        skill = extract_skill(path)
        assert skill["name"] == "tdd"
        assert skill["agent_dir"] == "crafter"

    def test_extract_template(self, nwave_tree: Path):
        path = nwave_tree / "nWave" / "templates" / "deliver-tdd.yaml"
        tmpl = extract_template(path)
        assert tmpl["name"] == "deliver-tdd"
        assert tmpl["type"] == "deliver-tdd"
        assert tmpl["version"] == "1.0.0"

    def test_missing_required_field_raises(self, tmp_path: Path):
        f = tmp_path / "bad.md"
        f.write_text("---\nfoo: bar\n---\n")
        with pytest.raises(DocgenError, match="Missing required fields"):
            extract_agent(f)


# ---------------------------------------------------------------------------
# Enrich
# ---------------------------------------------------------------------------
class TestEnrich:
    def test_valid_cross_refs(self, nwave_tree: Path):
        paths = {
            "agents": list((nwave_tree / "nWave" / "agents").glob("*.md")),
            "commands": list((nwave_tree / "nWave" / "tasks" / "nw").glob("*.md")),
            "skills": list((nwave_tree / "nWave" / "skills").rglob("*.md")),
            "templates": list((nwave_tree / "nWave" / "templates").glob("*.yaml")),
        }
        data = extract_all(paths)
        enriched = enrich(data)
        assert len(enriched["agents"]) == 1

    def test_broken_agent_skill_ref_raises(self):
        data = {
            "agents": [
                {
                    "name": "nw-test",
                    "skills": ["nonexistent"],
                    "tools": [],
                    "description": "",
                    "model": "",
                    "max_turns": 0,
                    "source_path": "",
                }
            ],
            "commands": [],
            "skills": [],
            "templates": [],
        }
        with pytest.raises(DocgenError, match="references skill 'nonexistent'"):
            enrich(data)

    def test_orphan_skill_raises(self):
        data = {
            "agents": [
                {
                    "name": "nw-test",
                    "skills": [],
                    "tools": [],
                    "description": "",
                    "model": "",
                    "max_turns": 0,
                    "source_path": "",
                }
            ],
            "commands": [],
            "skills": [
                {
                    "name": "orphan",
                    "description": "",
                    "agent_dir": "no-such-agent",
                    "source_path": "",
                }
            ],
            "templates": [],
        }
        with pytest.raises(DocgenError, match="no matching agent"):
            enrich(data)


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
class TestRender:
    def test_render_produces_all_pages(self, nwave_tree: Path):
        paths = {
            "agents": list((nwave_tree / "nWave" / "agents").glob("*.md")),
            "commands": list((nwave_tree / "nWave" / "tasks" / "nw").glob("*.md")),
            "skills": list((nwave_tree / "nWave" / "skills").rglob("*.md")),
            "templates": list((nwave_tree / "nWave" / "templates").glob("*.yaml")),
        }
        data = enrich(extract_all(paths))
        pages = render(data)

        assert "index.md" in pages
        assert "agents/index.md" in pages
        assert "commands/index.md" in pages
        assert "skills/index.md" in pages
        assert "templates/index.md" in pages
        assert "agents/nw-crafter.md" in pages

    def test_master_index_has_counts(self, nwave_tree: Path):
        paths = {
            "agents": list((nwave_tree / "nWave" / "agents").glob("*.md")),
            "commands": list((nwave_tree / "nWave" / "tasks" / "nw").glob("*.md")),
            "skills": list((nwave_tree / "nWave" / "skills").rglob("*.md")),
            "templates": list((nwave_tree / "nWave" / "templates").glob("*.yaml")),
        }
        data = enrich(extract_all(paths))
        index = render(data)["index.md"]
        assert "1 agents" in index
        assert "1 commands" in index
        assert "2 skills" in index

    def test_agent_detail_lists_skills(self, nwave_tree: Path):
        paths = {
            "agents": list((nwave_tree / "nWave" / "agents").glob("*.md")),
            "commands": list((nwave_tree / "nWave" / "tasks" / "nw").glob("*.md")),
            "skills": list((nwave_tree / "nWave" / "skills").rglob("*.md")),
            "templates": list((nwave_tree / "nWave" / "templates").glob("*.yaml")),
        }
        data = enrich(extract_all(paths))
        page = render(data)["agents/nw-crafter.md"]
        assert "tdd" in page
        assert "refactoring" in page


# ---------------------------------------------------------------------------
# Write + Check
# ---------------------------------------------------------------------------
class TestWriteAndCheck:
    def test_write_then_check_passes(self, nwave_tree: Path, tmp_path: Path):
        output_dir = tmp_path / "output"
        pages = run_pipeline(nwave_tree, output_dir)
        write_pages(pages, output_dir)
        assert check_pages(pages, output_dir) == []

    def test_check_detects_missing(self, tmp_path: Path):
        pages = {"missing.md": "content"}
        stale = check_pages(pages, tmp_path)
        assert len(stale) == 1
        assert "missing" in stale[0]

    def test_check_detects_stale(self, tmp_path: Path):
        out = tmp_path / "file.md"
        out.write_text("old content")
        stale = check_pages({"file.md": "new content"}, tmp_path)
        assert len(stale) == 1
        assert "stale" in stale[0]


# ---------------------------------------------------------------------------
# Fix 1: Skill links in agent detail
# ---------------------------------------------------------------------------
class TestSkillLinks:
    def test_agent_detail_links_skills_to_source(self, nwave_tree: Path):
        paths = {
            "agents": list((nwave_tree / "nWave" / "agents").glob("*.md")),
            "commands": list((nwave_tree / "nWave" / "tasks" / "nw").glob("*.md")),
            "skills": list((nwave_tree / "nWave" / "skills").rglob("*.md")),
            "templates": list((nwave_tree / "nWave" / "templates").glob("*.yaml")),
        }
        data = enrich(extract_all(paths))
        page = render(data)["agents/nw-crafter.md"]
        # Skills should be linked, not plain text
        assert "[tdd](../../../nWave/skills/crafter/tdd.md)" in page
        assert "[refactoring](../../../nWave/skills/crafter/refactoring.md)" in page


# ---------------------------------------------------------------------------
# Fix 2: Wave grouping in agents index
# ---------------------------------------------------------------------------
class TestWaveGrouping:
    @pytest.mark.parametrize(
        "description,expected_wave",
        [
            ("Handles DISCOVER wave tasks", "DISCOVER"),
            ("Use for DISCUSS wave planning", "DISCUSS"),
            ("Runs before DESIGN wave", "DESIGN"),
            ("DISTILL wave acceptance tests", "DISTILL"),
            ("DELIVER wave implementation", "DELIVER"),
            ("DEVOP wave deployment", "DEVOP"),
            ("A utility agent", "Other"),
        ],
    )
    def test_infer_wave(self, description: str, expected_wave: str):
        assert _infer_wave(description) == expected_wave

    def test_agents_index_has_wave_sections(self, nwave_tree: Path):
        paths = {
            "agents": list((nwave_tree / "nWave" / "agents").glob("*.md")),
            "commands": list((nwave_tree / "nWave" / "tasks" / "nw").glob("*.md")),
            "skills": list((nwave_tree / "nWave" / "skills").rglob("*.md")),
            "templates": list((nwave_tree / "nWave" / "templates").glob("*.yaml")),
        }
        data = enrich(extract_all(paths))
        page = render(data)["agents/index.md"]
        # nw-crafter has no wave keyword -> Other
        assert "## Other" in page
        assert "## All Agents" in page

    def test_agent_detail_shows_wave(self, nwave_tree: Path):
        paths = {
            "agents": list((nwave_tree / "nWave" / "agents").glob("*.md")),
            "commands": list((nwave_tree / "nWave" / "tasks" / "nw").glob("*.md")),
            "skills": list((nwave_tree / "nWave" / "skills").rglob("*.md")),
            "templates": list((nwave_tree / "nWave" / "templates").glob("*.yaml")),
        }
        data = enrich(extract_all(paths))
        page = render(data)["agents/nw-crafter.md"]
        assert "**Wave:** Other" in page


# ---------------------------------------------------------------------------
# Fix 3: Bidirectional command<->agent cross-references
# ---------------------------------------------------------------------------
class TestCommandAgentCrossRefs:
    def test_extract_command_finds_agent_refs(self, nwave_tree: Path):
        path = nwave_tree / "nWave" / "tasks" / "nw" / "deliver.md"
        cmd = extract_command(path)
        assert "nw-crafter" in cmd["agents"]

    def test_enrich_populates_agent_commands(self, nwave_tree: Path):
        paths = {
            "agents": list((nwave_tree / "nWave" / "agents").glob("*.md")),
            "commands": list((nwave_tree / "nWave" / "tasks" / "nw").glob("*.md")),
            "skills": list((nwave_tree / "nWave" / "skills").rglob("*.md")),
            "templates": list((nwave_tree / "nWave" / "templates").glob("*.yaml")),
        }
        data = enrich(extract_all(paths))
        agent = data["agents"][0]
        assert "deliver" in agent["commands"]

    def test_commands_index_has_agents_column(self, nwave_tree: Path):
        paths = {
            "agents": list((nwave_tree / "nWave" / "agents").glob("*.md")),
            "commands": list((nwave_tree / "nWave" / "tasks" / "nw").glob("*.md")),
            "skills": list((nwave_tree / "nWave" / "skills").rglob("*.md")),
            "templates": list((nwave_tree / "nWave" / "templates").glob("*.yaml")),
        }
        data = enrich(extract_all(paths))
        page = render(data)["commands/index.md"]
        assert "Agents" in page
        assert "[nw-crafter](../agents/nw-crafter.md)" in page

    def test_agent_detail_has_commands_section(self, nwave_tree: Path):
        paths = {
            "agents": list((nwave_tree / "nWave" / "agents").glob("*.md")),
            "commands": list((nwave_tree / "nWave" / "tasks" / "nw").glob("*.md")),
            "skills": list((nwave_tree / "nWave" / "skills").rglob("*.md")),
            "templates": list((nwave_tree / "nWave" / "templates").glob("*.yaml")),
        }
        data = enrich(extract_all(paths))
        page = render(data)["agents/nw-crafter.md"]
        assert "## Commands" in page
        assert "`/nw:deliver`" in page


# ---------------------------------------------------------------------------
# Integration: full pipeline on real nWave tree
# ---------------------------------------------------------------------------
class TestIntegration:
    """Run against the actual nWave directory if available."""

    @pytest.fixture
    def real_root(self) -> Path:
        root = Path(__file__).resolve().parent.parent
        if not (root / "nWave" / "agents").exists():
            pytest.skip("nWave directory not found")
        return root

    def test_full_pipeline_succeeds(self, real_root: Path):
        pages = run_pipeline(real_root, real_root / "docs" / "generated")
        assert len(pages) > 5

    def test_artifact_counts_match_source(self, real_root: Path):
        from scripts.docgen import scan

        paths = scan(real_root)
        pages = run_pipeline(real_root, real_root / "docs" / "generated")
        index = pages["index.md"]
        assert f"{len(paths['agents'])} agents" in index
        assert f"{len(paths['commands'])} commands" in index
        assert f"{len(paths['skills'])} skills" in index

    def test_all_agents_have_detail_pages(self, real_root: Path):
        from scripts.docgen import scan

        paths = scan(real_root)
        pages = run_pipeline(real_root, real_root / "docs" / "generated")
        agent_pages = [
            k for k in pages if k.startswith("agents/") and k != "agents/index.md"
        ]
        assert len(agent_pages) == len(paths["agents"])

    def test_cross_links_valid(self, real_root: Path):
        """Pipeline completes without DocgenError means all cross-refs are valid."""
        pages = run_pipeline(real_root, real_root / "docs" / "generated")
        assert pages  # No DocgenError raised
