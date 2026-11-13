"""Parses `nwstep record STEP --FIELD VALUE --item NAME=VALUE ...` without knowing the fields in advance."""

from __future__ import annotations

from nwstep.domain.submission import Submission


class RecordArguments:
    def __init__(self, tokens: list[str]) -> None:
        self.step: str | None = None
        self.workspace: str | None = None
        self.root: str | None = None
        scalars: list[tuple[str, str]] = []
        items: list[tuple[str, str]] = []
        problems: list[str] = []
        index = 0
        if tokens and not tokens[0].startswith("--"):
            self.step = tokens[0]
            index = 1
        while index < len(tokens):
            token = tokens[index]
            if not token.startswith("--") or token == "--":
                problems.append(f"unexpected argument '{token}'")
                index += 1
                continue
            if index + 1 >= len(tokens):
                problems.append(f"'{token}' needs a value")
                break
            value = tokens[index + 1]
            index += 2
            name = token[2:]
            if name == "workspace":
                self.workspace = value
            elif name == "root":
                self.root = value
            elif name == "item":
                item_name, separator, item_value = value.partition("=")
                if separator and item_name:
                    items.append((item_name, item_value))
                else:
                    problems.append(f"item '{value}' must be written NAME=VALUE")
            else:
                scalars.append((name, value))
        self.submission = Submission(scalars, items, problems)
