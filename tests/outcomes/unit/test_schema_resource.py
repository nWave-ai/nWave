"""Unit test: the outcomes JSON Schema travels with the package.

Regression guard for the `outcomes register` FileNotFoundError: the schema
used to be resolved by walking OUT of the package
(``Path(__file__).resolve().parents[3] / "docs" / ...``), which lands in
``site-packages/docs/...`` in any real install, and the schema was shipped
by no wheel include map.

WHEN the outcomes registry validates an entry, the system SHALL load the
schema as a resource of the ``nwave_ai.outcomes`` package.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from importlib import resources
from pathlib import Path

import yaml


def test_schema_is_a_loadable_package_resource() -> None:
    """The schema is readable via importlib.resources and is draft-07 JSON."""
    raw = (
        resources.files("nwave_ai.outcomes")
        .joinpath("schema.json")
        .read_text(encoding="utf-8")
    )
    schema = json.loads(raw)

    assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
    assert schema["properties"]["id"]["pattern"] == "^OUT-[A-Z0-9-]+$"


def test_register_succeeds_in_installed_shape_without_repo_docs_tree(
    tmp_path: Path,
) -> None:
    """Drive the real CLI from an installed-shape tree that has no ``docs/``.

    Copies only the ``nwave_ai`` package into a bare directory that stands in
    for ``site-packages`` and runs ``outcomes register`` from a project dir
    outside the checkout. A source-tree run masks the defect entirely, so the
    guard has to assert the installed shape.
    """
    repo_root = Path(__file__).resolve().parents[3]
    site_packages = tmp_path / "site-packages"
    shutil.copytree(
        repo_root / "nwave_ai",
        site_packages / "nwave_ai",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    assert not (site_packages / "docs").exists()

    project = tmp_path / "project"
    project.mkdir()

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "nwave_ai.cli",
            "outcomes",
            "register",
            "--id",
            "OUT-1",
            "--kind",
            "operation",
            "--input-shape",
            "x",
            "--output-shape",
            "y",
            "--feature",
            "demo",
            "--keywords",
            "k",
        ],
        cwd=project,
        env={
            "PATH": "/usr/bin:/bin",
            "PYTHONPATH": str(site_packages),
            "HOME": str(tmp_path / "home"),
        },
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert completed.returncode == 0, (
        f"register failed in installed shape: exit={completed.returncode}\n"
        f"stdout={completed.stdout}\nstderr={completed.stderr}"
    )
    registry = project / "docs" / "product" / "outcomes" / "registry.yaml"
    data = yaml.safe_load(registry.read_text(encoding="utf-8"))
    assert [o["id"] for o in data["outcomes"]] == ["OUT-1"]
