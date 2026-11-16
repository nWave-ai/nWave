"""Entry point for `python -m nwexpress`."""

import sys

from nwexpress.infrastructure.cli import Cli

raise SystemExit(Cli().run(sys.argv[1:]))
