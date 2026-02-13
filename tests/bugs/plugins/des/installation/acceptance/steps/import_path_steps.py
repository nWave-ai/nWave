"""
Import Path Step Definitions for Bug 3: src.des Imports in Installed Module.

This module contains step definitions for testing:
- Bad import patterns ("from src.des" instead of "from des")
- Import success with only installed path in PYTHONPATH
- Hook execution without development PYTHONPATH
- Package structure validation

Domain: Import Path Validation
Bug: Installed DES uses "from des..." imports which only work with
     PYTHONPATH pointing to dev directory
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, then, when

from .helpers import scan_for_bad_imports


# -----------------------------------------------------------------------------
# Given Steps: Import Path Preconditions
# -----------------------------------------------------------------------------


@given(parsers.parse('PYTHONPATH contains only "{path}"'))
def pythonpath_contains_only(path: str, clean_env, test_context: dict):
    """
    Set PYTHONPATH to contain only the specified path.

    This simulates production environment where only installed location is in path.
    """
    expanded_path = str(Path(path).expanduser())
    clean_env["PYTHONPATH"] = expanded_path
    test_context["pythonpath"] = expanded_path
    test_context["restricted_pythonpath"] = True


@given("PYTHONPATH does NOT contain the development project root")
def pythonpath_no_dev_root(clean_env, project_root: Path, test_context: dict):
    """
    Ensure PYTHONPATH does not include the development project root.

    The project root is where src/ exists - if this is in PYTHONPATH,
    "from src.des" imports work even though they shouldn't.
    """
    current_path = clean_env.get("PYTHONPATH", "")
    project_root_str = str(project_root)

    # Remove project root from PYTHONPATH if present
    paths = [
        p for p in current_path.split(os.pathsep) if p and project_root_str not in p
    ]
    clean_env["PYTHONPATH"] = os.pathsep.join(paths) if paths else ""

    test_context["dev_root_excluded"] = True
    test_context["project_root_str"] = project_root_str


# -----------------------------------------------------------------------------
# When Steps: Import Path Actions
# -----------------------------------------------------------------------------


@when("I scan all Python files for import statements")
def scan_for_imports(test_context: dict):
    """
    Scan all Python files in installed DES for import statements.

    Looks for problematic "from src.des" or "import src.des" patterns.
    """
    des_path = test_context.get("installed_des_path")
    if not des_path:
        des_path = Path.home() / ".claude" / "lib" / "python" / "des"

    if not des_path.exists():
        pytest.skip(f"DES not installed at {des_path}")

    bad_imports = scan_for_bad_imports(des_path)
    test_context["bad_import_files"] = bad_imports


@when("I scan all Python files in the installed DES directory")
def scan_installed_des(test_context: dict):
    """Alias for scanning imports."""
    scan_for_imports(test_context)


@when(parsers.parse('I import "{import_statement}"'))
def try_import(import_statement: str, test_context: dict):
    """
    Attempt to import a module using only the restricted PYTHONPATH.

    BUG DETECTION: If import fails with ImportError mentioning 'src',
    the bug is present.
    """
    pythonpath = test_context.get("pythonpath", "")

    # Build Python command to test import
    # We use subprocess to ensure clean environment
    # Keep stdlib but remove development source paths
    python_code = f"""
import sys
# Remove development source paths but keep stdlib
sys.path = [p for p in sys.path if '/mnt/c/Repositories' not in p and '/src' not in p]
# Add installed DES path at the beginning
sys.path.insert(0, '{pythonpath}')
{import_statement}
print("IMPORT_SUCCESS")
"""

    result = subprocess.run(
        [sys.executable, "-c", python_code],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": pythonpath},
    )

    test_context["import_stdout"] = result.stdout
    test_context["import_stderr"] = result.stderr
    test_context["import_returncode"] = result.returncode
    test_context["import_success"] = "IMPORT_SUCCESS" in result.stdout


@when(parsers.parse("I import the following DES modules:"))
def try_import_modules(datatable, test_context: dict):
    """
    Attempt to import multiple DES modules in a single subprocess.

    Uses datatable with 'module_path' column.
    Batches all imports into one process to avoid per-module startup cost.
    """
    pythonpath = test_context.get("pythonpath", "")

    # Skip header row if present
    rows = datatable[1:] if datatable and datatable[0] == ["module_path"] else datatable

    modules = [row[0] if isinstance(row, list) else row["module_path"] for row in rows]

    # Build a single script that tests all imports
    import_tests = "\n".join(
        f"""try:
    from {mod} import *
    print("SUCCESS:{mod}")
except ImportError as e:
    print(f"FAILED:{mod}:{{e}}")"""
        for mod in modules
    )

    python_code = f"""
import sys
sys.path = [p for p in sys.path if '/mnt/c/Repositories' not in p and '/src' not in p]
sys.path.insert(0, '{pythonpath}')
{import_tests}
"""

    result = subprocess.run(
        [sys.executable, "-c", python_code],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": pythonpath},
    )

    # Parse per-module results from batched output
    stdout = result.stdout
    import_results = [
        {
            "module": mod,
            "success": f"SUCCESS:{mod}" in stdout,
            "stdout": stdout,
            "stderr": result.stderr,
        }
        for mod in modules
    ]

    test_context["module_import_results"] = import_results


@when("I execute the DES pre-task hook command")
def execute_hook_command(test_context: dict):
    """
    Execute the DES pre-task hook with restricted PYTHONPATH.

    BUG DETECTION: If hook fails with ImportError, the bug is present.
    """
    pythonpath = test_context.get("pythonpath", "")

    # Simulate hook invocation
    cmd = [
        sys.executable,
        "-m",
        "des.adapters.drivers.hooks.claude_code_hook_adapter",
        "pre-task",
    ]

    # Provide minimal valid input to stdin
    import json

    hook_input = json.dumps({"tool_input": {"prompt": "test prompt"}})

    result = subprocess.run(
        cmd,
        input=hook_input,
        capture_output=True,
        text=True,
        env={"PYTHONPATH": pythonpath},
    )

    test_context["hook_stdout"] = result.stdout
    test_context["hook_stderr"] = result.stderr
    test_context["hook_returncode"] = result.returncode


@when(parsers.parse('I run "{command}" without arguments'))
def run_command_no_args(command: str, test_context: dict):
    """
    Run a command without arguments.

    Used for testing that hook adapter gives usage error, not ImportError.
    """
    pythonpath = test_context.get("pythonpath", "")

    # Parse the command
    parts = command.split()
    if parts[0] == "python3":
        parts[0] = sys.executable

    result = subprocess.run(
        parts,
        capture_output=True,
        text=True,
        env={"PYTHONPATH": pythonpath},
    )

    test_context["command_stdout"] = result.stdout
    test_context["command_stderr"] = result.stderr
    test_context["command_returncode"] = result.returncode


@when("I analyze import statements across all DES files")
def analyze_all_imports(test_context: dict):
    """
    Comprehensive analysis of import patterns across all DES files.
    """
    des_path = test_context.get("installed_des_path")
    if not des_path:
        des_path = Path.home() / ".claude" / "lib" / "python" / "des"

    if not des_path.exists():
        pytest.skip(f"DES not installed at {des_path}")

    analysis = {
        "src_des_imports": [],
        "des_imports": [],
        "mixed_files": [],
    }

    for py_file in des_path.rglob("*.py"):
        try:
            content = py_file.read_text()
            has_src_des = "from src.des" in content or "import src.des" in content
            has_des = "from des." in content or "import des." in content

            if has_src_des:
                analysis["src_des_imports"].append(str(py_file))
            if has_des and not has_src_des:
                analysis["des_imports"].append(str(py_file))
            if has_src_des and has_des:
                analysis["mixed_files"].append(str(py_file))
        except Exception:
            pass

    test_context["import_analysis"] = analysis


# -----------------------------------------------------------------------------
# Then Steps: Import Path Assertions
# -----------------------------------------------------------------------------


@then(parsers.parse('no files should contain "{pattern}"'))
def verify_no_pattern(pattern: str, test_context: dict):
    """
    Verify no files contain the specified pattern.

    BUG DETECTION: If files contain "from src.des", the bug is present.
    """
    bad_files = test_context.get("bad_import_files", [])

    if pattern == "from src.des":
        matching_files = [f for f in bad_files if "from src.des" in Path(f).read_text()]
    elif pattern == "import src.des":
        # Rescan specifically for this pattern
        des_path = test_context.get("installed_des_path")
        if not des_path:
            des_path = Path.home() / ".claude" / "lib" / "python" / "des"

        matching_files = []
        for py_file in des_path.rglob("*.py"):
            try:
                if "import src.des" in py_file.read_text():
                    matching_files.append(str(py_file))
            except Exception:
                pass
    else:
        matching_files = bad_files

    assert len(matching_files) == 0, (
        f"BUG DETECTED: Found '{pattern}' in installed DES files.\n"
        f"Files with bad imports:\n"
        f"{chr(10).join(matching_files)}\n"
        f"The import path bug is present - installed DES uses development paths."
    )


@then("the import should succeed without ImportError")
def verify_import_success(test_context: dict):
    """
    Verify the import succeeded.

    BUG DETECTION: If import failed, the bug is present.
    """
    success = test_context.get("import_success", False)
    stderr = test_context.get("import_stderr", "")
    stdout = test_context.get("import_stdout", "")

    if not success:
        pytest.fail(
            f"BUG DETECTED: Import failed with restricted PYTHONPATH.\n"
            f"This indicates installed DES uses 'from src.des' imports.\n"
            f"Stdout: {stdout}\n"
            f"Stderr: {stderr}"
        )


@then("all imports should succeed without ImportError")
def verify_all_imports_success(test_context: dict):
    """
    Verify all module imports succeeded.
    """
    results = test_context.get("module_import_results", [])
    failed = [r for r in results if not r["success"]]

    if failed:
        failure_details = "\n".join(
            [f"  - {r['module']}: {r['stderr']}" for r in failed]
        )
        pytest.fail(
            f"BUG DETECTED: {len(failed)} module import(s) failed.\n"
            f"Failed modules:\n{failure_details}\n"
            f"This indicates installed DES uses 'from src.des' imports."
        )


@then("the hook should execute without ImportError")
def verify_hook_no_import_error(test_context: dict):
    """
    Verify hook executed without ImportError.
    """
    stderr = test_context.get("hook_stderr", "")

    # ImportError would be in stderr
    if "ImportError" in stderr or "ModuleNotFoundError" in stderr:
        pytest.fail(
            f"BUG DETECTED: Hook failed with ImportError.\n"
            f"This indicates installed DES uses 'from src.des' imports.\n"
            f"Stderr: {stderr}"
        )


@then("the hook should return a valid response")
def verify_hook_valid_response(test_context: dict):
    """
    Verify hook returned valid JSON response.
    """
    import json

    stdout = test_context.get("hook_stdout", "")

    try:
        response = json.loads(stdout)
        # Hook should return either decision or status
        assert "decision" in response or "status" in response, (
            f"Hook response missing expected fields: {response}"
        )
    except json.JSONDecodeError:
        # If it's not JSON, check if it was an error we expected
        stderr = test_context.get("hook_stderr", "")
        if "ImportError" in stderr:
            pytest.fail(
                f"BUG DETECTED: Hook failed with ImportError.\nStderr: {stderr}"
            )


@then("the command should fail with usage error (missing command)")
def verify_usage_error(test_context: dict):
    """
    Verify command failed with usage error, not ImportError.
    """
    stderr = test_context.get("command_stderr", "")
    returncode = test_context.get("command_returncode", 0)

    # Should fail because missing command argument
    assert returncode != 0, "Command should fail without arguments"

    # But not because of ImportError
    if "ImportError" in stderr or "ModuleNotFoundError" in stderr:
        pytest.fail(
            f"BUG DETECTED: Command failed with ImportError instead of usage error.\n"
            f"Stderr: {stderr}"
        )


@then("the error should NOT be ImportError")
def verify_not_import_error(test_context: dict):
    """
    Verify the error is not an ImportError.
    """
    stderr = test_context.get("command_stderr", "")

    assert "ImportError" not in stderr, (
        f"BUG DETECTED: Got ImportError when expecting usage error.\nStderr: {stderr}"
    )
    assert "ModuleNotFoundError" not in stderr, (
        f"BUG DETECTED: Got ModuleNotFoundError when expecting usage error.\n"
        f"Stderr: {stderr}"
    )


@then(parsers.parse('I should find {count:d} occurrences of "{pattern}"'))
def verify_pattern_count(count: int, pattern: str, test_context: dict):
    """
    Verify specific count of pattern occurrences.
    """
    des_path = test_context.get("installed_des_path")
    if not des_path:
        des_path = Path.home() / ".claude" / "lib" / "python" / "des"

    total_occurrences = 0
    for py_file in des_path.rglob("*.py"):
        try:
            content = py_file.read_text()
            total_occurrences += content.count(pattern)
        except Exception:
            pass

    if count == 0:
        assert total_occurrences == 0, (
            f"BUG DETECTED: Found {total_occurrences} occurrences of '{pattern}'. "
            f"Expected 0."
        )
    else:
        assert total_occurrences == count, (
            f"Expected {count} occurrences of '{pattern}', found {total_occurrences}"
        )


@then(
    parsers.parse(
        'I should find {count:d} occurrences of "{pattern}" as a string literal'
    )
)
def verify_pattern_count_literal(count: int, pattern: str, test_context: dict):
    """
    Verify specific count of pattern occurrences (alias for string literal checks).
    """
    verify_pattern_count(count, pattern, test_context)


@then(parsers.parse('all imports should use "{prefix}" or "{alt_prefix}" patterns'))
def verify_correct_import_patterns(prefix: str, alt_prefix: str, test_context: dict):
    """
    Verify all imports use correct patterns.
    """
    analysis = test_context.get("import_analysis", {})
    src_des_files = analysis.get("src_des_imports", [])

    assert len(src_des_files) == 0, (
        f"BUG DETECTED: {len(src_des_files)} files use 'src.des' imports:\n"
        f"{chr(10).join(src_des_files)}"
    )


@then('no mixed "src.des" and "des" prefixes should exist in the same file')
def verify_no_mixed_imports(test_context: dict):
    """
    Verify no file mixes import styles.
    """
    analysis = test_context.get("import_analysis", {})
    mixed_files = analysis.get("mixed_files", [])

    assert len(mixed_files) == 0, (
        f"Found {len(mixed_files)} files with mixed import styles:\n"
        f"{chr(10).join(mixed_files)}"
    )


@then(parsers.parse('all internal imports should use consistent "{prefix}" prefix'))
def verify_consistent_prefix(prefix: str, test_context: dict):
    """
    Verify all internal imports use consistent prefix (e.g., "from des.").
    """
    analysis = test_context.get("import_analysis", {})
    src_des_files = analysis.get("src_des_imports", [])

    assert len(src_des_files) == 0, (
        f"BUG DETECTED: {len(src_des_files)} files don't use consistent '{prefix}' prefix:\n"
        f"{chr(10).join(src_des_files)}"
    )


@then("the following __init__.py files should exist:")
def verify_init_files(datatable, test_context: dict):
    """
    Verify __init__.py files exist at specified paths.
    """
    des_base = test_context.get("installed_des_path")
    if not des_base:
        des_base = Path.home() / ".claude" / "lib" / "python"

    # Skip header row if present
    rows = datatable[1:] if datatable and datatable[0] == ["path"] else datatable

    missing = []
    for row in rows:
        path = row[0] if isinstance(row, list) else row["path"]
        full_path = des_base.parent / path  # path includes "des/"

        if not full_path.exists():
            missing.append(path)

    assert len(missing) == 0, f"Missing __init__.py files:\n{chr(10).join(missing)}"
