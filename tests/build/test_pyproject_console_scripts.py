"""Tests for [project.scripts] entries in pyproject.toml.

Asserts that the public CLI (nwave-ai) plus 5 DES CLI console scripts are
declared with correct module mappings.

Regression-lock for issue #41: v3.12.0 wheel shipped without the nwave-ai
entry point because patch_pyproject.py:_add_cli_entry_point early-returns
when [project.scripts] already exists in source. The fix is to declare
nwave-ai directly in source so its presence does not depend on the patcher.
"""

from pathlib import Path


try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]


PYPROJECT_PATH = Path(__file__).parent.parent.parent / "pyproject.toml"

EXPECTED_SCRIPTS = {
    "nwave-ai": "nwave_ai.cli:main",
    "des-log-phase": "des.cli.log_phase:main",
    "des-init-log": "des.cli.init_log:main",
    "des-verify-integrity": "des.cli.verify_deliver_integrity:main",
    "des-roadmap": "des.cli.roadmap:main",
    "des-health-check": "des.cli.health_check:main",
}


def _load_pyproject() -> dict:
    with open(PYPROJECT_PATH, "rb") as f:
        return tomllib.load(f)


def test_project_scripts_section_exists_with_6_entries() -> None:
    data = _load_pyproject()
    scripts = data["project"]["scripts"]
    assert len(scripts) == 6, (
        f"Expected exactly 6 console script entries, got {len(scripts)}: {list(scripts.keys())}"
    )


def test_project_scripts_maps_to_correct_modules() -> None:
    data = _load_pyproject()
    scripts = data["project"]["scripts"]
    for name, expected_entry_point in EXPECTED_SCRIPTS.items():
        assert name in scripts, f"Missing console script: {name!r}"
        assert scripts[name] == expected_entry_point, (
            f"Script {name!r} maps to {scripts[name]!r}, expected {expected_entry_point!r}"
        )


def test_nwave_ai_console_script_is_declared_in_source() -> None:
    """Issue #41 regression: nwave-ai must be in [project.scripts] at source,
    not injected by patch_pyproject.py (whose skip-if-exists guard early-returns
    when [project.scripts] already has any entries)."""
    data = _load_pyproject()
    scripts = data["project"]["scripts"]
    assert scripts.get("nwave-ai") == "nwave_ai.cli:main", (
        "nwave-ai console script must be declared in source pyproject.toml "
        "[project.scripts] so the public wheel always ships it. "
        f"Got: {scripts.get('nwave-ai')!r}"
    )
