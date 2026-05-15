"""Unit tests for nwave_ai.state_delta.chaos perturbation primitives.

Test budget: 5 distinct behaviors x 2 = 10 max tests. Using 8.

Behaviors under test:
  B1. chaos_env_perturbation: mutates env vars inside block, restores on exit.
  B2. chaos_env_perturbation: restoration works even when action raises.
  B3. chaos_filesystem_truncation: truncates existing files, restores on exit.
  B4. chaos_filesystem_truncation: removes created-during-chaos files on exit.
  B5. chaos_ordering_swap: executes sequence in swapped order, yields results.
  B6. enumerate_perturbations: emits correct count and named perturbations.
  B7. enumerate_perturbations: perturbations restore state after application.
  B8. chaos module does not load hypothesis at import time (A9 contract).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from nwave_ai.state_delta.chaos import (
    chaos_env_perturbation,
    chaos_filesystem_truncation,
    chaos_ordering_swap,
    enumerate_perturbations,
)


# ---------------------------------------------------------------------------
# B1 — chaos_env_perturbation: mutate inside block, restore on exit
# ---------------------------------------------------------------------------


class TestChaosEnvPerturbation:
    """chaos_env_perturbation applies env mutations inside the block only."""

    def test_env_var_mutated_inside_block_and_restored_after(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        GIVEN: PATH is set to a known value
        WHEN:  chaos_env_perturbation overrides PATH inside the block
        THEN:  PATH reflects the override inside the block
               AND PATH is restored to the original value after the block exits
        """
        monkeypatch.setenv("PATH", "/original/bin")

        observed_inside: list[str] = []

        with chaos_env_perturbation({"PATH": "/chaos/bin"}):
            observed_inside.append(os.environ.get("PATH", ""))

        assert observed_inside == ["/chaos/bin"], (
            f"Expected PATH='/chaos/bin' inside block, got {observed_inside}"
        )
        assert os.environ.get("PATH") == "/original/bin", (
            "PATH must be restored to original value after context exit"
        )

    def test_env_var_removal_restores_absence_on_exit(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        GIVEN: CHAOS_TEST_VAR is set to 'original'
        WHEN:  chaos_env_perturbation removes it (value=None) inside the block
        THEN:  CHAOS_TEST_VAR is absent inside the block
               AND CHAOS_TEST_VAR is restored to 'original' after exit
        """
        monkeypatch.setenv("CHAOS_TEST_VAR", "original")

        absent_inside = False
        with chaos_env_perturbation({"CHAOS_TEST_VAR": None}):
            absent_inside = "CHAOS_TEST_VAR" not in os.environ

        assert absent_inside, "CHAOS_TEST_VAR must be absent inside perturbation block"
        assert os.environ.get("CHAOS_TEST_VAR") == "original", (
            "CHAOS_TEST_VAR must be restored after context exit"
        )

    def test_env_restored_even_when_action_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        GIVEN: HOME is set to '/home/user'
        WHEN:  chaos_env_perturbation overrides HOME AND the block body raises
        THEN:  HOME is restored to '/home/user' despite the exception
        """
        monkeypatch.setenv("HOME", "/home/user")

        with pytest.raises(RuntimeError, match="simulated failure"):
            with chaos_env_perturbation({"HOME": "/chaos/home"}):
                raise RuntimeError("simulated failure")

        assert os.environ.get("HOME") == "/home/user", (
            "HOME must be restored even when the block raises"
        )


# ---------------------------------------------------------------------------
# B3 / B4 — chaos_filesystem_truncation
# ---------------------------------------------------------------------------


class TestChaosFilesystemTruncation:
    """chaos_filesystem_truncation truncates files inside block, restores on exit."""

    def test_existing_file_truncated_inside_block_and_restored(
        self, tmp_path: Path
    ) -> None:
        """
        GIVEN: settings.json contains non-empty JSON content
        WHEN:  chaos_filesystem_truncation truncates it inside the block
        THEN:  the file is empty (0 bytes) inside the block
               AND the original content is restored after the block exits
        """
        settings = tmp_path / "settings.json"
        original_content = b'{"key": "value"}'
        settings.write_bytes(original_content)

        observed_size_inside: list[int] = []

        with chaos_filesystem_truncation([settings]):
            observed_size_inside.append(settings.stat().st_size)

        assert observed_size_inside == [0], (
            f"File must be 0 bytes inside truncation block, got {observed_size_inside}"
        )
        assert settings.read_bytes() == original_content, (
            "Original file content must be restored after context exit"
        )

    def test_nonexistent_file_created_empty_inside_block_then_removed(
        self, tmp_path: Path
    ) -> None:
        """
        GIVEN: target.json does not exist
        WHEN:  chaos_filesystem_truncation is applied to a non-existent path
        THEN:  an empty file exists at that path inside the block (0 bytes)
               AND the file is removed after the block exits
        """
        target = tmp_path / "target.json"
        assert not target.exists(), "Pre-condition: file must not exist before test"

        file_existed_inside: list[bool] = []
        size_inside: list[int] = []

        with chaos_filesystem_truncation([target]):
            file_existed_inside.append(target.exists())
            size_inside.append(target.stat().st_size if target.exists() else -1)

        assert file_existed_inside == [True], "File must exist inside truncation block"
        assert size_inside == [0], (
            f"File must be 0 bytes inside block, got {size_inside}"
        )
        assert not target.exists(), (
            "Non-existent file must be removed after context exit"
        )


# ---------------------------------------------------------------------------
# B5 — chaos_ordering_swap
# ---------------------------------------------------------------------------


class TestChaosOrderingSwap:
    """chaos_ordering_swap executes the sequence with two steps swapped."""

    def test_sequence_executed_in_swapped_order(self) -> None:
        """
        GIVEN: action_sequence = [lambda: 'a', lambda: 'b', lambda: 'c']
               swap_indices = (0, 2)
        WHEN:  chaos_ordering_swap executes the swapped sequence
        THEN:  results == ['c', 'b', 'a']
               (indices 0 and 2 are swapped; index 1 stays)
        """
        execution_order: list[str] = []

        def step_a() -> str:
            execution_order.append("a")
            return "a"

        def step_b() -> str:
            execution_order.append("b")
            return "b"

        def step_c() -> str:
            execution_order.append("c")
            return "c"

        with chaos_ordering_swap([step_a, step_b, step_c], (0, 2)) as results:
            pass

        assert results == ["c", "b", "a"], (
            f"Expected ['c', 'b', 'a'] from swapped execution, got {results}"
        )
        assert execution_order == ["c", "b", "a"], (
            f"Execution order should reflect swap, got {execution_order}"
        )


# ---------------------------------------------------------------------------
# B6 — enumerate_perturbations: count and names
# ---------------------------------------------------------------------------


class TestEnumeratePerturbations:
    """enumerate_perturbations returns correctly named and counted perturbations."""

    def test_correct_count_for_env_and_file_axes(self, tmp_path: Path) -> None:
        """
        GIVEN: env_keys=['PATH', 'HOME'], file_paths=[settings_file]
        WHEN:  enumerate_perturbations is called
        THEN:  returns 4 perturbations:
               - 2 per-key env corruptions (PATH, HOME)
               - 1 all-keys removal (PATH + HOME together)
               - 1 filesystem truncation (settings_file)
        """
        settings_file = tmp_path / "settings.json"
        perturbations = enumerate_perturbations(
            env_keys=["PATH", "HOME"],
            file_paths=[settings_file],
        )

        assert len(perturbations) == 4, (
            f"Expected 4 perturbations (2 per-key + 1 all-removal + 1 file), "
            f"got {len(perturbations)}"
        )

    def test_perturbation_names_are_descriptive(self, tmp_path: Path) -> None:
        """
        GIVEN: env_keys=['PATH'], file_paths=[settings_file]
        WHEN:  enumerate_perturbations is called
        THEN:  each returned callable has a __name__ identifying the perturbation type
        """
        settings_file = tmp_path / "settings.json"
        perturbations = enumerate_perturbations(
            env_keys=["PATH"],
            file_paths=[settings_file],
        )

        names = [p.__name__ for p in perturbations]
        assert any("chaos_env_set" in n for n in names), (
            f"Expected a 'chaos_env_set' perturbation name, got {names}"
        )
        assert any("chaos_env_remove" in n for n in names), (
            f"Expected a 'chaos_env_remove' perturbation name, got {names}"
        )
        assert any("chaos_truncate" in n for n in names), (
            f"Expected a 'chaos_truncate' perturbation name, got {names}"
        )

    def test_perturbations_restore_env_state_after_application(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        GIVEN: PATH is set to '/original/bin'
        WHEN:  each env perturbation from enumerate_perturbations is applied and exited
        THEN:  PATH is restored to '/original/bin' after each perturbation exits
        """
        monkeypatch.setenv("PATH", "/original/bin")

        perturbations = enumerate_perturbations(env_keys=["PATH"])

        for perturbation in perturbations:
            with perturbation():
                pass  # perturbation active inside block
            assert os.environ.get("PATH") == "/original/bin", (
                f"PATH must be restored after perturbation '{perturbation.__name__}' exits"
            )


# ---------------------------------------------------------------------------
# B8 — A9 lazy-import contract: chaos module must not load hypothesis at import
# ---------------------------------------------------------------------------


_A9_SCRIPT = """
import sys
import nwave_ai.state_delta.chaos
leaked = [m for m in sys.modules if "hypothesis" in m]
assert not leaked, f"hypothesis leaked into sys.modules: {leaked}"
"""


def test_chaos_module_import_does_not_load_hypothesis() -> None:
    """
    GIVEN: a fresh Python interpreter
    WHEN:  nwave_ai.state_delta.chaos is imported
    THEN:  hypothesis is NOT loaded into sys.modules (A9 contract)
    """
    result = subprocess.run(
        [sys.executable, "-c", _A9_SCRIPT],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"hypothesis leaked after importing chaos module.\nstderr: {result.stderr}"
    )
    assert result.stderr == "", f"Unexpected stderr: {result.stderr}"
