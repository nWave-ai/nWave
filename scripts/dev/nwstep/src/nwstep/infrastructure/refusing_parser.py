"""An argparse parser whose usage errors are refusals with WHAT, WHY and HOW, not a bare exit."""

from __future__ import annotations

import argparse
from typing import NoReturn

from nwstep.application.how_line import HowLine
from nwstep.domain.refusal import Refusal


class RefusingParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise Refusal(
            what=message,
            why="the command line does not match the nwstep commands",
            how=HowLine().command("--help"),
        )
