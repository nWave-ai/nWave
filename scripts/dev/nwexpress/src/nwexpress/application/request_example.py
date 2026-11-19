"""The request command a refusal names as its HOW: complete, with every option a request needs.

Each value the caller must still supply is a placeholder in angle brackets, so filling the placeholders gives a command that
writes a request. The one section that may read stdin is named as '-'; a second one never is, because stdin is read once.
"""

from __future__ import annotations

from nwexpress.application.how_line import HowLine


OPTIONAL_SECTIONS = ("--deliver", "--decisions")


class RequestExample:
    @staticmethod
    def command(how: HowLine, workspace: str, stdin: str | None) -> str:
        """The request command for the workspace; the option named stdin reads standard input, and no other does."""

        def section(option: str, placeholder: str) -> str:
            return "-" if option == stdin else placeholder

        arguments = [
            "request",
            "--workspace",
            workspace,
            "--card",
            "<card id>",
            "--title",
            "<title>",
            "--problem",
            section("--problem", "<problem file>"),
        ]
        if stdin in OPTIONAL_SECTIONS:
            arguments += [stdin, "-"]
        arguments += [
            "--acceptance",
            section("--acceptance", "<acceptance file>"),
            "--scratch",
            "<scratch folder>",
        ]
        return how.command(*arguments)
