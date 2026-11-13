"""Binds the shipped dynamic template to one clone, workspace, request and the optional authority and baseline."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from nwstep.application.interactive_protocol import (
    INTERACTIVE_PROTOCOL,
    PAUSE_INTERACTIVE_PROTOCOL,
)
from nwstep.application.jev_protocol import section as jev_section
from nwstep.domain.refusal import Refusal
from nwstep.domain.run_mode import INTERACTIVE
from nwstep.domain.template import Template


if TYPE_CHECKING:
    from nwstep.domain.jev_consent import JevConsent


class Prompt:
    DECLARED = frozenset(
        {
            "root",
            "workspace",
            "cli",
            "steps",
            "request",
            "authority",
            "baseline_failures",
        }
    )
    NO_AUTHORITY = "none given"
    NO_BASELINE = "none known"

    def __init__(self, template_path: Path, invocation: str) -> None:
        self._template_path = template_path
        self._invocation = invocation

    def render(
        self,
        *,
        root: Path,
        workspace: Path,
        steps: tuple[str, ...],
        request: str,
        authority: str | None,
        baseline: str | None,
        mode: str,
        consent: JevConsent,
        skill: Path,
        pauses: bool,
    ) -> str:
        values = {
            "root": str(root),
            "workspace": str(workspace),
            "cli": self._invocation,
            "steps": steps,
            "request": request,
            "authority": self.NO_AUTHORITY if authority is None else authority,
            "baseline_failures": self.NO_BASELINE if baseline is None else baseline,
        }
        text = Template(self._read()).render(values, self.DECLARED, self._how())
        text += jev_section(consent, skill)
        if mode == INTERACTIVE:
            text += PAUSE_INTERACTIVE_PROTOCOL if pauses else INTERACTIVE_PROTOCOL
        return text

    def _read(self) -> str:
        try:
            return self._template_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise Refusal(
                what=f"the prompt template {self._template_path} cannot be read: {error}",
                why="the prompt is this template bound to a workspace; without it there is nothing to print",
                how=f"restore {self._template_path} in the nwstep checkout",
            ) from None

    def _how(self) -> str:
        return (
            f"edit {self._template_path} so that every placeholder is one of "
            f"{', '.join(sorted(self.DECLARED))}, each filled once"
        )
