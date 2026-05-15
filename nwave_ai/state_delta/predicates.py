"""Predicate factories for assert_state_delta.

Each factory returns a ``Predicate`` — a callable ``(old, new) -> bool`` — whose
``__name__`` identifies it in violation messages.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


Predicate = Callable[[Any, Any], bool]
Normalizer = Callable[[Any], Any]


def unchanged() -> Predicate:
    """Return a predicate that passes when ``old == new``.

    Example::

        pred = unchanged()
        pred("/h", "/h")   # True
        pred("/h", "/h2")  # False
    """

    def _predicate(old: Any, new: Any) -> bool:
        return bool(old == new)

    _predicate.__name__ = "unchanged()"
    return _predicate


def prepended_with(prefix: str, sep: str = ":") -> Predicate:
    """Return a predicate that passes when ``new == prefix + sep + old``.

    Example::

        pred = prepended_with("/des/bin")
        pred("/usr/bin", "/des/bin:/usr/bin")  # True
        pred("/usr/bin", "/wrong")             # False
    """
    expected_prefix = prefix + sep

    def _predicate(old: Any, new: Any) -> bool:
        return bool(new == expected_prefix + old)

    _predicate.__name__ = f"prepended_with({prefix})"
    return _predicate


def appended_with(suffix: str, sep: str = ":") -> Predicate:
    """Return a predicate that passes when ``new == old + sep + suffix``.

    Example::

        pred = appended_with(".bak")
        pred("/etc/hosts", "/etc/hosts:.bak")  # True
        pred("/etc/hosts", "/etc/hosts")       # False
    """

    def _predicate(old: Any, new: Any) -> bool:
        return bool(new == f"{old}{sep}{suffix}")

    _predicate.__name__ = f"appended_with({suffix})"
    return _predicate


def set_to(value: Any) -> Predicate:
    """Return a predicate that passes when ``new == value`` (``old`` is ignored).

    Example::

        pred = set_to("active")
        pred("inactive", "active")  # True
        pred("pending",  "active")  # True  — old is irrelevant
        pred("inactive", "pending") # False
    """

    def _predicate(old: Any, new: Any) -> bool:
        return bool(new == value)

    _predicate.__name__ = f"set_to({value!r})"
    return _predicate


def containing(substring: str) -> Predicate:
    """Return a predicate that passes when ``substring in new`` (``old`` is ignored).

    Example::

        pred = containing("/usr/bin")
        pred("", "/des/bin:/usr/bin")   # True
        pred("", "/des/bin:/opt/bin")   # False
    """

    def _predicate(old: Any, new: Any) -> bool:
        return substring in new

    _predicate.__name__ = f"containing({substring!r})"
    return _predicate


def normalized_to(normalizer: Normalizer) -> Predicate:
    """Return a predicate that passes when ``normalizer(old) == normalizer(new)``.

    Example::

        def home_expander(v: str) -> str:
            return v.replace("$HOME", "/home/u")

        pred = normalized_to(home_expander)
        pred("/home/u/.local/bin", "$HOME/.local/bin")   # True
        pred("/home/u/.local/bin", "$HOME/.other/bin")   # False
    """

    def _predicate(old: Any, new: Any) -> bool:
        return bool(normalizer(old) == normalizer(new))

    _predicate.__name__ = "normalized_to(<normalizer>)"
    return _predicate


def idempotent_after(prefix: str, sep: str = ":") -> Predicate:
    """Return a predicate that passes when ``prefix`` is already the first segment of ``new``.

    Used to assert that a "prepend if absent" operation was already applied (i.e. the
    prepend is idempotent because the prefix is already present as the first segment).

    Example::

        pred = idempotent_after("DES_BIN")
        pred("anything", "DES_BIN:/usr/bin")   # True  — prefix is first segment
        pred("anything", "/usr/bin:/opt/bin")  # False — prefix not first segment
    """

    def _check(old: Any, new: Any) -> bool:
        return bool(new.split(sep)[0] == prefix)

    _check.__name__ = f"idempotent_after({prefix})"
    return _check


def legacy_healed(
    detector: Callable[[Any], bool],
    healed_check: Callable[[Any], bool],
) -> Predicate:
    """Return a predicate implementing the D-11 legacy-heal 4-case paper-trace.

    Passes iff ``detector(old)`` and ``healed_check(new)`` are both True.
    When ``detector(old)`` is False the predicate short-circuits to False
    (``old`` is not a legacy fabricated value; a different predicate should
    be used for non-legacy inputs).

    Example::

        LEGACY = "DES_BIN:SYSTEM_PATH_FALLBACK"
        pred = legacy_healed(
            detector=lambda s: s == LEGACY,
            healed_check=lambda s: s != LEGACY and s.startswith("DES_BIN:"),
        )
        pred(LEGACY, "DES_BIN:/usr/bin")  # True  — Case 1: healed
        pred(LEGACY, LEGACY)              # False — Case 2: heal failed
        pred("/usr/bin", "DES_BIN:/usr/bin")  # False — Case 3: not legacy
    """

    def _check(old: Any, new: Any) -> bool:
        return detector(old) and healed_check(new)

    _check.__name__ = "legacy_healed(<det>,<heal>)"
    return _check
