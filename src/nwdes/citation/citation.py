"""A test citation: the file that declares a test and, for a generative law, the name its author gives it."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Citation:
    test_path: str
    test: str | None = None

    def describe(self) -> str:
        return self.test_path if self.test is None else f"{self.test_path} {self.test}"
