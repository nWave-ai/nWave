"""Advisory name-token and arity ranking of module-level responsibilities."""

from __future__ import annotations

import ast
import re

from codefact.scope import subject


def tokens(identifier: str) -> frozenset[str]:
    return frozenset(
        part.lower()
        for part in re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", identifier).split("_")
        if part
    )


def _arity(node) -> int:
    if isinstance(node, ast.ClassDef):
        initializer = next(
            (
                child
                for child in node.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                and child.name == "__init__"
            ),
            None,
        )
        return max(0, _arity(initializer) - 1) if initializer is not None else 0
    return len(node.args.posonlyargs) + len(node.args.args) + len(node.args.kwonlyargs)


def rank(snapshot, parsed, request):
    symbols = tuple(
        (path, node)
        for path, tree in parsed
        if tree is not None
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    )
    if not symbols:
        return None
    query = subject(request)
    query_tokens = tokens(query)
    query_arity = request.get("arity")
    ranked = tuple(
        (
            len(query_tokens & tokens(node.name))
            / len(query_tokens | tokens(node.name)),
            abs(_arity(node) - query_arity) if isinstance(query_arity, int) else 0,
            {
                "symbol": node.name,
                "file": snapshot.location(path),
                "line": node.lineno,
                "overlap": len(query_tokens & tokens(node.name))
                / len(query_tokens | tokens(node.name)),
            },
        )
        for path, node in symbols
        if node.name != query and query_tokens & tokens(node.name)
    )
    return {
        "candidates": [
            item[2] for item in sorted(ranked, key=lambda item: (-item[0], item[1]))
        ],
        "unparsed_count": sum(tree is None for _, tree in parsed),
    }
