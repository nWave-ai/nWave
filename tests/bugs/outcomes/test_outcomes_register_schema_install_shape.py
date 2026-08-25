"""Regression oracle for nWave-ai/nWave#63.

The package is relocated without the repository ``docs/`` tree.  This is the
observable installation shape that the old ``__file__.parents[...]`` lookup
could not survive.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest
import yaml


pytest_plugins = ("tests.build.unit.test_wheel_contract",)

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_RESOURCE = Path("nwave_ai/outcomes/schema.json")
EMPTY_REGISTRY = 'schema_version: "0.1"\noutcomes: []\n'


def _installed_shape(tmp_path: Path) -> tuple[Path, Path, Path]:
    site_packages = tmp_path / "site-packages"
    shutil.copytree(REPO_ROOT / "nwave_ai", site_packages / "nwave_ai")
    project = tmp_path / "project"
    project.mkdir()
    registry = project / "registry.yaml"
    registry.write_text(EMPTY_REGISTRY, encoding="utf-8")
    return site_packages, project, registry


def _register(
    site_packages: Path,
    project: Path,
    registry: Path,
    outcome_id: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "nwave_ai.cli",
            "outcomes",
            "--registry",
            str(registry),
            "register",
            "--id",
            outcome_id,
            "--kind",
            "operation",
            "--input-shape",
            "request",
            "--output-shape",
            "registry row",
        ],
        cwd=project,
        env={**os.environ, "PYTHONPATH": str(site_packages)},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_register_is_invariant_under_package_relocation(tmp_path: Path) -> None:
    """A normal installed package can validate and persist an outcome."""
    site_packages, project, registry = _installed_shape(tmp_path)

    result = _register(site_packages, project, registry, "OUT-INSTALL-1")

    assert result.returncode == 0, result.stderr
    assert "REGISTERED: OUT-INSTALL-1" in result.stdout
    assert "Traceback (most recent call last)" not in result.stderr
    rows = yaml.safe_load(registry.read_text(encoding="utf-8"))["outcomes"]
    assert [row["id"] for row in rows] == ["OUT-INSTALL-1"]


def test_missing_packaged_schema_refuses_without_writing(tmp_path: Path) -> None:
    """A damaged install is distinguishable from invalid input and writes nothing."""
    site_packages, project, registry = _installed_shape(tmp_path)
    schema = site_packages / SCHEMA_RESOURCE
    schema.unlink(missing_ok=True)
    before = registry.read_bytes()

    result = _register(site_packages, project, registry, "OUT-UNCHECKABLE")

    assert result.returncode == 3
    assert "refus" in result.stderr.lower()
    assert "schema" in result.stderr.lower()
    assert "reinstall" in result.stderr.lower()
    assert "Traceback (most recent call last)" not in result.stderr
    assert registry.read_bytes() == before


@pytest.mark.slow
def test_built_wheel_contains_outcomes_schema(built_wheel: Path) -> None:
    """The resource travels in the artifact users actually install."""
    assert SCHEMA_RESOURCE.as_posix() in ZipFile(built_wheel).namelist()
