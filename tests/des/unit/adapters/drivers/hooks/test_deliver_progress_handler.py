"""Tests for the deliver progress handler's log/roadmap base discovery.

Regression coverage for RCA p1 Branch C (the silent-failure sibling of the
SubagentStop hardcoded-base bug fixed in step 01-01). The handler reconstructed
a hardcoded ``docs/feature`` base when resolving roadmap.json / execution-log.json,
so a project namespaced under the override base ``docs/nwave/feature`` was never
found — track_progress saw no roadmap and the handler skipped silently (returned
0 with no progress recorded).

The fix reuses the cwd=-based candidate-base search from execution_log_resolver
(step 01-01) so the base is OBSERVED from disk and the override base wins.
"""

from __future__ import annotations

from pathlib import Path

from des.adapters.drivers.hooks.deliver_progress_handler import _resolve_deliver_paths


def _make_wave_dir(cwd: Path, base_suffix: str, project_id: str) -> Path:
    """Create docs/<base_suffix>/feature/<project_id>/deliver/ with a log file."""
    wave_dir = cwd / "docs" / base_suffix / project_id / "deliver"
    wave_dir.mkdir(parents=True)
    # resolve_execution_log_path needs the log present to OBSERVE this base.
    (wave_dir / "execution-log.json").write_text("{}", encoding="utf-8")
    return wave_dir


def test_resolves_paths_under_override_base(tmp_path: Path) -> None:
    """A project under docs/nwave/feature resolves there, not docs/feature.

    Failing-for-right-reason against current code: the handler passes
    base=docs/feature, so the override-base log is never found, the resolver
    raises FileNotFoundError, and the fallback reconstructs the hardcoded
    docs/feature/<id>/deliver paths — the assertion on the override base fails.
    """
    project_id = "fix-subagent-stop-hardcoded-base-path-p2"
    wave_dir = _make_wave_dir(tmp_path, "nwave/feature", project_id)

    roadmap_path, exec_log_path, progress_path = _resolve_deliver_paths(
        str(tmp_path), project_id
    )

    assert exec_log_path == wave_dir / "execution-log.json"
    assert roadmap_path == wave_dir / "roadmap.json"
    assert progress_path == wave_dir / ".develop-progress.json"


def test_default_base_behavior_unchanged(tmp_path: Path) -> None:
    """The common default-base case (docs/feature) still resolves correctly."""
    project_id = "some-default-feature"
    wave_dir = _make_wave_dir(tmp_path, "feature", project_id)

    roadmap_path, exec_log_path, progress_path = _resolve_deliver_paths(
        str(tmp_path), project_id
    )

    assert exec_log_path == wave_dir / "execution-log.json"
    assert roadmap_path == wave_dir / "roadmap.json"
    assert progress_path == wave_dir / ".develop-progress.json"


def test_missing_project_falls_back_to_default_deliver(tmp_path: Path) -> None:
    """When no log exists anywhere, fall back to docs/feature/<id>/deliver.

    Preserves the existing missing-file handling: handle_deliver_progress checks
    roadmap_path.exists() and returns 0, so the fallback must point at a stable
    default location rather than raising.
    """
    project_id = "never-initialized"

    roadmap_path, exec_log_path, progress_path = _resolve_deliver_paths(
        str(tmp_path), project_id
    )

    default_wave = tmp_path / "docs" / "feature" / project_id / "deliver"
    assert exec_log_path == default_wave / "execution-log.json"
    assert roadmap_path == default_wave / "roadmap.json"
    assert progress_path == default_wave / ".develop-progress.json"
