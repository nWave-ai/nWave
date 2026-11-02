"""Shared CheckResult dataclass for nwave_ai checks.

Extracted from scripts/install/preflight_checker so that both the installer
preflight layer and the doctor diagnostic command share the same type without
a cross-boundary import.
"""

from dataclasses import dataclass
from enum import Enum


class CheckStatus(Enum):
    """What a check can honestly say about the thing it examined."""

    PASSED = "passed"
    FAILED = "failed"
    COULD_NOT_VERIFY = "could_not_verify"


@dataclass
class CheckResult:
    """Result of a single check.

    Invariants, rejected at construction time:
      - when passed=True, both error_code and remediation MUST be None;
      - when verified=False the check could not decide: it MUST NOT read as
        passed and MUST carry a non-empty error_code and remediation.

    Build an undecidable result with ``CheckResult.could_not_verify``.

    Attributes:
        passed: Whether the check passed successfully.
        error_code: Short error code (None if passed).
        message: Human-readable description of the check result.
        remediation: Instructions to fix the issue (None if passed).
        check_name: Identifier of the check that produced this result (set by runner).
        verified: False only when the check could not decide (see ``status``).
    """

    passed: bool
    error_code: str | None
    message: str
    remediation: str | None
    check_name: str = ""
    verified: bool = True

    def __post_init__(self) -> None:
        if not self.verified:
            self._require_unverified_result_is_admitted()
        if self.passed and self.error_code is not None:
            raise ValueError(
                f"CheckResult invariant violated: passed=True but error_code={self.error_code!r}"
            )
        if self.passed and self.remediation is not None:
            raise ValueError(
                "CheckResult invariant violated: passed=True but remediation is set"
            )

    @classmethod
    def could_not_verify(
        cls, error_code: str, message: str, remediation: str
    ) -> "CheckResult":
        """Build the result of a check that could not decide either way."""
        return cls(
            passed=False,
            error_code=error_code,
            message=message,
            remediation=remediation,
            verified=False,
        )

    @property
    def status(self) -> CheckStatus:
        """Passed, failed (known) or could not verify; derived, never stored."""
        if self.passed:
            return CheckStatus.PASSED
        if self.verified:
            return CheckStatus.FAILED
        return CheckStatus.COULD_NOT_VERIFY

    def _require_unverified_result_is_admitted(self) -> None:
        if self.passed:
            raise ValueError(
                "CheckResult invariant violated: verified=False with passed=True "
                "would read as success for a check that could not verify; "
                "build it with CheckResult.could_not_verify(error_code, message, "
                "remediation), which reports passed=False with an explanation"
            )
        missing = [
            name
            for name, value in (
                ("error_code", self.error_code),
                ("remediation", self.remediation),
            )
            if not value
        ]
        if missing:
            raise ValueError(
                f"CheckResult invariant violated: verified=False but "
                f"{' and '.join(missing)} missing or empty; a result that could not "
                "be verified without them loses its explanation — build it with "
                "CheckResult.could_not_verify(error_code, message, remediation)"
            )
