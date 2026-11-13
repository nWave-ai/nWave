"""What a project declares about its tests, parsed once into value objects.

Pure. The raw ``tests`` block (from ``.nwave/config.json`` or from a file the caller
names) becomes a :class:`Declaration`, or a :class:`Malformed` that lists every defect
found in one pass. Nothing downstream re-checks a parsed value. An absent block is the
declared fallback: one run at a time, classes ``short`` and ``long``, no selection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING

from nwave_ai.testrun.queue_policy import CapacityLimits


if TYPE_CHECKING:
    from collections.abc import Mapping


TRANSITIVE = "transitive"
_NO_SETTINGS: Mapping[str, object] = MappingProxyType({})


@dataclass(frozen=True)
class Depth:
    """How many dependency hops a use follows; ``hops`` is ``None`` for every hop."""

    hops: int | None

    def shown(self) -> int | str:
        return TRANSITIVE if self.hops is None else self.hops


@dataclass(frozen=True)
class QueueDeclaration:
    """The order and the size of the queue as this project wants them.

    ``max_wait_seconds`` bounds the wait for a place. Its fallback of half an hour
    is longer than the aging threshold, so an aged run still gets its turn, and
    short enough that a run which never ends costs a waiting run minutes, not a
    working session. A project whose runs are longer declares more.
    """

    classes: tuple[str, ...] = ("short", "long")
    aging_seconds: float = 1200.0
    limits: CapacityLimits = field(default_factory=CapacityLimits)
    max_wait_seconds: float = 1800.0

    def rank(self, run_class: str) -> int | None:
        return self.classes.index(run_class) if run_class in self.classes else None

    def last_class(self) -> str:
        return self.classes[-1]


@dataclass(frozen=True)
class DeclaredCommand:
    """A test command the project names, with its class and time limit when declared."""

    argv: tuple[str, ...]
    run_class: str | None = None
    timeout_seconds: float | None = None


@dataclass(frozen=True)
class ToolResolution:
    """How to see where the tool under test resolves, and how to repair it."""

    argv: tuple[str, ...]
    repair: str | None = None


@dataclass(frozen=True)
class SelectionRules:
    """Where the tests are, who computes dependencies, and the depth of each use."""

    test_roots: tuple[str, ...]
    test_files: tuple[str, ...]
    adapters: Mapping[str, str]
    adapter_settings: Mapping[str, Mapping[str, object]]
    assets: tuple[tuple[str, tuple[str, ...]], ...]
    no_tests: tuple[str, ...]
    widest: tuple[str, ...]
    local_ceiling: int | None
    uses: Mapping[str, Depth]
    ignore: tuple[str, ...]

    def settings_of(self, adapter: str) -> Mapping[str, object]:
        return self.adapter_settings.get(adapter, _NO_SETTINGS)


@dataclass(frozen=True)
class Declaration:
    """Everything the queue and the selector read from the project."""

    queue: QueueDeclaration = field(default_factory=QueueDeclaration)
    commands: Mapping[str, DeclaredCommand] = field(
        default_factory=lambda: MappingProxyType({})
    )
    candidate: Mapping[str, tuple[str, ...]] = field(
        default_factory=lambda: MappingProxyType({})
    )
    tool_resolution: ToolResolution | None = None
    selection: SelectionRules | None = None


@dataclass(frozen=True)
class Malformed:
    """A declaration that cannot be used, with every defect it has."""

    defects: tuple[str, ...]


_ROOT_KEYS = ("queue", "commands", "candidate", "tool_resolution", "selection")
_QUEUE_KEYS = (
    "classes",
    "aging_seconds",
    "max_wait_seconds",
    "max_concurrent",
    "cores_per_run",
    "memory_per_run_mb",
)
_COMMAND_KEYS = ("argv", "class", "timeout_seconds")
_RESOLUTION_KEYS = ("argv", "repair")
_SELECTION_KEYS = (
    "test_roots",
    "test_files",
    "adapters",
    "assets",
    "no_tests",
    "widest",
    "local_ceiling",
    "uses",
    "ignore",
)


def parse_declaration(document: object | None) -> Declaration | Malformed:
    """Parse the raw ``tests`` block; an absent block is the declared fallback."""
    if document is None:
        return Declaration()
    if not isinstance(document, dict):
        return Malformed(
            (f"the declaration must be an object, got {_shown(document)}",)
        )
    defects = _unknown_keys("", document, _ROOT_KEYS)
    queue, queue_defects = _queue(document.get("queue"))
    commands, command_defects = _commands(document.get("commands"), queue.classes)
    candidate, candidate_defects = _candidate(document.get("candidate"))
    resolution, resolution_defects = _resolution(document.get("tool_resolution"))
    selection, selection_defects = _selection(document.get("selection"))
    defects = (
        *defects,
        *queue_defects,
        *command_defects,
        *candidate_defects,
        *resolution_defects,
        *selection_defects,
    )
    if defects:
        return Malformed(tuple(defects))
    return Declaration(queue, commands, candidate, resolution, selection)


def _shown(value: object) -> str:
    text = repr(value)
    return text if len(text) <= 60 else text[:57] + "..."


def _unknown_keys(
    where: str, block: Mapping[str, object], known: tuple[str, ...]
) -> tuple[str, ...]:
    return tuple(
        f"{where}{key} is not a known key (known: {', '.join(known)})"
        for key in block
        if key not in known
    )


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_whole(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _strings(value: object, *, allow_empty: bool) -> tuple[str, ...] | None:
    """A list of non-empty strings, or ``None`` when the value is not one."""
    if not isinstance(value, list) or (not value and not allow_empty):
        return None
    if not all(isinstance(item, str) and item for item in value):
        return None
    return tuple(value)


def _queue(block: object) -> tuple[QueueDeclaration, tuple[str, ...]]:
    default = QueueDeclaration()
    if block is None:
        return default, ()
    if not isinstance(block, dict):
        return default, (f"queue must be an object, got {_shown(block)}",)
    defects = list(_unknown_keys("queue.", block, _QUEUE_KEYS))
    classes = default.classes
    if "classes" in block:
        declared = _strings(block["classes"], allow_empty=False)
        if declared is None or len(set(declared)) != len(declared):
            defects.append(
                "queue.classes must be a list of one or more distinct names, "
                f"first served first, got {_shown(block['classes'])}"
            )
        else:
            classes = declared
    aging = block.get("aging_seconds", default.aging_seconds)
    if not _is_number(aging) or aging < 0:
        defects.append(
            f"queue.aging_seconds must be a number of seconds, 0 or more, got {_shown(aging)}"
        )
        aging = default.aging_seconds
    ceiling = block.get("max_concurrent", default.limits.max_concurrent)
    if not _is_whole(ceiling) or ceiling < 1:
        defects.append(
            f"queue.max_concurrent must be a whole number of at least 1, got {_shown(ceiling)}"
        )
        ceiling = default.limits.max_concurrent
    cores = block.get("cores_per_run", default.limits.cores_per_run)
    if not _is_number(cores) or cores <= 0:
        defects.append(
            f"queue.cores_per_run must be a number above 0, got {_shown(cores)}"
        )
        cores = default.limits.cores_per_run
    memory = block.get("memory_per_run_mb", default.limits.memory_per_run_mb)
    if not _is_whole(memory) or memory < 1:
        defects.append(
            "queue.memory_per_run_mb must be a whole number of megabytes, "
            f"at least 1, got {_shown(memory)}"
        )
        memory = default.limits.memory_per_run_mb
    wait = block.get("max_wait_seconds", default.max_wait_seconds)
    if not _is_number(wait) or not 0 < wait < float("inf"):
        defects.append(
            "queue.max_wait_seconds must be a number of seconds above 0, "
            f"got {_shown(wait)}"
        )
        wait = default.max_wait_seconds
    return (
        QueueDeclaration(
            classes,
            float(aging),
            CapacityLimits(ceiling, float(cores), memory),
            float(wait),
        ),
        tuple(defects),
    )


def _commands(
    block: object, classes: tuple[str, ...]
) -> tuple[Mapping[str, DeclaredCommand], tuple[str, ...]]:
    if block is None:
        return MappingProxyType({}), ()
    if not isinstance(block, dict):
        return MappingProxyType({}), (
            f"commands must be an object, got {_shown(block)}",
        )
    defects: list[str] = []
    commands: dict[str, DeclaredCommand] = {}
    for name, entry in block.items():
        where = f"commands.{name}."
        if not name or name.startswith("-"):
            defects.append(f"commands.{name} must not be empty or start with '-'")
        if not isinstance(entry, dict):
            defects.append(f"commands.{name} must be an object, got {_shown(entry)}")
            continue
        defects.extend(_unknown_keys(where, entry, _COMMAND_KEYS))
        argv = _strings(entry.get("argv"), allow_empty=False)
        if argv is None:
            defects.append(
                f"{where}argv must be a list of one or more words, "
                f"got {_shown(entry.get('argv'))}"
            )
        run_class = entry.get("class")
        if run_class is not None and run_class not in classes:
            defects.append(
                f"{where}class must be one of {', '.join(classes)}, got {_shown(run_class)}"
            )
        limit = entry.get("timeout_seconds")
        if limit is not None and (not _is_number(limit) or limit <= 0):
            defects.append(
                f"{where}timeout_seconds must be a number above 0, got {_shown(limit)}"
            )
            limit = None
        if argv is not None:
            commands[name] = DeclaredCommand(
                argv, run_class, None if limit is None else float(limit)
            )
    return MappingProxyType(commands), tuple(defects)


def _candidate(block: object) -> tuple[Mapping[str, tuple[str, ...]], tuple[str, ...]]:
    if block is None:
        return MappingProxyType({}), ()
    if not isinstance(block, dict):
        return MappingProxyType({}), (
            f"candidate must be an object, got {_shown(block)}",
        )
    defects: list[str] = []
    readers: dict[str, tuple[str, ...]] = {}
    for name, argv in block.items():
        words = _strings(argv, allow_empty=False)
        if words is None:
            defects.append(
                f"candidate.{name} must be a list of one or more words, got {_shown(argv)}"
            )
        else:
            readers[name] = words
    return MappingProxyType(readers), tuple(defects)


def _resolution(block: object) -> tuple[ToolResolution | None, tuple[str, ...]]:
    if block is None:
        return None, ()
    if not isinstance(block, dict):
        return None, (f"tool_resolution must be an object, got {_shown(block)}",)
    defects = list(_unknown_keys("tool_resolution.", block, _RESOLUTION_KEYS))
    argv = _strings(block.get("argv"), allow_empty=False)
    if argv is None:
        defects.append(
            "tool_resolution.argv must be a list of one or more words, "
            f"got {_shown(block.get('argv'))}"
        )
    repair = block.get("repair")
    if repair is not None and not isinstance(repair, str):
        defects.append(f"tool_resolution.repair must be text, got {_shown(repair)}")
        repair = None
    if argv is None:
        return None, tuple(defects)
    return ToolResolution(argv, repair), tuple(defects)


def _depth(value: object) -> Depth | None:
    if value == TRANSITIVE:
        return Depth(None)
    if _is_whole(value) and value >= 1:
        return Depth(value)
    return None


def _selection(block: object) -> tuple[SelectionRules | None, tuple[str, ...]]:
    if block is None:
        return None, ()
    if not isinstance(block, dict):
        return None, (f"selection must be an object, got {_shown(block)}",)
    defects: list[str] = []

    def strings(key: str, *, required: bool) -> tuple[str, ...]:
        if key not in block and not required:
            return ()
        found = _strings(block.get(key), allow_empty=not required)
        if found is None:
            defects.append(
                f"selection.{key} must be a list of "
                f"{'one or more ' if required else ''}paths or patterns, "
                f"got {_shown(block.get(key))}"
            )
            return ()
        return found

    adapters = block.get("adapters", {})
    if not isinstance(adapters, dict) or not all(
        isinstance(extension, str)
        and extension.startswith(".")
        and isinstance(name, str)
        and name
        for extension, name in adapters.items()
    ):
        defects.append(
            "selection.adapters must map a file extension such as '.py' to an "
            f"adapter name, got {_shown(adapters)}"
        )
        adapters = {}
    settings = {}
    for name in sorted(set(adapters.values())):
        if name in block:
            if isinstance(block[name], dict):
                settings[name] = MappingProxyType(dict(block[name]))
            else:
                defects.append(
                    f"selection.{name} must be an object of settings for the "
                    f"'{name}' adapter, got {_shown(block[name])}"
                )
    defects.extend(
        _unknown_keys("selection.", block, (*_SELECTION_KEYS, *sorted(settings)))
    )
    assets = block.get("assets", {})
    asset_rules: list[tuple[str, tuple[str, ...]]] = []
    if not isinstance(assets, dict):
        defects.append(f"selection.assets must be an object, got {_shown(assets)}")
    else:
        for prefix, directories in assets.items():
            mapped = _strings(directories, allow_empty=False)
            if not prefix or mapped is None:
                defects.append(
                    f"selection.assets.{prefix} must list one or more test "
                    f"directories, got {_shown(directories)}"
                )
            else:
                asset_rules.append((prefix, mapped))
    ceiling = block.get("local_ceiling")
    if ceiling is not None and (not _is_whole(ceiling) or ceiling < 1):
        defects.append(
            f"selection.local_ceiling must be a whole number of at least 1, got {_shown(ceiling)}"
        )
        ceiling = None
    uses = block.get("uses")
    depths: dict[str, Depth] = {}
    if not isinstance(uses, dict) or not uses:
        defects.append(
            "selection.uses must name one or more uses with their depth, "
            f"got {_shown(uses)}"
        )
    else:
        for name, value in uses.items():
            depth = _depth(value)
            if depth is None:
                defects.append(
                    f"selection.uses.{name} must be a whole number of hops, at "
                    f"least 1, or '{TRANSITIVE}', got {_shown(value)}"
                )
            else:
                depths[name] = depth
    rules = SelectionRules(
        test_roots=strings("test_roots", required=True),
        test_files=strings("test_files", required=True),
        adapters=MappingProxyType(dict(adapters)),
        adapter_settings=MappingProxyType(settings),
        assets=tuple(sorted(asset_rules, key=lambda rule: -len(rule[0]))),
        no_tests=strings("no_tests", required=False),
        widest=strings("widest", required=False),
        local_ceiling=ceiling,
        uses=MappingProxyType(depths),
        ignore=strings("ignore", required=False),
    )
    return (None if defects else rules), tuple(defects)
