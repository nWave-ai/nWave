"""Regression contract for the dependency-security toolchain.

The gate deliberately inspects source configuration.  It must remain runnable
without synchronising the project environment: that is the failure mode this
contract protects against.
"""

import importlib.util
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parents[2]


def _commit_validator_module():
    path = ROOT / "scripts/hooks/commit_msg.py"
    spec = importlib.util.spec_from_file_location("commit_msg_under_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_commit_validation_has_no_gitlint_dependency() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    pre_commit = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert '"gitlint' not in pyproject
    assert "jorisroovers/gitlint" not in pre_commit
    assert "pip install gitlint" not in workflow
    assert "scripts/hooks/commit_msg.py" in pre_commit
    assert "scripts/hooks/commit_msg.py" in workflow


def test_ci_audits_the_frozen_complete_dependency_graph() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "uv export --frozen --all-groups" in workflow
    assert "pip-audit==" in workflow
    assert "pip-audit -r" in workflow


def test_native_validator_accepts_current_commit() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/hooks/commit_msg.py"),
            "--commit",
            "HEAD",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_dependabot_exemption_applies_only_to_body_length() -> None:
    validator = _commit_validator_module()
    long_body = "x" * (validator.BODY_MAX_LINE_LENGTH + 1)

    assert not validator.validate_commit_text(
        "chore(deps): Bump dependency",
        author_name="dependabot[bot]",
    )
    assert validator.validate_commit_text(
        f"chore(deps): bump dependency\n\n{long_body}",
        author_name="dependabot[bot]",
    )


def test_native_validator_preserves_gitlint_generated_commit_exemptions() -> None:
    validator = _commit_validator_module()

    assert validator.validate_commit_text(
        "Merge pull request #71 from nWave-ai/fix/example",
        is_merge_commit=True,
    )

    for message in (
        'Revert "feat: add example"',
        "fixup! feat: add example",
        "amend! feat: add example",
        "squash! feat: add example",
    ):
        assert validator.validate_commit_text(message), message

    for human_message in (
        "Merge changes manually",
        "Revert changes manually",
        "fixup changes manually",
        "amend changes manually",
        "squash changes manually",
    ):
        assert not validator.validate_commit_text(human_message), human_message


def test_native_validator_preserves_gitlint_title_policy() -> None:
    validator = _commit_validator_module()

    for message in (
        "fix(ci,installer): preserve compound scope",
        "fix(mode/trailer gates): preserve slash and space scope",
        "docs(loops+piles): preserve plus scope",
    ):
        assert validator.validate_commit_text(message), message

    for message in (
        "fix: 123 is not an alphabetic subject",
        "fix: _symbol is not an alphabetic subject",
    ):
        assert not validator.validate_commit_text(message), message


def test_native_validator_ignores_git_comments_and_scissors_content() -> None:
    validator = _commit_validator_module()
    long_line = "x" * (validator.BODY_MAX_LINE_LENGTH + 1)
    with_comment = f"fix: valid subject\n\n# {long_line}"
    below_scissors = f"fix: valid subject\n\n# {validator.SCISSORS_MARKER}\n{long_line}"

    assert validator.validate_commit_text(
        validator.cleanup_commit_message(with_comment)
    )
    assert validator.validate_commit_text(
        validator.cleanup_commit_message(below_scissors)
    )
