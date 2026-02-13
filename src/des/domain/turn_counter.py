"""Turn counter for tracking and validating turn limits per DES phase."""


class TurnCounter:
    """Tracks turn count for each DES phase and validates against limits."""

    def __init__(self) -> None:
        """Initialize turn counter with empty phase tracking."""
        self._turn_counts: dict[str, int] = {}

    def get_current_turn(self, phase: str) -> int:
        """Get current turn count for specified phase.

        Args:
            phase: Name of the DES phase (e.g., "DISCOVER", "DISCUSS")

        Returns:
            Current turn count for the phase (0 if phase not tracked yet)
        """
        return self._turn_counts.get(phase, 0)

    def increment_turn(self, phase: str) -> None:
        """Increment turn count for specified phase by 1.

        Args:
            phase: Name of the DES phase to increment
        """
        current_count = self.get_current_turn(phase)
        self._turn_counts[phase] = current_count + 1

    def is_limit_exceeded(self, phase: str, max_turns: int) -> bool:
        """Check if turn count exceeds maximum allowed turns for phase.

        Args:
            phase: Name of the DES phase to check
            max_turns: Maximum allowed turns for the phase

        Returns:
            True if current turn count exceeds max_turns, False otherwise
        """
        current_count = self.get_current_turn(phase)
        return current_count > max_turns

    def reset_turn(self, phase: str) -> None:
        """Reset turn count for specified phase to zero.

        Args:
            phase: Name of the DES phase to reset
        """
        self._turn_counts[phase] = 0

    def to_dict(self) -> dict[str, int]:
        """Serialize counter state to dictionary.

        Returns:
            Dictionary mapping phase names to turn counts
        """
        return dict(self._turn_counts)

    def from_dict(self, state: dict[str, int]) -> None:
        """Restore counter state from dictionary.

        Args:
            state: Dictionary mapping phase names to turn counts
        """
        self._turn_counts = dict(state)
