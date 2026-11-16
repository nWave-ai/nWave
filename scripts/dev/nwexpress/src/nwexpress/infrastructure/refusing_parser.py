"""An argparse parser whose usage errors are refusals with WHAT, WHY and HOW, not a bare exit."""

from __future__ import annotations

import argparse
from typing import NoReturn

from nwexpress.application.how_line import HowLine
from nwexpress.domain.refusal import Refusal


class RefusingParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise Refusal(
            what=message,
            why="the command line does not match the nwexpress commands",
            how=HowLine().command("--help"),
        )
