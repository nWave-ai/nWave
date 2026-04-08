"""UpdateCheckService - application service for version update checks.

Fetches the latest version from PyPI, compares to the local version via
importlib.metadata, and returns a structured result. On timeout or any
network/JSON error, returns a silent-skip result (no exception propagates).

Integrates UpdateCheckPolicy for frequency gating. Persists last_checked
via DESConfig after each successful network check.

Architecture: application layer service.
- Driving port: check_for_updates() public method
- Driven port boundaries: HTTP endpoint (injectable via constructor), DESConfig
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from des.adapters.driven.config.des_config import DESConfig

from des.domain.update_check_policy import CheckDecision, UpdateCheckPolicy


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


class UpdateStatus(Enum):
    """Status of an update check."""

    UP_TO_DATE = "UP_TO_DATE"
    UPDATE_AVAILABLE = "UPDATE_AVAILABLE"
    SKIP = "SKIP"


@dataclass(frozen=True)
class UpdateCheckResult:
    """Result of an update check.

    Attributes:
        status:    Outcome of the check (UP_TO_DATE, UPDATE_AVAILABLE, SKIP).
        latest:    Latest version string from PyPI (present when UPDATE_AVAILABLE).
        changelog: Release notes from GitHub (present when available).
    """

    status: UpdateStatus
    latest: str | None = field(default=None)
    changelog: str | None = field(default=None)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

_DEFAULT_PYPI_URL = "https://pypi.org/pypi/nwave-ai/json"
_DEFAULT_GITHUB_RELEASES_URL = (
    "https://api.github.com/repos/nWave-ai/nWave/releases/latest"
)
_DEFAULT_TIMEOUT = 5  # seconds


class UpdateCheckService:
    """Checks for available updates by querying PyPI.

    Constructor accepts injectable URLs, local version, and DESConfig to
    enable testing without real network calls or filesystem access.

    When des_config is provided, the service:
    - Evaluates UpdateCheckPolicy before making any network calls (frequency gate)
    - Persists last_checked timestamp after a successful PyPI fetch
    - Passes skipped_versions from config to the policy
    """

    def __init__(
        self,
        pypi_url: str = _DEFAULT_PYPI_URL,
        local_version: str | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
        github_releases_url: str = _DEFAULT_GITHUB_RELEASES_URL,
        des_config: DESConfig | None = None,
    ) -> None:
        """Initialise the service.

        Args:
            pypi_url:             PyPI JSON endpoint (injectable for tests).
            local_version:        Local package version string; auto-detected when None.
            timeout:              HTTP request timeout in seconds (default 5).
            github_releases_url:  GitHub Releases API endpoint (injectable for tests).
            des_config:           DESConfig instance for frequency gating and state
                                  persistence. When None, frequency gating is skipped.
        """
        self._pypi_url = pypi_url
        self._local_version = local_version or _detect_local_version()
        self._timeout = timeout
        self._github_releases_url = github_releases_url
        self._des_config = des_config
        self._policy = UpdateCheckPolicy()

    # ------------------------------------------------------------------
    # Public API (driving port)
    # ------------------------------------------------------------------

    def check_for_updates(self) -> UpdateCheckResult:
        """Fetch latest version from PyPI and compare to local version.

        When des_config is provided:
        - Evaluates frequency policy before any network calls.
        - Persists last_checked after a successful UP_TO_DATE or UPDATE_AVAILABLE result.

        Returns:
            UpdateCheckResult with status UP_TO_DATE, UPDATE_AVAILABLE, or SKIP.
            Never raises an exception.
        """
        if self._des_config is not None:
            decision = self._evaluate_policy()
            if decision == CheckDecision.SKIP:
                return UpdateCheckResult(status=UpdateStatus.SKIP)

        latest = self._fetch_latest_version()
        if latest is None:
            return UpdateCheckResult(status=UpdateStatus.SKIP)

        # Re-check policy with actual latest version (for skipped_versions rule)
        if self._des_config is not None:
            decision = self._evaluate_policy(latest_version=latest)
            if decision == CheckDecision.SKIP:
                return UpdateCheckResult(status=UpdateStatus.SKIP)

        if _is_newer(latest, self._local_version):
            changelog = self._fetch_changelog(latest)
            result = UpdateCheckResult(
                status=UpdateStatus.UPDATE_AVAILABLE,
                latest=latest,
                changelog=changelog,
            )
        else:
            result = UpdateCheckResult(status=UpdateStatus.UP_TO_DATE)

        # Persist last_checked after successful network fetch
        if self._des_config is not None:
            self._persist_last_checked()

        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _evaluate_policy(self, latest_version: str | None = None) -> CheckDecision:
        """Evaluate the update check policy using DESConfig state.

        When frequency is None (update_check key absent — first run), the policy
        receives None and evaluates Rule 3 (frequency=None, last_checked=None → CHECK).
        """
        if self._des_config is None:
            return CheckDecision.CHECK
        frequency: str | None = self._des_config.update_check_frequency
        last_checked_str = self._des_config.update_check_last_checked
        skipped_versions = self._des_config.update_check_skipped_versions

        last_checked: datetime | None = None
        if last_checked_str is not None:
            try:
                last_checked = datetime.fromisoformat(last_checked_str)
            except ValueError:
                last_checked = None

        return self._policy.evaluate(
            frequency=frequency,
            last_checked=last_checked,
            latest_version=latest_version,
            skipped_versions=skipped_versions,
            current_time=datetime.now(tz=timezone.utc),
        )

    def _persist_last_checked(self) -> None:
        """Write last_checked=now to DESConfig. Silently ignores any errors."""
        if self._des_config is None:
            return
        try:
            now_iso = datetime.now(tz=timezone.utc).isoformat()
            self._des_config.save_update_check_state(
                last_checked=now_iso,
                skipped_versions=self._des_config.update_check_skipped_versions,
            )
        except Exception:
            pass  # State persistence is best-effort; never block the service

    def _fetch_json(
        self, url: str, extra_headers: dict[str, str] | None = None
    ) -> bytes | None:
        """Fetch JSON bytes from URL. Returns None on any HTTP or network failure.

        Args:
            url: The URL to fetch.
            extra_headers: Optional headers to add to the request.

        Returns:
            Raw response bytes on HTTP 200, None on any failure.
        """
        try:
            req = urllib.request.Request(url)
            if extra_headers:
                for name, value in extra_headers.items():
                    req.add_header(name, value)
            with urllib.request.urlopen(req, timeout=self._timeout) as response:
                if response.status != 200:
                    return None
                return response.read()
        except Exception:
            return None

    def _fetch_latest_version(self) -> str | None:
        """Fetch latest version from PyPI. Returns None on any failure."""
        raw = self._fetch_json(self._pypi_url)
        if raw is None:
            return None
        try:
            data = json.loads(raw)
            return str(data["info"]["version"])
        except (json.JSONDecodeError, KeyError, TypeError):
            return None

    def _fetch_changelog(self, latest_version: str) -> str | None:
        """Fetch release notes from GitHub for the latest version tag.

        Returns the release body when the response tag matches the latest version.
        Returns None on any failure or when the tag does not match.
        """
        raw = self._fetch_json(
            self._github_releases_url,
            extra_headers={"Accept": "application/vnd.github+json"},
        )
        if raw is None:
            return None
        try:
            data = json.loads(raw)
            tag_name: str = str(data["tag_name"])
            # Accept tags like "v2.0.0" or "2.0.0" matching the version
            normalised_tag = tag_name.lstrip("v")
            if normalised_tag != latest_version:
                return None
            body = data.get("body")
            if not body:
                return None
            # Cap changelog injection to 2000 chars to limit additionalContext token use
            return str(body)[:2000]
        except (json.JSONDecodeError, KeyError, TypeError):
            return None


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _detect_local_version() -> str:
    """Return the installed nwave-ai version, or '0.0.0' when unavailable."""
    try:
        return pkg_version("nwave-ai")
    except PackageNotFoundError:
        return "0.0.0"


def _is_newer(candidate: str, current: str) -> bool:
    """Return True when candidate version is strictly newer than current.

    Uses simple tuple comparison on integer version parts.  Sufficient for
    PEP 440 epoch-free semantic versions (MAJOR.MINOR.PATCH).
    """
    try:
        return _parse_version(candidate) > _parse_version(current)
    except (ValueError, AttributeError):
        return False


def _parse_version(v: str) -> tuple[int, ...]:
    """Parse a version string into a tuple of integers for comparison."""
    return tuple(int(part) for part in v.split("."))
