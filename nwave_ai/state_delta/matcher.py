"""Core matcher for assert_state_delta."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal


if TYPE_CHECKING:
    from collections.abc import Mapping

    from nwave_ai.state_delta.predicates import Predicate


@dataclass(frozen=True)
class Violation:
    """A single state-delta violation.

    Attributes:
        kind: Classification of the violation.
        key: The environment key that violated the constraint.
        old: Value before the operation.
        new: Value after the operation.
        predicate_name: Name of the failing predicate (``predicate_failed`` only).
    """

    kind: Literal["undeclared_change", "predicate_failed", "strict_universe_mismatch"]
    key: str
    old: Any
    new: Any
    predicate_name: str | None  # None for undeclared_change / strict_universe_mismatch


@dataclass(frozen=True)
class MatcherResult:
    """Aggregated result of a matcher run (internal; exposed for testing convenience)."""

    violations: tuple[Violation, ...]


def _format_violation(v: Violation) -> str:
    """Render one violation as a single human-readable line."""
    base = f"  kind={v.kind!r} key={v.key!r} old={v.old!r} new={v.new!r}"
    if v.predicate_name is not None:
        base += f" predicate_name={v.predicate_name!r}"
    return base


def _collect_violations(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    universe: set[str],
    expected: Mapping[str, Predicate],
) -> tuple[Violation, ...]:
    """Collect all violations across *universe* without raising."""
    violations: list[Violation] = []

    for key in universe:
        old_value = before.get(key)
        new_value = after.get(key)

        predicate = expected.get(key)

        if predicate is not None:
            if not predicate(old_value, new_value):
                predicate_name = getattr(predicate, "__name__", repr(predicate))
                violations.append(
                    Violation(
                        kind="predicate_failed",
                        key=key,
                        old=old_value,
                        new=new_value,
                        predicate_name=predicate_name,
                    )
                )
        # Implicit-unchanged: key in universe but not declared in expected
        elif old_value != new_value:
            violations.append(
                Violation(
                    kind="undeclared_change",
                    key=key,
                    old=old_value,
                    new=new_value,
                    predicate_name=None,
                )
            )

    return tuple(violations)


def assert_state_delta(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    universe: set[str],
    expected: Mapping[str, Predicate],
    *,
    strict: bool = False,
) -> None:
    """Assert that state transitions satisfy expected predicates.

    For each key in ``universe``:

    - If the key has a predicate in ``expected``, the predicate is called with
      ``(before[key], after[key])``.  A ``False`` return records a
      ``predicate_failed`` violation.
    - If the key is **not** in ``expected``, ``before[key] == after[key]`` is
      required.  A difference records an ``undeclared_change`` violation
      (implicit-unchanged enforcement).

    All violations are collected across the full ``universe`` before a single
    ``AssertionError`` is raised (multi-violation contract, A7).

    Args:
        before: State snapshot before the operation.
        after: State snapshot after the operation.
        universe: Keys whose transitions are under scrutiny.
        expected: Mapping of key -> predicate to apply.
        strict: Reserved for future use (strict/lax mode, step 01-03).

    Returns:
        None when all constraints pass.

    Raises:
        AssertionError: One error listing ALL violations when any constraint fails.
    """
    violations: list[Violation] = []

    if strict:
        extra_keys = (before.keys() | after.keys()) - universe
        for key in sorted(extra_keys):
            violations.append(
                Violation(
                    kind="strict_universe_mismatch",
                    key=key,
                    old=before.get(key),
                    new=after.get(key),
                    predicate_name=None,
                )
            )

    violations.extend(_collect_violations(before, after, universe, expected))

    if not violations:
        return None

    lines = [f"assert_state_delta: {len(violations)} violation(s) detected:"]
    lines.extend(_format_violation(v) for v in violations)
    raise AssertionError("\n".join(lines))
