"""Architectural enforcement guard — no production caller of
``write_settings_attribution`` (AB-10, ADR-CA-007 §8 / DDD-1).

The ``settings.json attribution.{commit,pr}`` write path is RETIRED: the gated
PreToolUse hook is the sole attribution mechanism. ``write_settings_attribution``
still EXISTS this release as a soon-to-be-deleted symbol (hard-delete at N+2),
but calling it from any production path re-introduces the un-gateable surface
this feature removed. This guard fails closed if any production ``*.py`` under
``scripts/install/`` or ``nwave_ai/`` (excluding ``tests/``) contains a CALL to
``write_settings_attribution``.

Defence is structural (AST walk), not behavioural — it holds at every commit,
independent of which code path runs. Precedent for the AST-walk style:
``tests/des/unit/application/test_scope_parity.py`` (commit ae109bd8).

The guard targets CALL SITES, not imports: the symbol may remain importable
during the deprecation window (migration cleanup may keep it reachable for the
N+2 removal), but no production code may invoke it. Guard + function are removed
together at N+2.

NOTE FOR DELIVER: this guard is RED right now, by design. Two production call
sites still invoke ``write_settings_attribution`` —
``nwave_ai/cli.py::_handle_attribution`` (the ``on`` branch) and
``scripts/install/plugins/attribution_plugin.py::_do_install``. DELIVER removes
both call sites (DDD-2); this guard flips GREEN when the last one is gone.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[3]
_PRODUCTION_ROOTS = (
    _REPO_ROOT / "scripts" / "install",
    _REPO_ROOT / "nwave_ai",
)
_TARGET = "write_settings_attribution"


@dataclass(frozen=True)
class _Call:
    """A located ``write_settings_attribution(...)`` call site."""

    file: str  # path relative to repo root
    line: int
    caller: str  # enclosing function/method name


def _collect_write_settings_calls() -> list[_Call]:
    """AST-walk every production ``*.py`` and collect call sites of the target.

    A call matches when the callee resolves to ``write_settings_attribution``
    either as a bare name (``write_settings_attribution(...)``) or as an
    attribute (``module.write_settings_attribution(...)``).
    """
    calls: list[_Call] = []
    for root in _PRODUCTION_ROOTS:
        if not root.exists():
            continue
        for py_file in root.rglob("*.py"):
            if "__pycache__" in py_file.parts or "/tests/" in py_file.as_posix():
                continue
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except SyntaxError:  # pragma: no cover -- defensive
                continue

            scopes: list[tuple[int, int, str]] = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    end = getattr(node, "end_lineno", node.lineno)
                    scopes.append((node.lineno, end, node.name))

            def _enclosing(
                line: int, _scopes: list[tuple[int, int, str]] = scopes
            ) -> str:
                best = ("<module>", -1)
                for start, end, name in _scopes:
                    if start <= line <= end and start > best[1]:
                        best = (name, start)
                return best[0]

            rel = py_file.relative_to(_REPO_ROOT).as_posix()
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                is_target = (isinstance(func, ast.Name) and func.id == _TARGET) or (
                    isinstance(func, ast.Attribute) and func.attr == _TARGET
                )
                if is_target:
                    calls.append(
                        _Call(
                            file=rel, line=node.lineno, caller=_enclosing(node.lineno)
                        )
                    )
    return calls


def test_no_production_caller_of_write_settings_attribution() -> None:
    """No production ``*.py`` may CALL ``write_settings_attribution`` (DDD-1)."""
    violations = _collect_write_settings_calls()
    assert not violations, (
        "The settings.json attribution write path is RETIRED (ADR-CA-007 DDD-1): "
        "no production code may call write_settings_attribution. Offending call "
        "sites:\n"
        + "\n".join(f"  - {v.file}:{v.line} in {v.caller}()" for v in violations)
    )


def test_ast_walk_reaches_production_files() -> None:
    """Sanity: the AST walk actually parsed production files (guard not vacuous)."""
    parsed = [
        p
        for root in _PRODUCTION_ROOTS
        if root.exists()
        for p in root.rglob("*.py")
        if "__pycache__" not in p.parts
    ]
    assert parsed, (
        "AST walk found ZERO production .py files under scripts/install/ or "
        "nwave_ai/ — the walk is broken, so the guard would be vacuously green."
    )
