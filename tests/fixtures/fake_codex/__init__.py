"""Fake-codex test harness package.

A contract-equivalent fake of the Codex CLI's hook invocation behavior, used
where the real ``codex`` binary is not available in the test environment
(e.g. dev machines without Docker, or CI runners that don't bundle Codex).

The harness implements exactly the documented Codex hooks contract per
``docs/feature/codex-empirical-e2e-support/spike-codex-hooks-schema.md``:

- Q1: read ``~/.codex/hooks.json`` event-keyed object root (``{"hooks": {"PreToolUse": [...]}}``)
- Q3: invoke configured ``command`` strings as-is via the shell (no argv injection)
- Q4: send the documented stdin JSON envelope to the hook command
- Q5: honor exit codes (0=allow, 2=block+stderr; anything else surfaces as error)
- Q6: match tool name against the matcher regex

The harness MUST NOT hardcode any test-specific output — it only honestly
invokes the configured command string. The audit log entries asserted in tests
are written by the real DES adapter that the configured command runs.
"""

from tests.fixtures.fake_codex.harness import (
    FakeCodexHarness,
    FakeCodexSchemaError,
    HookInvocation,
)


__all__ = ["FakeCodexHarness", "FakeCodexSchemaError", "HookInvocation"]
