"""Regression tests for _PLUGIN_DISCOVERY_SCRIPT HOME env hardening.

Bug: When $HOME is set to empty string, Path.home() returns '/' instead of
the actual home directory. The discovery script must detect this and fall
back to pwd.getpwuid(os.getuid()).pw_dir.

See: docs/analysis/rca-plugin-hooks-no-home-env.md
"""

from __future__ import annotations

import os
import pwd
import subprocess
import sys


def _extract_home_resolution_code() -> str:
    """Extract the HOME-resolution logic from _PLUGIN_DISCOVERY_SCRIPT.

    Parses the semicolon-delimited one-liner to find the statements that
    resolve the home directory variable 'h', then returns them as
    standalone Python code that prints the resolved value.

    Raises ValueError if no 'h=' statements are found (meaning the
    hardening has not been applied yet).
    """
    from scripts.build_plugin import _PLUGIN_DISCOVERY_SCRIPT

    statements = [s.strip() for s in _PLUGIN_DISCOVERY_SCRIPT.split(";") if s.strip()]

    # Collect: HOME-resolution-relevant imports + all 'h=' assignments.
    # Allow-list: only stdlib modules used by the HOME logic (os, sys, pwd, pathlib).
    # Broader 'startswith("import ", "from ")' would sweep in unrelated runtime
    # imports (e.g. `from des.adapters...`) that don't exist in test subprocess,
    # causing ModuleNotFoundError before HOME logic runs.
    allowed_import_prefixes = (
        "import os",
        "import sys",
        "import pwd",
        "from pathlib",
        "from os",
        "from sys",
        "from pwd",
    )
    code_lines: list[str] = []
    for stmt in statements:
        if stmt.startswith(allowed_import_prefixes) or stmt.startswith("h="):
            code_lines.append(stmt)

    # If no 'h=' lines found, the hardening hasn't been applied
    has_h_var = any(line.startswith("h=") for line in code_lines)
    if not has_h_var:
        raise ValueError(
            "_PLUGIN_DISCOVERY_SCRIPT does not contain 'h=' variable. "
            "HOME hardening has not been applied."
        )

    code_lines.append("print(h)")
    return "\n".join(code_lines)


def _run_home_resolution(env_override: dict[str, str | None] | None = None) -> str:
    """Run the HOME-resolution logic from _PLUGIN_DISCOVERY_SCRIPT in a subprocess.

    Returns the resolved home directory path.
    """
    script = _extract_home_resolution_code()

    env = os.environ.copy()
    if env_override is not None:
        for k, v in env_override.items():
            if v is None:
                env.pop(k, None)
            else:
                env[k] = v

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Subprocess failed (rc={result.returncode}): {result.stderr}"
        )
    return result.stdout.strip()


class TestDiscoveryScriptHomeHardening:
    """Tests for HOME environment variable hardening in _PLUGIN_DISCOVERY_SCRIPT."""

    def test_plugin_discovery_script_contains_home_validation(self) -> None:
        """The _PLUGIN_DISCOVERY_SCRIPT string must contain HOME hardening code.

        Structural check: the script must import pwd and use getpwuid
        as a fallback, not rely solely on Path.home().
        """
        from scripts.build_plugin import _PLUGIN_DISCOVERY_SCRIPT

        assert "pwd" in _PLUGIN_DISCOVERY_SCRIPT, (
            "_PLUGIN_DISCOVERY_SCRIPT must import pwd module for getpwuid fallback"
        )
        assert "getpwuid" in _PLUGIN_DISCOVERY_SCRIPT, (
            "_PLUGIN_DISCOVERY_SCRIPT must use getpwuid as HOME fallback"
        )
        assert "Path.home()" not in _PLUGIN_DISCOVERY_SCRIPT, (
            "_PLUGIN_DISCOVERY_SCRIPT must not use Path.home() directly -- "
            "it returns '/' when HOME=''"
        )

    def test_discovery_script_with_home_empty_string(self) -> None:
        """When HOME='', the script must NOT resolve home to '/'.

        This is the core regression: Path.home() returns '/' when HOME='',
        causing glob to search from filesystem root.
        """
        resolved = _run_home_resolution({"HOME": ""})
        assert resolved != "/", (
            "Discovery script resolved home to '/' when HOME=''. "
            "Must fall back to pwd.getpwuid()."
        )
        assert len(resolved) > 1, f"Home path suspiciously short: {resolved!r}"

    def test_discovery_script_with_home_unset(self) -> None:
        """When HOME is unset, the script should use pwd.getpwuid() fallback."""
        expected = pwd.getpwuid(os.getuid()).pw_dir
        resolved = _run_home_resolution({"HOME": None})
        assert resolved == expected, (
            f"Expected {expected!r} from pwd.getpwuid(), got {resolved!r}"
        )

    def test_discovery_script_with_home_valid(self) -> None:
        """When HOME is a valid path, the script should use it directly."""
        real_home = os.environ.get("HOME", pwd.getpwuid(os.getuid()).pw_dir)
        resolved = _run_home_resolution({"HOME": real_home})
        assert resolved == real_home, f"Expected {real_home!r}, got {resolved!r}"

    def test_discovery_script_rejects_root_as_home(self) -> None:
        """If HOME resolves to '/', the script must reject it and try fallback.

        Even if HOME='/' explicitly, this is almost certainly wrong for a
        regular user and the script should use pwd.getpwuid() instead.
        """
        resolved = _run_home_resolution({"HOME": "/"})
        assert resolved != "/", (
            "Discovery script accepted '/' as home directory. "
            "Must fall back to pwd.getpwuid()."
        )
