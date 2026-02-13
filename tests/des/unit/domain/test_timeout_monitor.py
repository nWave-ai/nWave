"""Unit tests for TimeoutMonitor component.

Tests the timeout monitoring logic that tracks elapsed time from phase start
and detects when duration thresholds are crossed.
"""

from datetime import datetime, timedelta, timezone

import pytest

from des.domain.timeout_monitor import TimeoutMonitor


class TestTimeoutMonitorCalculatesElapsedTime:
    """Test that TimeoutMonitor correctly calculates elapsed time."""

    def test_calculates_elapsed_time_from_phase_start(self, mocked_time_provider):
        """TimeoutMonitor calculates elapsed seconds from phase started_at timestamp."""
        # Given: Fixed base time at 2026-01-26 10:00:00 UTC
        base_time = datetime(2026, 1, 26, 10, 0, 0, tzinfo=timezone.utc)
        mocked_time_provider.set_time(base_time)

        # And: A phase started 5 minutes ago
        started_at = (base_time - timedelta(minutes=5)).isoformat()
        monitor = TimeoutMonitor(
            started_at=started_at, time_provider=mocked_time_provider
        )

        # When: Getting elapsed seconds
        elapsed = monitor.get_elapsed_seconds()

        # Then: Should be exactly 300 seconds (5 minutes)
        assert elapsed == 300, f"Expected 300 seconds, got {elapsed}"

    def test_handles_recent_phase_start(self, mocked_time_provider):
        """TimeoutMonitor handles phases that just started (< 1 second ago)."""
        # Given: Fixed base time at 2026-01-26 10:00:00 UTC
        base_time = datetime(2026, 1, 26, 10, 0, 0, tzinfo=timezone.utc)
        mocked_time_provider.set_time(base_time)

        # And: A phase that just started
        started_at = base_time.isoformat()
        monitor = TimeoutMonitor(
            started_at=started_at, time_provider=mocked_time_provider
        )

        # When: Getting elapsed seconds
        elapsed = monitor.get_elapsed_seconds()

        # Then: Should be exactly 0 seconds
        assert elapsed == 0, f"Expected 0 seconds, got {elapsed}"

    def test_handles_timezone_aware_timestamps(self, mocked_time_provider):
        """TimeoutMonitor correctly parses timezone-aware ISO timestamps."""
        # Given: Fixed base time at 2026-01-26 10:00:00 UTC
        base_time = datetime(2026, 1, 26, 10, 0, 0, tzinfo=timezone.utc)
        mocked_time_provider.set_time(base_time)

        # And: A timezone-aware timestamp from 10 minutes ago
        started_at = (base_time - timedelta(minutes=10)).isoformat()
        monitor = TimeoutMonitor(
            started_at=started_at, time_provider=mocked_time_provider
        )

        # When: Getting elapsed seconds
        elapsed = monitor.get_elapsed_seconds()

        # Then: Should be exactly 600 seconds
        assert elapsed == 600, f"Expected 600 seconds, got {elapsed}"


class TestTimeoutMonitorThresholdDetection:
    """Test that TimeoutMonitor detects crossed thresholds."""

    def test_returns_empty_list_when_no_thresholds_crossed(self, mocked_time_provider):
        """check_thresholds returns empty list when elapsed time is under all thresholds."""
        # Given: Fixed base time at 2026-01-26 10:00:00 UTC
        base_time = datetime(2026, 1, 26, 10, 0, 0, tzinfo=timezone.utc)
        mocked_time_provider.set_time(base_time)

        # And: A phase started 2 minutes ago
        started_at = (base_time - timedelta(minutes=2)).isoformat()
        monitor = TimeoutMonitor(
            started_at=started_at, time_provider=mocked_time_provider
        )

        # When: Checking thresholds [5, 10, 15] minutes
        crossed = monitor.check_thresholds(duration_minutes=[5, 10, 15])

        # Then: Should return empty list
        assert crossed == []

    def test_returns_single_crossed_threshold(self, mocked_time_provider):
        """check_thresholds returns list with single crossed threshold."""
        # Given: Fixed base time at 2026-01-26 10:00:00 UTC
        base_time = datetime(2026, 1, 26, 10, 0, 0, tzinfo=timezone.utc)
        mocked_time_provider.set_time(base_time)

        # And: A phase started 7 minutes ago
        started_at = (base_time - timedelta(minutes=7)).isoformat()
        monitor = TimeoutMonitor(
            started_at=started_at, time_provider=mocked_time_provider
        )

        # When: Checking thresholds [5, 10, 15] minutes
        crossed = monitor.check_thresholds(duration_minutes=[5, 10, 15])

        # Then: Should return [5] (only first threshold crossed)
        assert crossed == [5]

    def test_returns_multiple_crossed_thresholds(self, mocked_time_provider):
        """check_thresholds returns all thresholds that have been crossed."""
        # Given: Fixed base time at 2026-01-26 10:00:00 UTC
        base_time = datetime(2026, 1, 26, 10, 0, 0, tzinfo=timezone.utc)
        mocked_time_provider.set_time(base_time)

        # And: A phase started 12 minutes ago
        started_at = (base_time - timedelta(minutes=12)).isoformat()
        monitor = TimeoutMonitor(
            started_at=started_at, time_provider=mocked_time_provider
        )

        # When: Checking thresholds [5, 10, 15] minutes
        crossed = monitor.check_thresholds(duration_minutes=[5, 10, 15])

        # Then: Should return [5, 10] (first two thresholds crossed)
        assert crossed == [5, 10]

    def test_returns_all_crossed_thresholds(self, mocked_time_provider):
        """check_thresholds returns all thresholds when all are crossed."""
        # Given: Fixed base time at 2026-01-26 10:00:00 UTC
        base_time = datetime(2026, 1, 26, 10, 0, 0, tzinfo=timezone.utc)
        mocked_time_provider.set_time(base_time)

        # And: A phase started 20 minutes ago
        started_at = (base_time - timedelta(minutes=20)).isoformat()
        monitor = TimeoutMonitor(
            started_at=started_at, time_provider=mocked_time_provider
        )

        # When: Checking thresholds [5, 10, 15] minutes
        crossed = monitor.check_thresholds(duration_minutes=[5, 10, 15])

        # Then: Should return [5, 10, 15] (all thresholds crossed)
        assert crossed == [5, 10, 15]

    def test_handles_empty_threshold_list(self, mocked_time_provider):
        """check_thresholds handles empty threshold list correctly."""
        # Given: Fixed base time at 2026-01-26 10:00:00 UTC
        base_time = datetime(2026, 1, 26, 10, 0, 0, tzinfo=timezone.utc)
        mocked_time_provider.set_time(base_time)

        # And: A phase started 10 minutes ago
        started_at = (base_time - timedelta(minutes=10)).isoformat()
        monitor = TimeoutMonitor(
            started_at=started_at, time_provider=mocked_time_provider
        )

        # When: Checking empty threshold list
        crossed = monitor.check_thresholds(duration_minutes=[])

        # Then: Should return empty list
        assert crossed == []

    def test_handles_unsorted_threshold_list(self, mocked_time_provider):
        """check_thresholds works correctly even with unsorted threshold list."""
        # Given: Fixed base time at 2026-01-26 10:00:00 UTC
        base_time = datetime(2026, 1, 26, 10, 0, 0, tzinfo=timezone.utc)
        mocked_time_provider.set_time(base_time)

        # And: A phase started 12 minutes ago
        started_at = (base_time - timedelta(minutes=12)).isoformat()
        monitor = TimeoutMonitor(
            started_at=started_at, time_provider=mocked_time_provider
        )

        # When: Checking unsorted thresholds [15, 5, 10] minutes
        crossed = monitor.check_thresholds(duration_minutes=[15, 5, 10])

        # Then: Should return crossed thresholds in order [5, 10]
        assert crossed == [5, 10]


class TestTimeoutMonitorEdgeCases:
    """Test edge cases and error handling."""

    def test_handles_future_started_at_timestamp(self, mocked_time_provider):
        """TimeoutMonitor handles future timestamps gracefully (returns 0 or negative)."""
        # Given: Fixed base time at 2026-01-26 10:00:00 UTC
        base_time = datetime(2026, 1, 26, 10, 0, 0, tzinfo=timezone.utc)
        mocked_time_provider.set_time(base_time)

        # And: A timestamp in the future (5 minutes from now)
        started_at = (base_time + timedelta(minutes=5)).isoformat()
        monitor = TimeoutMonitor(
            started_at=started_at, time_provider=mocked_time_provider
        )

        # When: Getting elapsed seconds
        elapsed = monitor.get_elapsed_seconds()

        # Then: Should return negative value
        assert elapsed == -300, (
            f"Expected -300 seconds for future timestamp, got {elapsed}"
        )

    def test_raises_error_for_invalid_timestamp_format(self, mocked_time_provider):
        """TimeoutMonitor raises ValueError for invalid timestamp format."""
        # Given: An invalid timestamp format
        invalid_timestamp = "not-a-valid-timestamp"

        # When/Then: Creating TimeoutMonitor should raise ValueError
        with pytest.raises(ValueError):
            TimeoutMonitor(
                started_at=invalid_timestamp, time_provider=mocked_time_provider
            )

    def test_handles_none_started_at(self, mocked_time_provider):
        """TimeoutMonitor raises ValueError for None started_at."""
        # When/Then: Creating TimeoutMonitor with None should raise ValueError
        with pytest.raises(ValueError):
            TimeoutMonitor(started_at=None, time_provider=mocked_time_provider)
