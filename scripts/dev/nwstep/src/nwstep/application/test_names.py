"""The test functions the clone's own test files define: Python `test*.py` functions read from their
source by AST, and the Rust `#[test]` functions of `.rs` files under a tests directory read by a bounded
line scan (`rust_test_names`).

A test name written in the oracle must be defined before craft, in the working tree (uncommitted is fine), so a
mapping to a misspelt or absent test is refused at record time instead of after the whole delivery.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from nwstep.domain.definitions import Definitions

PRUNED = frozenset({".git", "__pycache__", ".tmp", "node_modules", ".nwstep"})


def test_name_of(item: str) -> str:
    """The test a mapping names: the text after '=>', and the function part of a pytest node id."""
    text = item.partition("=>")[2] if "=>" in item else item
    return text.strip().rsplit("::", 1)[-1].strip()


_RUST_FN = re.compile(
    r"^(?:pub(?:\([^)]*\))?\s+)?(?:async\s+|unsafe\s+)*fn\s+([A-Za-z_][A-Za-z0-9_]*)"
)
_RUST_TEST_MARK = "#[test]"
_DECOYS = ("#[", "//")


def _unclosed(code: str) -> int:
    """How many attribute-argument delimiters the line opens without closing.

    A string literal holding a delimiter is counted as a delimiter: the scan reads lines, it does not lex Rust.
    """
    return (
        code.count("(")
        + code.count("[")
        - code.count(")")
        - code.count("]")
    )


def _code_of(line: str, depth: int) -> tuple[str, int]:
    """The code text of a line and the block-comment depth it leaves open.

    Block comments nest as in Rust and a `//` line comment hides the rest of its line. A string literal
    holding a comment marker is read as a marker: the scan reads lines, it does not lex Rust.
    """
    code: list[str] = []
    index = 0
    while index < len(line):
        if depth == 0 and line.startswith("//", index):
            break
        if line.startswith("/*", index):
            depth += 1
            index += 2
            continue
        if depth > 0 and line.startswith("*/", index):
            depth -= 1
            index += 2
            continue
        if depth == 0:
            code.append(line[index])
        index += 1
    return "".join(code), depth


def rust_test_names(source: str) -> set[str]:
    """The names of the `fn` items marked `#[test]`.

    Attributes, line comments and block comments (nested ones included) may sit between the mark and the
    function, the mark may share the function's line, and an attribute argument that continues on more
    lines keeps the mark waiting until its delimiters close; the mark does not reach past another item.
    The scan reads lines, it does not lex Rust: comment markers inside string literals shift what it
    reads, and a function sharing the line where an attribute closes is missed. A missed definition
    surfaces as a refusal naming it when a mapping writes it, never as a silent wrong success.
    """
    names: set[str] = set()
    pending = False
    depth = 0
    marks = 0
    for raw in source.splitlines():
        code, depth = _code_of(raw.strip(), depth)
        code = code.strip()
        if not code:
            continue
        if code.startswith(_RUST_TEST_MARK):
            pending = True
            code = code[len(_RUST_TEST_MARK) :].strip()
            if not code:
                continue
            if code.startswith(_DECOYS):
                marks = max(0, marks + _unclosed(code))
                continue
        elif not pending:
            continue
        if code.startswith(_DECOYS):
            marks = max(0, marks + _unclosed(code))
            continue
        marked = _RUST_FN.match(code)
        if marked is not None:
            names.add(marked.group(1))
            pending = False
            marks = 0
            continue
        if pending and marks > 0:
            marks = max(0, marks + _unclosed(code))
            continue
        marks = max(0, marks + _unclosed(code))
        if marks == 0:
            pending = False
    return names


class TestNames:
    def __init__(self, workspace_directory: Path) -> None:
        self._workspace = workspace_directory.resolve()

    def defined_in(self, root: Path) -> frozenset[str]:
        names: set[str] = set()
        for directory, subdirectories, files in os.walk(root):
            subdirectories[:] = [name for name in subdirectories if name not in PRUNED]
            for file_name in files:
                path = Path(directory, file_name)
                if self._workspace in path.resolve().parents:
                    continue
                if (
                    file_name.endswith(".rs")
                    and "tests" in Path(directory).relative_to(root).parts
                ):
                    try:
                        names |= rust_test_names(path.read_text(encoding="utf-8"))
                    except (OSError, UnicodeDecodeError):
                        continue
                    continue
                if not (file_name.startswith("test") and file_name.endswith(".py")):
                    continue
                try:
                    names |= Definitions(path.read_text(encoding="utf-8")).functions()
                except (OSError, UnicodeDecodeError, ValueError):
                    continue
        return frozenset(names)
