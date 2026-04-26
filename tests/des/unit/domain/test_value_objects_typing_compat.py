"""Regression tests for Python 3.10 compatibility of typing.Self imports.

Issue #43 — `typing.Self` was added in Python 3.11 (PEP 673). Importing it
unconditionally in `value_objects.py` breaks DES on Python 3.10, which is
the documented `requires-python` floor.

These tests are AST-based so they catch the regression statically on any
interpreter (the CI matrix runs 3.11+ today; the static check still works).
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest


MODULE_PATH = (
    Path(__file__).resolve().parents[4] / "src" / "des" / "domain" / "value_objects.py"
)


def _module_ast() -> ast.Module:
    """Parse the value_objects.py module into an AST."""
    source = MODULE_PATH.read_text(encoding="utf-8")
    return ast.parse(source, filename=str(MODULE_PATH))


def _top_level_import_froms(tree: ast.Module) -> list[ast.ImportFrom]:
    """Collect ImportFrom nodes that live directly at module top level
    (i.e. NOT nested inside try/except/if/function/class blocks).
    """
    return [node for node in tree.body if isinstance(node, ast.ImportFrom)]


def _find_module_level_try_blocks(tree: ast.Module) -> list[ast.Try]:
    """Collect Try blocks that live directly at module top level."""
    return [node for node in tree.body if isinstance(node, ast.Try)]


class TestValueObjectsTypingCompat:
    """AST-based regression tests for the typing.Self conditional import."""

    def test_no_bare_typing_self_import(self) -> None:
        """Top-level `from typing import ...` MUST NOT include Self.

        A bare top-level import of `Self` from `typing` breaks Python 3.10.
        The fix wraps the import in a try/except ImportError block, which
        is NOT a top-level ImportFrom (it lives inside a Try node).
        """
        tree = _module_ast()
        bare_imports = _top_level_import_froms(tree)

        offending = [
            node
            for node in bare_imports
            if node.module == "typing"
            and any(alias.name == "Self" for alias in node.names)
        ]

        assert offending == [], (
            "value_objects.py contains a bare top-level "
            "`from typing import Self` — this fails on Python 3.10. "
            "Wrap the import in a try/except ImportError block with a "
            "typing_extensions fallback."
        )

    def test_conditional_typing_self_import_present(self) -> None:
        """A top-level try/except block MUST import Self from both typing
        (try branch) and typing_extensions (except ImportError handler).
        """
        tree = _module_ast()
        try_blocks = _find_module_level_try_blocks(tree)

        def _imports_self_from(block_body: list[ast.stmt], module: str) -> bool:
            for stmt in block_body:
                if (
                    isinstance(stmt, ast.ImportFrom)
                    and stmt.module == module
                    and any(alias.name == "Self" for alias in stmt.names)
                ):
                    return True
            return False

        matching = [
            try_node
            for try_node in try_blocks
            if _imports_self_from(try_node.body, "typing")
            and any(
                isinstance(handler.type, ast.Name)
                and handler.type.id == "ImportError"
                and _imports_self_from(handler.body, "typing_extensions")
                for handler in try_node.handlers
            )
        ]

        assert matching, (
            "value_objects.py must contain a top-level "
            "`try: from typing import Self / except ImportError: "
            "from typing_extensions import Self` block to remain "
            "compatible with Python 3.10."
        )

    def test_module_imports_successfully(self) -> None:
        """Importing the module on the running interpreter must succeed
        and `Self` must be a resolvable attribute on the module.
        """
        try:
            module = importlib.import_module("des.domain.value_objects")
        except ImportError as exc:  # pragma: no cover — diagnostic path
            pytest.fail(f"Failed to import des.domain.value_objects: {exc}")

        assert hasattr(module, "Self"), (
            "des.domain.value_objects does not expose `Self` — the "
            "conditional import block must bind the name at module scope."
        )
