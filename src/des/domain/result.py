"""Result type for explicit error handling.

Provides type-safe success/failure handling without exceptions,
making error cases explicit in function signatures.
"""

from dataclasses import dataclass
from typing import Generic, TypeVar


T = TypeVar("T")
E = TypeVar("E")


@dataclass(frozen=True)
class Success(Generic[T]):
    """Represents a successful result with a value.

    Use this when an operation succeeds and produces a value.
    """

    value: T

    def is_success(self) -> bool:
        """Always returns True for Success."""
        return True

    def is_failure(self) -> bool:
        """Always returns False for Success."""
        return False

    def unwrap(self) -> T:
        """Return the wrapped value."""
        return self.value

    def unwrap_or(self, default: T) -> T:
        """Return the wrapped value, ignoring the default."""
        return self.value


@dataclass(frozen=True)
class Failure(Generic[E]):
    """Represents a failed result with an error.

    Use this when an operation fails and produces an error.
    """

    error: E

    def is_success(self) -> bool:
        """Always returns False for Failure."""
        return False

    def is_failure(self) -> bool:
        """Always returns True for Failure."""
        return True

    def unwrap(self) -> None:
        """Raises an error since there is no value to unwrap."""
        raise ValueError(f"Cannot unwrap a Failure: {self.error}")

    def unwrap_or(self, default: object) -> object:
        """Return the default value since this is a Failure."""
        return default


# Type alias for cleaner usage
Result = Success[T] | Failure[E]
