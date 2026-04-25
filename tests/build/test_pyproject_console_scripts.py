"""Tests for [project.scripts] entries in pyproject.toml.

Asserts that the nwave-ai installer entry point and 5 DES CLI console scripts
are declared with correct module mappings.
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
