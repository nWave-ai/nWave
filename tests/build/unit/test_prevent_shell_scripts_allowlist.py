"""Regression tests for the install.sh allowlist in prevent_shell_scripts.py.

The zero-shell-scripts guard was given a narrow exception so the curl-able
bootstrap `scripts/install/install.sh` can be committed. These tests pin both
halves of the contract so a future refactor of the hook can't silently break
it: the sanctioned path is allowed AND every other shell script is still
blocked.
"""

from scripts.hooks.prevent_shell_scripts import ALLOWLIST, check_for_shell_scripts


def test_install_sh_is_in_the_allowlist():
    assert "scripts/install/install.sh" in ALLOWLIST


def test_allowlisted_script_is_not_blocked():
    assert check_for_shell_scripts(["scripts/install/install.sh"]) == []


def test_other_shell_script_is_still_blocked():
    prohibited = check_for_shell_scripts(["scripts/rogue.sh"])
    assert [path for path, _ in prohibited] == ["scripts/rogue.sh"]


def test_allowlist_matches_exact_path_only():
    # A sibling .sh in the same directory is NOT exempt — only the exact path.
    prohibited = check_for_shell_scripts(["scripts/install/other.sh"])
    assert [path for path, _ in prohibited] == ["scripts/install/other.sh"]


def test_mixed_batch_blocks_only_non_allowlisted():
    files = [
        "scripts/install/install.sh",  # allowed
        "scripts/rogue.sh",  # blocked
        "nwave_ai/cli.py",  # not a shell script
    ]
    prohibited = check_for_shell_scripts(files)
    assert [path for path, _ in prohibited] == ["scripts/rogue.sh"]


def test_other_prohibited_extensions_unaffected_by_allowlist():
    files = ["deploy.ps1", "run.bat", "build.bash"]
    prohibited = check_for_shell_scripts(files)
    assert {path for path, _ in prohibited} == set(files)
