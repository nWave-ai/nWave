"""The pre-review checks a project declares and the receipt a handoff record keeps of them.

Pure: text in, values or a refusal out. The declaration is the committed file
.nwave/prereview.json of the candidate: a list of named commands and, optionally, one remote
verification command. nwstep names no check of its own; what runs is what the file declares.
"""

from __future__ import annotations

import json
import re
import shlex
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from nwstep.domain.refusal import Refusal


if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from nwstep.domain.command_outcome import CommandOutcome


FILE = ".nwave/prereview.json"
# The name of the receipt among the values of a record.
KEY = "prereview"
# The remote command is told which candidate to verify through this environment variable.
CANDIDATE_VARIABLE = "NWAVE_CANDIDATE"
# No spawn is unbounded: a declared command that runs longer is stopped, and that is not a pass.
# One hour leaves room for a check that first waits its turn on a project lock.
COMMAND_TIMEOUT_S = 3600
SHAPE = (
    '{"checks": [{"name": "NAME", "command": ["PROGRAM", "ARGUMENT"]}], '
    '"remote": {"command": ["PROGRAM"]}}'
)
WHY_DECLARED = (
    "a declaration that cannot be read is neither a pass nor 'no checks declared'; the file is "
    f"{SHAPE}, both members optional, each command a list of words started without a shell"
)
WHY_PASSED = (
    "the project declares these checks so that a candidate reaches review only after each "
    "exits 0; a check that did not run is not a check that passed"
)
# A check name is one word that is safe as a file name: the output of each check is kept under it.
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_LINE_BOUNDARIES = "\x00\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029"
# The states a receipt keeps, as the record stores them and the summary reads them back.
_COMMITTED = "committed"
_MODIFIED = "modified"
_UNNAMED = "unnamed"
_REQUESTED = "requested"
_KEPT = "kept"
_WITHHELD = "withheld"
_NO_RESULT = "no-result"


@dataclass(frozen=True)
class Check:
    name: str
    command: tuple[str, ...]


@dataclass(frozen=True)
class Declaration:
    """What one candidate declares; with neither member it declares nothing."""

    checks: tuple[Check, ...] = ()
    remote: tuple[str, ...] | None = None


@dataclass(frozen=True)
class Committed:
    """git names the candidate exactly: a commit and a clean work tree."""

    commit: str

    def as_value(self) -> dict[str, Any]:
        return {"state": _COMMITTED, "commit": self.commit}


@dataclass(frozen=True)
class Modified:
    """The work tree differs from its commit, so the commit alone does not name what the checks ran on."""

    commit: str

    def as_value(self) -> dict[str, Any]:
        return {"state": _MODIFIED, "commit": self.commit}


@dataclass(frozen=True)
class Unnamed:
    """git could not name the candidate; the reason is kept and shown."""

    reason: str

    def as_value(self) -> dict[str, Any]:
        return {"state": _UNNAMED, "reason": self.reason}


Candidate = Committed | Modified | Unnamed


@dataclass(frozen=True)
class CheckResult:
    """One declared check as it ran: an exit code, or the reason it gave none (it could not start, or ran past the bound),
    and the file its full output was kept in."""

    check: Check
    outcome: CommandOutcome
    kept: str

    @property
    def passed(self) -> bool:
        return self.outcome.problem is None and self.outcome.exit_code == 0

    def as_value(self) -> dict[str, Any]:
        return {
            "name": self.check.name,
            "argv": list(self.check.command),
            "exit_code": self.outcome.exit_code,
            "duration_s": round(self.outcome.duration_s, 3),
        }

    def failure(self) -> str:
        shown = f"'{self.check.name}' `{shlex.join(self.check.command)}`"
        if self.outcome.problem is not None:
            return f"{shown} {self.outcome.problem}"
        return f"{shown} exited {self.outcome.exit_code} (output kept in {self.kept})"


@dataclass(frozen=True)
class Request:
    """The remote verification is due: run the command, told this commit."""

    command: tuple[str, ...]
    commit: str

    def observed(self, outcome: CommandOutcome) -> dict[str, Any]:
        value: dict[str, Any] = {"argv": list(self.command), "candidate": self.commit}
        if outcome.problem is not None:
            return {**value, "state": _NO_RESULT, "reason": outcome.problem}
        return {
            **value,
            "state": _REQUESTED,
            "exit_code": outcome.exit_code,
            "duration_s": round(outcome.duration_s, 3),
        }


@dataclass(frozen=True)
class Kept:
    """An earlier handoff record of this candidate holds the result; it is shown, not requested again."""

    earlier: Mapping[str, Any]

    def as_value(self) -> dict[str, Any]:
        return {**self.earlier, "state": _KEPT}


@dataclass(frozen=True)
class Withheld:
    """The candidate is not one commit a remote verification can be told, so nothing is requested."""

    command: tuple[str, ...]
    reason: str

    def as_value(self) -> dict[str, Any]:
        return {"argv": list(self.command), "state": _WITHHELD, "reason": self.reason}


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    names = [name for name, _ in pairs]
    if len(set(names)) != len(names):
        raise ValueError("a JSON object names a key twice")
    return dict(pairs)


def _unknown(member: str, value: dict[str, Any], known: tuple[str, ...]) -> list[str]:
    return [
        f"{member}{key}: not a member (the members are {', '.join(known)})"
        for key in value
        if key not in known
    ]


def _word_problem(word: object) -> bool:
    return (
        not isinstance(word, str)
        or not word
        or any(character in word for character in _LINE_BOUNDARIES)
    )


def _command(member: str, value: object) -> list[str]:
    if not isinstance(value, list) or not value:
        return [f"{member}: a command is a non-empty list of words"]
    if any(_word_problem(word) for word in value):
        return [f"{member}: each word is a non-empty string on one line, without NUL"]
    return []


def _check(index: int, entry: object, earlier: list[object]) -> list[str]:
    member = f"checks[{index}]"
    if not isinstance(entry, dict):
        return [f"{member}: a check is an object with a name and a command"]
    name = entry.get("name")
    problems = _unknown(member + ".", entry, ("name", "command"))
    if not isinstance(name, str) or not _NAME.match(name):
        problems.append(
            f"{member}.name: one word of letters, digits, '.', '_' and '-', starting with a letter or digit"
        )
    elif name in earlier:
        problems.append(f"{member}.name: {name!r} is declared twice")
    return problems + _command(member + ".command", entry.get("command"))


def _checks(value: object) -> list[str]:
    if not isinstance(value, list):
        return ["checks: a list of checks"]
    names = [entry.get("name") if isinstance(entry, dict) else None for entry in value]
    return [
        problem
        for index, entry in enumerate(value)
        for problem in _check(index, entry, names[:index])
    ]


def _remote(value: object) -> list[str]:
    if not isinstance(value, dict):
        return ["remote: an object with a command"]
    return _unknown("remote.", value, ("command",)) + _command(
        "remote.command", value.get("command")
    )


def _problems(document: object) -> list[str]:
    if not isinstance(document, dict):
        return ["the declaration is a JSON object"]
    return (
        _unknown("", document, ("checks", "remote"))
        + (_checks(document["checks"]) if "checks" in document else [])
        + (_remote(document["remote"]) if "remote" in document else [])
    )


def parse(text: str | None, path: str) -> Declaration:
    """The declaration of a candidate from the text of its file; no file declares nothing.

    Every defect of the document is named in one refusal. A document that cannot be read is
    refused: it is never taken for a candidate that declares nothing.
    """
    if text is None:
        return Declaration()
    try:
        document = json.loads(text, object_pairs_hook=_unique)
    except (ValueError, RecursionError) as error:
        raise Refusal(
            what=f"{path} is not one JSON document: {error}", why=WHY_DECLARED
        ) from None
    problems = _problems(document)
    if problems:
        raise Refusal(
            what=f"{path} is malformed: {'; '.join(problems)}", why=WHY_DECLARED
        )
    return Declaration(
        tuple(
            Check(entry["name"], tuple(entry["command"]))
            for entry in document.get("checks", ())
        ),
        tuple(document["remote"]["command"]) if "remote" in document else None,
    )


def blocked(results: Iterable[CheckResult]) -> Refusal | None:
    """The refusal that names every declared check that did not exit 0, or None when each did."""
    failed = [result.failure() for result in results if not result.passed]
    if not failed:
        return None
    return Refusal(
        what=f"{len(failed)} pre-review check(s) failed: {'; '.join(failed)}",
        why=WHY_PASSED,
    )


def _holds_result(receipt: Mapping[str, Any], commit: str) -> bool:
    remote = receipt.get("remote") or {}
    return remote.get("candidate") == commit and remote.get("state") in (
        _REQUESTED,
        _KEPT,
    )


def remote_request(
    declared: Declaration,
    candidate: Candidate,
    earlier: Iterable[Mapping[str, Any]],
) -> Request | Kept | Withheld | None:
    """What becomes of the remote verification at this record; None when the project declares none.

    It is requested once per candidate: only for a candidate git names exactly, and only when
    no earlier receipt of that candidate holds its result. A request that gave no exit code left
    no result, so it is due again.
    """
    if declared.remote is None:
        return None
    if isinstance(candidate, Modified):
        return Withheld(
            declared.remote,
            "the candidate has uncommitted changes, which no commit names",
        )
    if isinstance(candidate, Unnamed):
        return Withheld(
            declared.remote, f"git cannot name the candidate: {candidate.reason}"
        )
    held = next(
        (
            receipt["remote"]
            for receipt in earlier
            if _holds_result(receipt, candidate.commit)
        ),
        None,
    )
    if held is not None:
        return Kept(held)
    return Request(declared.remote, candidate.commit)


def receipt(
    candidate: Candidate,
    results: Iterable[CheckResult],
    remote: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """The receipt as the handoff record keeps it; it has a remote entry only when one is declared."""
    value: dict[str, Any] = {
        "candidate": candidate.as_value(),
        "checks": [result.as_value() for result in results],
    }
    if remote is not None:
        value["remote"] = dict(remote)
    return value


def _candidate_line(candidate: Mapping[str, Any]) -> str:
    if candidate["state"] == _UNNAMED:
        return f"  - candidate: INDETERMINATE: {candidate['reason']}"
    suffix = " with uncommitted changes" if candidate["state"] == _MODIFIED else ""
    return f"  - candidate: commit {candidate['commit']}{suffix}"


def _remote_line(remote: Mapping[str, Any]) -> str:
    command = f"`{shlex.join(remote['argv'])}`"
    state = remote["state"]
    if state == _WITHHELD:
        return f"  - remote verification: INDETERMINATE: {command} not requested: {remote['reason']}"
    if state == _NO_RESULT:
        return f"  - remote verification: INDETERMINATE: {command} for {remote['candidate']} {remote['reason']}"
    again = (
        " (requested at an earlier handoff record of this candidate; not requested again)"
        if state == _KEPT
        else ""
    )
    return (
        f"  - remote verification: {command} for {remote['candidate']} exited "
        f"{remote['exit_code']} in {remote['duration_s']}s{again}"
    )


def lines(value: Mapping[str, Any]) -> list[str]:
    """The receipt as the reviewer's summary prints it; only a check that exited is shown with an exit code."""
    checks = [
        f"  - check {check['name']}: `{shlex.join(check['argv'])}` exited "
        f"{check['exit_code']} in {check['duration_s']}s"
        for check in value["checks"]
    ]
    return [
        "- **pre-review receipt** (run by the tool when this record was written):",
        _candidate_line(value["candidate"]),
        *(checks or ["  - no checks declared"]),
        *([_remote_line(value["remote"])] if "remote" in value else []),
    ]
