"""What a Python source defines (by AST, never by text search), and its assert messages that look interpolated but are not f-strings."""

from __future__ import annotations

import ast
import re


class Definitions:
    _PLACEHOLDER = re.compile(r"\{[A-Za-z_][\w.]*(?:![rsa])?(?::[^{}]*)?\}")

    def __init__(self, source: str) -> None:
        try:
            self._tree = ast.parse(source)
        except SyntaxError as error:
            raise ValueError(f"the source does not parse: {error.msg}") from None

    def names(self) -> frozenset[str]:
        """Every function and class name in the source, at any depth."""
        return frozenset(
            node.name
            for node in ast.walk(self._tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        )

    def functions(self) -> frozenset[str]:
        return frozenset(
            node.name
            for node in ast.walk(self._tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        )

    def property_functions(self) -> frozenset[str]:
        """Functions decorated with given (hypothesis's @given, bare or as an attribute): their inputs are generated."""
        return frozenset(
            node.name
            for node in ast.walk(self._tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and any(self._is_given(decorator) for decorator in node.decorator_list)
        )

    @staticmethod
    def _is_given(decorator: ast.expr) -> bool:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(target, ast.Name):
            return target.id == "given"
        return isinstance(target, ast.Attribute) and target.attr == "given"

    def placeholder_asserts(self) -> tuple[tuple[int, str], ...]:
        """Assert messages that are plain string literals holding a {name} replacement field."""
        found: list[tuple[int, str]] = []
        for node in ast.walk(self._tree):
            if not isinstance(node, ast.Assert) or node.msg is None:
                continue
            message = node.msg
            if isinstance(message, ast.Constant) and isinstance(message.value, str):
                if self._PLACEHOLDER.search(message.value):
                    found.append((node.lineno, message.value))
        return tuple(sorted(found))
