"""Structural Python observations from snapshot bytes, with no filesystem access."""

from __future__ import annotations

import ast
import re

from codefact import scope
from codefact.model import (
    REFERENCE_SHAPES,
    STABLE_CORE_CAPABILITY_IDS,
    Answers,
    Fault,
    Passes,
    Provider,
    Reply,
    observation_count,
)


HANDLED = STABLE_CORE_CAPABILITY_IDS | {"query.similar-responsibility"}


def parse(snapshot, path):
    content = scope.text(snapshot, path)
    try:
        return (
            ast.parse(content, filename=snapshot.absolute(path))
            if content is not None
            else None
        )
    except (SyntaxError, ValueError):
        return None


def _syntax_failed(snapshot, path, tree):
    # Legacy reads an unreadable or undecodable file as empty text, which parses.
    return tree is None and scope.text(snapshot, path) is not None


def cover(capability, request, snapshot):
    if capability.id not in HANDLED or not scope.files(snapshot, "*.py"):
        return Passes()
    subject = scope.subject(request)
    observed = {subject, subject.rsplit(".", 1)[-1]} - {""}
    other = tuple(path for path in scope.files(snapshot) if not path.endswith(".py"))
    if other and (
        not subject
        or any(
            re.search(
                rf"(?<!\w){re.escape(name)}(?!\w)", scope.text(snapshot, path) or ""
            )
            for path in other
            for name in observed
        )
    ):
        return Passes()
    return Answers("approx", REFERENCE_SHAPES)


def name(node):
    match node:
        case ast.Name(id=value):
            return value
        case ast.Attribute(value=owner, attr=attribute):
            return name(owner) + "." + attribute
        case _:
            return ""


def functions(tree):
    return tuple(
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )


def _sites(snapshot, parsed, target, calls):
    return [
        f"{snapshot.location(path)}:{node.lineno}"
        for path, tree in parsed
        if tree is not None
        for function in functions(tree)
        for nodes in (tuple(ast.walk(function)),)
        for callees in (
            frozenset(id(node.func) for node in nodes if isinstance(node, ast.Call)),
        )
        for node in nodes
        if _matches(node, target, calls, callees)
    ]


def _matches(node, target, calls, callees):
    if not target:
        return False
    if calls:
        return (
            isinstance(node, ast.Call) and name(node.func).rsplit(".", 1)[-1] == target
        )
    return (
        isinstance(node, (ast.Name, ast.Attribute))
        and isinstance(node.ctx, ast.Load)
        and id(node) not in callees
        and name(node).rsplit(".", 1)[-1] == target
    )


def answer(capability, request, snapshot):
    paths = scope.files(snapshot, "*.py")
    parsed = tuple((path, parse(snapshot, path)) for path in paths)
    faults = tuple(snapshot.location(path) for path, tree in parsed if tree is None)
    symbol = scope.subject(request)
    target = symbol.rsplit(".", 1)[-1]
    if capability.id == "query.similar-responsibility":
        from codefact.similar import rank

        result = rank(snapshot, parsed, request)
        if result is None:
            return Fault(
                "unparseable-source", len(faults), faults, scope.health(snapshot)
            )
        payload = result
    elif capability.id == "query.atoms-in-file":
        atoms = (
            tuple(
                node.name
                for _, tree in parsed
                if tree is not None
                for node in functions(tree)
            )
            + tuple(
                node.name
                for _, tree in parsed
                if tree is not None
                for node in tree.body
                if isinstance(node, ast.ClassDef)
            )
            + tuple(
                target.id
                for _, tree in parsed
                if tree is not None
                for node in tree.body
                if isinstance(node, (ast.Assign, ast.AnnAssign))
                for target in (
                    node.targets if isinstance(node, ast.Assign) else (node.target,)
                )
                if isinstance(target, ast.Name)
            )
        )
        payload = {
            "atoms": sorted(set(atoms)),
            "unparseable": bool(paths)
            and all(_syntax_failed(snapshot, path, tree) for path, tree in parsed),
        }
    elif capability.id == "query.adr-section":
        payload = {
            "anchor": symbol,
            "files": [
                path.rsplit("/", 1)[-1]
                for path in paths
                if symbol and symbol in (scope.text(snapshot, path) or "")
            ],
        }
    elif capability.id == "query.never-wired":
        calls = _sites(snapshot, parsed, target, True)
        reads = _sites(snapshot, parsed, target, False)
        payload = {
            "symbol": symbol,
            "never_wired": not (calls or reads),
            "call_sites": calls,
            "read_sites": reads,
        }
    else:
        payload = {
            "symbol": symbol,
            "sites": _sites(
                snapshot, parsed, target, capability.id == "query.callers-of"
            ),
        }
    return Reply(
        payload, observation_count(payload), len(faults), faults, scope.health(snapshot)
    )


PROVIDER = Provider("ast", cover, answer)
