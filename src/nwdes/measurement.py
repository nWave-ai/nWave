"""Pure observations of supplied intervals and native delivery evidence."""

import json
import re
import shlex
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from functools import reduce
from typing import Literal

from nwdes import drafts, handoff
from nwdes.contracts import Built, Defect, Refused, checked


@dataclass(frozen=True)
class RequestInterval:
    role: str
    task: str | None
    slice: str | None
    start_ms: int
    end_ms: int
    continuation: bool
    rework: bool


@dataclass(frozen=True)
class SessionFile:
    path: str
    expected_parent: str | None
    raw: bytes
    error: str | None = None


@dataclass(frozen=True)
class SessionTree:
    root_name: str
    root_absolute: str
    root: SessionFile
    descendants: tuple[SessionFile, ...]


@dataclass(frozen=True)
class Occurrence:
    session: str
    call: str
    line: int
    argv: tuple[str, ...]
    values: Mapping | None
    start_ms: int
    end_ms: int | None
    ok: bool
    path: str = ""
    command: str = ""
    stdout: str = ""
    cause: str = ""
    native_exit: int | None = None
    segment: int = 0

    @property
    def identity(self):
        return self.session + ":" + self.call

    @property
    def part(self):
        return self.argv[0] if self.argv else ""

    def _argument(self, name, default=None):
        if self.values is not None:
            return self.values.get(name, default)
        flag = "--" + name
        return next(
            (
                word.split("=", 1)[1]
                if word.startswith(flag + "=")
                else self.argv[index + 1]
                for index, word in enumerate(self.argv)
                if word.startswith(flag + "=")
                or (word == flag and index + 1 < len(self.argv))
            ),
            default,
        )

    @property
    def slice(self):
        return self._argument("slice")

    @property
    def subject(self):
        return self._argument("subject", "legacy") if self.part == "review" else None

    @property
    def scope(self):
        if self.part == "review":
            scope = (self.values or {}).get("review-scope")
            if scope is None:
                scope = drafts.review_scope(
                    None if self.subject == "legacy" else self.subject,
                    self.slice,
                    replay=True,
                )
            return scope.value if isinstance(scope, Built) else None
        return self.slice if self.part in ("craft", "acceptance") else None

    @property
    def verb(self):
        return (self.values or {}).get("role-verb", " ".join(self.argv[1:2]))


@dataclass(frozen=True)
class Commit:
    id: str
    committer_s: int
    changed: tuple[str, ...]
    files: Mapping[str, bytes | None]


@dataclass(frozen=True)
class History:
    candidate: Commit
    ancestors: tuple[Commit, ...]
    chain: tuple[Commit, ...]
    current: Mapping[str, bytes | None] | None
    clean: bool
    head: str = ""
    dirty: tuple[str, ...] = ()
    causes: tuple[str, ...] = ()
    file_causes: Mapping = handoff.EMPTY


@dataclass(frozen=True)
class SessionEvidence:
    history: History | None = None
    handoff_path: str = ""
    parse_values: Callable[[tuple[str, ...]], Mapping | None] = lambda argv: None
    causes: tuple[str, ...] = ()
    rework_cause: str | None = None


@dataclass(frozen=True)
class Bound:
    commit: str | None


@dataclass(frozen=True)
class Unbound:
    cause: str


Binding = Bound | Unbound


@dataclass(frozen=True)
class Accepted:
    end_ms: int


@dataclass(frozen=True)
class NotMeasured:
    causes: tuple[str, ...]


Endpoint = Accepted | NotMeasured


@dataclass(frozen=True)
class TrialReport:
    source: Literal["supplied", "host"]
    runtime: str | None
    elapsed_ms: int | None
    elapsed_missing: tuple[str, ...]
    role_ms: tuple[tuple[str, int], ...]
    requests: int
    continuations: int
    rework: int
    continuation_and_rework: int
    unanswered: int
    max_concurrent_crafters: int
    max_concurrent_reviewers: int
    excluded: tuple[tuple[str, str], ...]
    objective_minutes: int | None
    delivery_lines: tuple[str, ...] = ()
    host_missing: tuple[str, ...] = ()
    rework_missing: str | None = None


ROLES = frozenset(
    (
        "nw-acceptance-designer",
        "nw-acceptance-designer-reviewer",
        "nw-functional-software-crafter",
        "nw-product-owner",
        "nw-software-crafter",
        "nw-software-crafter-reviewer",
        "nw-solution-architect",
        "nw-solution-architect-reviewer",
        "nw-user-examiner",
    )
)
CRAFTERS = frozenset(("nw-functional-software-crafter", "nw-software-crafter"))
PARTS = ("design", "acceptance", "expectations", "examine", "craft", "review")
IDENT = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
ROOT_NAME = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d{3}Z_(" + IDENT + r")\.jsonl"
)


def invalid(subject, why):
    return Defect(
        "PartInvalid: " + subject,
        why,
        "Supply input conforming to nwdes measure --help.",
    )


def _instant(value, host=False):
    pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}" + (
        r"\.\d{3}Z" if host else r"(?:\.\d{1,3})?Z"
    )
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        return None
    try:
        delta = datetime.fromisoformat(value.replace("Z", "+00:00")) - datetime(
            1970, 1, 1, tzinfo=UTC
        )
        return (delta.days * 86400 + delta.seconds) * 1000 + delta.microseconds // 1000
    except ValueError:
        return None


def _object(pairs):
    if len({name for name, _ in pairs}) != len(pairs):
        raise ValueError("Duplicate JSON key")
    return dict(pairs)


def _json(raw, subject, flag):
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return checked(
            None,
            (
                Defect(
                    "InputUnreadable: " + flag + " " + subject,
                    "Input is not strict UTF-8.",
                    "Supply a readable UTF-8 file.",
                ),
            ),
        )
    try:
        return Built(
            json.loads(
                text,
                object_pairs_hook=_object,
                parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
            )
        )
    except (ValueError, TypeError) as error:
        return checked(None, (invalid(subject, f"Input is not strict JSON: {error}"),))


def _request(value, subject):
    if not isinstance(value, dict):
        return checked(None, (invalid(subject, "A request must be an object."),))
    fields = ("role", "task", "slice", "start", "end", "continuation", "rework")
    start, end = _instant(value.get("start")), _instant(value.get("end"))
    valid = {
        "role": isinstance(value.get("role"), str) and bool(value.get("role")),
        "task": value.get("task") is None or isinstance(value.get("task"), str),
        "slice": value.get("slice") is None or isinstance(value.get("slice"), str),
        "start": start is not None,
        "end": end is not None and (start is None or end > start),
        "continuation": type(value.get("continuation")) is bool,
        "rework": type(value.get("rework")) is bool,
    }
    defects = tuple(
        invalid(subject + "." + field, "Missing or invalid request field.")
        for field in fields
        if field not in value or not valid[field]
    ) + tuple(
        invalid(subject + "." + field, "Unknown request field.")
        for field in value
        if field not in fields
    )
    return checked(
        RequestInterval(
            value.get("role"),
            value.get("task"),
            value.get("slice"),
            start,
            end,
            value.get("continuation"),
            value.get("rework"),
        ),
        defects,
    )


def _union(intervals):
    def step(state, interval):
        total, end = state
        start, stop = interval
        return total + max(0, stop - max(start, end)), max(end, stop)

    return reduce(step, sorted(intervals), (0, -(10**30)))[0]


def _concurrency(intervals):
    events = sorted(
        (point, change)
        for x in intervals
        for point, change in ((x.start_ms, 1), (x.end_ms, -1))
        if x.end_ms > x.start_ms
    )
    return reduce(
        lambda state, event: (state[0] + event[1], max(state[1], state[0] + event[1])),
        events,
        (0, 0),
    )[1]


def _report(intervals, objective):
    return TrialReport(
        "supplied",
        None,
        max((x.end_ms for x in intervals), default=0)
        - min((x.start_ms for x in intervals), default=0),
        (),
        tuple(
            (
                role,
                _union(
                    tuple((x.start_ms, x.end_ms) for x in intervals if x.role == role)
                ),
            )
            for role in sorted({x.role for x in intervals})
        ),
        len(intervals),
        sum(x.continuation for x in intervals),
        sum(x.rework for x in intervals),
        sum(x.continuation and x.rework for x in intervals),
        0,
        _concurrency(tuple(x for x in intervals if x.role in CRAFTERS)),
        _concurrency(tuple(x for x in intervals if x.role.endswith("-reviewer"))),
        (),
        objective,
    )


def report_from_requests(raw: bytes, label: str, objective_minutes: int | None):
    parsed = _json(raw, label, "--requests")
    if isinstance(parsed, Refused):
        return parsed
    if not isinstance(parsed.value, list) or not parsed.value:
        return checked(
            None, (invalid(label, "Supply a nonempty JSON array of requests."),)
        )
    requests = tuple(
        _request(value, f"{label}[{i}]") for i, value in enumerate(parsed.value)
    )
    defects = tuple(
        d for result in requests if isinstance(result, Refused) for d in result.defects
    )
    return checked(
        _report(
            tuple(result.value for result in requests if isinstance(result, Built)),
            objective_minutes,
        ),
        defects,
    )


@dataclass(frozen=True)
class _Session:
    file: SessionFile
    identity: str
    internal: bool
    records: tuple[dict, ...]


def _session(file):
    if file.error is not None:
        return checked(None, (invalid(file.path, file.error),))
    try:
        lines = file.raw.decode("utf-8", errors="strict").splitlines()
    except UnicodeError:
        return checked(None, (invalid(file.path, "Session is not UTF-8."),))
    parsed = tuple(
        _json(line.encode(), f"{file.path}:{i + 1}", "--host-sessions")
        for i, line in enumerate(lines)
    )
    defects = tuple(
        d for result in parsed if isinstance(result, Refused) for d in result.defects
    ) + tuple(
        invalid(f"{file.path}:{i + 1}", "Each record must be a JSON object.")
        for i, result in enumerate(parsed)
        if isinstance(result, Built) and not isinstance(result.value, dict)
    )
    if defects:
        return checked(None, defects)
    records = tuple(result.value for result in parsed)
    header = records[1] if len(records) > 1 else {}
    identity = header.get("id")
    defects = (
        ()
        if records and records[0].get("type") == "title"
        else (invalid(file.path + ":1", "First record must be a title."),)
    )
    if (
        header.get("type") != "session"
        or header.get("version") != 3
        or not isinstance(identity, str)
        or not re.fullmatch(IDENT, identity)
    ):
        defects += (
            invalid(
                file.path + ":2", "Expected a version-3 session with a lowercase UUID."
            ),
        )
    if (
        file.expected_parent is not None
        and "parentSession" in header
        and header["parentSession"] != file.expected_parent
    ):
        defects += (
            invalid(
                file.path + ":2",
                "Foreign store: parentSession differs from " + file.expected_parent,
            ),
        )
    defects += tuple(
        invalid(
            f"{file.path}:{i + 1}",
            "Message needs a record-level UTC millisecond timestamp.",
        )
        for i, record in enumerate(records)
        if record.get("type") == "message"
        and _instant(record.get("timestamp"), True) is None
    )

    def message_shape(record):
        message = record.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("role"), str):
            return False
        content = message.get("content", ())
        if not isinstance(content, (list, tuple, str)):
            return False
        return all(
            isinstance(item.get("arguments"), dict)
            and isinstance(item["arguments"].get("command"), str)
            if isinstance(item, dict)
            and item.get("type") == "toolCall"
            and item.get("name") == "bash"
            else True
            for item in content
        )

    defects += tuple(
        invalid(f"{file.path}:{i + 1}", "Malformed native message or bash arguments.")
        for i, record in enumerate(records)
        if record.get("type") == "message" and not message_shape(record)
    )
    return checked(
        _Session(
            file,
            identity,
            file.expected_parent is not None and "parentSession" not in header,
            records,
        ),
        defects,
    )


def _messages(session):
    return tuple(
        record for record in session.records if record.get("type") == "message"
    )


def _agent(session):
    return next(
        (
            record.get("agent")
            for record in session.records
            if record.get("type") == "session_init"
        ),
        None,
    )


def _requests(session):
    messages = _messages(session)
    starts = tuple(
        i
        for i, record in enumerate(messages)
        if record.get("message", {}).get("role") == "user"
    )

    def request(index, start):
        stop = starts[index + 1] if index + 1 < len(starts) else len(messages)
        assistants = tuple(
            record
            for record in messages[start + 1 : stop]
            if record.get("message", {}).get("role") == "assistant"
        )
        return (
            session.identity,
            index,
            _instant(messages[start]["timestamp"], True),
            _instant(assistants[-1]["timestamp"], True) if assistants else None,
            _agent(session),
        )

    return tuple(request(index, start) for index, start in enumerate(starts))


def _rework(raw, label, requests):
    if raw is None:
        return Built(frozenset())
    subject = "--rework " + str(label)
    parsed = _json(raw, subject, "--rework")
    if isinstance(parsed, Refused):
        return parsed
    if not isinstance(parsed.value, list):
        return checked(None, (invalid(subject, "Rework must be an array."),))
    known = frozenset((r[0], r[1]) for r in requests)

    def pair(value):
        return (
            isinstance(value, dict)
            and set(value) == {"session", "request"}
            and isinstance(value["session"], str)
            and type(value["request"]) is int
            and (value["session"], value["request"]) in known
        )

    return checked(
        frozenset((v["session"], v["request"]) for v in parsed.value if pair(v)),
        tuple(
            invalid(
                f"{subject}[{i}]",
                "Expected a validated descendant session and existing request index.",
            )
            for i, value in enumerate(parsed.value)
            if not pair(value)
        ),
    )


def command_lines(command):
    """Keep physical line identity while joining shell continuations."""
    result = []
    pending = ""
    first = 1
    for number, text in enumerate(command.splitlines(), 1):
        if not pending:
            first = number
        pending += text[:-1] if text.endswith("\\") else text
        if not text.endswith("\\"):
            result.append((first, pending))
            pending = ""
    if pending:
        result.append((first, pending))
    return tuple(result)


@dataclass(frozen=True)
class _ShellPart:
    text: str
    after: str
    expansion: bool


def _shell_parts(text):
    parts = []
    start, index = 0, 0
    quote, escaped, expansion = "", False, False
    while index < len(text):
        char = text[index]
        if escaped:
            escaped = False
        elif char == "\\" and quote != "'":
            escaped = True
        elif char == quote:
            quote = ""
        elif char in ("'", '"') and not quote:
            quote = char
        elif (quote != "'" and char in ("$", "`")) or (not quote and char in "*?[~"):
            expansion = True
        elif not quote and char in ";&|":
            operator = (
                text[index : index + 2]
                if text[index : index + 2] in ("&&", "||")
                else char
            )
            parts.append(_ShellPart(text[start:index].strip(), operator, expansion))
            index += len(operator)
            start, expansion = index, False
            continue
        index += 1
    parts.append(_ShellPart(text[start:].strip(), "", expansion))
    return tuple(parts)


def _command_argv(text):
    try:
        words = shlex.split(text, posix=True)
    except ValueError:
        words = text.split()
        position = next(
            (
                index
                for index, word in enumerate(words[:-1])
                if (word == "nwdes" or word.endswith("/nwdes"))
                and words[index + 1] in (*PARTS, "prompt", "lane", "slice")
            ),
            None,
        )
        return (
            None
            if position is None
            else (tuple(words[position + 1 :]), "unparsed command")
        )
    if len(words) < 2 or not (words[0] == "nwdes" or words[0].endswith("/nwdes")):
        return None
    return (
        (tuple(words[1:]), "")
        if words[1] in (*PARTS, "prompt", "lane", "slice")
        else None
    )


def _read_only_prompt(argv, parse_values):
    redirect = next(
        (index for index, word in enumerate(argv) if word == ">"), len(argv)
    )
    if redirect < len(argv) and redirect + 2 != len(argv):
        return None
    values = parse_values(argv[:redirect])
    if values is None:
        return None
    identity = tuple(values.get(name) for name in ("role", "task", "handoff"))
    if any(
        isinstance(value, str) and ("$" in value or "`" in value) for value in identity
    ):
        return None
    return values


def _line_commands(text, parse_values):
    parts = _shell_parts(text)
    commands = tuple(_command_argv(part.text) for part in parts)
    literal_chain = all(part.after in ("", "&&") for part in parts) and all(
        command is not None and not command[1] and not part.expansion
        for part, command in zip(parts, commands, strict=True)
    )
    result = []
    for index, (part, command) in enumerate(zip(parts, commands, strict=True)):
        if command is None:
            continue
        argv, error = command
        if not error and ("--help" in argv or "-h" in argv):
            continue
        file_values = any(
            word.startswith("--") and word.split("=", 1)[0].endswith("-file")
            for word in argv
        )
        unsafe = argv[0] in PARTS and (
            part.expansion or file_values or not literal_chain
        )
        values = (
            None
            if error or unsafe
            else _read_only_prompt(argv, parse_values)
            if argv[0] == "prompt"
            else parse_values(argv)
        )
        cause = error or ("not replayable" if values is None else "")
        result.append((index, argv, values, cause))
    return tuple(result)


def occurrences(sessions, parse_values):
    def in_session(session):
        results = {
            r.get("message", {}).get("toolCallId"): r
            for r in _messages(session)
            if r.get("message", {}).get("role") == "toolResult"
        }
        found = []
        for number, record in enumerate(session.records, 1):
            message = record.get("message", {})
            if message.get("role") != "assistant":
                continue
            for call in message.get("content", ()):
                if (
                    not isinstance(call, dict)
                    or call.get("type") != "toolCall"
                    or call.get("name") != "bash"
                ):
                    continue
                command = call.get("arguments", {}).get("command", "")
                result = results.get(call.get("id"))
                body = result.get("message", {}) if result else {}
                stdout = "\n".join(
                    c.get("text", "")
                    for c in body.get("content", ())
                    if isinstance(c, dict)
                )
                details = body.get("details")
                native_exit = (
                    details.get("exitCode") if isinstance(details, Mapping) else None
                )
                base = Occurrence(
                    session.identity,
                    call.get("id", ""),
                    number,
                    (),
                    None,
                    _instant(record["timestamp"], True),
                    _instant(result["timestamp"], True) if result else None,
                    body.get("isError") is False,
                    session.file.path,
                    command,
                    stdout,
                    native_exit=native_exit if type(native_exit) is int else None,
                )
                found.append(base)
                for offset, text in command_lines(command):
                    for segment, argv, values, cause in _line_commands(
                        text, parse_values
                    ):
                        location = f"{session.file.path}:{number + offset - 1}"
                        found.append(
                            replace(
                                base,
                                line=number + offset - 1,
                                segment=segment,
                                argv=argv,
                                values=values,
                                cause=cause + " " + location if cause else "",
                            )
                        )
        return tuple(found)

    return tuple(
        sorted(
            (o for s in sessions for o in in_session(s)),
            key=lambda o: (
                o.end_ms if o.end_ms is not None else o.start_ms,
                o.session,
                o.call,
                o.line,
                o.segment,
            ),
        )
    )


def session_occurrences(tree, parse_values):
    parsed = tuple(_session(file) for file in (tree.root, *tree.descendants))
    sessions = tuple(
        result.value
        for index, result in enumerate(parsed)
        if isinstance(result, Built)
        and (
            index == 0 or (not result.value.internal and _agent(result.value) in ROLES)
        )
    )
    return occurrences(sessions, parse_values)


def record_path(path, kind, scope):
    if kind not in ("craft", "review"):
        return path
    scope = (
        scope
        if kind != "review" or isinstance(scope, drafts.ReviewScope)
        else drafts.Legacy(scope)
    )
    key = drafts.DraftKey(kind, scope)
    return path.rsplit("/", 1)[0] + "/runs/" + key.filename


def _file_part(files, path, kind, scope):
    filename = record_path(path, kind, scope)
    raw = (files or {}).get(filename)
    if raw is None:
        return Unbound("missing or unreadable " + filename)
    parsed = handoff.parse_json(raw, filename)
    if isinstance(parsed, Refused) or not isinstance(parsed.value, Mapping):
        return Unbound("malformed " + filename)
    value = parsed.value
    if kind in ("craft", "review"):
        return value
    name = "examination" if kind == "examine" else kind
    part = value.get(name)
    if kind == "acceptance":
        part = (part or {}).get(scope, ())
    try:
        return handoff.freeze(
            handoff.expanded(
                handoff.CANONICAL_SCHEMAS["examination"]
                if kind == "examine"
                else handoff.ROLE_SCHEMAS[kind],
                part,
                value.get("facts", handoff.EMPTY),
            )
        )
    except (KeyError, TypeError, AttributeError):
        return Unbound("malformed " + filename + " " + kind)


def _seed_snapshot(files, path, kind, scope):
    filename = record_path(path, kind, scope)
    if kind in ("craft", "review") and filename in files and files[filename] is None:
        return None
    return _file_part(files, path, kind, scope)


def _equal(actual, replay):
    if isinstance(actual, Mapping) and isinstance(replay, Mapping):
        actual = {
            key: value
            for key, value in actual.items()
            if value not in (None, (), handoff.EMPTY)
        }
        replay = {
            key: value
            for key, value in replay.items()
            if value not in (None, (), handoff.EMPTY)
        }
        keys = set(actual) - ({"id"} if "id" not in replay else set())
        return keys == set(replay) and all(
            _equal(actual[key], replay[key]) for key in replay
        )
    if isinstance(actual, (tuple, list)) and isinstance(replay, (tuple, list)):
        return len(actual) == len(replay) and all(
            _equal(a, b) for a, b in zip(actual, replay, strict=True)
        )
    return actual == replay


@dataclass(frozen=True)
class _Record:
    close: Occurrence
    replay: object
    binding: Binding
    postimage: object = None
    files: Mapping | None = None


@dataclass(frozen=True)
class _Delivery:
    root: _Session
    sessions: tuple[_Session, ...]
    events: tuple[Occurrence, ...]
    closes: tuple[Occurrence, ...]
    history: History
    path: str

    @property
    def feature(self):
        return any(
            not session.internal and _agent(session) == "nw-solution-architect"
            for session in self.sessions[1:]
        )


def _seed_part(part, kind):
    if kind in ("craft", "review"):
        return drafts.seed(part, kind)
    # The projection is already expanded. Seed delegates retained-row semantics to drafts.
    previous = handoff.Handoff(
        "",
        handoff.Project(),
        handoff.EMPTY,
        design=part if kind == "design" else None,
        expectations=part if kind == "expectations" else None,
        examination=part if kind == "examine" else handoff.EMPTY,
        acceptance=handoff.freeze({"selected": part})
        if kind == "acceptance"
        else handoff.EMPTY,
    )

    # Identity fact mappings leave the expanded text untouched through the seed owner.
    def texts(value):
        if isinstance(value, Mapping):
            return tuple(t for child in value.values() for t in texts(child))
        if isinstance(value, (tuple, list)):
            return tuple(t for child in value for t in texts(child))
        return (value,) if isinstance(value, str) else ()

    previous = replace(
        previous, facts=handoff.freeze({text: text for text in texts(part)})
    )
    return drafts.seed(previous, kind, "selected")


def _draft_start(close, events) -> Occurrence | None:
    start = None
    for event in events:
        if event is close:
            return start
        if (
            event.part != close.part
            or event.scope != close.scope
            or not event.ok
            or event.end_ms is None
        ):
            continue
        if event.verb in ("close", "abort"):
            start = None
        elif event.verb == "open" or start is None:
            start = event
    return start


def _review_evidence_at(history, event, content):
    head = next(
        (
            commit.id
            for commit in reversed((*history.ancestors, *history.chain))
            if commit.committer_s <= event.start_ms // 1000
        ),
        None,
    )
    return (
        drafts.ReviewEvidence(head, (), content)
        if head is not None
        else Unbound(
            f"not replayable {event.path}:{event.line}: no history HEAD at observation"
        )
    )


def _recorded_review_content(close, history, path):
    """The oracle content the newest published review record carries, or None.

    Uncommitted oracle bytes cannot be recomputed from history, so replay reuses the
    recorded content and still checks every other stamp against the published record.
    """
    if close.part != "review":
        return None
    snapshots = (
        history.current,
        *(commit.files for commit in (*history.chain, *history.ancestors)),
    )
    for files in snapshots:
        record = _file_part(files, path, close.part, close.scope)
        if isinstance(record, Mapping):
            return record.get("content")
    return None


def _replay(close, events, records, history, path):
    start = _draft_start(close, events)
    if start is not None and start.session != close.session:
        return Unbound(
            f"not replayable {start.path}:{start.line}: draft started in session "
            + start.session
            + " and closed in "
            + close.session
        )
    same = tuple(
        o
        for o in events
        if o.session == close.session
        and o.part == close.part
        and o.scope == close.scope
        and o.ok
        and o.end_ms is not None
        and o.end_ms <= close.end_ms
        and not (
            o.end_ms == close.end_ms
            and o.call == close.call
            and (o.line, o.segment) > (close.line, close.segment)
        )
    )
    active = (
        same[next(index for index, event in enumerate(same) if event is start) :]
        if start is not None
        else (close,)
    )
    content = _recorded_review_content(close, history, path)
    draft = drafts.empty(close.part)
    for event in active:
        if event.cause or event.values is None:
            return Unbound(event.cause or f"not replayable {event.path}:{event.line}")
        evidence = (
            _review_evidence_at(history, event, content)
            if drafts.needs_review_evidence(close.part, event.verb)
            else None
        )
        if isinstance(evidence, Unbound):
            return evidence
        if event.verb == "open":
            previous = next(
                (
                    r.postimage
                    for r in reversed(records)
                    if r.close.part == close.part
                    and r.close.scope == close.scope
                    and isinstance(r.binding, Bound)
                    and r.close.end_ms <= event.end_ms
                ),
                None,
            )
            if previous is None:
                commits = tuple(
                    c
                    for c in (*history.ancestors, *history.chain)
                    if c.committer_s < event.start_ms // 1000
                )
                previous = (
                    _seed_snapshot(commits[-1].files, path, close.part, close.scope)
                    if commits
                    else None
                )
                if isinstance(previous, Unbound):
                    return previous
            draft = (
                _seed_part(previous, close.part)
                if previous is not None
                else drafts.seed(None, close.part)
            )
        elif event.verb == "close":
            if close.part == "review":
                reviewed = drafts.review_record(
                    draft,
                    evidence,
                    event.values.get("outcome"),
                    event.values.get("diagnostic"),
                )
                if isinstance(reviewed, Refused):
                    return Unbound(
                        f"not replayable {event.path}:{event.line}: "
                        + "; ".join(
                            defect.what + " " + defect.why
                            for defect in reviewed.defects
                        )
                    )
                return reviewed.value
            if close.part == "craft":
                return handoff.freeze(
                    {
                        **draft,
                        "outcome": event.values.get("outcome"),
                        "diagnostic": event.values.get("diagnostic"),
                        "blocked_by": event.values.get("blocked-by"),
                        "slice": close.scope,
                    }
                )
            if close.part == "examine":
                problems = handoff.examination_observation_problems(draft)
                if problems:
                    return Unbound(
                        f"not replayable {event.path}:{event.line}: "
                        + "; ".join(
                            defect.what + " " + defect.why for defect in problems
                        )
                    )
                return handoff.examination_verdicts(draft)
            return draft
        else:
            edit = drafts.prepare_edit(close.part, event.verb, event.values)
            if isinstance(edit, Refused):
                return Unbound(f"not replayable {event.path}:{event.line}")
            if evidence is not None:
                edit = drafts.stamp_review(edit, evidence)
            draft = drafts.apply_edit(draft, edit)
        if isinstance(draft, Refused):
            return Unbound(f"not replayable {event.path}:{event.line}")
    return Unbound(f"not replayable {close.path}:{close.line}")


def _bind(close, replay, records, delivery):
    closes, history, path = delivery.closes, delivery.history, delivery.path
    if isinstance(replay, Unbound):
        return _Record(close, replay, replay)
    later = tuple(
        o
        for o in closes
        if o.end_ms > close.end_ms
        and (
            (o.part == close.part and o.scope == close.scope)
            or (close.part == "examine" and o.part == "expectations")
        )
    )
    expectation = next(
        (
            r
            for r in reversed(records)
            if r.close.part == "expectations"
            and r.close.end_ms < close.end_ms
            and isinstance(r.binding, Bound)
        ),
        None,
    )

    def matches(files):
        actual = _file_part(files, path, close.part, close.scope)
        if isinstance(actual, Unbound):
            return actual
        if not _equal(actual, replay):
            return Unbound(
                "current handoff not equal to replay " + path + " " + close.identity
            )
        if close.part == "examine":
            rows = _file_part(files, path, "expectations", None)
            if (
                expectation is None
                or isinstance(rows, Unbound)
                or rows != expectation.postimage
            ):
                return Unbound(
                    "expectations not equal to latest bound expectations "
                    + path
                    + " "
                    + close.identity
                )
        return actual

    commits = (
        history.chain if close.part in ("review", "examine") else history.ancestors
    )
    cause = "no bound postimage equal to replay " + path + " " + close.identity
    for commit in commits:
        if commit.committer_s < close.end_ms // 1000:
            continue
        intervening = next(
            (o for o in later if o.end_ms // 1000 <= commit.committer_s), None
        )
        if intervening:
            cause = "intervening " + intervening.part + " close " + intervening.identity
            continue
        actual = matches(commit.files)
        if not isinstance(actual, Unbound):
            return _Record(close, replay, Bound(commit.id), actual, commit.files)
        cause = actual.cause + " at " + commit.id
    if later:
        cause = "later " + later[0].part + " close " + later[0].identity
    elif history.head != history.candidate.id:
        cause += "; HEAD is not candidate " + history.candidate.id
    elif not history.clean:
        cause = "paths outside handoff directory: " + ", ".join(history.dirty)
    else:
        actual = matches(history.current)
        if not isinstance(actual, Unbound):
            return _Record(close, replay, Bound(None), actual, history.current)
        cause = actual.cause
    return _Record(close, replay, Unbound(cause))


def _prompt_for(root, role, task, before, events):
    return next(
        (
            o
            for o in reversed(events)
            if o.session == root.identity
            and o.part == "prompt"
            and o.ok
            and o.end_ms is not None
            and o.end_ms < before
            and (o.values or {}).get("role") == role
            and (task is None or (o.values or {}).get("task") == task)
        ),
        None,
    )


def _record_only(commit, path):
    directory = path.rsplit("/", 1)[0] + "/"
    return all(changed.startswith(directory) for changed in commit.changed)


def _endpoint(records, delivery):
    closes, root, sessions = delivery.closes, delivery.root, delivery.sessions
    events, history, path = delivery.events, delivery.history, delivery.path
    exams = tuple(r for r in records if r.close.part == "examine")
    if not exams:
        return NotMeasured(
            (
                "no successful examine close; missing examination or expectations "
                + path,
            )
        ), None
    latest = exams[-1]
    close = latest.close
    causes = []
    if (
        len(
            tuple(o for o in closes if o.part == "examine" and o.end_ms == close.end_ms)
        )
        != 1
    ):
        causes.append("ambiguous examine closes " + close.identity)
    if isinstance(latest.binding, Unbound):
        causes.append(latest.binding.cause)
    session = next(s for s in sessions if s.identity == close.session)
    starts = tuple(r[2] for r in _requests(session))
    prompt = _prompt_for(
        root, "nw-user-examiner", "examine", min(starts, default=close.start_ms), events
    )
    candidate = history.candidate
    if prompt is None:
        causes.append("missing candidate examine prompt " + candidate.id)
    elif candidate.committer_s >= prompt.start_ms // 1000:
        causes.append(
            (
                "candidate time ambiguous "
                if candidate.committer_s == prompt.start_ms // 1000
                else "candidate committed after examine prompt "
            )
            + candidate.id
        )
    if isinstance(latest.binding, Bound):
        for commit in history.chain:
            if latest.binding.commit == commit.id:
                if not _record_only(commit, path):
                    causes.append("product change after candidate " + commit.id)
                break
            if not _record_only(commit, path):
                causes.append("product change after candidate " + commit.id)
        fixed = _file_part(latest.files, path, "expectations", None)
        rows = fixed.get("rows", ()) if isinstance(fixed, Mapping) else ()
        ids = tuple(row.get("id") for row in rows)
        verdicts = latest.postimage
        if not ids:
            causes.append("empty expectations " + path)
        elif len(set(ids)) != len(ids):
            causes.append("duplicate expectation ids " + path)
        if not isinstance(verdicts, Mapping) or set(verdicts) != set(ids):
            causes.append("examination keys differ from expectation ids " + path)
        elif any(verdict.get("verdict") != "met" for verdict in verdicts.values()):
            causes.extend(
                "unmet expectation " + identity
                for identity, verdict in verdicts.items()
                if verdict.get("verdict") != "met"
            )
    return (NotMeasured(tuple(causes)) if causes else Accepted(close.end_ms)), latest


def _whole_candidate_reviews(records, events):
    subjects_declared = any(
        event.part == "review" and event.subject != "legacy" for event in events
    )
    return tuple(
        record
        for record in records
        if record.close.part == "review"
        and (not subjects_declared or record.close.subject == "candidate")
    )


def _lifecycle(records, endpoint, latest, delivery):
    root, events, history, path = (
        delivery.root,
        delivery.events,
        delivery.history,
        delivery.path,
    )
    causes = list(endpoint.causes if isinstance(endpoint, NotMeasured) else ())
    reviews = _whole_candidate_reviews(records, events)

    def required(kind, scope=None, accepted=False):
        candidates = tuple(
            r
            for r in (reviews if kind == "review" else records)
            if r.close.part == kind
            and (kind == "review" or r.close.scope == scope)
            and (latest is None or r.close.end_ms <= latest.close.end_ms)
        )
        last = candidates[-1] if candidates else None
        if (
            last is None
            or isinstance(last.binding, Unbound)
            or (accepted and last.postimage.get("outcome") != "accepted")
        ):
            causes.append(
                "missing bound accepted "
                + kind
                + (" " + scope if scope else "")
                + (
                    ": " + last.binding.cause
                    if last and isinstance(last.binding, Unbound)
                    else ""
                )
            )
        return last

    if delivery.feature:
        required("design")
    required("expectations")
    files = latest.files if latest and latest.files else history.current
    design = _file_part(files, path, "design", None)
    for scope in design.get("slices", {}) if isinstance(design, Mapping) else ():
        required("acceptance", scope)
        required("craft", scope, True)
    review = required("review", accepted=True)
    if review:
        prompt = _prompt_for(
            root, "nw-software-crafter-reviewer", None, review.close.start_ms, events
        )
        if prompt is None or prompt.start_ms // 1000 <= history.candidate.committer_s:
            causes.append(
                (
                    "review candidate time ambiguous "
                    if prompt is not None
                    and prompt.start_ms // 1000 == history.candidate.committer_s
                    else "review not of candidate "
                )
                + history.candidate.id
            )
    return tuple(dict.fromkeys(causes))


def _tail(endpoint, latest, delivery):
    root, events, history, path = (
        delivery.root,
        delivery.events,
        delivery.history,
        delivery.path,
    )
    if (
        isinstance(endpoint, NotMeasured)
        or latest is None
        or not isinstance(latest.binding, Bound)
        or latest.binding.commit is None
    ):
        return "not measured (no bound committed examination for lane integration)"
    for event in events:
        if (
            event.session != root.identity
            or event.part != "lane"
            or event.argv[1:2] != ("integrate",)
            or not event.ok
            or event.end_ms is None
            or event.end_ms < endpoint.end_ms
        ):
            continue
        tip = (event.values or {}).get("candidate")
        chain = tuple(c.id for c in history.chain)
        if (
            tip not in chain
            or latest.binding.commit not in chain
            or chain.index(tip) < chain.index(latest.binding.commit)
        ):
            continue
        if all(_record_only(c, path) for c in history.chain[: chain.index(tip) + 1]):
            return _seconds(event.end_ms - endpoint.end_ms)
    return (
        "not measured (no lane integrate qualifying for candidate "
        + history.candidate.id
        + ")"
    )


def history_snapshot_ids(ancestors, chain, events):
    """Select binding windows and exact pre-open seeds before reading their bytes."""
    closes = tuple(
        event
        for event in events
        if event.ok
        and event.end_ms is not None
        and event.part in PARTS
        and event.verb == "close"
    )
    early_start = min(
        (
            event.end_ms // 1000
            for event in closes
            if event.part not in ("review", "examine")
        ),
        default=None,
    )
    late_start = min(
        (
            event.end_ms // 1000
            for event in closes
            if event.part in ("review", "examine")
        ),
        default=None,
    )
    windows = (
        *(
            commit.id
            for commit in ancestors
            if early_start is not None and commit.committer_s >= early_start
        ),
        *(
            commit.id
            for commit in chain
            if late_start is not None and commit.committer_s >= late_start
        ),
    )
    commits = (*ancestors, *chain)
    seeds = tuple(
        next(
            (
                commit.id
                for commit in reversed(commits)
                if commit.committer_s < event.start_ms // 1000
            ),
            None,
        )
        for event in events
        if event.ok
        and event.end_ms is not None
        and event.part in PARTS
        and event.verb == "open"
    )
    return frozenset(
        (*windows, *(identity for identity in seeds if identity is not None))
    )


def _record_lines(records, events):
    lines = []
    reviews = _whole_candidate_reviews(records, events)
    for record in records:
        close = record.close
        prefix = (
            "record "
            + close.part
            + (
                " " + close.subject
                if close.part == "review" and close.subject != "legacy"
                else ""
            )
            + (" " + close.slice if close.slice else "")
            + " "
            + close.identity
        )
        if isinstance(record.binding, Unbound):
            lines.append(prefix + " not bound (" + record.binding.cause + ")")
            continue
        lines.append(prefix + " bound " + (record.binding.commit or "current handoff"))
        if close.part == "craft":
            for command in record.postimage.get("commands", ()):
                native = next(
                    (
                        o
                        for o in reversed(events)
                        if not o.argv
                        and o.session == close.session
                        and o.command == command["command"]
                        and o.end_ms is not None
                    ),
                    None,
                )
                status = (
                    "not observed"
                    if native is None
                    else "succeeded"
                    if native.ok
                    else "failed"
                )
                line = f"recorded {close.scope} {command['command']} exit {command['exit']} native {status}"
                lines.append(
                    line
                    + (
                        f" native exit {native.native_exit}"
                        if native is not None and native.native_exit is not None
                        else ""
                    )
                )
        elif close.part == "review" and record in reviews:
            lines.append(
                f"review outcome {record.postimage.get('outcome')} findings {len(record.postimage.get('findings', ()))}"
            )
    return tuple(lines)


def unavailable_report(causes, objective_minutes=None, *, root=False):
    return replace(
        _report((), objective_minutes),
        source="host",
        runtime="unknown",
        elapsed_ms=None,
        elapsed_missing=tuple(causes),
        host_missing=tuple(causes) if root else (),
        rework_missing="not declared",
        delivery_lines=(
            "integration tail: not measured (" + ", ".join(causes) + ")",
            "qualification: incomplete (" + ", ".join(causes) + ")",
            "observation provenance is not verified beyond commit order",
        ),
    )


def report_from_sessions(
    tree: SessionTree,
    rework: bytes | None,
    rework_label: str | None,
    objective_minutes: int | None,
    *,
    evidence: SessionEvidence | None = None,
):
    evidence = evidence or SessionEvidence()
    history, handoff_path = evidence.history, evidence.handoff_path
    parsed_root = _session(tree.root)
    name = ROOT_NAME.fullmatch(tree.root_name)
    if (
        isinstance(parsed_root, Refused)
        or name is None
        or (isinstance(parsed_root, Built) and parsed_root.value.identity != name[1])
    ):
        why = (
            "; ".join(d.what + " " + d.why for d in parsed_root.defects)
            if isinstance(parsed_root, Refused)
            else "misnamed root or mismatched id"
        )
        return Built(
            unavailable_report(
                ("root session " + tree.root_absolute + " " + why,),
                objective_minutes,
                root=True,
            )
        )
    root = parsed_root.value
    parsed = tuple(
        _session(file) for file in sorted(tree.descendants, key=lambda f: f.path)
    )
    sessions = (root, *(p.value for p in parsed if isinstance(p, Built)))
    defects = tuple(
        d.what + " " + d.why
        for p in parsed
        if isinstance(p, Refused)
        for d in p.defects
    )
    duplicate = tuple(
        "duplicate session id " + s.identity + " " + s.file.path
        for i, s in enumerate(sessions)
        if any(p.identity == s.identity for p in sessions[:i])
    )
    roles = tuple(s for s in sessions[1:] if not s.internal and _agent(s) in ROLES)
    requests = tuple(r for s in roles for r in _requests(s))
    marks = _rework(rework, rework_label, requests)
    marked = marks.value if isinstance(marks, Built) else frozenset()
    rework_missing = evidence.rework_cause or (
        "; ".join(d.what + " " + d.why for d in marks.defects)
        if isinstance(marks, Refused)
        else "not declared"
        if rework is None
        else None
    )
    intervals = tuple(
        RequestInterval(r[4], None, None, r[2], r[3], r[1] > 0, (r[0], r[1]) in marked)
        for r in requests
        if r[3] is not None
    )
    runtime = next(
        (
            r["runtime"]["version"]
            for r in root.records
            if isinstance(r.get("runtime"), dict) and "version" in r["runtime"]
        ),
        "unknown",
    )
    base = replace(
        _report(intervals, objective_minutes),
        source="host",
        runtime=runtime,
        requests=len(requests),
        continuations=sum(r[1] > 0 for r in requests),
        rework=len(marked),
        continuation_and_rework=sum(
            r[1] > 0 and (r[0], r[1]) in marked for r in requests
        ),
        unanswered=sum(r[3] is None for r in requests),
        excluded=tuple(
            sorted(
                (s.file.path, "internal" if s.internal else "no role")
                for s in sessions[1:]
                if s.internal or _agent(s) not in ROLES
            )
        ),
        rework_missing=rework_missing,
    )
    events = occurrences((root, *roles), evidence.parse_values)
    closes = tuple(
        o
        for o in events
        if o.part in PARTS
        and o.ok
        and o.end_ms is not None
        and (o.verb == "close" or o.argv[1:2] == ("close",))
    )
    delivery = (
        _Delivery(root, sessions, events, closes, history, handoff_path)
        if history is not None
        else None
    )
    records = ()
    if history is not None:
        for close in closes:
            replay = _replay(close, events, records, history, handoff_path)
            records = (
                *records,
                _bind(close, replay, records, delivery),
            )
    causes = (
        *evidence.causes,
        *defects,
        *duplicate,
        *(history.causes if history else ()),
    )
    endpoint, latest = (
        _endpoint(records, delivery)
        if history
        else (NotMeasured(tuple(causes) or ("no candidate",)), None)
    )
    if causes:
        endpoint = NotMeasured(
            tuple(
                dict.fromkeys(
                    (
                        *causes,
                        *(endpoint.causes if isinstance(endpoint, NotMeasured) else ()),
                    )
                )
            )
        )
    architects = tuple(s for s in roles if _agent(s) == "nw-solution-architect")
    starts = (
        tuple(r[2] for s in architects for r in _requests(s))
        if architects
        else tuple(r[2] for r in _requests(root))[:1]
    )
    if not starts:
        endpoint = NotMeasured(
            (
                *(endpoint.causes if isinstance(endpoint, NotMeasured) else ()),
                "no design start or root bug-report intake",
            )
        )
    qualification = (
        _lifecycle(records, endpoint, latest, delivery) if history else endpoint.causes
    )
    return Built(
        replace(
            base,
            elapsed_ms=endpoint.end_ms - min(starts)
            if isinstance(endpoint, Accepted)
            else None,
            elapsed_missing=endpoint.causes
            if isinstance(endpoint, NotMeasured)
            else (),
            delivery_lines=(
                "integration tail: "
                + (
                    _tail(endpoint, latest, delivery)
                    if history
                    else "not measured (no lane integrate; no candidate)"
                ),
                "qualification: "
                + (
                    "incomplete (" + ", ".join(qualification) + ")"
                    if qualification
                    else "complete"
                ),
                "observation provenance is not verified beyond commit order",
                *_record_lines(records, events),
            ),
        )
    )


def _seconds(ms):
    sign = "-" if ms < 0 else ""
    return f"{sign}{abs(ms) // 1000}.{abs(ms) % 1000:03d}"


def render(report: TrialReport) -> str:
    def diagnostic(text):
        return " ".join(text.split())

    report = replace(
        report,
        elapsed_missing=tuple(diagnostic(cause) for cause in report.elapsed_missing),
        host_missing=tuple(diagnostic(cause) for cause in report.host_missing),
        rework_missing=diagnostic(report.rework_missing)
        if report.rework_missing
        else None,
        delivery_lines=tuple(
            diagnostic(line)
            if line.startswith(("integration tail:", "qualification:"))
            or (line.startswith("record ") and " not bound (" in line)
            else line
            for line in report.delivery_lines
        ),
    )
    missing = (
        "not measured (" + ", ".join(report.host_missing) + ")"
        if report.host_missing
        else None
    )
    rework = (
        "unknown (" + report.rework_missing + ")" if report.rework_missing else None
    )
    return (
        "\n".join(
            (
                "source: supplied, not host-recorded"
                if report.source == "supplied"
                else "source: host-recorded omp sessions",
                "runtime: "
                + (missing or ("none" if report.runtime is None else report.runtime)),
                "elapsed_seconds: "
                + (
                    _seconds(report.elapsed_ms)
                    if report.elapsed_ms is not None
                    else "not measured (" + ", ".join(report.elapsed_missing) + ")"
                ),
                *report.delivery_lines,
                *(
                    ("role_seconds: " + missing,)
                    if missing
                    else tuple(
                        "role_seconds: " + role + " " + _seconds(ms)
                        for role, ms in report.role_ms
                    )
                    or ("role_seconds: none",)
                ),
                "requests: " + (missing or str(report.requests)),
                "continuations: " + (missing or str(report.continuations)),
                "rework: "
                + (
                    missing
                    or rework
                    or (
                        str(report.rework)
                        + (
                            " supplied"
                            if report.source == "supplied"
                            else " root-declared"
                        )
                    )
                ),
                "continuation_and_rework: "
                + (missing or rework or str(report.continuation_and_rework)),
                "unanswered: " + (missing or str(report.unanswered)),
                "max_concurrent_crafters: "
                + (missing or str(report.max_concurrent_crafters)),
                "max_concurrent_reviewers: "
                + (missing or str(report.max_concurrent_reviewers)),
                *(
                    ("excluded: " + missing,)
                    if missing
                    else tuple(
                        f"excluded: {path} {reason}" for path, reason in report.excluded
                    )
                    or ("excluded: none",)
                ),
                "objective_minutes: "
                + (
                    "none"
                    if report.objective_minutes is None
                    else str(report.objective_minutes)
                ),
            )
        )
        + "\n"
    )
