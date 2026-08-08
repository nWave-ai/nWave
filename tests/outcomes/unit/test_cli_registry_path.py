"""Unit test: the CLI explains an unusable registry path instead of tracebacking.

``_ensure_registry`` creates the registry skeleton on first use. That write was
unguarded, and the package-resource fix (issue #63) is what makes ``register``
reachable in an installed environment — so a read-only filesystem, a denied
permission, or a path occupied by a directory is now the next failure a real
user meets.

WHEN the registry path cannot be read or created, the system SHALL print a
message naming the path and the cause, and SHALL exit non-zero rather than
raise.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from nwave_ai.outcomes.cli import (
    RegistryPathUnusableError,
    _ensure_registry,
    handle_outcomes,
)


_REGISTER_ARGV = [
    "register",
    "--id",
    "OUT-1",
    "--kind",
    "operation",
    "--input-shape",
    "x",
    "--output-shape",
    "y",
]


def test_kind_choices_are_derived_from_the_domain_vocabulary() -> None:
    """argparse restates nothing — its choices come from ``OutcomeKind``."""
    from typing import get_args

    from nwave_ai.outcomes.cli import _KIND_CHOICES
    from nwave_ai.outcomes.domain.outcome import OutcomeKind

    assert _KIND_CHOICES == get_args(OutcomeKind)


def test_path_occupied_by_a_directory_is_named(tmp_path: Path) -> None:
    occupied = tmp_path / "registry.yaml"
    occupied.mkdir()

    with pytest.raises(RegistryPathUnusableError) as err:
        _ensure_registry(occupied)

    assert str(occupied) in str(err.value)
    assert "not a regular file" in str(err.value)


def test_unwritable_parent_is_named(tmp_path: Path, monkeypatch) -> None:
    """An OSError from the skeleton write surfaces as a named error, not a
    traceback. Patched rather than chmod-driven so the test holds where the
    suite runs as root and where chmod semantics differ."""
    target = tmp_path / "ro" / "registry.yaml"

    def _deny(*_args, **_kwargs):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(Path, "mkdir", _deny)

    with pytest.raises(RegistryPathUnusableError) as err:
        _ensure_registry(target)

    assert str(target) in str(err.value)
    assert "Permission denied" in str(err.value)


def test_cli_exits_4_and_reports_instead_of_raising(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    occupied = tmp_path / "registry.yaml"
    occupied.mkdir()

    exit_code = handle_outcomes(["--registry", str(occupied), *_REGISTER_ARGV])

    assert exit_code == 4
    captured = capsys.readouterr()
    assert "ERROR:" in captured.err
    assert str(occupied) in captured.err
