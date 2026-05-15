"""Adversarial state perturbation harness for chaos-discipline testing.

Complements assert_state_delta: where the matcher catches static post-state
violations, this harness injects RUNTIME state corruption to validate that
production code is robust to mid-action environment changes.

Three classes of perturbation:

  1. **Environment perturbation** — mutate env vars mid-action, restore on exit.
  2. **Filesystem truncation** — truncate files mid-action to simulate partial
     writes or disk-full conditions.
  3. **Ordering swap** — reorder two dependent operations to test order-dependence.

Pure functional API: all primitives are context managers that take, corrupt, and
restore external state. No classes. No global mutable state inside this module.

A9 contract (ADR-002): hypothesis is NOT imported at module level. Call
``enumerate_perturbations_strategy()`` to get the Hypothesis strategy — that is
the only function that lazy-loads hypothesis.

Usage::

    from nwave_ai.state_delta.chaos import (
        chaos_env_perturbation,
        chaos_filesystem_truncation,
        chaos_ordering_swap,
        enumerate_perturbations,
        enumerate_perturbations_strategy,
    )
"""

from __future__ import annotations

import os
from collections.abc import Callable, Generator, Iterable
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path  # noqa: TC003 — used at runtime in function bodies
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    # hypothesis stays lazy per A9 contract — never loaded at module import time.
    from hypothesis.strategies import SearchStrategy


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

# A perturbation is a callable that accepts no arguments and returns a context
# manager whose __enter__ applies the mutation and whose __exit__ restores it.
# AbstractContextManager[None] is the correct type for @contextmanager functions —
# they return _GeneratorContextManager which implements AbstractContextManager.
Perturbation = Callable[[], AbstractContextManager[None]]


# ---------------------------------------------------------------------------
# Primitive 1: environment perturbation
# ---------------------------------------------------------------------------


@contextmanager
def chaos_env_perturbation(
    env_overrides: dict[str, str | None],
) -> Generator[None, None, None]:
    """Mutate env vars mid-action, restore on exit.

    Applies ``env_overrides`` to ``os.environ`` on enter, restores original
    values (or removes keys that were absent before) on exit.

    Args:
        env_overrides: Mapping of env-var name to new value. A value of ``None``
            removes the key from ``os.environ``.

    Yields:
        None — the mutated environment is visible inside the ``with`` block.

    Example::

        with chaos_env_perturbation({"PATH": "/broken", "HOME": None}):
            DESPlugin()._install_des_shims(context)  # runs under corrupted env
    """
    originals: dict[str, str | None] = {}
    for key in env_overrides:
        originals[key] = os.environ.get(key)

    try:
        for key, value in env_overrides.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, original_value in originals.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value


# ---------------------------------------------------------------------------
# Primitive 2: filesystem truncation
# ---------------------------------------------------------------------------


@contextmanager
def chaos_filesystem_truncation(
    file_paths: Iterable[Path],
    truncate_at: int = 0,
) -> Generator[None, None, None]:
    """Truncate files mid-action to simulate partial writes or disk-full conditions.

    Saves original content of each file before the block. On enter, truncates
    each file to ``truncate_at`` bytes. On exit, restores all files to their
    original content (or removes them if they did not exist before).

    Files that do not exist at context entry are created empty and then removed
    on exit — this lets callers corrupt files that the action-under-test creates
    during the block. If you want to simulate truncation of a file the action
    creates, pass the target path; the harness will leave an empty file for the
    action to encounter, then clean up.

    Args:
        file_paths: Iterable of paths to truncate on context entry.
        truncate_at: Byte offset at which to truncate. 0 means empty file.

    Yields:
        None — truncated files are visible inside the ``with`` block.

    Example::

        settings = claude_dir / "settings.json"
        with chaos_filesystem_truncation([settings]):
            DESPlugin()._install_des_shims(context)
    """
    paths = list(file_paths)
    saved: dict[Path, bytes | None] = {}

    for path in paths:
        if path.exists():
            saved[path] = path.read_bytes()
        else:
            saved[path] = None  # did not exist before

    try:
        for path in paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "wb") as fh:
                fh.truncate(truncate_at)
        yield
    finally:
        for path, original_content in saved.items():
            if original_content is None:
                # File did not exist before — remove if still present
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(original_content)


# ---------------------------------------------------------------------------
# Primitive 3: ordering swap
# ---------------------------------------------------------------------------


@contextmanager
def chaos_ordering_swap(
    action_sequence: list[Callable[[], Any]],
    swap_indices: tuple[int, int],
) -> Generator[list[Any], None, None]:
    """Execute a sequence of actions with two entries swapped to test order-dependence.

    Unlike the other primitives, this is NOT a mid-action injection (there is
    nothing to "restore" after reordering pure function calls). Instead it wraps
    the execution of an explicit sequence, running the swapped order and yielding
    the list of return values so the caller can assert on them.

    Useful for testing that two steps in a pipeline are genuinely independent
    (i.e., swapping them produces the same net result) or that they are correctly
    ordered (i.e., swapping them produces a different — expected-to-fail — result).

    Args:
        action_sequence: Ordered list of zero-argument callables to execute.
        swap_indices: Pair of indices (i, j) to swap before execution.

    Yields:
        List of return values from the swapped execution.

    Raises:
        IndexError: If either index is out of bounds.

    Example::

        with chaos_ordering_swap([step_a, step_b, step_c], (0, 2)) as results:
            pass  # results == [step_c(), step_b(), step_a()]
    """
    i, j = swap_indices
    swapped = list(action_sequence)
    swapped[i], swapped[j] = swapped[j], swapped[i]

    results: list[Any] = []
    try:
        for action in swapped:
            results.append(action())
        yield results
    finally:
        pass  # no state to restore; sequence was never mutated in-place


# ---------------------------------------------------------------------------
# Perturbation enumeration — exhaustive iteration over applicable perturbations
# ---------------------------------------------------------------------------


def enumerate_perturbations(
    env_keys: Iterable[str] | None = None,
    file_paths: Iterable[Path] | None = None,
) -> list[Perturbation]:
    """Return all perturbations applicable to the declared state surface.

    Produces one perturbation per declared axis:
    - One ``chaos_env_perturbation`` per env key (sets it to a known-bad value).
    - One ``chaos_env_perturbation`` that removes all listed env keys.
    - One ``chaos_filesystem_truncation`` per file path (truncates to 0 bytes).

    The combination of these primitives covers the key failure modes that
    a real Chaos Monkey would inject — environment corruption and filesystem
    corruption. Ordering-swap perturbations are not enumerated automatically
    (they require caller knowledge of the step sequence) but can be composed
    manually using ``chaos_ordering_swap``.

    Args:
        env_keys: Env-var names that the action-under-test reads or writes.
        file_paths: File paths that the action-under-test reads or writes.

    Returns:
        List of zero-argument callables, each returning a context manager.
        Call each as ``with perturbation():`` to apply.

    Example::

        from contextlib import ExitStack
        perturbations = enumerate_perturbations(
            env_keys=["PATH", "HOME"],
            file_paths=[settings_file],
        )
        for perturbation in perturbations:
            with perturbation():
                action()  # executed under one perturbation at a time
    """
    result: list[Perturbation] = []

    resolved_env_keys = list(env_keys) if env_keys is not None else []
    resolved_file_paths = list(file_paths) if file_paths is not None else []

    # Per-key env corruption: set each key to an intentionally broken value
    for key in resolved_env_keys:
        broken_value = f"__CHAOS_BROKEN_{key}__"

        def _make_env_perturb(k: str, v: str) -> Perturbation:
            def _perturbation() -> AbstractContextManager[None]:
                return chaos_env_perturbation({k: v})

            _perturbation.__name__ = f"chaos_env_set({k!r}={v!r})"
            return _perturbation

        result.append(_make_env_perturb(key, broken_value))

    # All-keys removal: remove all listed env keys simultaneously
    if resolved_env_keys:
        removal_overrides = dict.fromkeys(resolved_env_keys)

        def _make_all_removal(overrides: dict[str, str | None]) -> Perturbation:
            def _perturbation() -> AbstractContextManager[None]:
                return chaos_env_perturbation(overrides)

            _perturbation.__name__ = f"chaos_env_remove({list(overrides.keys())!r})"
            return _perturbation

        result.append(_make_all_removal(removal_overrides))

    # Per-file truncation
    for file_path in resolved_file_paths:

        def _make_file_perturb(p: Path) -> Perturbation:
            def _perturbation() -> AbstractContextManager[None]:
                return chaos_filesystem_truncation([p])

            _perturbation.__name__ = f"chaos_truncate({p.name!r})"
            return _perturbation

        result.append(_make_file_perturb(file_path))

    return result


# ---------------------------------------------------------------------------
# Hypothesis strategy for perturbation enumeration (lazy import)
# ---------------------------------------------------------------------------


def enumerate_perturbations_strategy(
    env_keys: Iterable[str] | None = None,
    file_paths: Iterable[Path] | None = None,
) -> SearchStrategy[Perturbation]:
    """Return a Hypothesis strategy that generates one perturbation at a time.

    Lazy-imports hypothesis inside the function body to keep the
    nwave-ai wheel install hypothesis-free at module load time (A9 contract).

    The strategy samples from the list returned by ``enumerate_perturbations``
    with the same arguments. Each Hypothesis example receives exactly one
    perturbation context manager to apply around the action-under-test.

    Args:
        env_keys: Env-var names passed to ``enumerate_perturbations``.
        file_paths: File paths passed to ``enumerate_perturbations``.

    Returns:
        A Hypothesis ``SearchStrategy[Perturbation]`` drawing from the
        enumerated perturbation list.

    Raises:
        ValueError: When the enumerated perturbation list is empty (no axes
            declared — would generate a vacuous strategy).

    Example::

        @given(perturbation=enumerate_perturbations_strategy(
            env_keys=["PATH"],
            file_paths=[settings_file],
        ))
        def test_install_robust_to_chaos(perturbation):
            with perturbation():
                DESPlugin()._install_des_shims(context)
            ...
    """
    # Lazy import — hypothesis is loaded only when this function is CALLED.
    from hypothesis import strategies as st

    perturbations = enumerate_perturbations(env_keys=env_keys, file_paths=file_paths)

    if not perturbations:
        raise ValueError(
            "enumerate_perturbations_strategy: no perturbations enumerated. "
            "Provide at least one env_key or file_path."
        )

    return st.sampled_from(perturbations)
