"""Extract classic-mode wall-clock baselines from historical execution logs.

Day 0 scaffolding (2026-05-19) per plan v3 §2.2. Business logic NOT YET
implemented — Day 1 crafter dispatch will add real extraction via DES sequencer.

Usage:
    python scripts/automation/classic_baseline_extractor.py \\
        --features fix-des-worktree-project-root-marker,fix-des-log-concurrency,fix-pytest-build-tier-flakies \\
        --cohort M \\
        --output docs/analysis/classic-baseline-M-2026-05-19.json

Output schema:
    {
      "cohort": "M",
      "features": [{
        "feature_id": "...",
        "phase_durations_s": {"RED": ..., "GREEN": ..., "COMMIT": ...},
        "total_wall_clock_s": ...,
        "at_count": ...
      }],
      "p50_total_s": ..., "p95_total_s": ...
    }

Source: docs/feature/{feature_id}/deliver/execution-log.json
SLA: plan v3 §2.4 — 3-day baseline measurement (2026-05-19 → 2026-05-22).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Sequence


logger = logging.getLogger(__name__)

COHORTS = ("S", "M", "L")


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="classic_baseline_extractor",
        description=(
            "Extract classic-mode wall-clock baselines from historical "
            "execution logs (plan v3 §2.2 — Day 0 scaffolding)."
        ),
    )
    parser.add_argument(
        "--features",
        type=str,
        required=False,
        help="Comma-separated feature_id list under docs/feature/.",
    )
    parser.add_argument(
        "--cohort",
        type=str,
        choices=COHORTS,
        required=False,
        help="Cohort size bucket: S (≤10 ATs), M (11–30), L (31–80).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=False,
        help="JSON output path (e.g. docs/analysis/classic-baseline-M-2026-05-19.json).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parse_args(argv)
    logger.info("classic_baseline_extractor invoked (cohort=%s)", args.cohort)
    print(
        "TODO: implement extraction from "
        "docs/feature/{id}/deliver/execution-log.json "
        "(Day 1 crafter dispatch — plan v3 §2.4)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
