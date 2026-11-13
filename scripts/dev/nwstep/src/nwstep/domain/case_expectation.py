"""What an executed case must observe, and what it proves: kind=new fails before the change for a declared cause; kind=preserve holds on both trees and executes a changed file."""

from __future__ import annotations

import re

from nwstep.domain.command_outcome import CommandOutcome


class CaseExpectation:
    NEW = "new"
    PRESERVE = "preserve"
    _KEY = re.compile(
        r",(exit|kind|contains|absent|baseline-contains|protects|artifact)="
    )
    _KINDS = (NEW, PRESERVE)

    def __init__(
        self,
        text: str,
        exit_code: int,
        kind: str,
        *,
        contains: str | None = None,
        absent: str | None = None,
        baseline_contains: str | None = None,
        protects: str | None = None,
        artifact: str | None = None,
    ) -> None:
        self.text = text
        self.exit_code = exit_code
        self.kind = kind
        self.contains = contains
        self.absent = absent
        self.baseline_contains = baseline_contains
        self.protects = protects
        self.artifact = artifact

    @classmethod
    def parse(cls, text: str) -> CaseExpectation:
        """Read 'exit=N' then ',key=VALUE' options; every case declares its kind, new or preserve."""
        stripped = text.strip()
        pairs = cls._pairs(stripped)
        for key, value in pairs.items():
            if key != "exit" and not value:
                raise ValueError(f"'{key}' needs a value")
        kind = pairs.get("kind")
        if kind is None:
            raise ValueError(
                "the expectation has no kind; end it with ',kind=new,baseline-contains=TEXT' "
                "(fails on the pre-feature tree, which prints TEXT) or ',kind=preserve,protects=PATH' "
                "(holds on both trees and executes PATH, a file changed from BASE to HEAD)"
            )
        if kind not in cls._KINDS:
            raise ValueError("kind is new or preserve")
        if kind == cls.NEW and "baseline-contains" not in pairs:
            raise ValueError(
                "kind=new needs ',baseline-contains=TEXT', the output of the pre-feature failure"
            )
        if kind == cls.NEW and "protects" in pairs:
            raise ValueError("protects applies to kind=preserve only")
        if kind == cls.PRESERVE and "protects" not in pairs:
            raise ValueError(
                "kind=preserve needs ',protects=PATH', a file changed from BASE to HEAD"
            )
        if kind == cls.PRESERVE and "baseline-contains" in pairs:
            raise ValueError("baseline-contains applies to kind=new only")
        try:
            exit_code = int(pairs["exit"])
        except ValueError:
            raise ValueError(f"exit code '{pairs['exit']}' is not an integer") from None
        return cls(
            stripped,
            exit_code,
            kind,
            contains=pairs.get("contains"),
            absent=pairs.get("absent"),
            baseline_contains=pairs.get("baseline-contains"),
            protects=pairs.get("protects"),
            artifact=pairs.get("artifact"),
        )

    @classmethod
    def _pairs(cls, text: str) -> dict[str, str]:
        if not text.startswith("exit="):
            raise ValueError("the expectation starts with exit=N")
        heads = [("exit", 0, len("exit="))] + [
            (match.group(1), match.start(), match.end())
            for match in cls._KEY.finditer(text)
        ]
        pairs: dict[str, str] = {}
        for index, (key, _start, end) in enumerate(heads):
            if key in pairs:
                raise ValueError(f"'{key}' is given twice")
            stop = heads[index + 1][1] if index + 1 < len(heads) else len(text)
            pairs[key] = text[end:stop]
        return pairs

    def holds(self, outcome: CommandOutcome) -> bool:
        if outcome.problem is not None or outcome.exit_code != self.exit_code:
            return False
        if self.contains is not None and self.contains not in outcome.output:
            return False
        return self.absent is None or self.absent not in outcome.output

    def cause_seen(self, outcome: CommandOutcome) -> bool:
        """Whether the output names the declared cause of the pre-feature failure."""
        return (
            self.baseline_contains is not None
            and self.baseline_contains in outcome.output
        )

    def observed(self, outcome: CommandOutcome) -> str:
        if outcome.problem is not None:
            return f"did not finish: {outcome.problem}"
        parts = [f"exit={outcome.exit_code}"]
        if self.contains is not None and self.contains not in outcome.output:
            parts.append(f"output lacks '{self.contains}'")
        if self.absent is not None and self.absent in outcome.output:
            parts.append(f"output contains '{self.absent}'")
        return ", ".join(parts)
