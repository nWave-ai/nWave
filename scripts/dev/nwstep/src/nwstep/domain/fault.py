"""Why a request was refused. The HOW line repairs the faults that have a mechanical fix."""

from __future__ import annotations

from enum import Enum


class Fault(Enum):
    SYNTAX = "syntax"
    UNKNOWN_NAME = "unknown_name"
    DUPLICATE = "duplicate"
    WRONG_FORM = "wrong_form"
    MISSING = "missing"
    ABSENT_PATH = "absent_path"
    VALUE = "value"
    COVERAGE = "coverage"
    COMMAND = "command"
    # A command value holds a shell operator outside quotes; the HOW repeats the words before the first operator, or
    # keeps the placeholder when that operator is an expansion the tool cannot write for the executor.
    SHELL_OPERATOR = "shell_operator"
    # The named value is wrong as written and is a fact the executor edits (a path, a name);
    # the HOW keeps it, so running the HOW reproduces the refusal and the named item is corrected.
    AS_WRITTEN = "as_written"
