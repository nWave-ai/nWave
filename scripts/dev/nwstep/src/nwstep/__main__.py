"""Entry point for `python -m nwstep`."""

import sys

from nwstep.infrastructure.cli import Cli

raise SystemExit(Cli().run(sys.argv[1:]))
