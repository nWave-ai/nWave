"""Read-only impact observations over an immutable source snapshot."""

from __future__ import annotations

import ast
import fnmatch
import hashlib
import json
import posixpath
import re
from dataclasses import asdict, dataclass
from itertools import chain, pairwise
from typing import TYPE_CHECKING

from codefact import index, scope
from codefact.index_layout import LAYOUT
from codefact.model import Coverage, LiveSource, Snapshot
from codefact.selection import (
    ContentHoldings,
    Judgment,
    JudgmentTable,
    Missing,
    MissingKind,
    ReachView,
    Selected,
    select,
)


if TYPE_CHECKING:
    from collections.abc import Mapping

JUDGMENT_TABLE_PATH = "tests/dynamic-reach-judgments.json"
_DEFAULT_NORECURSEDIRS = (
    "*.egg",
    ".*",
    "_darcs",
    "build",
    "CVS",
    "dist",
    "node_modules",
    "venv",
    "{arch}",
)
_DISPATCH_MODULES = frozenset({"nwave_ai.cli"})
_COMMAND_PREFIXES = _DISPATCH_MODULES | {"nwave-ai"}


def _ancestry(path: str):
    while path:
        yield path
        path = path.rpartition("/")[0]


@dataclass(frozen=True)
class _PytestSettings:
    testpaths: tuple[str, ...]
    python_files: tuple[str, ...]
    import_roots: tuple[str, ...]
    norecursedirs: tuple[str, ...] = _DEFAULT_NORECURSEDIRS

    def in_test_tree(self, path: str) -> bool:
        return any(
            entry in (".", path)
            or path.startswith(entry + "/")
            or fnmatch.fnmatchcase(path, entry + "/*")
            for entry in self.testpaths
        )

    def is_test_file(self, path: str) -> bool:
        return any(
            fnmatch.fnmatchcase(
                path if "/" in pattern else path.rpartition("/")[2], pattern
            )
            for pattern in self.python_files
        )

    def prunes(self, directory: str) -> bool:
        return any(
            fnmatch.fnmatchcase(
                directory if "/" in pattern else directory.rpartition("/")[2], pattern
            )
            for pattern in self.norecursedirs
        )

    def is_content_root(self, path: str) -> bool:
        return path in self.import_roots or path in self.testpaths

    def is_beneath_source_root(self, path: str) -> bool:
        return any(
            path.startswith(root + "/") for root in self.import_roots if root != "."
        )


def pytest_settings(pyproject_text: str) -> _PytestSettings:
    lines = pyproject_text.splitlines()
    section = ""
    for start, line in enumerate(lines):
        if re.match(r"^\s*\[tool\.pytest\.ini_options\]\s*(?:#.*)?$", line):
            end = start + 1
            while end < len(lines) and not re.match(r"^\s*\[", lines[end]):
                end += 1
            section = "\n".join(lines[start + 1 : end])
            break

    def strings(key: str, default: tuple[str, ...]) -> tuple[str, ...]:
        found = re.search(
            rf"""^\s*{key}\s*=\s*(?P<value>\[[^\]]*\]|"[^"\n]*"|'[^'\n]*')""",
            section,
            re.MULTILINE,
        )
        if found is None:
            return default
        value = re.sub(r"#[^\n]*", "", found.group("value"))
        quoted = re.findall(r"""["']([^"']*)["']""", value)
        words = (
            tuple(quoted)
            if value.startswith("[")
            else tuple(quoted[0].split())
            if quoted
            else ()
        )
        return words or default

    return _PytestSettings(
        tuple(map(posixpath.normpath, strings("testpaths", (".",)))),
        strings("python_files", ("test_*.py", "*_test.py")),
        tuple(map(posixpath.normpath, strings("pythonpath", ("src", ".")))),
        strings("norecursedirs", _DEFAULT_NORECURSEDIRS),
    )


@dataclass(frozen=True)
class _Syntax:
    nodes: tuple[ast.AST, ...]
    runtime: tuple[ast.AST, ...]
    calls: tuple[ast.Call, ...]
    plugins: tuple[str, ...]


def _observe(tree: ast.Module, *, full: bool = True) -> _Syntax:
    plugin_values = (
        {
            id(node.value)
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "pytest_plugins"
                for target in node.targets
            )
        }
        if full
        else set()
    )
    nodes, runtime, calls, plugins = [], [], [], []
    pending = [(tree, True, False)]
    while pending:
        node, runs, plugin = pending.pop()
        if full:
            plugin = plugin or id(node) in plugin_values
            if (
                isinstance(
                    node,
                    (
                        ast.Import,
                        ast.ImportFrom,
                        ast.List,
                        ast.Tuple,
                        ast.Call,
                        ast.BinOp,
                    ),
                )
                or (isinstance(node, ast.Constant) and isinstance(node.value, str))
                or (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant))
            ):
                nodes.append(node)
            if isinstance(node, ast.Call):
                calls.append(node)
            if (
                plugin
                and isinstance(node, ast.Constant)
                and isinstance(node.value, str)
            ):
                plugins.append(node.value)
        if runs and isinstance(node, (ast.Import, ast.ImportFrom, ast.Attribute)):
            runtime.append(node)
        guarded = isinstance(node, ast.If) and (
            (isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING")
            or (
                isinstance(node.test, ast.Attribute)
                and node.test.attr == "TYPE_CHECKING"
            )
        )
        for name in node._fields:
            child_runs = runs and (not guarded or name == "orelse")
            if not full and not child_runs:
                continue
            value = getattr(node, name, None)
            if isinstance(value, list):
                for child in value:
                    if isinstance(child, ast.AST):
                        pending.append((child, child_runs, plugin))
            elif isinstance(value, ast.AST):
                pending.append((value, child_runs, plugin))
    return _Syntax(tuple(nodes), tuple(runtime), tuple(calls), tuple(plugins))


def _string_of(node: ast.AST | None) -> str | None:
    return (
        node.value
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
        else None
    )


def _call_name(node: ast.Call) -> str | None:
    return (
        node.func.id
        if isinstance(node.func, ast.Name)
        else node.func.attr
        if isinstance(node.func, ast.Attribute)
        else None
    )


def _owner_name(node: ast.Call) -> str | None:
    return (
        node.func.value.id
        if isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        else None
    )


@dataclass(frozen=True)
class _ImportResolver:
    known: frozenset[str]
    import_roots: tuple[str, ...]
    lazy: Mapping[str, Mapping[str, str]]

    def module_file(self, dotted: str) -> str | None:
        stem = dotted.replace(".", "/")
        return next(
            (
                candidate
                for root in self.import_roots
                for base in ("" if root == "." else root + "/",)
                for candidate in (base + stem + ".py", base + stem + "/__init__.py")
                if candidate in self.known
            ),
            None,
        )

    def closure_of_module(self, dotted: str) -> frozenset[str]:
        parts = dotted.split(".")
        return frozenset(
            found
            for end in range(1, len(parts) + 1)
            if (found := self.module_file(".".join(parts[:end]))) is not None
        )

    def _served_by(self, package: str, name: str | None) -> frozenset[str]:
        table = self.lazy[package]
        directory = package.removesuffix("__init__.py")
        all_modules = frozenset(
            path
            for path in self.known
            if path.startswith(directory) and path != package
        )
        if not table:
            return all_modules
        targets = set()
        for exported in (name,) if name is not None else table:
            module = table.get(exported)
            seen = set()
            while module in table and module not in seen:
                seen.add(module)
                module = table[module]
            if module is not None:
                targets.update(
                    self.closure_of_module(module)
                    if self.module_file(module)
                    else all_modules
                )
        return frozenset(targets)

    def imports_of(
        self, syntax: _Syntax, path: str, *, plugins: bool
    ) -> frozenset[str]:
        directory = path.rpartition("/")[0]
        relative = directory
        for root in self.import_roots:
            if root == ".":
                break
            if directory == root or directory.startswith(root + "/"):
                relative = directory[len(root) + 1 :]
                break
        package = relative.split("/") if relative else []
        targets = set()
        served = {}
        nodes = syntax.runtime
        for node in nodes:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    targets.update(self.closure_of_module(alias.name))
                    dotted = (
                        alias.name if alias.asname else alias.name.partition(".")[0]
                    )
                    package_file = self.module_file(dotted)
                    if package_file in self.lazy:
                        served[alias.asname or dotted] = package_file
                        if not self.lazy[package_file]:
                            targets.update(self._served_by(package_file, None))
            elif isinstance(node, ast.ImportFrom):
                keep = len(package) - (node.level - 1)
                if node.level and keep < 0:
                    continue
                parts = (
                    [*package[:keep], *(node.module.split(".") if node.module else [])]
                    if node.level
                    else node.module.split(".")
                    if node.module
                    else []
                )
                base = ".".join(parts)
                package_file = self.module_file(base) if base else None
                for alias in node.names:
                    submodule = f"{base}.{alias.name}" if base else alias.name
                    if alias.name != "*" and self.module_file(submodule):
                        targets.update(self.closure_of_module(submodule))
                    else:
                        if base:
                            targets.update(self.closure_of_module(base))
                        if package_file in self.lazy:
                            targets.update(
                                self._served_by(
                                    package_file,
                                    None if alias.name == "*" else alias.name,
                                )
                            )
        for node in nodes:
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id in served
            ):
                targets.update(self._served_by(served[node.value.id], node.attr))
        if plugins:
            for name in syntax.plugins:
                targets.update(self.closure_of_module(name))
        return frozenset(targets)


@dataclass(frozen=True)
class CommandLaunch:
    names: frozenset[str]
    unnamed: bool = False


def _command_launch(syntax: _Syntax, rows: Mapping[str, object]) -> CommandLaunch:
    linked = set()
    unnamed = False
    dispatcher = any(
        (
            isinstance(node, ast.ImportFrom)
            and node.module in _DISPATCH_MODULES
            and any(alias.name == "main" for alias in node.names)
        )
        or (
            isinstance(node, ast.Import)
            and any(alias.name in _DISPATCH_MODULES for alias in node.names)
        )
        for node in syntax.nodes
    )
    for node in syntax.nodes:
        if isinstance(node, (ast.List, ast.Tuple)):
            for before, after in pairwise(
                [_string_of(element) for element in node.elts]
            ):
                if before in _COMMAND_PREFIXES:
                    if after is None:
                        unnamed = True
                    elif after in rows:
                        linked.add(after)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            linked.update(
                after
                for before, after in pairwise(node.value.split())
                if before == "des" and after in rows
            )
        elif isinstance(node, ast.Call) and _call_name(node) == "main" and node.args:
            first = node.args[0]
            name = (
                _string_of(first.elts[0])
                if isinstance(first, (ast.List, ast.Tuple)) and first.elts
                else None
            )
            if name in rows:
                linked.add(name)
            elif name is None and dispatcher:
                unnamed = True
    return CommandLaunch(frozenset(linked), unnamed)


def _literal_arguments(node: ast.AST) -> list[ast.Constant] | None:
    if (
        isinstance(node, ast.Call)
        and node.args
        and not node.keywords
        and all(_string_of(arg) is not None for arg in node.args)
    ):
        return list(node.args)
    return None


def _joined_operands(node: ast.AST) -> list[ast.Constant] | None:
    if isinstance(node, ast.Call):
        arguments = _literal_arguments(node)
        return arguments if arguments and len(arguments) > 1 else None
    if (
        isinstance(node, ast.BinOp)
        and isinstance(node.op, ast.Div)
        and _string_of(node.right) is not None
    ):
        return [
            *(_literal_arguments(node.left) or _joined_operands(node.left) or []),
            node.right,
        ]
    return None


def _named_paths(syntax: _Syntax):
    consumed = set()
    for node in syntax.nodes:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            consumed.add(id(node.value))
            continue
        operands = _joined_operands(node)
        if operands is not None and not any(id(item) in consumed for item in operands):
            consumed.update(id(item) for item in operands)
            words = [str(item.value) for item in operands]
            for step in (
                range(1, len(words) + 1)
                if isinstance(node, ast.BinOp)
                else (len(words),)
            ):
                yield "/".join(words[:step])
        elif (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in consumed
        ):
            yield node.value


def _launch_argv(call: ast.Call) -> list[str | None] | None:
    argument = call.args[0] if call.args else None
    for keyword in call.keywords:
        if keyword.arg == "args":
            argument = keyword.value
    if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
        return argument.value.split()
    if not isinstance(argument, (ast.List, ast.Tuple)):
        return None
    return [
        "python"
        if isinstance(element, ast.Attribute)
        and element.attr == "executable"
        and isinstance(element.value, ast.Name)
        and element.value.id == "sys"
        else _string_of(element)
        for element in argument.elts
    ]


def _os_launch_family(name: str | None) -> tuple[str, str] | None:
    for family in ("exec", "spawn"):
        if (
            name
            and name.startswith(family)
            and (variant := name.removeprefix(family))
            in {"l", "le", "lp", "lpe", "v", "ve", "vp", "vpe"}
        ):
            return family, variant
    return None


def _os_launch_argv(
    call: ast.Call, family: str, variant: str
) -> list[str | None] | None:
    arguments = call.args[1:] if family == "spawn" else call.args
    if not arguments:
        return None
    program = _string_of(arguments[0])
    if variant.startswith("l"):
        return [program, *(_string_of(arg) for arg in arguments[2:])]
    if len(arguments) < 2 or not isinstance(arguments[1], (ast.List, ast.Tuple)):
        return None
    return [program, *(_string_of(arg) for arg in arguments[1].elts[1:])]


def _launch_is_static(words: list[str | None] | None, commands: frozenset[str]) -> bool:
    if not words or words[0] is None:
        return False
    program, rest = words[0], words[1:]
    if program == "des":
        return bool(rest) and rest[0] in commands
    if not posixpath.basename(program).startswith("python"):
        return True
    if rest[:2] == ["-m", "pytest"]:
        return True
    if rest[:1] == ["-m"] and len(rest) > 2:
        return rest[1] in _DISPATCH_MODULES and rest[2] in commands
    first = next(
        (word for word in rest if word is None or not word.startswith("-")), None
    )
    return first is not None and first.endswith(".py")


def is_dynamic_reach(tree: ast.Module, commands: frozenset[str] = frozenset()) -> bool:
    return _dynamic_reach(_observe(tree).calls, commands)


def _dynamic_reach(calls: tuple[ast.Call, ...], commands: frozenset[str]) -> bool:
    owner_calls = {
        "subprocess": {
            "run",
            "Popen",
            "call",
            "check_call",
            "check_output",
            "getoutput",
            "getstatusoutput",
        },
        "os": {"system", "popen"},
        "asyncio": {"create_subprocess_exec", "create_subprocess_shell"},
    }
    for node in calls:
        name, owner = _call_name(node), _owner_name(node)
        family = _os_launch_family(name) if owner == "os" else None
        if family:
            if not _launch_is_static(_os_launch_argv(node, *family), commands):
                return True
            continue
        if isinstance(node.func, ast.Attribute):
            dynamic = name in {"import_module", "spec_from_file_location"} or (
                owner == "runpy" and name in {"run_module", "run_path"}
            )
            launch = name in owner_calls.get(owner, ()) or name == "spawn"
        else:
            dynamic = name in {
                "__import__",
                "import_module",
                "spec_from_file_location",
                "run_module",
                "run_path",
                "exec",
                "eval",
            }
            launch = name in {
                "Popen",
                "check_call",
                "check_output",
                "create_subprocess_exec",
                "create_subprocess_shell",
                "spawn",
            }
        if dynamic or (launch and not _launch_is_static(_launch_argv(node), commands)):
            return True
    return False


def _confined(path: object) -> bool:
    return (
        isinstance(path, str)
        and bool(path)
        and not path.startswith("/")
        and ".." not in posixpath.normpath(path).split("/")
    )


def _judgments(snapshot: Snapshot) -> JudgmentTable | Missing:
    source = snapshot.entries.get(JUDGMENT_TABLE_PATH)
    if source is None:
        return JudgmentTable()
    try:
        document = json.loads(source.content)
        if (
            not isinstance(document, dict)
            or set(document) != {"version", "judgments"}
            or document["version"] != 1
            or not isinstance(document["judgments"], list)
        ):
            raise ValueError("not a version 1 judgment table")
        entries = []
        for item in document["judgments"]:
            if (
                not isinstance(item, dict)
                or set(item) != {"test_file", "sha256", "reaches"}
                or not _confined(item["test_file"])
                or not isinstance(item["sha256"], str)
                or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"])
                or not isinstance(item["reaches"], list)
                or not all(_confined(path) for path in item["reaches"])
            ):
                raise ValueError("malformed judgment")
            entries.append(
                Judgment(item["test_file"], item["sha256"], frozenset(item["reaches"]))
            )
        return JudgmentTable(tuple(entries))
    except (TypeError, ValueError, RecursionError):
        return Missing(MissingKind.JUDGMENT_TABLE_UNREADABLE, JUDGMENT_TABLE_PATH)


def _parse(content: bytes | None) -> ast.Module | None:
    try:
        return ast.parse(content) if content is not None else None
    except (SyntaxError, ValueError, RecursionError):
        return None


def _lazy_packages(trees: Mapping[str, ast.Module]) -> Mapping[str, Mapping[str, str]]:
    packages = {}
    for path, tree in trees.items():
        if not path.endswith("/__init__.py") or not any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "__getattr__"
            for node in tree.body
        ):
            continue
        table = {}
        for node in tree.body:
            value = (
                node.value if isinstance(node, (ast.Assign, ast.AnnAssign)) else None
            )
            if (
                isinstance(value, ast.Dict)
                and value.keys
                and all(
                    _string_of(key) is not None and _string_of(item) is not None
                    for key, item in zip(value.keys, value.values, strict=True)
                )
            ):
                table.update(
                    (_string_of(key), _string_of(item))
                    for key, item in zip(value.keys, value.values, strict=True)
                )
        packages[path] = table
    return packages


def build_reach_view(snapshot: Snapshot) -> ReachView:
    settings = pytest_settings(scope.text(snapshot, "pyproject.toml") or "")
    discovered = frozenset(
        path
        for path in snapshot.entries
        if path.endswith(".py")
        and settings.in_test_tree(path)
        and not any(
            settings.prunes(directory) for directory in tuple(_ancestry(path))[1:]
        )
    )
    files = frozenset(scope.files(snapshot, "*.py")) | discovered
    trees = {
        path: tree
        for path in files
        if (tree := _parse(snapshot.entries[path].content)) is not None
    }
    resolver = _ImportResolver(files, settings.import_roots, _lazy_packages(trees))
    registry = resolver.module_file("nwave_ai.cli")
    commands = {}
    registry_syntax = _observe(trees[registry]) if registry in trees else None
    if registry_syntax is not None:
        for node in registry_syntax.calls:
            if _call_name(node) == "_SubcommandRow" and len(node.args) >= 2:
                name, module = _string_of(node.args[0]), _string_of(node.args[1])
                if name is not None and module is not None:
                    commands[name] = resolver.module_file(module)
    test_tree = frozenset(path for path in files if settings.in_test_tree(path))
    tests = frozenset(path for path in test_tree if settings.is_test_file(path))
    conftests = frozenset(
        path for path in test_tree if path.rpartition("/")[2] == "conftest.py"
    )
    imports, links, content = set(), set(), set()
    dynamic, digests = set(), {}
    existing = frozenset(
        chain(
            snapshot.entries,
            chain.from_iterable(
                tuple(_ancestry(path))[1:] for path in snapshot.entries
            ),
        )
    )
    for path, tree in trees.items():
        holds = path in tests or (
            path not in test_tree and not settings.is_beneath_source_root(path)
        )
        full = path in test_tree or holds
        if not full and b"import" not in snapshot.entries[path].content:
            continue
        syntax = registry_syntax if path == registry else _observe(tree, full=full)
        imports.update(
            (path, target)
            for target in resolver.imports_of(syntax, path, plugins=path in conftests)
        )
        named = tuple(_named_paths(syntax)) if path in test_tree or holds else ()
        if path in test_tree:
            launch = _command_launch(syntax, commands)
            modules = {
                commands[name]
                for name in (commands if launch.unnamed else launch.names)
                if commands.get(name) is not None
            }
            if launch.unnamed and registry:
                modules.add(registry)
            (links if path in tests else imports).update(
                (path, module) for module in modules
            )
            words = list(named)
            for node in syntax.nodes:
                run = (
                    [_string_of(item) for item in node.elts]
                    if isinstance(node, (ast.List, ast.Tuple))
                    else node.value.split()
                    if isinstance(node, ast.Constant)
                    and isinstance(node.value, str)
                    and len(node.value) <= 400
                    else []
                )
                for before, after in pairwise(run):
                    if before == "-m" and after is not None:
                        imports.update(
                            (path, target)
                            for target in resolver.closure_of_module(after)
                        )
                words.extend(word for word in run if word is not None)
            imports.update(
                (path, posixpath.normpath(word))
                for word in words
                if word.endswith(".py") and posixpath.normpath(word) in files
            )
            if _dynamic_reach(syntax.calls, frozenset(commands)):
                dynamic.add(path)
                digests[path] = hashlib.sha256(
                    snapshot.entries[path].content
                ).hexdigest()
        if holds:
            for candidate in named:
                if (
                    not candidate
                    or len(candidate) > 200
                    or "\n" in candidate
                    or "\0" in candidate
                    or candidate.startswith(("/", "~"))
                ):
                    continue
                held = posixpath.normpath(candidate)
                if (
                    held not in {".", "..", path}
                    and not held.startswith("../")
                    and held in existing
                    and not settings.is_content_root(held)
                ):
                    content.add((path, held))
    table = _judgments(snapshot)
    return ReachView(
        tests,
        conftests,
        test_tree,
        frozenset(imports),
        index.file_call_edges(snapshot),
        frozenset(links),
        frozenset(dynamic),
        files - trees.keys(),
        digests,
        table if isinstance(table, JudgmentTable) else JudgmentTable(),
        table if isinstance(table, Missing) else None,
        ContentHoldings(frozenset(content)),
    )


def report(snapshot: Snapshot, changed: tuple[str, ...]) -> dict[str, object]:
    paths = tuple(sorted(set(changed)))
    queried = tuple(path for path in paths if _confined(path))
    gaps = frozenset(
        Missing(MissingKind.OUTSIDE_ROOT, path) for path in paths if path not in queried
    )
    paired_index = index.read_index(snapshot)
    if paired_index is None:
        uncovered = tuple(
            sorted(
                set(scope.files(snapshot, "*.py"))
                | {path for path in queried if path.endswith(".py")}
            )
        )
        measured = Coverage(missing=uncovered)
        present = LiveSource()
        if LAYOUT is not None and any(
            path in (snapshot.index_entries or snapshot.entries)
            for path in LAYOUT.paths
        ):
            gaps |= {Missing(MissingKind.INDEX_UNPAIRED, LAYOUT.pairing)}
        else:
            gaps |= frozenset(
                Missing(MissingKind.ABSENT_FROM_INDEX, path) for path in uncovered
            )
    else:
        _, recorded, present = paired_index
        measured = index.coverage(snapshot, recorded, queried)
        gaps |= frozenset(
            chain(
                (
                    Missing(MissingKind.ABSENT_FROM_INDEX, path)
                    for path in measured.missing
                ),
                (Missing(MissingKind.STALE, path) for path in measured.stale),
            )
        )
    outcome = select(queried, build_reach_view(snapshot), gaps)
    table = snapshot.entries.get(JUDGMENT_TABLE_PATH)
    document = {
        "query": "impacted-tests",
        "mode": "shadow",
        "changed": list(paths),
        "index_snapshot": asdict(present),
        "coverage": {key: list(value) for key, value in asdict(measured).items()},
        "judgment_table": {
            "path": JUDGMENT_TABLE_PATH,
            "sha256": hashlib.sha256(table.content).hexdigest()
            if table and table.content is not None
            else None,
        },
    }
    if isinstance(outcome, Selected):
        document.update(outcome="selected", tests=sorted(outcome.tests))
    else:
        document.update(
            outcome="indeterminate",
            widened_tests=sorted(outcome.widened_tests),
            reached_tests=sorted(outcome.reached_tests),
            missing=[
                {"kind": gap.kind.value, "path": gap.path}
                for gap in sorted(outcome.missing, key=lambda gap: gap.sort_key)
            ],
        )
    return document
