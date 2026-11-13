"""The run mode of a delivery: auto or interactive. One workspace binds one mode and keeps it."""

from __future__ import annotations

from nwstep.domain.refusal import Refusal

AUTO = "auto"
INTERACTIVE = "interactive"
CHOICES = (AUTO, INTERACTIVE)


def requested(value: str | None) -> str:
    """The mode a prompt command was given; a missing one is refused, naming both values."""
    if value in CHOICES:
        return value
    raise Refusal(
        what="prompt needs a mode: pass --mode auto or --mode interactive",
        why=(
            "auto prints the plain delivery prompt and interactive adds the interactive "
            "protocol that stops for the owner; a prompt without a mode is ambiguous"
        ),
        how="run the prompt command again with --mode auto or --mode interactive",
    )


def bind(recorded: str | None, requested_mode: str) -> str:
    """The mode the workspace keeps; a prompt with the other mode is refused, naming the recorded one."""
    if recorded is None or recorded == requested_mode:
        return requested_mode
    raise Refusal(
        what=f"this workspace runs in {recorded} mode; the prompt asked for {requested_mode}",
        why=(
            "the mode decides what the prompt asks the executor to do; one workspace "
            "cannot switch between an automatic run and an interactive run"
        ),
        how=(
            f"run the prompt command again with --mode {recorded}, or initialize a new "
            f"workspace for a {requested_mode} run"
        ),
    )
