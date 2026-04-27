"""Lock the OpenCode step-definition attribute-aliasing contract.

The skill-restructuring acceptance steps use module-level pytest attributes
(`pytest.opencode_target` and `pytest.opencode_install_dir`) to share state
between @given/@when steps and @then steps within a scenario. Historically
these two names diverged: the @given path set `opencode_target` while the
@then path read `opencode_install_dir`, so any scenario using the @given +
@then combination relied on a sibling @when scenario having run first on the
SAME xdist worker to leave `opencode_install_dir` populated.

Under `pytest -n auto --dist=loadgroup`, scenarios distribute across workers
and that cross-scenario coupling silently breaks: a worker may run the
@given+@then scenario in isolation, hit `pytest.opencode_install_dir` and
raise `AttributeError: module 'pytest' has no attribute 'opencode_install_dir'`.

This regression test enforces the alias contract: every step that establishes
the OpenCode install-directory state MUST set BOTH `pytest.opencode_target`
AND `pytest.opencode_install_dir` to the same Path. Long-term fix is to
replace `pytest.X` module-level state with proper fixture scoping (tracked
as test-infrastructure backlog).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_distribution_steps_module():
    """Load distribution_steps.py without going through the package import.

    The acceptance test directory name contains a hyphen
    (`skill-restructuring`) which is not a valid Python package, and the
    sibling conftest re-loads the steps via importlib. We do the same here so
    we can test the step functions in isolation.
    """
    repo_root = Path(__file__).resolve().parents[3]
    step_file = (
        repo_root
        / "tests"
        / "installer"
        / "acceptance"
        / "skill-restructuring"
        / "steps"
        / "distribution_steps.py"
    )
    spec = importlib.util.spec_from_file_location(
        "_test_distribution_steps_under_test", str(step_file)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def reset_pytest_opencode_attrs():
    """Strip pytest module-level OpenCode attrs before AND after each test.

    Prevents leakage from prior tests in the session and from this test into
    subsequent tests on the same worker.
    """
    for attr in ("opencode_target", "opencode_install_dir"):
        if hasattr(pytest, attr):
            delattr(pytest, attr)
    yield
    for attr in ("opencode_target", "opencode_install_dir"):
        if hasattr(pytest, attr):
            delattr(pytest, attr)


def _populate_source(source_dir: Path) -> None:
    """Create a minimal nw-prefixed skill in the source dir."""
    skill = source_dir / "nw-example-skill"
    skill.mkdir(parents=True, exist_ok=True)
    (skill / "SKILL.md").write_text(
        "---\nname: example-skill\ndescription: x\n---\n\n# Body\n",
        encoding="utf-8",
    )


def test_given_opencode_install_complete_sets_both_attribute_aliases(
    tmp_path: Path, reset_pytest_opencode_attrs
):
    """The @given step MUST set both `opencode_target` and `opencode_install_dir`.

    Locks the contract that prevents the xdist parallel-safety regression
    described in the module docstring.
    """
    module = _load_distribution_steps_module()
    source_dir = tmp_path / "nWave" / "skills"
    source_dir.mkdir(parents=True)
    _populate_source(source_dir)

    # Invoke the @given step body. Pytest-BDD wraps it; we call the underlying
    # function directly. The third positional arg is `populate_troubleshooter_skills`
    # which is a fixture used only as a setup hook — pass None.
    module.opencode_install_complete(source_dir, tmp_path, None)

    assert hasattr(pytest, "opencode_target"), (
        "@given step did not set pytest.opencode_target"
    )
    assert hasattr(pytest, "opencode_install_dir"), (
        "@given step must also set pytest.opencode_install_dir as alias for "
        "@then steps that read this canonical name (xdist parallel safety)"
    )
    assert pytest.opencode_target == pytest.opencode_install_dir, (
        "Both attributes must point to the same target directory"
    )


def test_when_opencode_plugin_installs_sets_both_attribute_aliases(
    tmp_path: Path, reset_pytest_opencode_attrs
):
    """The @when step MUST set both attributes too, symmetric with @given."""
    module = _load_distribution_steps_module()
    source_dir = tmp_path / "nWave" / "skills"
    source_dir.mkdir(parents=True)
    _populate_source(source_dir)

    module.opencode_plugin_installs(source_dir, tmp_path)

    assert hasattr(pytest, "opencode_install_dir"), (
        "@when step did not set pytest.opencode_install_dir"
    )
    assert hasattr(pytest, "opencode_target"), (
        "@when step must also set pytest.opencode_target as alias (xdist "
        "parallel safety)"
    )
    assert pytest.opencode_target == pytest.opencode_install_dir, (
        "Both attributes must point to the same target directory"
    )
