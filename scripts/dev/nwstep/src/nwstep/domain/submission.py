"""What the executor gave on the command line, before any rule has checked it."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable


class Submission:
    def __init__(
        self,
        scalars: Iterable[tuple[str, str]] = (),
        items: Iterable[tuple[str, str]] = (),
        problems: Iterable[str] = (),
    ) -> None:
        self._scalars = tuple(scalars)
        self._items = tuple(items)
        self.problems = tuple(problems)

    def scalar(self, name: str) -> str | None:
        return next((value for key, value in self._scalars if key == name), None)

    def scalars_of(self, name: str) -> list[str]:
        return [value for key, value in self._scalars if key == name]

    def items_of(self, name: str) -> list[str]:
        return [value for key, value in self._items if key == name]

    def repeated_scalars(self) -> tuple[str, ...]:
        counts = Counter(key for key, _ in self._scalars)
        return tuple(sorted(name for name, count in counts.items() if count > 1))

    def names(self) -> tuple[str, ...]:
        return tuple(sorted({key for key, _ in (*self._scalars, *self._items)}))

    def given(self) -> dict[str, list[list[str]]]:
        """The submission as it was given, kept in the record so that a replay can record the step again."""
        return {
            "scalars": [[key, value] for key, value in self._scalars],
            "items": [[key, value] for key, value in self._items],
        }

    @classmethod
    def from_given(cls, given: dict[str, list[list[str]]]) -> Submission:
        return cls(
            scalars=[(key, value) for key, value in given.get("scalars", [])],
            items=[(key, value) for key, value in given.get("items", [])],
        )
