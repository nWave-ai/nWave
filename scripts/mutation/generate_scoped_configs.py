#!/usr/bin/env python3
"""
Generate feature-scoped mutation testing configurations from execution-log.yaml

This script extracts implementation files from execution-log.yaml and creates
per-component Cosmic Ray configurations with scoped test commands that only run
tests related to each changed file.

Approach:
- Maps implementation files to their test files (unit, integration, acceptance, E2E)
- Generates cosmic-ray-{component}.toml configs with scoped test commands
- Runs only relevant tests per mutant (10-50x faster than full test suite)

Usage:
    python scripts/mutation/generate_scoped_configs.py <project-id>

Example:
    python scripts/mutation/generate_scoped_configs.py des-hook-enforcement

Output:
    docs/feature/{project-id}/mutation/cosmic-ray-{component}.toml (one per implementation file)
"""

import argparse
import os
import sys
from pathlib import Path

import yaml


def extract_implementation_files(execution_status_path: str) -> list[str]:
    """Extract all implementation files from execution-log.yaml"""
    with open(execution_status_path) as f:
        data = yaml.safe_load(f)

    impl_files = set()
    for step in data["execution_status"]["completed_steps"]:
        if "files_modified" in step and "implementation" in step["files_modified"]:
            for file in step["files_modified"]["implementation"]:
                if file.startswith("src/") and file.endswith(".py"):
                    impl_files.add(file)

    return sorted(impl_files)


def find_unit_test(impl_file: str) -> str | None:
    """
    Find unit test file for implementation file using naming convention.

    Conventions tried (in order):
    1. src/module/submodule/foo.py → tests/module/unit/submodule/test_foo.py
    2. src/module/submodule/foo.py → tests/module/unit/test_foo.py (flat)
    3. src/module/submodule/foo.py → tests/unit/test_foo.py (global unit tests)
    """
    # Parse implementation file path
    parts = impl_file.split("/")
    if len(parts) < 3:  # Need at least src/module/file.py
        return None

    # Extract: src/module/submodule/.../file.py
    module = parts[1]  # e.g., "des"
    file_name = parts[-1]  # e.g., "validator.py"
    subpath = "/".join(parts[2:-1])  # e.g., "application" or "adapters/driven/config"

    # Try 1: Full hierarchical path
    test_file = (
        f"tests/{module}/unit/{subpath}/test_{file_name}"
        if subpath
        else f"tests/{module}/unit/test_{file_name}"
    )
    if os.path.exists(test_file):
        return test_file

    # Try 2: Flat structure within module
    test_file_flat = f"tests/{module}/unit/test_{file_name}"
    if os.path.exists(test_file_flat):
        return test_file_flat

    # Try 3: Global unit tests (not module-prefixed)
    test_file_global = f"tests/unit/test_{file_name}"
    if os.path.exists(test_file_global):
        return test_file_global

    return None


def find_acceptance_tests(project_id: str) -> list[str]:
    """Find all acceptance test files for the feature"""
    acceptance_tests = []

    # Look in common acceptance test locations
    patterns = [
        f"tests/*/acceptance/test_{project_id.replace('-', '_')}*.py",
        "tests/*/acceptance/test_*_steps.py",
        "tests/*/acceptance/test_*.py",
    ]

    for pattern in patterns:
        import glob

        for test_file in glob.glob(pattern):
            if test_file not in acceptance_tests:
                acceptance_tests.append(test_file)

    return sorted(acceptance_tests)


def find_integration_tests(impl_file: str, module: str) -> list[str]:
    """Find integration tests that might test this implementation file"""
    integration_tests = []

    # Look for integration tests in the same module
    integration_dir = f"tests/{module}/integration"
    if os.path.exists(integration_dir):
        import glob

        for test_file in glob.glob(f"{integration_dir}/**/*.py", recursive=True):
            if test_file.startswith("test_"):
                integration_tests.append(test_file)

    return integration_tests


def map_implementation_to_tests(impl_file: str, project_id: str) -> list[str]:
    """
    Map an implementation file to all test files that should run for mutation testing.

    Includes:
    - Direct unit test (naming convention)
    - Feature acceptance tests (E2E)
    - Related integration tests
    """
    tests = []

    # Extract module from implementation file
    module = impl_file.split("/")[1] if "/" in impl_file else None

    # 1. Unit test (direct)
    unit_test = find_unit_test(impl_file)
    if unit_test:
        tests.append(unit_test)

    # 2. Acceptance tests (E2E) for the feature
    acceptance_tests = find_acceptance_tests(project_id)
    tests.extend(acceptance_tests)

    # 3. Integration tests (if any)
    if module:
        integration_tests = find_integration_tests(impl_file, module)
        tests.extend(integration_tests)

    # Deduplicate and sort
    return sorted(set(tests))


def generate_cosmic_ray_config(impl_file: str, test_files: list[str], output_path: str):
    """Generate a Cosmic Ray TOML config file for a single implementation file"""

    # Extract component name for config file naming
    component_name = impl_file.replace("src/", "").replace("/", "_").replace(".py", "")

    # Build test command (space-separated test files)
    test_command = f"pytest -x {' '.join(test_files)}"

    config_content = f"""# Feature-Scoped Mutation Testing Configuration
# Component: {impl_file}
# Generated by: scripts/mutation/generate_scoped_configs.py
#
# This config runs ONLY the tests that exercise this specific implementation file:
# - Unit tests: Direct tests for this component
# - Acceptance tests: E2E tests that exercise this component
# - Integration tests: Tests that validate component integration
#
# Approach: Feature-scoped (not full test suite)
# Benefit: 10-50x faster than running entire test suite per mutant

[cosmic-ray]
module-path = "{impl_file}"
timeout = 30.0
excluded-modules = []
test-command = "{test_command}"

[cosmic-ray.distributor]
name = "local"

[cosmic-ray.execution-engine]
name = "local"
"""

    config_file = os.path.join(output_path, f"cosmic-ray-{component_name}.toml")
    with open(config_file, "w") as f:
        f.write(config_content)

    return config_file, component_name


def count_lines(file_path: str) -> int:
    """Count non-blank, non-comment lines in a Python file"""
    if not os.path.exists(file_path):
        return 0

    count = 0
    with open(file_path) as f:
        for line in f:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                count += 1
    return count


def main():
    parser = argparse.ArgumentParser(
        description="Generate feature-scoped mutation testing configurations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate configs for a feature
  python scripts/mutation/generate_scoped_configs.py des-hook-enforcement

  # Output is written to:
  docs/feature/{project-id}/mutation/cosmic-ray-*.toml
        """,
    )
    parser.add_argument("project_id", help="Project ID (e.g., des-hook-enforcement)")
    parser.add_argument(
        "--output-dir",
        help="Output directory (default: docs/feature/{project-id}/mutation/)",
    )

    args = parser.parse_args()

    project_id = args.project_id
    execution_status_path = f"docs/feature/{project_id}/execution-log.yaml"

    # Check if execution status file exists
    if not os.path.exists(execution_status_path):
        print(f"❌ Error: {execution_status_path} not found")
        print("   Make sure you run this from the project root and the feature exists")
        sys.exit(1)

    # Determine output directory
    output_dir = args.output_dir or f"docs/feature/{project_id}/mutation/"
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 60}")
    print("Feature-Scoped Mutation Testing Config Generator")
    print(f"{'=' * 60}\n")
    print(f"Project: {project_id}")
    print(f"Output: {output_dir}")
    print()

    # Extract implementation files
    print("STEP 1: Extracting implementation files from execution-log.yaml...")
    impl_files = extract_implementation_files(execution_status_path)

    if not impl_files:
        print("❌ No implementation files found in execution-log.yaml")
        sys.exit(1)

    print(f"✓ Found {len(impl_files)} implementation files")
    print()

    # Generate configs
    print("STEP 2: Mapping implementation files to test files...")
    print()

    configs_generated = []
    total_impl_lines = 0

    for impl_file in impl_files:
        # Map to tests
        test_files = map_implementation_to_tests(impl_file, project_id)

        if not test_files:
            print(f"⚠️  {impl_file}")
            print("   No test files found (skipping mutation testing)")
            print()
            continue

        # Count lines
        lines = count_lines(impl_file)
        total_impl_lines += lines

        # Generate config
        config_file, component_name = generate_cosmic_ray_config(
            impl_file, test_files, output_dir
        )
        configs_generated.append(
            {
                "component": component_name,
                "impl_file": impl_file,
                "lines": lines,
                "test_count": len(test_files),
                "config_file": config_file,
            }
        )

        print(f"✓ {impl_file} ({lines} LOC)")
        print(f"  Tests: {len(test_files)} file(s)")
        for test in test_files[:3]:  # Show first 3 tests
            print(f"    - {test}")
        if len(test_files) > 3:
            print(f"    ... and {len(test_files) - 3} more")
        print(f"  Config: {os.path.basename(config_file)}")
        print()

    # Summary
    print(f"{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}\n")
    print(f"Implementation files: {len(impl_files)}")
    print(f"Configs generated: {len(configs_generated)}")
    print(f"Total implementation lines: {total_impl_lines}")
    print(
        f"Expected mutants: ~{total_impl_lines * 5}-{total_impl_lines * 10} (at 5-10 per 100 LOC)"
    )
    print()

    if configs_generated:
        print("Generated configs:")
        for config in configs_generated:
            print(f"  - {os.path.basename(config['config_file'])}")
        print()

        print("Next steps:")
        print()
        print("  1. Initialize mutation sessions:")
        for config in configs_generated:
            config_path = config["config_file"]
            session_name = config["component"]
            print(
                f"     .venv-mutation/bin/cosmic-ray init {config_path} {output_dir}{session_name}-session.sqlite"
            )
        print()

        print("  2. Execute mutation testing (run in parallel for speed):")
        for config in configs_generated:
            config_path = config["config_file"]
            session_name = config["component"]
            print(
                f"     .venv-mutation/bin/cosmic-ray exec {config_path} {output_dir}{session_name}-session.sqlite &"
            )
        print()

        print("  3. Generate reports:")
        for config in configs_generated:
            session_name = config["component"]
            print(
                f"     .venv-mutation/bin/cr-report {output_dir}{session_name}-session.sqlite"
            )
        print()
    else:
        print("❌ No configs generated (no test files found)")
        sys.exit(1)


if __name__ == "__main__":
    main()
