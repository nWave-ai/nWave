"""The dependency adapters this version has, by the name a project declares.

A project maps a file extension to an adapter name (``selection.adapters``). A name
that is not here is not guessed around: the selector reports every file of that
type as undecided, with the name it missed.

To add a language, add a module with the two functions of
``selection.DependencyAdapter`` and name it here.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING

from nwave_ai.testrun import python_dependencies


if TYPE_CHECKING:
    from collections.abc import Mapping

    from nwave_ai.testrun.selection import DependencyAdapter


ADAPTERS: Mapping[str, DependencyAdapter] = MappingProxyType(
    {"python": python_dependencies}
)
