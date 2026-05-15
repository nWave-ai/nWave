"""Tests for install_nwave._resolve_platform_override() — --platform flag.

Codifies the contract: every choice surfaced by argparse MUST have a
corresponding entry in the platform_map.  Regression guards against
silent dropping of a target when a new platform is added (or removed).
"""

from __future__ import annotations

import pytest

from scripts.install.install_nwave import _resolve_platform_override


class TestPlatformFlagResolution:
    """The --platform flag must resolve to the documented platform set."""

    def test_auto_returns_none_for_autodetect(self):
        assert _resolve_platform_override("auto") is None

    def test_claude_code_returns_singleton(self):
        assert _resolve_platform_override("claude-code") == {"claude_code"}

    def test_opencode_returns_singleton(self):
        assert _resolve_platform_override("opencode") == {"opencode"}

    def test_codex_returns_singleton(self):
        """Codex must be selectable explicitly, not only via auto-detect."""
        assert _resolve_platform_override("codex") == {"codex"}

    def test_all_includes_every_explicit_platform(self):
        """``--platform all`` must include every explicit platform target —
        otherwise users requesting "all" silently miss the absent target.
        """
        explicit = {
            _resolve_platform_override(flag).pop()
            for flag in ("claude-code", "opencode", "codex")
        }
        assert _resolve_platform_override("all") == explicit

    def test_unknown_flag_raises(self):
        """Argparse normally guards this, but the resolver must fail loud
        if called with a value outside its choices set.
        """
        with pytest.raises(KeyError):
            _resolve_platform_override("unknown")
