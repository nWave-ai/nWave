"""Harness CLI entry — the single driving port, uniform across all OSes.

Parses lane args, builds the real adapters, calls SmokeRunner, and maps
SmokeResult to a process exit code (DESIGN L1):

    SmokeResult.passed is True  -> exit 0
    SmokeResult.passed is False -> exit 1 (NEVER 0 on any failed step)

This exit-code mapping is the fix for "red annotations / green pipeline": a
failed lane returns non-zero so the matrix job actually fails.

Invoked uniformly on every OS:

    python -m scripts.release.rc_smoke \
        --tool TOOL --installer {uv|pipx} --version VER --target PATH [--depth boot]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scripts.release.rc_smoke.adapters import (
    RealArtifactFileSystem,
    SubprocessInstaller,
    SubprocessRunner,
)
from scripts.release.rc_smoke.contracts import UnsupportedToolError, tool_contract
from scripts.release.rc_smoke.result import SmokeDepth
from scripts.release.rc_smoke.runner import SmokeRunner


EXIT_PASS = 0
EXIT_FAIL = 1


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.release.rc_smoke",
        description="Cross-OS multi-tool RC boot-smoke harness (one lane).",
    )
    parser.add_argument(
        "--tool", required=True, help="tool id (claude-code / codex / opencode)"
    )
    parser.add_argument(
        "--installer", required=True, choices=("uv", "pipx"), help="install tool"
    )
    parser.add_argument(
        "--version", required=True, help="published nwave-ai version to install"
    )
    parser.add_argument(
        "--target", required=True, type=Path, help="isolated install target dir"
    )
    parser.add_argument(
        "--depth",
        default=SmokeDepth.BOOT.value,
        choices=(SmokeDepth.BOOT.value, SmokeDepth.TURN.value),
        help="smoke depth (boot = default; turn reserved/deferred)",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    """Parse args, run the lane, return the process exit code."""
    args = _parse_args(argv)

    try:
        contract = tool_contract(args.tool)
    except UnsupportedToolError as exc:
        print(f"rc-smoke: {exc}", file=sys.stderr)
        return EXIT_FAIL

    runner = SmokeRunner(
        installer=SubprocessInstaller(args.installer),
        process=SubprocessRunner(),
        filesystem=RealArtifactFileSystem(),
    )
    result = runner.run(
        contract=contract,
        version=args.version,
        target=args.target,
        depth=SmokeDepth(args.depth),
    )

    if result.passed:
        print(f"rc-smoke: {result.tool} lane PASSED")
        return EXIT_PASS

    print(result.diagnostics, file=sys.stderr)
    return EXIT_FAIL


if __name__ == "__main__":  # pragma: no cover - process entry
    sys.exit(main(sys.argv[1:]))
