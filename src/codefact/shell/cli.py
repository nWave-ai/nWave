"""The code-fact command: argument parsing, snapshot reads and JSON rendering."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from codefact import index, python_ast, scope, text_search
from codefact.fold import resolve, verify_composition_coverage
from codefact.impact import report
from codefact.model import (
    STABLE_CORE_CAPABILITY_IDS,
    Answered,
    Capability,
    Failed,
    Indeterminate,
    Refreshed,
    RefreshIndeterminate,
)
from codefact.shell.files import read_tree


PROVIDERS = verify_composition_coverage(
    (*index.PROVIDERS, python_ast.PROVIDER, text_search.PROVIDER)
)

# Legacy parity: a resolution that carries no cause names this one.
NO_COVERING_PROVIDER = "no-covering-provider"


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        super().error(
            message
            + " HOW: use `code-fact query.callers-of SYMBOL --root ROOT`; query.atoms-in-file ignores any subject, only --root FILE_OR_ROOT."
        )


def _print(document):
    print(json.dumps(document, sort_keys=True))


def _explain(what, why, how):
    print(f"WHAT: {what}. WHY: {why}. HOW: {how}.", file=sys.stderr)


def _cause_of(resolution) -> str:
    return resolution.cause if isinstance(resolution, Failed) else NO_COVERING_PROVIDER


def main(argv: list[str] | None = None) -> int:
    tokens = sys.argv[1:] if argv is None else list(argv)
    if tokens[:1] == ["find-similar-responsibility"]:
        return _similar(tokens[1:])
    if tokens[:1] == ["impacted-tests"]:
        return _impacted(tokens[1:])
    parser = _Parser(prog="code-fact")
    parser.add_argument(
        "capability", choices=[*sorted(STABLE_CORE_CAPABILITY_IDS), "refresh"]
    )
    parser.add_argument("subject", nargs="?")
    parser.add_argument("--root", default=".")
    args = parser.parse_args(tokens)
    if args.capability == "refresh":
        if args.subject:
            parser.error("refresh takes no subject")
        root_ignore = Path(args.root) / ".gitignore"
        if root_ignore.is_file():
            # Decoded strictly before refresh answers, as legacy's TreeScope read does:
            # an undecodable root .gitignore ends the console loudly.
            root_ignore.read_text(encoding="utf-8")

        from codefact.shell.index_refresh import refresh

        return _render_refresh(refresh(Path(args.root)), args.root)
    if args.capability != "query.atoms-in-file" and not args.subject:
        parser.error("subject is required for this capability")
    key = "anchor" if args.capability == "query.adr-section" else "symbol"
    request = {} if args.capability == "query.atoms-in-file" else {key: args.subject}
    snapshot = read_tree(args.root)
    scope.root_ignore_text(snapshot)  # outside the fold: a fault would hide the crash
    resolution = resolve(Capability(args.capability), request, PROVIDERS, snapshot)
    if isinstance(resolution, Answered):
        _print(
            {
                "provider": resolution.provider_id,
                "confidence": resolution.confidence,
                "payload": resolution.payload,
                "index": asdict(resolution.index),
                "coverage": asdict(resolution.coverage),
                "trace": [asdict(entry) for entry in resolution.trace],
            }
        )
        return 0
    if isinstance(resolution, Indeterminate):
        _print(
            {
                "resolution": "indeterminate",
                "uncovered": resolution.uncovered(),
                "index": asdict(resolution.index),
                "coverage": asdict(resolution.coverage),
                "trace": [asdict(entry) for entry in resolution.trace],
            }
        )
        _explain(
            f"`code-fact {args.capability}` is indeterminate",
            "the index does not cover every file and a query never regenerates it",
            f"read uncovered, run `code-fact refresh --root {args.root}` and repeat the query",
        )
        return 1
    _print(
        {
            "resolution": "failed",
            "cause": _cause_of(resolution),
            "trace": [asdict(entry) for entry in resolution.trace],
        }
    )
    _explain(
        f"`code-fact {args.capability}` has no answer",
        "no provider could answer this request",
        "inspect the trace and supply a readable target",
    )
    return 1


def _render_refresh(outcome, root):
    if isinstance(outcome, Refreshed):
        _print(
            {
                "refresh": "refreshed",
                "index": asdict(outcome.index),
                "coverage": asdict(outcome.coverage),
            }
        )
        return 0
    if isinstance(outcome, RefreshIndeterminate):
        _print(
            {
                "refresh": "indeterminate",
                "changed": outcome.changed,
                "reason": outcome.reason,
            }
        )
    else:
        _print({"refresh": "refused", "reason": outcome.reason})
    _explain(
        "`code-fact refresh` did not complete",
        outcome.reason,
        f"resolve the cause and run `code-fact refresh --root {root}` again",
    )
    return 1


def _similar(tokens):
    parser = _Parser(prog="code-fact find-similar-responsibility")
    parser.add_argument("--name", required=True)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--arity", type=int)
    parser.add_argument("--format", choices=["json"], default="json")
    args = parser.parse_args(tokens)
    result = resolve(
        Capability("query.similar-responsibility"),
        {"name": args.name, "arity": args.arity},
        PROVIDERS,
        read_tree(args.scope),
    )
    if isinstance(result, Answered):
        _print({"reason_code": "live-non-callable", "detail": "", **result.payload})
    else:
        _print(
            {
                "reason_code": "absent",
                "candidates": [],
                "detail": "The scope contains no parseable module-level symbols.",
                "unparsed_count": sum(entry.fault_count for entry in result.trace),
            }
        )
    return 0


def _impacted(tokens):
    parser = _Parser(prog="code-fact impacted-tests")
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--root", default=".")
    args = parser.parse_args(tokens)
    document = report(read_tree(args.root), tuple(args.paths))
    _print(document)
    return 0
