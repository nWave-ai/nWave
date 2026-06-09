"""Unit tests for ReviewerSigningPlugin.

Friction-fix F-01 (docs/analysis/atdd-pure-dogfooding-friction-2026-05-20.md):
the ATDD-pure AT-review HMAC signing key had no provisioning path. This plugin
provisions a per-project key at install time so atdd_pure `/nw-deliver` does not
hit `key-absent` with no guidance.

Tests drive the plugin through its install() driving port and assert at the
driven port boundary (the `.nwave/secrets/reviewer-signing.key` filesystem
slot). State-delta over the secrets directory catches undeclared mutations.

Behaviors tested (budget: 4 behaviors x 2 = 8 max; using 5 tests):
1. Key absent + env unset -> install generates a 64-hex-char key file
2. Key already present -> install leaves the existing key byte-identical
3. NWAVE_REVIEWER_SIGNING_KEY set -> install skips file provisioning
4. Generated key file has restrictive permissions (0600) where OS supports it
5. verify() reports the provisioned/present/env state without failing
"""

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from nwave_ai.state_delta import assert_state_delta, set_to, unchanged

from scripts.install.plugins.base import InstallContext
from scripts.install.plugins.reviewer_signing_plugin import ReviewerSigningPlugin


_KEY_RELPATH = Path(".nwave") / "secrets" / "reviewer-signing.key"
_SIGNING_KEY_ENV = "NWAVE_REVIEWER_SIGNING_KEY"


def _make_context(tmp_path: Path) -> InstallContext:
    """Build an InstallContext rooted at an isolated tmp project dir."""
    return InstallContext(
        claude_dir=tmp_path / ".claude",
        scripts_dir=tmp_path / "scripts",
        templates_dir=tmp_path / "templates",
        logger=MagicMock(),
        project_root=tmp_path,
    )


def _secrets_state(project_root: Path) -> dict[str, object]:
    """Snapshot the reviewer-signing-key filesystem slots."""
    key_file = project_root / _KEY_RELPATH
    return {
        "key.exists": key_file.is_file(),
        "key.content": key_file.read_bytes() if key_file.is_file() else None,
    }


@pytest.fixture(autouse=True)
def _no_env_key(monkeypatch: pytest.MonkeyPatch):
    """Ensure NWAVE_REVIEWER_SIGNING_KEY is unset unless a test sets it."""
    monkeypatch.delenv(_SIGNING_KEY_ENV, raising=False)


def test_install_generates_key_when_absent_and_env_unset(tmp_path: Path):
    """Behavior 1: absent key + unset env -> a 64-hex-char key file is created."""
    context = _make_context(tmp_path)
    before = _secrets_state(tmp_path)

    result = ReviewerSigningPlugin().install(context)

    after = _secrets_state(tmp_path)
    key_file = tmp_path / _KEY_RELPATH
    generated = key_file.read_bytes()

    assert result.success
    assert len(generated) == 64
    assert all(c in b"0123456789abcdef" for c in generated)
    assert_state_delta(
        before,
        after,
        universe={"key.exists", "key.content"},
        expected={
            "key.exists": set_to(True),
            "key.content": set_to(generated),
        },
        strict=True,
    )


def test_install_preserves_existing_key(tmp_path: Path):
    """Behavior 2: an existing key is NEVER overwritten (idempotent)."""
    key_file = tmp_path / _KEY_RELPATH
    key_file.parent.mkdir(parents=True, exist_ok=True)
    sentinel = b"deadbeef" * 8  # 64 chars, a pre-existing key
    key_file.write_bytes(sentinel)
    context = _make_context(tmp_path)
    before = _secrets_state(tmp_path)

    result = ReviewerSigningPlugin().install(context)

    after = _secrets_state(tmp_path)
    assert result.success
    assert key_file.read_bytes() == sentinel
    assert_state_delta(
        before,
        after,
        universe={"key.exists", "key.content"},
        expected={"key.exists": unchanged(), "key.content": unchanged()},
        strict=True,
    )


def test_install_skips_file_when_env_var_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Behavior 3: env var present -> no key file is provisioned."""
    monkeypatch.setenv(_SIGNING_KEY_ENV, "env-provided-key")
    context = _make_context(tmp_path)
    before = _secrets_state(tmp_path)

    result = ReviewerSigningPlugin().install(context)

    after = _secrets_state(tmp_path)
    assert result.success
    assert not (tmp_path / _KEY_RELPATH).exists()
    assert_state_delta(
        before,
        after,
        universe={"key.exists", "key.content"},
        expected={"key.exists": unchanged(), "key.content": unchanged()},
        strict=True,
    )


@pytest.mark.skipif(
    os.name != "posix", reason="file mode bits only meaningful on POSIX"
)
def test_generated_key_has_restrictive_permissions(tmp_path: Path):
    """Behavior 4: the generated key file is mode 0600 on POSIX."""
    context = _make_context(tmp_path)

    ReviewerSigningPlugin().install(context)

    key_file = tmp_path / _KEY_RELPATH
    mode = key_file.stat().st_mode & 0o777
    assert mode == 0o600


def test_verify_reports_present_key(tmp_path: Path):
    """Behavior 5: verify() succeeds and reports the provisioned key."""
    context = _make_context(tmp_path)
    plugin = ReviewerSigningPlugin()
    plugin.install(context)

    result = plugin.verify(context)

    assert result.success
    assert "reviewer signing key" in result.message.lower()


@pytest.mark.skipif(os.name != "posix", reason="chmod 555 only meaningful on POSIX")
def test_install_soft_skips_on_readonly_project_dir(tmp_path: Path):
    """Behavior 6: install must NOT crash when .nwave/ is read-only (EROFS class).

    Mirrors the v3.16.0rc4/rc5 Validate Published RC failure: /src is a
    read-only container mount, so .nwave/secrets/ cannot be created. The
    install must succeed (success=True) with an explanatory soft-skip
    message, leaving artifact provisioning to env-var fallback or to a
    later run on a writable dir.
    """
    nwave_dir = tmp_path / ".nwave"
    nwave_dir.mkdir()
    nwave_dir.chmod(0o555)  # read-only
    context = _make_context(tmp_path)
    try:
        result = ReviewerSigningPlugin().install(context)
    finally:
        nwave_dir.chmod(0o755)  # restore for cleanup
    assert result.success, f"install crashed on read-only dir: {result.message}"
    assert (
        "read-only" in result.message.lower() or "skipped" in result.message.lower()
    ), f"soft-skip message should mention read-only or skipped: {result.message}"
    assert not (tmp_path / _KEY_RELPATH).exists()
