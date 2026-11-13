"""Console script `nwstep`: runs the nwstep package beside this file, in the checkout or in the wheel."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    source = Path(__file__).resolve().parents[1] / "dev" / "nwstep" / "src"
    sys.path.insert(0, str(source))
    from nwstep.infrastructure.cli import Cli

    raise SystemExit(Cli().run(sys.argv[1:]))
