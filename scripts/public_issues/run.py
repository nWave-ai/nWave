"""The command the public workflow runs: one pass over the repository, dry unless ISSUE_CLOSE_LIVE is 'true'.

Usage (in the workflow): python3 -m scripts.public_issues.run
Settings come from the environment: GITHUB_TOKEN, GITHUB_REPOSITORY, ISSUE_CLOSE_LIVE and
FORCE_DRY_RUN (the dispatch input dry_run). Exit 0 after a full pass, 1 when a call was refused,
2 when a setting is missing.
"""

from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from scripts.public_issues import urllib_transport
from scripts.public_issues.api_error import ApiError
from scripts.public_issues.github_api import GitHubApi, Transport
from scripts.public_issues.run_mode import RunMode
from scripts.public_issues.sweep import run_sweep


if TYPE_CHECKING:
    from collections.abc import Callable, Mapping


def main(
    argv: list[str] | None = None,
    env: Mapping[str, str] | None = None,
    transport: Transport | None = None,
    now: datetime | None = None,
    emit: Callable[[str], None] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.parse_args(argv or [])
    say = emit if emit is not None else print
    settings = os.environ if env is None else env
    token = settings.get("GITHUB_TOKEN", "")
    repository = settings.get("GITHUB_REPOSITORY", "")
    if not token or not repository:
        missing = "GITHUB_TOKEN" if not token else "GITHUB_REPOSITORY"
        say(
            f"WHAT: {missing} is not set. WHY: the pass cannot read the repository without it. "
            f"HOW: run the job from the workflow, or export {missing} and run again."
        )
        return 2
    mode = RunMode.from_settings(
        settings.get("ISSUE_CLOSE_LIVE"), settings.get("FORCE_DRY_RUN")
    )
    say(f"mode: {mode.reason}")
    api = GitHubApi(repository, token, transport or urllib_transport.send)
    try:
        run_sweep(api, now or datetime.now(UTC), mode, say)
    except ApiError as error:
        say(f"FAILED: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
