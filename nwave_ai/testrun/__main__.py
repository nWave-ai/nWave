"""``python -m nwave_ai.testrun``: the same command as ``nwave-ai tests``.

The form the hooks use: it needs the interpreter and this tree, nothing installed.
"""

from __future__ import annotations

import sys

from nwave_ai.testrun.cli import main


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
