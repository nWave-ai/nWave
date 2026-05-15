"""Pytest configuration for tests/speculative/.

Provides a Hypothesis-safe tmp_path fixture and suppresses the
function_scoped_fixture health check for this package.

The speculative audit tests use `tmp_path` with `@given`. Pytest's built-in
`tmp_path` is function-scoped and returns the **same Path object** for every
Hypothesis example within one test invocation.  Because `write_trace` appends
to a JSONL file, examples accumulate entries and `len(recovered) == 1` fails
by example 2.

Fix: override `tmp_path` to return an `_EpochRootPath`.  Before each Hypothesis
example call, Hypothesis invokes the wrapped inner test function.  We wrap that
inner function (via `pytest_itemcollected`) to advance an epoch counter stored
on the `_EpochRootPath` instance.  All `root / child` calls within one epoch
land in the same slot; the slot changes when the epoch advances (i.e. at the
start of each new Hypothesis example).
"""

from __future__ import annotations

import itertools
from functools import wraps
from pathlib import Path
from typing import Any

import pytest
from hypothesis import HealthCheck, is_hypothesis_test, settings


settings.register_profile(
    "speculative",
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
settings.load_profile("speculative")

_global_epoch = itertools.count()

# Slot registry: maps (root_id, epoch) -> slot_path
_slot_cache: dict[tuple[int, int], Path] = {}


class _EpochRootPath(type(Path())):  # type: ignore[misc]
    """Path subclass whose `/` operator is epoch-stable within one example.

    All `root / child` calls sharing the same epoch resolve to the same
    slot subdirectory.  When the epoch advances (triggered by the Hypothesis
    example-boundary wrapper installed in `pytest_itemcollected`), subsequent
    `/` calls land in a fresh slot.

    This gives each Hypothesis example an isolated filesystem root while
    keeping write_trace and read_traces calls within the same example
    co-located.
    """

    _current_epoch: int

    def __new__(cls, *args: Any, **kwargs: Any) -> _EpochRootPath:
        obj = super().__new__(cls, *args, **kwargs)
        obj._current_epoch = next(_global_epoch)
        return obj

    def advance_epoch(self) -> None:
        """Advance to a new epoch (called at each Hypothesis example boundary)."""
        self._current_epoch = next(_global_epoch)

    def __truediv__(self, key: Any) -> Path:  # type: ignore[override]
        cache_key = (id(self), self._current_epoch)
        if cache_key not in _slot_cache:
            # Use Path() explicitly to avoid returning _EpochRootPath (infinite recursion)
            slot = Path(super().__truediv__(f"_ep{self._current_epoch}"))
            slot.mkdir(parents=True, exist_ok=True)
            _slot_cache[cache_key] = slot
        return _slot_cache[cache_key] / key


@pytest.fixture()
def tmp_path(tmp_path: Path) -> _EpochRootPath:  # type: ignore[override]
    """Return an _EpochRootPath so Hypothesis examples are filesystem-isolated."""
    return _EpochRootPath(tmp_path)


def pytest_itemcollected(item: pytest.Item) -> None:
    """Wrap @given test inner functions to advance the epoch before each example.

    Hypothesis calls ``item.obj`` (the @given-wrapped function) which in turn
    calls the inner test function once per example.  We replace the inner test
    function with a wrapper that calls ``tmp_path_arg.advance_epoch()`` before
    delegating, advancing the filesystem slot so each example gets a clean root.
    """
    if not hasattr(item, "obj") or not is_hypothesis_test(item.obj):
        return

    inner = item.obj.hypothesis.inner_test  # type: ignore[attr-defined]

    import inspect

    params = list(inspect.signature(inner).parameters)
    if "tmp_path" not in params:
        return

    tmp_path_index = params.index("tmp_path")

    @wraps(inner)
    def _epoch_advancing_inner(*args: Any, **kwargs: Any) -> Any:
        # tmp_path may be positional or keyword
        if "tmp_path" in kwargs:
            epoch_path = kwargs["tmp_path"]
        elif tmp_path_index < len(args):
            epoch_path = args[tmp_path_index]
        else:
            return inner(*args, **kwargs)

        if isinstance(epoch_path, _EpochRootPath):
            epoch_path.advance_epoch()
        return inner(*args, **kwargs)

    item.obj.hypothesis.inner_test = _epoch_advancing_inner  # type: ignore[attr-defined]
