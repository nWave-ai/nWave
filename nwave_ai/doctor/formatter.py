"""Doctor formatter — converts CheckResult lists to human or JSON output.

Step 01-01: stubs returning empty string / empty JSON object.
Step 01-03: implement render_human (emoji-prefixed lines) and render_json (stable structure).

Both renderings read one ``CheckTally`` built from the ordered results, so the
passed / failed / could-not-verify buckets always add up to the rows shown.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from nwave_ai.common.check_result import CheckStatus


if TYPE_CHECKING:
    from nwave_ai.common.check_result import CheckResult


_HUMAN_PREFIX = {
    CheckStatus.PASSED: "✅ ",
    CheckStatus.FAILED: "⚠️  ",
    CheckStatus.COULD_NOT_VERIFY: "❓ ",
}


@dataclass(frozen=True)
class CheckTally:
    """The ordered results and their disjoint status counts.

    Invariant: ``passed + failed + could_not_verify == total``; ``failed`` counts
    known failures only, and a check that could not verify is never counted as
    passed or as failed.
    """

    results: tuple[CheckResult, ...]
    passed: int
    failed: int
    could_not_verify: int

    @classmethod
    def of(cls, results: list[CheckResult]) -> CheckTally:
        statuses = [result.status for result in results]
        return cls(
            results=tuple(results),
            passed=statuses.count(CheckStatus.PASSED),
            failed=statuses.count(CheckStatus.FAILED),
            could_not_verify=statuses.count(CheckStatus.COULD_NOT_VERIFY),
        )

    @property
    def total(self) -> int:
        return len(self.results)


def render_human(results: list[CheckResult]) -> str:
    """Render check results as human-readable text.

    Passes render as "✅ <check_name>: <message>".
    Failures render as "⚠️  <check_name>: <message>" followed by indented remediation.
    Checks that could not verify render as "❓ <check_name>: <message>" followed by
    indented remediation.
    Ends with a summary line:
    "N/M checks passed, F failed, U could not be verified".

    Args:
        results: Ordered list of CheckResult objects from run_doctor().

    Returns:
        Multi-line string with emoji-prefixed pass/fail/could-not-verify lines.
    """
    tally = CheckTally.of(results)
    lines: list[str] = []

    for result in tally.results:
        prefix = _HUMAN_PREFIX[result.status]
        lines.append(f"{prefix}{result.check_name}: {result.message}")
        if not result.passed and result.remediation:
            for rem_line in result.remediation.splitlines():
                lines.append(f"   {rem_line}")

    lines.append("")
    lines.append(
        f"{tally.passed}/{tally.total} checks passed, {tally.failed} failed, "
        f"{tally.could_not_verify} could not be verified"
    )
    return "\n".join(lines)


def render_json(results: list[CheckResult]) -> str:
    """Render check results as a JSON string.

    Structure: {"checks": [{"name", "passed", "message", "remediation", "status"}],
                "summary": {"total", "passed", "failed", "could_not_verify"}}.
    ``status`` is "passed", "failed" or "could_not_verify"; ``passed`` is true
    only for "passed".

    Args:
        results: Ordered list of CheckResult objects from run_doctor().

    Returns:
        JSON string with stable keys.
    """
    tally = CheckTally.of(results)
    return json.dumps(
        {
            "checks": [
                {
                    "name": r.check_name,
                    "passed": r.passed,
                    "message": r.message,
                    "remediation": r.remediation,
                    "status": r.status.value,
                }
                for r in tally.results
            ],
            "summary": {
                "total": tally.total,
                "passed": tally.passed,
                "failed": tally.failed,
                "could_not_verify": tally.could_not_verify,
            },
        },
        indent=2,
    )
