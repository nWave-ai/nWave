"""Step definitions for subprocess timeout calibration regression.

Drives two property-based scenarios from
``tests/bugs/installer/acceptance/test_subprocess_timeout_calibration.feature``:

Scenario A — Every subprocess.run timeout has >= 3.5x headroom over its
             serial baseline (Root Causes A + C in the RCA).
  Driving port: AST walk of target source files via ``ast.parse(...).walk()``.
  The scenario reads each target file's source, walks the AST for ``Call``
  nodes whose function resolves to ``subprocess.run``, extracts the
  ``timeout=`` keyword's literal value, pairs (file, line, timeout) with the
  measured serial baseline, and asserts ``timeout >= baseline * 3.5`` for
  every pair. Pre-fix: >=1 pair fails (currently install_smoke.py:51 at
  120s / 66s = 1.82x). Post-fix (step 01-02): all pairs pass.

Scenario B — Tutorial setup-script idempotent-second-run assertion embeds
             ``parent.name``, ``stdout``, ``stderr`` (Root Cause B).
  Driving port: AST walk of
  ``tests/build/acceptance/test_tutorial_setup_scripts.py``. Locates the
  ``Assert`` node inside ``test_idempotent_second_run`` whose test condition
  matches ``first.returncode == 0`` and inspects its message string. Pre-fix:
  message references only ``stderr``. Post-fix: message references all three.

PBT + state-delta paradigm: the property is itself the test; the
``state-delta`` framing applies at the universe-of-(file,line,timeout,baseline)
tuples scope — the universe is the full set of build-tier timeout literals,
the expected predicate is "headroom ratio >= 3.5", strict in that NO tuple in
the universe may violate. Hypothesis ``@given`` is not the right primitive
here because the universe is a small, exhaustively enumerable set (11
literals) rather than a strategy-generated input space. The property is
exhaustively checked over the universe in a single AST walk.

Port-to-port: the scenarios invoke ONLY stdlib ``ast`` + filesystem reads via
the pytest-bdd driver. No imports of production-code helpers — the scenarios
are independent of any helper that step 01-02 might author.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when


# ----------------------------------------------------------------------------
# Configuration: target files, baselines, headroom ratio
# ----------------------------------------------------------------------------

# Project root resolved relative to this file (tests/bugs/installer/acceptance/steps/)
PROJECT_ROOT = Path(__file__).resolve().parents[5]

# Headroom ratio: observed parallel-contention multiplier 2.66x over serial
# baselines (RCA evidence: 66s serial pip install -> 176s under parallel
# pytest-xdist contention) + ~30% safety margin against future suite growth
# and neighbour-process drift. Chosen at 3.5x per architect adjustment in
# step 01-01 task spec; the value lives here as the single source of truth.
HEADROOM_RATIO: float = 3.5

# Empirically measured serial baselines (seconds) per (file, line) target.
# Sources:
#   - test_install_smoke.py — RCA section 2 timing harness
#   - test_build_dist.py    — pytest --durations=0 average ~0.39s
#   - validate_installed_wheel.py — repeated subprocess invocation harness ~5s
TIMEOUT_TARGETS: dict[tuple[str, int], float] = {
    # test_install_smoke.py: pip-install (66s), venv-create (10s), wheel-build (6s)
    ("tests/build/unit/test_install_smoke.py", 51): 66.0,
    ("tests/build/unit/test_install_smoke.py", 72): 10.0,
    ("tests/build/unit/test_install_smoke.py", 84): 6.0,
    # test_build_dist.py: 5 build_dist.py invocations (~0.4s avg)
    ("tests/build/unit/test_build_dist.py", 427): 0.4,
    ("tests/build/unit/test_build_dist.py", 445): 0.4,
    ("tests/build/unit/test_build_dist.py", 462): 0.4,
    ("tests/build/unit/test_build_dist.py", 476): 0.4,
    ("tests/build/unit/test_build_dist.py", 501): 0.4,
    # validate_installed_wheel.py: 3 venv-python subprocess calls (~5s avg)
    ("scripts/validation/validate_installed_wheel.py", 75): 5.0,
    ("scripts/validation/validate_installed_wheel.py", 104): 5.0,
    ("scripts/validation/validate_installed_wheel.py", 138): 5.0,
}

# Tutorial assertion target (Scenario B)
TUTORIAL_TEST_FILE = "tests/build/acceptance/test_tutorial_setup_scripts.py"
TUTORIAL_FUNC_NAME = "test_idempotent_second_run"
REQUIRED_SUBSTRINGS = ("parent.name", "stdout", "stderr")


# ----------------------------------------------------------------------------
# Pytest-bdd scenario binding
# ----------------------------------------------------------------------------

scenarios("../test_subprocess_timeout_calibration.feature")


# ----------------------------------------------------------------------------
# Scenario state
# ----------------------------------------------------------------------------


class _ScenarioState:
    """Container for cross-step state. Pytest-bdd uses one fixture per scenario."""

    def __init__(self) -> None:
        self.headroom_ratio: float = HEADROOM_RATIO
        self.baselines: dict[tuple[str, int], float] = {}
        # Scenario A: list of (file, line, timeout, baseline, ratio, ok)
        self.timeout_pairs: list[tuple[str, int, float, float, float, bool]] = []
        # Scenario B: assertion message string + substring-presence flags
        self.assertion_message: str | None = None
        self.substring_hits: dict[str, bool] = {}


@pytest.fixture
def scenario_state() -> _ScenarioState:
    return _ScenarioState()


# ----------------------------------------------------------------------------
# AST helpers (no production-code imports — stdlib only)
# ----------------------------------------------------------------------------


def _is_subprocess_run_call(node: ast.Call) -> bool:
    """Return True if `node` is a Call to subprocess.run (any common alias)."""
    func = node.func
    # subprocess.run(...)
    if isinstance(func, ast.Attribute) and func.attr == "run":
        if isinstance(func.value, ast.Name) and func.value.id == "subprocess":
            return True
    # from subprocess import run; run(...)
    return isinstance(func, ast.Name) and func.id == "run"


def _extract_timeout_literal_with_line(
    call: ast.Call,
) -> tuple[int, float] | None:
    """Return (line_of_literal, numeric_value) for the `timeout=` kwarg, or None.

    The line returned is the literal's own line (``kw.value.lineno``), NOT the
    enclosing Call's start line. This matches the line numbers operators see
    in the source file when looking at the timeout literal itself.
    """
    for kw in call.keywords:
        if kw.arg == "timeout":
            value = kw.value
            if isinstance(value, ast.Constant) and isinstance(
                value.value, (int, float)
            ):
                return (value.lineno, float(value.value))
    return None


def _walk_subprocess_run_timeouts(
    source_path: Path,
) -> Iterable[tuple[int, float]]:
    """Yield (literal_line_no, timeout) for every subprocess.run call with timeout."""
    text = source_path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(source_path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _is_subprocess_run_call(node):
            found = _extract_timeout_literal_with_line(node)
            if found is not None:
                yield found


def _find_idempotent_returncode_assert(source_path: Path) -> ast.Assert | None:
    """Locate the `assert first.returncode == 0` node in test_idempotent_second_run.

    Returns the ``Assert`` AST node whose test is ``first.returncode == 0`` and
    which lives inside the function ``test_idempotent_second_run``. Returns
    ``None`` if the function or the assertion shape is not found.
    """
    text = source_path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(source_path))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == TUTORIAL_FUNC_NAME:
            for child in ast.walk(node):
                if isinstance(child, ast.Assert):
                    test = child.test
                    # Match: <name>.returncode == 0
                    if (
                        isinstance(test, ast.Compare)
                        and isinstance(test.left, ast.Attribute)
                        and test.left.attr == "returncode"
                        and len(test.ops) == 1
                        and isinstance(test.ops[0], ast.Eq)
                        and len(test.comparators) == 1
                        and isinstance(test.comparators[0], ast.Constant)
                        and test.comparators[0].value == 0
                    ):
                        # Confirm the left-hand attribute's value is named "first"
                        # (idempotency test has a `first.returncode` and a
                        # `second.returncode`; we want the FIRST one per AC #3).
                        owner = test.left.value
                        if isinstance(owner, ast.Name) and owner.id == "first":
                            return child
    return None


def _stringify_assert_message(msg_node: ast.expr | None) -> str:
    """Flatten an assertion-message AST node into its source-text approximation."""
    if msg_node is None:
        return ""
    return ast.unparse(msg_node)


# ----------------------------------------------------------------------------
# Scenario A — subprocess timeout headroom property
# ----------------------------------------------------------------------------


@given("the empirically measured serial baselines for build-tier subprocesses")
def given_baselines(scenario_state: _ScenarioState) -> None:
    scenario_state.baselines = dict(TIMEOUT_TARGETS)


@given("the headroom ratio is 3.5")
def given_ratio(scenario_state: _ScenarioState) -> None:
    scenario_state.headroom_ratio = HEADROOM_RATIO


@when("the AST of every targeted build-tier source file is walked")
def when_walk_ast(scenario_state: _ScenarioState) -> None:
    pairs: list[tuple[str, int, float, float, float, bool]] = []
    # Group targets by file so we parse each file once
    by_file: dict[str, list[tuple[int, float]]] = {}
    for (rel_path, line_no), baseline in scenario_state.baselines.items():
        by_file.setdefault(rel_path, []).append((line_no, baseline))

    for rel_path, expected_pairs in by_file.items():
        source_path = PROJECT_ROOT / rel_path
        observed: dict[int, float] = dict(_walk_subprocess_run_timeouts(source_path))
        for line_no, baseline in expected_pairs:
            timeout = observed.get(line_no)
            assert timeout is not None, (
                f"AST walk found no subprocess.run(...timeout=...) at "
                f"{rel_path}:{line_no} — target table out of sync with source. "
                f"Observed lines in {rel_path}: {sorted(observed.keys())}"
            )
            ratio = timeout / baseline
            ok = ratio >= scenario_state.headroom_ratio
            pairs.append((rel_path, line_no, timeout, baseline, ratio, ok))
    scenario_state.timeout_pairs = pairs


@then("every subprocess.run timeout literal satisfies the headroom rule")
def then_every_timeout_meets_headroom(scenario_state: _ScenarioState) -> None:
    failures = [p for p in scenario_state.timeout_pairs if not p[5]]
    assert not failures, (
        "Subprocess timeout headroom violations (timeout < baseline x "
        f"{scenario_state.headroom_ratio}):\n"
        + "\n".join(
            f"  {file}:{line} timeout={timeout}s baseline={baseline}s "
            f"ratio={ratio:.2f}x (need >= {scenario_state.headroom_ratio}x)"
            for file, line, timeout, baseline, ratio, _ in failures
        )
    )


# ----------------------------------------------------------------------------
# Scenario B — tutorial idempotency assertion-message diagnostic property
# ----------------------------------------------------------------------------


@given("the tutorial setup-script idempotency test at test_tutorial_setup_scripts.py")
def given_tutorial_test(scenario_state: _ScenarioState) -> None:
    # Sentinel — file existence verified in the When step via AST parse.
    source_path = PROJECT_ROOT / TUTORIAL_TEST_FILE
    assert source_path.is_file(), f"Target tutorial test file missing: {source_path}"


@when("the AST of its first-run-returncode assertion is inspected")
def when_inspect_assertion(scenario_state: _ScenarioState) -> None:
    source_path = PROJECT_ROOT / TUTORIAL_TEST_FILE
    node = _find_idempotent_returncode_assert(source_path)
    assert node is not None, (
        f"Could not locate `assert first.returncode == 0` inside "
        f"`{TUTORIAL_FUNC_NAME}` in {TUTORIAL_TEST_FILE} — AST shape changed."
    )
    message = _stringify_assert_message(node.msg)
    scenario_state.assertion_message = message
    scenario_state.substring_hits = {
        sub: (sub in message) for sub in REQUIRED_SUBSTRINGS
    }


@then("the assertion message string references parent.name")
def then_message_has_parent_name(scenario_state: _ScenarioState) -> None:
    assert scenario_state.substring_hits.get("parent.name"), (
        f"Tutorial idempotency assertion message lacks `parent.name`. "
        f"Operators cannot identify which setup-script (tutorial-step) "
        f"failed. Message text: {scenario_state.assertion_message!r}"
    )


@then("the assertion message string references stdout")
def then_message_has_stdout(scenario_state: _ScenarioState) -> None:
    assert scenario_state.substring_hits.get("stdout"), (
        f"Tutorial idempotency assertion message lacks `stdout`. "
        f"Operators cannot see what the script printed on success-then-failure. "
        f"Message text: {scenario_state.assertion_message!r}"
    )


@then("the assertion message string references stderr")
def then_message_has_stderr(scenario_state: _ScenarioState) -> None:
    assert scenario_state.substring_hits.get("stderr"), (
        f"Tutorial idempotency assertion message lacks `stderr`. "
        f"Operators cannot see the error output. "
        f"Message text: {scenario_state.assertion_message!r}"
    )
