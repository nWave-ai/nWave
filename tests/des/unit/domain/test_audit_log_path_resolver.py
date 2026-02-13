"""Unit tests for AuditLogPathResolver.

Tests that the shared path resolver produces deterministic, consistent paths
for both writer and reader.
"""

from des.domain.audit_log_path_resolver import AuditLogPathResolver


class TestAuditLogPathResolver:
    """Unit tests for AuditLogPathResolver."""

    def test_explicit_dir_takes_priority(self, tmp_path):
        """Explicit log_dir parameter should be used directly."""
        explicit = tmp_path / "explicit-logs"
        resolver = AuditLogPathResolver(log_dir=explicit)
        assert resolver.resolve() == explicit

    def test_env_var_takes_priority_over_defaults(self, tmp_path, monkeypatch):
        """DES_AUDIT_LOG_DIR env var should override defaults."""
        env_dir = tmp_path / "env-logs"
        monkeypatch.setenv("DES_AUDIT_LOG_DIR", str(env_dir))
        resolver = AuditLogPathResolver()
        assert resolver.resolve() == env_dir

    def test_project_local_default(self, tmp_path, monkeypatch):
        """Without env var, should use project-local .nwave/des/logs/."""
        monkeypatch.delenv("DES_AUDIT_LOG_DIR", raising=False)
        monkeypatch.chdir(tmp_path)
        resolver = AuditLogPathResolver()
        assert resolver.resolve() == tmp_path / ".nwave" / "des" / "logs"

    def test_cwd_override(self, tmp_path, monkeypatch):
        """Explicit cwd parameter should override Path.cwd()."""
        monkeypatch.delenv("DES_AUDIT_LOG_DIR", raising=False)
        cwd_dir = tmp_path / "my-project"
        cwd_dir.mkdir()
        resolver = AuditLogPathResolver(cwd=cwd_dir)
        assert resolver.resolve() == cwd_dir / ".nwave" / "des" / "logs"
