"""Which files a Python file depends on: the first dependency adapter.

Pure and standard library only (``ast``). A dependency is every project file that
running this file can load or start:

* an import, absolute or relative, at any depth of the file (the packages on the way
  included, since importing ``a.b`` runs ``a/__init__.py``);
* a module named in a string: ``importlib.import_module("a.b")``, a patch target
  ``"a.b.Thing"``;
* a module another process is started with: ``[sys.executable, "-m", "a"]`` reaches
  ``a/__main__.py``;
* a project file named by its path, as text or built with ``/``:
  ``"scripts/tool.py"``, ``ROOT / "scripts" / "tool.py"``;
* each file the project declares ``implicit`` (for example ``conftest.py``) in the
  file's own directory or above it: files the runner loads without being named.

Settings (``selection.python`` in the declaration): ``import_roots``, the directories
modules are imported from, default the project root; ``implicit``, default none.

Not seen, by construction: a module name or path assembled at run time.
"""

from __future__ import annotations

import ast
import posixpath
import re
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping


# What a path, a module name or the ``-m`` switch can be made of, inside any text.
_WORD = re.compile(r"[A-Za-z0-9_./-]+")

# The settings of this adapter and what each one is when it is not declared.
_DEFAULTS: Mapping[str, tuple[str, ...]] = {"import_roots": (".",), "implicit": ()}


def _is_names(value: object) -> bool:
    return isinstance(value, (list, tuple)) and all(
        isinstance(item, str) and item for item in value
    )


def setting_defects(settings: Mapping[str, object]) -> tuple[str, ...]:
    """Every setting this adapter does not know or cannot use."""
    known = ", ".join(_DEFAULTS)
    return (
        *(
            f"{key} is not a known setting (known: {known})"
            for key in settings
            if key not in _DEFAULTS
        ),
        *(
            f"{key} must be a list of names, got {settings[key]!r}"
            for key in _DEFAULTS
            if key in settings and not _is_names(settings[key])
        ),
    )


def _strings(settings: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = settings.get(key)
    return tuple(value) if _is_names(value) else _DEFAULTS[key]


def _module_file(
    dotted: str, roots: tuple[str, ...], files: frozenset[str]
) -> str | None:
    stem = dotted.replace(".", "/")
    for root in roots:
        base = "" if root in (".", "") else root.rstrip("/") + "/"
        for candidate in (f"{base}{stem}.py", f"{base}{stem}/__init__.py"):
            if candidate in files:
                return candidate
    return None


def _module_files(
    dotted: str, roots: tuple[str, ...], files: frozenset[str]
) -> Iterator[str]:
    """The file of a module and of every package on the way to it."""
    parts = dotted.split(".")
    for end in range(1, len(parts) + 1):
        found = _module_file(".".join(parts[:end]), roots, files)
        if found is not None:
            yield found


def _launched(
    dotted: str, roots: tuple[str, ...], files: frozenset[str]
) -> Iterator[str]:
    """What ``python -m dotted`` runs: the module, and a package's ``__main__``."""
    yield from _module_files(dotted, roots, files)
    main = _module_file(f"{dotted}.__main__", roots, files)
    if main is not None:
        yield main


def _package_of(path: str, roots: tuple[str, ...]) -> list[str]:
    """The dotted package a file lives in, as its parts."""
    directory = posixpath.dirname(path)
    for root in sorted(roots, key=len, reverse=True):
        if root in (".", ""):
            continue
        root = root.rstrip("/")
        if directory == root:
            return []
        if directory.startswith(root + "/"):
            return directory[len(root) + 1 :].split("/")
    return directory.split("/") if directory else []


def _named_module(
    word: str, roots: tuple[str, ...], files: frozenset[str]
) -> str | None:
    """The longest dotted prefix of ``word`` that is a project module, if any."""
    parts = word.split(".")
    if len(parts) < 2 or not all(part.isidentifier() for part in parts):
        return None
    for end in range(len(parts), 1, -1):
        dotted = ".".join(parts[:end])
        if _module_file(dotted, roots, files) is not None:
            return dotted
    return None


def _path_words(node: ast.AST) -> list[str] | None:
    """The text operands of a path built with ``/``, left to right."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        right = node.right
        if isinstance(right, ast.Constant) and isinstance(right.value, str):
            return [*(_path_words(node.left) or []), right.value]
    return None


def _docstrings(tree: ast.Module) -> set[int]:
    """The string nodes that are prose about the code, not names in it."""
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            found.add(id(node.value))
    return found


def _imports(
    node: ast.AST, package: list[str], roots: tuple[str, ...], files: frozenset[str]
) -> Iterator[str]:
    if isinstance(node, ast.Import):
        for alias in node.names:
            yield from _module_files(alias.name, roots, files)
    elif isinstance(node, ast.ImportFrom):
        keep = len(package) - (node.level - 1)
        if node.level and keep < 0:
            return
        parts = [
            *(package[:keep] if node.level else []),
            *(node.module.split(".") if node.module else []),
        ]
        base = ".".join(parts)
        if base:
            yield from _module_files(base, roots, files)
        for alias in node.names:
            if alias.name != "*":
                yield from _module_files(
                    f"{base}.{alias.name}" if base else alias.name, roots, files
                )


def _named_by_text(
    text: str, directory: str, roots: tuple[str, ...], files: frozenset[str]
) -> Iterator[str]:
    """Project files a piece of text names: a path, a module, ``-m module``.

    The text may be one word or a whole program given to another interpreter.
    """
    words = _WORD.findall(text)
    for position, found in enumerate(words):
        word = found.rstrip(".")
        if position and words[position - 1] == "-m":
            yield from _launched(word, roots, files)
        beside = posixpath.join(directory, word)
        if "/" not in word and "." not in word:
            yield from (path for path in (word, beside) if path in files)
            continue
        for candidate in (posixpath.normpath(word), posixpath.normpath(beside)):
            if candidate in files:
                yield candidate
        module = _named_module(word, roots, files)
        if module is not None:
            yield from _module_files(module, roots, files)


def _implicit(
    path: str, names: tuple[str, ...], files: frozenset[str]
) -> Iterator[str]:
    directory = posixpath.dirname(path)
    while True:
        for name in names:
            candidate = posixpath.join(directory, name) if directory else name
            if candidate in files and candidate != path:
                yield candidate
        if not directory:
            return
        directory = posixpath.dirname(directory)


def dependencies(
    path: str, text: str, files: frozenset[str], settings: Mapping[str, object]
) -> frozenset[str] | None:
    """The project files ``path`` depends on; ``None`` when it does not parse."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError):
        return None
    roots = _strings(settings, "import_roots")
    package = _package_of(path, roots)
    directory = posixpath.dirname(path)
    prose = _docstrings(tree)
    found = set(_implicit(path, _strings(settings, "implicit"), files))
    for node in ast.walk(tree):
        found.update(_imports(node, package, roots, files))
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) not in prose:
                found.update(_named_by_text(node.value, directory, roots, files))
        elif isinstance(node, (ast.List, ast.Tuple)):
            words = [
                item.value
                for item in node.elts
                if isinstance(item, ast.Constant) and isinstance(item.value, str)
            ]
            found.update(_named_by_text(" ".join(words), directory, roots, files))
        else:
            joined = _path_words(node)
            if joined:
                found.update(_named_by_text("/".join(joined), directory, roots, files))
    found.discard(path)
    return frozenset(found)


def may_reference(
    path: str, text: str, target: str, settings: Mapping[str, object]
) -> bool:
    """False only when ``path`` cannot depend on ``target``.

    Every dependency above names its target by the target's own name; a package
    file or a ``__main__`` by the name of its directory; an implicit file is
    reached from the directory it is in and from those below it.
    """
    name = posixpath.basename(target)
    directory = posixpath.dirname(target)
    inside = not directory or path.startswith(directory + "/")
    if inside and name in _strings(settings, "implicit"):
        return True
    if name in ("__init__.py", "__main__.py"):
        return inside or posixpath.basename(directory) in text
    return (name[:-3] if name.endswith(".py") else name) in text
