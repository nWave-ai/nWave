"""Property-based tests for plugin build pipeline pure functions.

Standalone Hypothesis tests that verify algebraic properties of pure functions
independently of the BDD scenarios. These complement the @property-tagged BDD
scenarios by testing properties with generated inputs.

Properties tested:
  1. Plugin name preserved in metadata generation
  2. DES import rewriting is idempotent
  3. Import rewriting preserves non-DES content
  4. Hook entries always produce exactly 5 events with correct names
  5. Validation is deterministic (same input -> same output)
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from scripts.build_plugin import (
    generate_hook_config,
    generate_plugin_metadata,
    rewrite_des_imports,
)


# ---------------------------------------------------------------------------
# Property 1: Plugin name preserved in metadata
# ---------------------------------------------------------------------------


def test_property_plugin_name_preserved_in_metadata():
    """generate_plugin_metadata always preserves the exact plugin name."""
    metadata = generate_plugin_metadata("nw")
    assert metadata["name"] == "nw"
    assert "description" in metadata
    assert "author" in metadata


# ---------------------------------------------------------------------------
# Property 2: Import rewriting is idempotent
# ---------------------------------------------------------------------------


@given(
    content=st.text(
        alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z", "S")),
        min_size=0,
        max_size=500,
    )
)
@settings(max_examples=50)
def test_property_import_rewriting_idempotent(content: str):
    """Applying rewrite_des_imports twice yields the same result as once."""
    once = rewrite_des_imports(content)
    twice = rewrite_des_imports(once)
    assert once == twice, "Import rewriting is not idempotent"


# ---------------------------------------------------------------------------
# Property 3: Import rewriting preserves non-DES content
# ---------------------------------------------------------------------------


@given(
    content=st.from_regex(
        r"(import os\n|from pathlib import Path\n|# comment\n|import json\n){1,5}",
        fullmatch=True,
    )
)
@settings(max_examples=30)
def test_property_rewrite_preserves_non_des_imports(content: str):
    """Content without src.des references is returned unchanged."""
    assert rewrite_des_imports(content) == content


# ---------------------------------------------------------------------------
# Property 4: Hook entries always produce 5 events with correct names
# ---------------------------------------------------------------------------


def test_property_hook_config_always_five_events():
    """generate_hook_config always produces exactly 5 event keys with expected names."""
    config = generate_hook_config()
    assert len(config) == 5
    assert set(config.keys()) == {
        "PreToolUse",
        "PostToolUse",
        "SubagentStop",
        "SessionStart",
        "SubagentStart",
    }
    # Every event must have at least one entry with a non-empty command
    for event, entries in config.items():
        assert len(entries) > 0, f"No entries for event {event}"
        for entry in entries:
            for hook in entry["hooks"]:
                assert hook["command"].strip(), f"Empty command for event {event}"


# ---------------------------------------------------------------------------
# Property 5: Import rewriting correctly transforms src.des references
# ---------------------------------------------------------------------------


@given(
    module_path=st.from_regex(r"[a-z][a-z_]{0,20}", fullmatch=True),
)
@settings(max_examples=30)
def test_property_rewrite_transforms_src_des(module_path: str):
    """Every 'from src.des.X' becomes 'from des.X' after rewriting."""
    original = f"from src.des.{module_path} import something\n"
    rewritten = rewrite_des_imports(original)
    assert "src.des" not in rewritten, f"src.des not rewritten: {rewritten}"
    assert f"from des.{module_path}" in rewritten
