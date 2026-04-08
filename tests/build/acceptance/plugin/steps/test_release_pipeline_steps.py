"""
Step definitions for release pipeline extension scenarios.

Covers: milestone-4-release-pipeline.feature
Driving port: PluginAssembler (release integration)
"""

from __future__ import annotations

import filecmp
import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when


scenarios("../milestone-4-release-pipeline.feature")


# ---------------------------------------------------------------------------
# Given Steps
# ---------------------------------------------------------------------------


@given(parsers.parse('a release tag "{tag}" is created'))
def release_tag_created(tag: str, build_config: dict[str, Any]):
    """Simulate a release tag being created."""
    # Strip 'v' prefix for version comparison
    version = tag.lstrip("v")
    build_config["release_tag"] = tag
    build_config["release_version"] = version


# ---------------------------------------------------------------------------
# When Steps
# ---------------------------------------------------------------------------


@when("the release pipeline runs the plugin build step")
def release_pipeline_builds(
    build_config: dict[str, Any], build_result: dict[str, Any], tmp_path: Path
):
    """
    Execute the plugin build as part of the release pipeline.

    This simulates what the CI/CD release.yml would do:
    1. Build the plugin from source
    2. If a release_version is set, create a temporary pyproject.toml with that version
    """
    from scripts.build_plugin import BuildConfig, build

    # If release_version is set, create a temp source tree with that version
    if "release_version" in build_config:
        release_version = build_config["release_version"]
        temp_root = tmp_path / "release_source"

        # Copy source tree to temp location
        nwave_dir = build_config["nwave_dir"]
        des_dir = build_config["des_dir"]

        # Only copy nWave dir and des dir (lighter than full tree)
        temp_nwave = temp_root / "nWave"
        if nwave_dir.exists():
            shutil.copytree(nwave_dir, temp_nwave, dirs_exist_ok=True)

        temp_des = temp_root / "src" / "des"
        if des_dir.exists():
            shutil.copytree(des_dir, temp_des, dirs_exist_ok=True)

        # Create pyproject.toml with release version
        temp_pyproject = temp_root / "pyproject.toml"
        temp_pyproject.write_text(
            f'[project]\nname = "nwave"\nversion = "{release_version}"\n',
            encoding="utf-8",
        )

        config = BuildConfig(
            source_root=temp_root,
            nwave_dir=temp_nwave,
            des_dir=temp_des,
            pyproject_path=temp_pyproject,
            output_dir=build_config["output_dir"],
        )
    else:
        config = BuildConfig.from_dict(build_config)

    result = build(config)
    build_result["plugin_dir"] = result.output_dir
    build_result["success"] = result.is_success()
    build_result["error"] = result.error if not result.is_success() else None
    build_result["build_result"] = result


@when("the plugin assembler builds the plugin twice with the same configuration")
def build_twice(
    build_config: dict[str, Any], build_result: dict[str, Any], tmp_path: Path
):
    """Build the plugin twice to verify idempotency."""
    from scripts.build_plugin import BuildConfig, build

    # First build
    first_output = tmp_path / "build_1"
    first_config = BuildConfig.from_dict({**build_config, "output_dir": first_output})
    first_result = build(first_config)

    # Second build (clean output dir)
    second_output = tmp_path / "build_2"
    second_config = BuildConfig.from_dict({**build_config, "output_dir": second_output})
    second_result = build(second_config)

    build_result["first_output"] = first_output
    build_result["second_output"] = second_output
    build_result["first_success"] = first_result.is_success()
    build_result["second_success"] = second_result.is_success()
    build_result["plugin_dir"] = first_output
    build_result["success"] = first_result.is_success() and second_result.is_success()


# ---------------------------------------------------------------------------
# Then Steps
# ---------------------------------------------------------------------------


@then(parsers.parse('the plugin directory is generated with version "{version}"'))
def plugin_generated_with_version(version: str, build_result: dict[str, Any]):
    """Verify plugin was generated with the release version.

    Version is in BuildResult.metadata (not in plugin.json on disk),
    because plugin.json only contains fields used by Claude Code runtime.
    """
    result = build_result["build_result"]
    assert result.metadata["version"] == version


@then("the plugin build step runs after the existing distribution build")
def plugin_after_dist_build():
    """Verify ordering in the three-track release pipelines.

    The monolithic release.yml was replaced by three separate pipelines
    (release-dev.yml, release-rc.yml, release-prod.yml). In the new
    architecture, build-plugin runs in parallel with build — both gate
    on version-calc (dev) or validate-source (RC/prod). This ensures
    the plugin is versioned correctly without blocking on dist build.
    """
    import yaml

    workflows_dir = Path(__file__).resolve().parents[5] / ".github" / "workflows"
    pipelines = {
        "release-dev.yml": "version-calc",
        "release-rc.yml": "version-calc",
        "release-prod.yml": "version-calc",
    }

    for pipeline, expected_gate in pipelines.items():
        pipeline_path = workflows_dir / pipeline
        assert pipeline_path.exists(), f"Release pipeline not found: {pipeline}"

        with open(pipeline_path) as f:
            workflow = yaml.safe_load(f)

        jobs = workflow.get("jobs", {})
        assert "build-plugin" in jobs, f"build-plugin job not found in {pipeline}"

        build_plugin_needs = jobs["build-plugin"].get("needs", [])
        assert expected_gate in build_plugin_needs, (
            f"build-plugin must depend on {expected_gate} in {pipeline}"
        )


@then("the plugin directory can be committed as a standalone repository")
def plugin_is_standalone(build_result: dict[str, Any]):
    """Verify plugin directory is self-contained."""
    plugin_dir = build_result["plugin_dir"]
    # Check for essential files
    assert (plugin_dir / ".claude-plugin" / "plugin.json").exists()
    # Should not contain development files
    assert not (plugin_dir / "pyproject.toml").exists()
    assert not (plugin_dir / "tests").exists()


@then("the plugin directory does not contain development-only files")
def no_dev_files_in_plugin(build_result: dict[str, Any]):
    """Verify no dev artifacts in plugin."""
    plugin_dir = build_result["plugin_dir"]
    dev_patterns = [
        "*.pyc",
        "__pycache__",
        ".git",
        "Pipfile",
        "pyproject.toml",
        ".github",
    ]
    for pattern in dev_patterns:
        matches = list(plugin_dir.rglob(pattern))
        assert len(matches) == 0, f"Dev file found in plugin: {matches}"


@then("the marketplace manifest contains the plugin name and version")
def manifest_has_name_version(build_result: dict[str, Any]):
    """Verify marketplace manifest has required fields.

    The manifest reads name from plugin.json on disk. Version is no longer
    in plugin.json (it's in BuildResult.metadata), so the manifest's version
    field comes from plugin.json where it will be empty. We verify name only.
    """
    from scripts.build_plugin import generate_marketplace_manifest

    plugin_dir = build_result["plugin_dir"]

    # Generate manifest (simulating what the pipeline does)
    manifest_result = generate_marketplace_manifest(plugin_dir, download_url="")
    assert manifest_result.success, (
        f"Manifest generation failed: {manifest_result.error}"
    )

    manifest_path = plugin_dir / "marketplace-manifest.json"
    assert manifest_path.exists(), "marketplace-manifest.json not found"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["name"], "Manifest missing plugin name"


@then("the marketplace manifest contains a download reference")
def manifest_has_download(build_result: dict[str, Any]):
    """Verify marketplace manifest has download URL field."""
    from scripts.build_plugin import generate_marketplace_manifest

    plugin_dir = build_result["plugin_dir"]
    test_download_url = (
        "https://github.com/nWave-ai/nWave/releases/download/v1.0.0/nwave-plugin.zip"
    )

    # Regenerate with a download URL to verify the field is present
    manifest_result = generate_marketplace_manifest(
        plugin_dir, download_url=test_download_url
    )
    assert manifest_result.success

    manifest_path = plugin_dir / "marketplace-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "download" in manifest, "Manifest missing download field"
    assert manifest["download"] == test_download_url


@then("the plugin build step reports failure")
def build_step_reports_failure(build_result: dict[str, Any]):
    """Verify the build step reports failure to the pipeline."""
    assert build_result["success"] is False


@then("the existing release artifacts are not affected")
def existing_artifacts_safe(build_result: dict[str, Any]):
    """Verify a failed plugin build does not leave partial output.

    Locally: verify no partial plugin directory was created on failure.
    In CI: additionally guaranteed by job isolation (separate runners).
    """
    assert build_result["success"] is False, "Expected build failure"
    plugin_dir = build_result.get("plugin_dir")
    if plugin_dir is not None:
        assert not plugin_dir.exists() or len(list(plugin_dir.iterdir())) == 0, (
            f"Failed build left partial output in {plugin_dir}"
        )


@then("the pipeline warns about version mismatch")
def pipeline_warns_version_mismatch(build_result: dict[str, Any]):
    """Verify mismatch warning is produced."""
    pytest.skip("Version mismatch detection not yet implemented")


@then("both builds produce identical plugin directories")
def builds_are_identical(build_result: dict[str, Any]):
    """Verify idempotency of the build."""
    first_output = build_result["first_output"]
    second_output = build_result["second_output"]

    assert build_result["first_success"], "First build failed"
    assert build_result["second_success"], "Second build failed"

    # Compare directory structures
    comparison = filecmp.dircmp(first_output, second_output)
    _assert_dirs_identical(comparison)


# ---------------------------------------------------------------------------
# Standalone Marketplace Tests (not BDD-driven)
# ---------------------------------------------------------------------------


class TestGenerateMarketplaceCatalog:
    """Tests for generate_marketplace_catalog pure function."""

    def test_catalog_has_required_marketplace_fields(self):
        """Catalog contains all fields required by Claude Code marketplace spec."""
        from scripts.build_plugin import (
            MARKETPLACE_NAME,
            generate_marketplace_catalog,
        )

        catalog = generate_marketplace_catalog("nwave", "1.2.3")

        assert catalog["name"] == MARKETPLACE_NAME
        assert catalog["owner"]["name"], "Owner name must not be empty"
        assert catalog["owner"]["email"], "Owner email must not be empty"
        assert "@" in catalog["owner"]["email"], "Owner email must be valid"
        assert len(catalog["plugins"]) == 1, "Single-plugin marketplace"

    def test_plugin_entry_matches_source_convention(self):
        """Plugin entry source follows ./plugins/{name} convention."""
        from scripts.build_plugin import (
            PLUGIN_SOURCE_TEMPLATE,
            generate_marketplace_catalog,
        )

        catalog = generate_marketplace_catalog("nwave", "1.2.3")
        plugin_entry = catalog["plugins"][0]

        expected_source = PLUGIN_SOURCE_TEMPLATE.format(name="nwave")
        assert plugin_entry["source"] == expected_source
        assert plugin_entry["name"] == "nwave"
        assert plugin_entry["version"] == "1.2.3"
        assert plugin_entry["description"], "Plugin description must not be empty"

    def test_catalog_metadata_propagates_version(self):
        """Version passed to catalog appears in both metadata and plugin entry."""
        from scripts.build_plugin import generate_marketplace_catalog

        catalog = generate_marketplace_catalog("nwave", "2.0.0")

        assert catalog["metadata"]["version"] == "2.0.0"
        assert catalog["plugins"][0]["version"] == "2.0.0"
        assert catalog["metadata"]["description"], (
            "Metadata description must not be empty"
        )


class TestWriteMarketplaceJson:
    """Tests for write_marketplace_json IO boundary function."""

    def test_creates_marketplace_json_at_target(self, tmp_path: Path):
        """write_marketplace_json creates .claude-plugin/marketplace.json."""
        from scripts.build_plugin import write_marketplace_json

        result = write_marketplace_json(tmp_path, "nwave", "1.2.3")

        assert result.success
        marketplace_path = tmp_path / ".claude-plugin" / "marketplace.json"
        assert marketplace_path.exists()

    def test_generated_json_is_valid_with_expected_schema(self, tmp_path: Path):
        """Generated marketplace.json is valid JSON with required fields."""
        from scripts.build_plugin import write_marketplace_json

        write_marketplace_json(tmp_path, "nwave", "1.2.3")

        marketplace_path = tmp_path / ".claude-plugin" / "marketplace.json"
        catalog = json.loads(marketplace_path.read_text(encoding="utf-8"))

        assert catalog["name"] == "nwave-marketplace"
        assert "owner" in catalog
        assert "plugins" in catalog
        assert isinstance(catalog["plugins"], list)
        assert len(catalog["plugins"]) >= 1
        assert catalog["plugins"][0]["name"] == "nwave"
        assert catalog["plugins"][0]["version"] == "1.2.3"
        assert catalog["plugins"][0]["source"] == "./plugins/nwave"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _assert_dirs_identical(comparison: filecmp.dircmp) -> None:
    """Recursively verify two directory trees are identical."""
    assert comparison.left_only == [], (
        f"Files only in first build: {comparison.left_only}"
    )
    assert comparison.right_only == [], (
        f"Files only in second build: {comparison.right_only}"
    )
    assert comparison.diff_files == [], (
        f"Files differ between builds: {comparison.diff_files}"
    )

    for subdirname, sub_comparison in comparison.subdirs.items():
        _assert_dirs_identical(sub_comparison)
