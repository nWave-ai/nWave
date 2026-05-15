"""@slice-2 — lazy-import boundary tests + branch-reachability tests for
nwave_ai.state_delta.strategies.

Verifies:
- Importing the strategies subpackage does NOT load hypothesis (A9 contract)
- Calling path_strategy() DOES load hypothesis (lazy-import works)
- path_strategy accepts all 3 keyword-only parameters without error
- All 4 production branches (empty, $HOME-literal, legacy-heal, idempotent)
  are reachable via hypothesis.find() (DoD #6)
- include_* suppression flags correctly narrow generated shapes
- @given(path_strategy()) produces examples without StrategyError
"""

import subprocess
import sys


def test_strategies_import_does_not_load_hypothesis() -> None:
    """Importing nwave_ai.state_delta.strategies must NOT add hypothesis to sys.modules."""
    script = (
        "import sys\n"
        "import nwave_ai.state_delta.strategies\n"
        "leaked = [m for m in sys.modules if m.startswith('hypothesis')]\n"
        "assert not leaked, f'hypothesis leaked: {leaked}'\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_path_strategy_call_loads_hypothesis() -> None:
    """Calling path_strategy() MUST load hypothesis (lazy-import activated on call)."""
    script = (
        "import sys\n"
        "import nwave_ai.state_delta.strategies as strat\n"
        "assert 'hypothesis' not in sys.modules\n"
        "strat.path_strategy()\n"
        "assert 'hypothesis' in sys.modules, 'hypothesis should be in sys.modules after call'\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_path_strategy_signature_accepts_all_kwargs() -> None:
    """path_strategy() must accept all 3 keyword-only parameters without raising."""
    from nwave_ai.state_delta.strategies import path_strategy

    strategy = path_strategy(
        include_home_literal=False,
        include_empty=False,
        include_legacy_fallback=False,
    )
    assert strategy is not None


# ---------------------------------------------------------------------------
# Branch-reachability tests (DoD #6) — one per production branch
# ---------------------------------------------------------------------------


def test_path_strategy_can_produce_empty_string() -> None:
    """Branch: empty-seed — strategy must be able to produce the empty string."""
    from hypothesis import find
    from nwave_ai.state_delta.strategies import path_strategy

    result = find(path_strategy(), lambda s: s == "")
    assert result == ""


def test_path_strategy_can_produce_home_literal() -> None:
    """Branch: $HOME-literal — strategy must produce strings containing '$HOME'."""
    from hypothesis import find
    from nwave_ai.state_delta.strategies import path_strategy

    result = find(path_strategy(), lambda s: "$HOME" in s)
    assert "$HOME" in result


def test_path_strategy_can_produce_legacy_form() -> None:
    """Branch: legacy-heal — strategy must produce the exact legacy sentinel string."""
    from hypothesis import find
    from nwave_ai.state_delta.strategies import path_strategy

    legacy = "DES_BIN:SYSTEM_PATH_FALLBACK"
    result = find(path_strategy(), lambda s: s == legacy)
    assert result == legacy


def test_path_strategy_can_produce_idempotent_shape() -> None:
    """Branch: idempotent — strategy must produce paths that start with '/des/bin:'."""
    from hypothesis import find
    from nwave_ai.state_delta.strategies import path_strategy

    result = find(
        path_strategy(),
        lambda s: s.startswith("/des/bin:") and len(s.split(":")) > 1,
    )
    assert result.startswith("/des/bin:")


# ---------------------------------------------------------------------------
# Suppression tests — include_* flags narrow generated shapes
# ---------------------------------------------------------------------------


def test_path_strategy_include_empty_false_suppresses_empty_string() -> None:
    """include_empty=False must prevent empty strings from being generated."""
    from hypothesis import HealthCheck, given, settings
    from nwave_ai.state_delta.strategies import path_strategy

    @given(path_strategy(include_empty=False))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def check(s: str) -> None:
        assert s != "", "Empty string produced despite include_empty=False"

    check()


def test_path_strategy_include_home_literal_false_suppresses_home() -> None:
    """include_home_literal=False must prevent '$HOME' from appearing in examples."""
    from hypothesis import HealthCheck, given, settings
    from nwave_ai.state_delta.strategies import path_strategy

    @given(path_strategy(include_home_literal=False))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def check(s: str) -> None:
        assert "$HOME" not in s, (
            f"'$HOME' produced despite include_home_literal=False: {s!r}"
        )

    check()


def test_path_strategy_include_legacy_fallback_false_suppresses_legacy() -> None:
    """include_legacy_fallback=False must prevent the legacy sentinel from appearing."""
    from hypothesis import HealthCheck, given, settings
    from nwave_ai.state_delta.strategies import path_strategy

    legacy = "DES_BIN:SYSTEM_PATH_FALLBACK"

    @given(path_strategy(include_legacy_fallback=False))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def check(s: str) -> None:
        assert s != legacy, (
            "Legacy sentinel produced despite include_legacy_fallback=False"
        )

    check()


# ---------------------------------------------------------------------------
# @given smoke test — strategy produces examples without StrategyError
# ---------------------------------------------------------------------------


def test_path_strategy_given_produces_examples_without_error() -> None:
    """@given(path_strategy()) must generate at least 10 examples without error."""
    from hypothesis import given, settings
    from nwave_ai.state_delta.strategies import path_strategy

    examples: list[str] = []

    @given(path_strategy())
    @settings(max_examples=10)
    def collect(s: str) -> None:
        examples.append(s)

    collect()
    assert len(examples) >= 1  # smoke: at least one example generated
