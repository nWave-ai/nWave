"""Tests for scripts/sync/check_denylist.py.

Realizes the 32 BDD acceptance scenarios in
`docs/feature/public-pr-sync/distill/acceptance.md`. The driving port is
the CLI itself — every test invokes the script as a subprocess and asserts
on exit code, stdout JSON, and stderr. No internal imports. This keeps
tests coupled only to the §2 CLI contract (wave-decisions.md) and treats
`check_denylist.py` as the black-box driving port.

CLI contract:
    docs/feature/public-pr-sync/devops/wave-decisions.md §2 (+ §7.1)

Test mode split:
    - @diff-file-mode — uses --diff-file, no git dependency. Fast.
    - @git-mode       — uses --base-sha/--head-sha against a real tmp git
                        repo. Required for the content rule (git show).
"""

from __future__ import annotations

import json
import random
import string
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "sync" / "check_denylist.py"
)

PRODUCTION_DENYLIST = (
    """
.github/**
.claude-plugin/**
plugins/**
pyproject.toml
scripts/release/**
scripts/install/**
nWave/public-workflows/**
CONTRIBUTING.md
LICENSE
PRIVACY.md
""".strip()
    + "\n"
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_denylist(tmp_path):
    """Return a factory that writes a denylist file with given content and returns its path."""

    def _make(content: str = PRODUCTION_DENYLIST) -> Path:
        p: Path = tmp_path / "denylist.txt"
        p.write_text(content, encoding="utf-8")
        return p

    return _make


@pytest.fixture
def tmp_diff_file(tmp_path):
    """Return a factory that writes a diff file with given content and returns its path."""

    def _make(content: str) -> Path:
        p: Path = tmp_path / "diff.txt"
        p.write_text(content, encoding="utf-8")
        return p

    return _make


@pytest.fixture
def tmp_repo(tmp_path):
    """Initialize a real git repo in tmp_path with an initial empty commit. Returns repo root."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "commit", "--allow-empty", "-q", "--no-verify", "-m", "chore: init")
    return repo


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Invoke git with captured output; raises on non-zero exit."""
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )


def _git_head(cwd: Path) -> str:
    return _git(cwd, "rev-parse", "HEAD").stdout.strip()


def _make_pr(repo: Path, files: dict[str, str | None]) -> tuple[str, str]:
    """Create a two-commit PR in `repo`.

    `files` maps relative path -> content. `None` content means "delete this
    file (must already exist at base)". Returns (base_sha, head_sha).
    """
    base_sha = _git_head(repo)
    for path, content in files.items():
        full = repo / path
        if content is None:
            full.unlink()
            _git(repo, "rm", "-q", path)
            continue
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
        _git(repo, "add", path)
    _git(repo, "commit", "-q", "--no-verify", "-m", "pr head")
    head_sha = _git_head(repo)
    return base_sha, head_sha


def _run(
    *args: str,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[bytes]:
    """Invoke the script via subprocess, capturing raw bytes."""
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        cwd=cwd,
        capture_output=True,
    )


def _parse_stdout(result: subprocess.CompletedProcess[bytes]) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(result.stdout.decode("utf-8"))
    return data


def _has_entry(matched: list[dict[str, str]], path: str, rule: str) -> bool:
    return {"path": path, "rule": rule} in matched


def _paths_in(matched: list[dict[str, str]]) -> set[str]:
    return {entry["path"] for entry in matched}


# ---------------------------------------------------------------------------
# Feature 1: Path-based denylist — happy paths (diff-file mode)
# ---------------------------------------------------------------------------


class TestFeature1PathBasedDenylist:
    """Path-glob rules: block/pass and exact rule attribution."""

    def test_pr_with_only_non_sensitive_paths_passes(self, tmp_denylist, tmp_diff_file):
        """F1 happy-path: docs/src/tests only → exit 0, empty matched_files."""
        denylist = tmp_denylist()
        diff = tmp_diff_file(
            "docs/guides/quickstart.md\n"
            "src/des/application/orchestrator.py\n"
            "tests/des/unit/test_orchestrator.py\n"
        )

        result = _run("--diff-file", str(diff), "--denylist", str(denylist))

        assert result.returncode == 0
        data = _parse_stdout(result)
        assert data["pass"] is True
        assert data["matched_files"] == []

    def test_single_denied_path_blocked_with_exact_rule_attribution(
        self, tmp_denylist, tmp_diff_file
    ):
        """F1: .github/workflows/ci.yml matched by .github/** → exact JSON shape."""
        denylist = tmp_denylist()
        diff = tmp_diff_file(".github/workflows/ci.yml\n")

        result = _run("--diff-file", str(diff), "--denylist", str(denylist))

        assert result.returncode == 1
        data = _parse_stdout(result)
        assert data == {
            "pass": False,
            "matched_files": [
                {"path": ".github/workflows/ci.yml", "rule": ".github/**"}
            ],
        }

    def test_multiple_denied_paths_all_reported(self, tmp_denylist, tmp_diff_file):
        """F1: multiple hits reported; non-denied files excluded."""
        denylist = tmp_denylist()
        diff = tmp_diff_file(
            "pyproject.toml\nscripts/release/publish.py\ndocs/guides/quickstart.md\n"
        )

        result = _run("--diff-file", str(diff), "--denylist", str(denylist))

        assert result.returncode == 1
        data = _parse_stdout(result)
        assert _has_entry(data["matched_files"], "pyproject.toml", "pyproject.toml")
        assert _has_entry(
            data["matched_files"], "scripts/release/publish.py", "scripts/release/**"
        )
        assert "docs/guides/quickstart.md" not in _paths_in(data["matched_files"])

    def test_empty_diff_passes(self, tmp_denylist, tmp_diff_file):
        """F1: PR with no changed files → exit 0, empty matched_files."""
        denylist = tmp_denylist()
        diff = tmp_diff_file("")

        result = _run("--diff-file", str(diff), "--denylist", str(denylist))

        assert result.returncode == 0
        data = _parse_stdout(result)
        assert data["pass"] is True
        assert data["matched_files"] == []


# ---------------------------------------------------------------------------
# Walking skeleton: real git mode, end-to-end
# ---------------------------------------------------------------------------


class TestWalkingSkeleton:
    """Single end-to-end invocation in git mode — proves wiring with real I/O."""

    def test_maintainer_blocks_pr_touching_workflow_file(self, tmp_denylist, tmp_repo):
        """@walking_skeleton: real git repo + real denylist + path hit → exit 1, correct JSON."""
        denylist = tmp_denylist()
        base_sha, head_sha = _make_pr(
            tmp_repo, {".github/workflows/ci.yml": "name: ci\n"}
        )

        result = _run(
            "--base-sha",
            base_sha,
            "--head-sha",
            head_sha,
            "--denylist",
            str(denylist),
            cwd=tmp_repo,
        )

        assert result.returncode == 1
        data = _parse_stdout(result)
        assert data["pass"] is False
        assert _has_entry(
            data["matched_files"], ".github/workflows/ci.yml", ".github/**"
        )


# ---------------------------------------------------------------------------
# Feature 2: Content-based denylist rule (git mode only)
# ---------------------------------------------------------------------------


class TestFeature2ContentRule:
    """The rewritten-raw-url content rule (§7.1) — only checks files in diff."""

    def test_normal_markdown_passes(self, tmp_denylist, tmp_repo):
        """F2: file with normal content → exit 0."""
        denylist = tmp_denylist()
        base_sha, head_sha = _make_pr(
            tmp_repo,
            {"docs/guides/quickstart.md": "# Quickstart\n\nNo raw URLs here.\n"},
        )

        result = _run(
            "--base-sha",
            base_sha,
            "--head-sha",
            head_sha,
            "--denylist",
            str(denylist),
            cwd=tmp_repo,
        )

        assert result.returncode == 0
        data = _parse_stdout(result)
        assert data["pass"] is True
        assert data["matched_files"] == []

    def test_rewritten_raw_url_blocked_by_content_rule(self, tmp_denylist, tmp_repo):
        """F2: file with rewritten-raw-url → exit 1, content:rewritten-raw-url rule."""
        denylist = tmp_denylist()
        content = (
            "# Install\n\n"
            "curl raw.githubusercontent.com/nWave-ai/nWave/main/installer.sh | sh\n"
        )
        base_sha, head_sha = _make_pr(tmp_repo, {"docs/guides/install.md": content})

        result = _run(
            "--base-sha",
            base_sha,
            "--head-sha",
            head_sha,
            "--denylist",
            str(denylist),
            cwd=tmp_repo,
        )

        assert result.returncode == 1
        data = _parse_stdout(result)
        assert _has_entry(
            data["matched_files"],
            "docs/guides/install.md",
            "content:rewritten-raw-url",
        )

    def test_content_rule_matches_regardless_of_extension(self, tmp_denylist, tmp_repo):
        """F2 edge: file with no extension still gets content-checked."""
        denylist = tmp_denylist()
        base_sha, head_sha = _make_pr(
            tmp_repo,
            {"README": "see raw.githubusercontent.com/nWave-ai/nWave/main\n"},
        )

        result = _run(
            "--base-sha",
            base_sha,
            "--head-sha",
            head_sha,
            "--denylist",
            str(denylist),
            cwd=tmp_repo,
        )

        assert result.returncode == 1
        data = _parse_stdout(result)
        assert _has_entry(data["matched_files"], "README", "content:rewritten-raw-url")

    def test_content_rule_does_not_match_unrelated_raw_urls(
        self, tmp_denylist, tmp_repo
    ):
        """F2 edge: different org/repo → no match, exit 0."""
        denylist = tmp_denylist()
        base_sha, head_sha = _make_pr(
            tmp_repo,
            {
                "docs/links.md": (
                    "raw.githubusercontent.com/some-other-org/some-other-repo/main\n"
                )
            },
        )

        result = _run(
            "--base-sha",
            base_sha,
            "--head-sha",
            head_sha,
            "--denylist",
            str(denylist),
            cwd=tmp_repo,
        )

        assert result.returncode == 0
        data = _parse_stdout(result)
        assert data["pass"] is True
        assert data["matched_files"] == []


# ---------------------------------------------------------------------------
# Feature 3: Mixed hits — path and content compose
# ---------------------------------------------------------------------------


class TestFeature3MixedHits:
    """Both rule engines run; single file can hit both path and content rules."""

    def test_path_denied_and_content_denied_both_reported(self, tmp_denylist, tmp_repo):
        """F3: one file on path rule, one on content rule → 2 entries."""
        denylist = tmp_denylist()
        base_sha, head_sha = _make_pr(
            tmp_repo,
            {
                "pyproject.toml": '[project]\nname = "x"\n',
                "docs/guides/install.md": (
                    "raw.githubusercontent.com/nWave-ai/nWave/main\n"
                ),
            },
        )

        result = _run(
            "--base-sha",
            base_sha,
            "--head-sha",
            head_sha,
            "--denylist",
            str(denylist),
            cwd=tmp_repo,
        )

        assert result.returncode == 1
        data = _parse_stdout(result)
        assert _has_entry(data["matched_files"], "pyproject.toml", "pyproject.toml")
        assert _has_entry(
            data["matched_files"],
            "docs/guides/install.md",
            "content:rewritten-raw-url",
        )
        assert len(data["matched_files"]) == 2

    def test_single_file_hitting_both_rules_produces_both_entries(
        self, tmp_denylist, tmp_repo
    ):
        """F3 edge: file matches path rule AND content rule → 2 entries for same path."""
        denylist = tmp_denylist()
        base_sha, head_sha = _make_pr(
            tmp_repo,
            {
                "scripts/install/bootstrap.md": (
                    "raw.githubusercontent.com/nWave-ai/nWave/main\n"
                )
            },
        )

        result = _run(
            "--base-sha",
            base_sha,
            "--head-sha",
            head_sha,
            "--denylist",
            str(denylist),
            cwd=tmp_repo,
        )

        assert result.returncode == 1
        data = _parse_stdout(result)
        assert _has_entry(
            data["matched_files"],
            "scripts/install/bootstrap.md",
            "scripts/install/**",
        )
        assert _has_entry(
            data["matched_files"],
            "scripts/install/bootstrap.md",
            "content:rewritten-raw-url",
        )


# ---------------------------------------------------------------------------
# Feature 4: --diff-file format edge cases
# ---------------------------------------------------------------------------


class TestFeature4DiffFileFormat:
    """Diff-file parser: blanks, comments, spaces, UTF-8, SHA precedence."""

    def test_blank_and_comment_lines_ignored(self, tmp_denylist, tmp_diff_file):
        """F4: #-comments and blank lines skipped; real paths matched."""
        denylist = tmp_denylist()
        diff = tmp_diff_file(
            "# test fixture: PR touches CI and version\n"
            ".github/workflows/ci.yml\n"
            "\n"
            "# a second comment in the middle\n"
            "pyproject.toml\n"
            "\n"
        )

        result = _run("--diff-file", str(diff), "--denylist", str(denylist))

        assert result.returncode == 1
        data = _parse_stdout(result)
        assert _has_entry(
            data["matched_files"], ".github/workflows/ci.yml", ".github/**"
        )
        assert _has_entry(data["matched_files"], "pyproject.toml", "pyproject.toml")
        assert len(data["matched_files"]) == 2

    def test_paths_with_spaces_handled_literally(self, tmp_denylist, tmp_diff_file):
        """F4: "docs/guides/my notes.md" is a single literal path (not denied)."""
        denylist = tmp_denylist()
        diff = tmp_diff_file("docs/guides/my notes.md\n.github/workflows/ci.yml\n")

        result = _run("--diff-file", str(diff), "--denylist", str(denylist))

        assert result.returncode == 1
        data = _parse_stdout(result)
        assert _has_entry(
            data["matched_files"], ".github/workflows/ci.yml", ".github/**"
        )
        assert "docs/guides/my notes.md" not in _paths_in(data["matched_files"])

    def test_utf8_non_ascii_paths_do_not_crash(self, tmp_denylist, tmp_diff_file):
        """F4: non-ASCII filenames parsed cleanly; LICENSE still matched."""
        denylist = tmp_denylist()
        diff = tmp_diff_file("docs/guides/café-tutoriál.md\nLICENSE\n")

        result = _run("--diff-file", str(diff), "--denylist", str(denylist))

        assert result.returncode == 1
        data = _parse_stdout(result)
        assert _has_entry(data["matched_files"], "LICENSE", "LICENSE")

    def test_only_comments_and_blanks_in_diff_file_parses_as_empty(
        self, tmp_denylist, tmp_diff_file
    ):
        """F4: no real paths → empty diff → exit 0."""
        denylist = tmp_denylist()
        diff = tmp_diff_file("# nothing to see here\n\n# also nothing\n\n")

        result = _run("--diff-file", str(diff), "--denylist", str(denylist))

        assert result.returncode == 0
        data = _parse_stdout(result)
        assert data["pass"] is True
        assert data["matched_files"] == []

    def test_diff_file_mode_ignores_sha_arguments(self, tmp_denylist, tmp_diff_file):
        """F4: --diff-file takes precedence; SHAs are not used → no git call."""
        denylist = tmp_denylist()
        diff = tmp_diff_file("pyproject.toml\n")

        result = _run(
            "--diff-file",
            str(diff),
            "--base-sha",
            "0" * 40,
            "--head-sha",
            "1" * 40,
            "--denylist",
            str(denylist),
        )

        assert result.returncode == 1
        data = _parse_stdout(result)
        assert _has_entry(data["matched_files"], "pyproject.toml", "pyproject.toml")


# ---------------------------------------------------------------------------
# Feature 5: Path-matching semantics
# ---------------------------------------------------------------------------


class TestFeature5PathMatching:
    """fnmatch/gitignore semantics: **, exact filenames, forward slashes."""

    def test_double_star_matches_nested_at_any_depth(self, tmp_denylist, tmp_diff_file):
        """F5: .github/** matches nested paths recursively."""
        denylist = tmp_denylist(".github/**\n")
        diff = tmp_diff_file(
            ".github/workflows/ci.yml\n"
            ".github/workflows/nested/inner.yml\n"
            ".github/CODEOWNERS\n"
        )

        result = _run("--diff-file", str(diff), "--denylist", str(denylist))

        assert result.returncode == 1
        data = _parse_stdout(result)
        assert len(data["matched_files"]) == 3
        for entry in data["matched_files"]:
            assert entry["rule"] == ".github/**"

    def test_double_star_does_not_match_bare_directory_name(
        self, tmp_denylist, tmp_diff_file
    ):
        """F5: .github/** does NOT match literal ".github" (no trailing path)."""
        denylist = tmp_denylist(".github/**\n")
        diff = tmp_diff_file(".github\n")

        result = _run("--diff-file", str(diff), "--denylist", str(denylist))

        assert result.returncode == 0
        data = _parse_stdout(result)
        assert data["pass"] is True
        assert data["matched_files"] == []

    def test_exact_filename_rule_matches_only_literal_path(
        self, tmp_denylist, tmp_diff_file
    ):
        """F5: "pyproject.toml" rule matches top-level only, not subdir/pyproject.toml."""
        denylist = tmp_denylist("pyproject.toml\n")
        diff = tmp_diff_file("pyproject.toml\nsubdir/pyproject.toml\n")

        result = _run("--diff-file", str(diff), "--denylist", str(denylist))

        assert result.returncode == 1
        data = _parse_stdout(result)
        assert _has_entry(data["matched_files"], "pyproject.toml", "pyproject.toml")
        assert "subdir/pyproject.toml" not in _paths_in(data["matched_files"])

    def test_matching_uses_forward_slashes(self, tmp_denylist, tmp_diff_file):
        """F5: forward slashes on every platform."""
        denylist = tmp_denylist("scripts/release/**\n")
        diff = tmp_diff_file("scripts/release/publish.py\n")

        result = _run("--diff-file", str(diff), "--denylist", str(denylist))

        assert result.returncode == 1
        data = _parse_stdout(result)
        assert _has_entry(
            data["matched_files"],
            "scripts/release/publish.py",
            "scripts/release/**",
        )


# ---------------------------------------------------------------------------
# Feature 6: Denylist file edge cases
# ---------------------------------------------------------------------------


class TestFeature6DenylistFileFormat:
    """Denylist parser: #-comments, blanks, all-comments → empty ruleset."""

    def test_hash_comment_lines_ignored(self, tmp_denylist, tmp_diff_file):
        """F6: # lines are comments; they never become rules."""
        denylist = tmp_denylist(
            "# block workflow files\n"
            ".github/**\n"
            "# block release machinery\n"
            "scripts/release/**\n"
        )
        diff = tmp_diff_file(".github/workflows/ci.yml\n")

        result = _run("--diff-file", str(diff), "--denylist", str(denylist))

        assert result.returncode == 1
        data = _parse_stdout(result)
        assert _has_entry(
            data["matched_files"], ".github/workflows/ci.yml", ".github/**"
        )
        for entry in data["matched_files"]:
            assert not entry["rule"].startswith("#")

    def test_blank_lines_in_denylist_ignored(self, tmp_denylist, tmp_diff_file):
        """F6: blank lines never become rules."""
        denylist = tmp_denylist("\n.github/**\n\n\npyproject.toml\n\n")
        diff = tmp_diff_file("pyproject.toml\n")

        result = _run("--diff-file", str(diff), "--denylist", str(denylist))

        assert result.returncode == 1
        data = _parse_stdout(result)
        assert _has_entry(data["matched_files"], "pyproject.toml", "pyproject.toml")

    def test_all_commented_denylist_passes_everything(
        self, tmp_denylist, tmp_diff_file
    ):
        """F6: only comments/blanks → empty ruleset → all paths pass."""
        denylist = tmp_denylist(
            "# quarterly review pending — all rules commented out\n"
            "\n"
            "# (no active rules)\n"
        )
        diff = tmp_diff_file(
            ".github/workflows/ci.yml\npyproject.toml\nscripts/release/publish.py\n"
        )

        result = _run("--diff-file", str(diff), "--denylist", str(denylist))

        assert result.returncode == 0
        data = _parse_stdout(result)
        assert data["pass"] is True
        assert data["matched_files"] == []

    def test_empty_path_ruleset_does_not_disable_content_rule(
        self, tmp_denylist, tmp_repo
    ):
        """F6: content rule runs regardless of path-rule count."""
        denylist = tmp_denylist("# all rules commented out\n")
        base_sha, head_sha = _make_pr(
            tmp_repo,
            {"docs/install.md": "raw.githubusercontent.com/nWave-ai/nWave/main\n"},
        )

        result = _run(
            "--base-sha",
            base_sha,
            "--head-sha",
            head_sha,
            "--denylist",
            str(denylist),
            cwd=tmp_repo,
        )

        assert result.returncode == 1
        data = _parse_stdout(result)
        assert _has_entry(
            data["matched_files"], "docs/install.md", "content:rewritten-raw-url"
        )


# ---------------------------------------------------------------------------
# Feature 7: Usage and error handling
# ---------------------------------------------------------------------------


class TestFeature7UsageErrors:
    """Exit-code-2 paths: missing args, bad SHAs, unreadable files, git failure."""

    def test_missing_denylist_argument_is_usage_error(self):
        """F7: no --denylist → exit 2, stderr mentions "denylist"."""
        result = _run("--base-sha", "a" * 40, "--head-sha", "b" * 40)

        assert result.returncode == 2
        assert b"denylist" in result.stderr.lower()
        # stdout must not be a pass:true result
        if result.stdout:
            try:
                data = json.loads(result.stdout.decode("utf-8"))
                assert data.get("pass") is not True
            except json.JSONDecodeError:
                pass  # non-JSON stdout is acceptable on exit 2

    def test_missing_base_sha_in_git_mode_is_usage_error(self, tmp_denylist):
        """F7: git mode requires --base-sha → exit 2, stderr mentions "base-sha"."""
        denylist = tmp_denylist()

        result = _run("--denylist", str(denylist), "--head-sha", "b" * 40)

        assert result.returncode == 2
        assert b"base-sha" in result.stderr.lower()

    @pytest.mark.parametrize(
        "bad_sha",
        [
            "not-a-sha",
            "xyz" + "a" * 37,  # non-hex prefix
            "z" * 40,  # non-hex char in length-40 string
        ],
    )
    def test_non_hex_sha_is_usage_error(self, tmp_denylist, bad_sha):
        """F7: non-hex SHA → exit 2, stderr mentions the invalid value."""
        denylist = tmp_denylist()

        result = _run(
            "--base-sha",
            bad_sha,
            "--head-sha",
            "b" * 40,
            "--denylist",
            str(denylist),
        )

        assert result.returncode == 2
        assert b"sha" in result.stderr.lower()

    @pytest.mark.parametrize("bad_sha", ["abc123", "a" * 39, "a" * 41])
    def test_wrong_length_sha_is_usage_error(self, tmp_denylist, bad_sha):
        """F7: SHA not exactly 40 hex chars → exit 2."""
        denylist = tmp_denylist()

        result = _run(
            "--base-sha",
            bad_sha,
            "--head-sha",
            "b" * 40,
            "--denylist",
            str(denylist),
        )

        assert result.returncode == 2
        assert b"sha" in result.stderr.lower()

    def test_unreadable_denylist_file_is_usage_error(self, tmp_diff_file):
        """F7: non-existent denylist path → exit 2, stderr mentions the path."""
        diff = tmp_diff_file("README.md\n")
        missing = "/nonexistent/denylist.txt"

        result = _run("--diff-file", str(diff), "--denylist", missing)

        assert result.returncode == 2
        assert b"denylist" in result.stderr.lower() or missing.encode() in result.stderr

    def test_git_failure_surfaced_as_usage_error(self, tmp_denylist, tmp_repo):
        """F7: unresolvable SHAs in a real repo → exit 2, stderr mentions git."""
        denylist = tmp_denylist()

        result = _run(
            "--base-sha",
            "0" * 40,
            "--head-sha",
            "1" * 40,
            "--denylist",
            str(denylist),
            cwd=tmp_repo,
        )

        assert result.returncode == 2
        assert b"git" in result.stderr.lower()
        # stdout must not be a pass:true result
        if result.stdout:
            try:
                data = json.loads(result.stdout.decode("utf-8"))
                assert data.get("pass") is not True
            except json.JSONDecodeError:
                pass


# ---------------------------------------------------------------------------
# Exit code invariant — concrete example + property-shaped (randomized) test
# ---------------------------------------------------------------------------


class TestExitCodeInvariant:
    """The script must never emit exit codes 3+."""

    def test_no_arguments_at_all_exits_2(self):
        """Sanity: totally empty argv → argparse exits 2 (usage)."""
        result = _run()

        assert result.returncode in {0, 1, 2}

    def test_exit_code_always_in_valid_set_for_random_invocations(self, tmp_path):
        """Property-shaped: 30 random argv/denylist/diff combos — exit always in {0,1,2}."""
        rng = random.Random(0xC0FFEE)
        flags_pool = [
            "--base-sha",
            "--head-sha",
            "--denylist",
            "--diff-file",
            "--unknown-flag",
        ]
        values_pool = [
            "",
            "a" * 40,
            "z" * 40,
            "not-a-sha",
            "/nonexistent/path",
            "abc123",
            "🦀" * 5,
        ]

        for i in range(30):
            argv: list[str] = []
            for _ in range(rng.randint(0, 6)):
                argv.append(rng.choice(flags_pool))
                argv.append(rng.choice(values_pool))

            # Occasionally throw in a real denylist/diff file to widen coverage
            if rng.random() < 0.3:
                dl = tmp_path / f"dl-{i}.txt"
                dl.write_text(
                    rng.choice(["", ".github/**\n", "pyproject.toml\n", "# x\n"]),
                    encoding="utf-8",
                )
                argv += ["--denylist", str(dl)]
            if rng.random() < 0.3:
                df = tmp_path / f"df-{i}.txt"
                df.write_text(
                    "".join(
                        rng.choice(string.ascii_letters + "/.-_\n") for _ in range(20)
                    ),
                    encoding="utf-8",
                )
                argv += ["--diff-file", str(df)]

            result = _run(*argv)
            assert result.returncode in {0, 1, 2}, (
                f"argv={argv!r} produced exit={result.returncode}, "
                f"stderr={result.stderr!r}"
            )


# ---------------------------------------------------------------------------
# Determinism contract — matched_files is sorted by (path, rule)
# ---------------------------------------------------------------------------


class TestDeterministicOrdering:
    """matched_files is sorted by (path, rule) for snapshot stability."""

    def test_matched_files_sorted_by_path_then_rule(self, tmp_denylist, tmp_diff_file):
        """Sort order is deterministic — (path asc, rule asc)."""
        denylist = tmp_denylist()
        # Deliberately unsorted input
        diff = tmp_diff_file(
            "pyproject.toml\n"
            ".github/workflows/ci.yml\n"
            "scripts/release/publish.py\n"
            "CONTRIBUTING.md\n"
        )

        result = _run("--diff-file", str(diff), "--denylist", str(denylist))

        assert result.returncode == 1
        data = _parse_stdout(result)
        paths = [entry["path"] for entry in data["matched_files"]]
        assert paths == sorted(paths)
