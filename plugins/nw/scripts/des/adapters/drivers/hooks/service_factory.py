"""Factory functions for hook handler application services.

Creates production-wired instances of PreToolUseService and SubagentStopService
with all required dependencies injected.

All factories accept an optional ``audit_writer_factory`` callable, enabling
the adapter to pass its own patchable factory for test isolation.

Extracted from claude_code_hook_adapter.py as part of P4 decomposition (step 4c).
"""

from collections.abc import Callable

from des.adapters.driven.git.git_commit_verifier import GitCommitVerifier
from des.adapters.driven.hooks.json_execution_log_reader import (
    JsonExecutionLogReader,
)
from des.adapters.driven.time.system_time import SystemTimeProvider
from des.adapters.driven.validation.git_scope_checker import GitScopeChecker
from des.adapters.drivers.hooks import hook_protocol
from des.application.pre_tool_use_service import PreToolUseService
from des.application.subagent_stop_service import SubagentStopService
from des.application.validator import TemplateValidator
from des.domain.des_enforcement_policy import DesEnforcementPolicy
from des.domain.des_marker_parser import DesMarkerParser
from des.domain.marker_completeness_policy import MarkerCompletenessPolicy
from des.domain.step_completion_validator import StepCompletionValidator
from des.domain.tdd_schema import TDDSchemaLoader
from des.ports.driven_ports.audit_log_writer import AuditLogWriter


def create_pre_tool_use_service(
    *,
    audit_writer_factory: Callable[[], AuditLogWriter] | None = None,
    deliverable_type: str | None = None,
) -> PreToolUseService:
    """Create PreToolUseService with production dependencies.

    Args:
        audit_writer_factory: Optional callable returning an AuditLogWriter.
            Falls back to ``create_audit_writer`` if None.
        deliverable_type: Resolved project deliverable type (ADR-PST-001,
            feature plugin-skill-deliverable-type). Threaded into the service so
            ``validate()`` can pass it pure into ``DesEnforcementPolicy.check``.
            ``None`` (default) preserves the existing app-code behaviour exactly.

    Returns:
        PreToolUseService configured for production use
    """
    factory = audit_writer_factory or hook_protocol._audit_writer_factory
    time_provider = SystemTimeProvider()
    audit_writer = factory()

    return PreToolUseService(
        marker_parser=DesMarkerParser(),
        prompt_validator=TemplateValidator(),
        audit_writer=audit_writer,
        time_provider=time_provider,
        enforcement_policy=DesEnforcementPolicy(),
        completeness_policy=MarkerCompletenessPolicy(),
        deliverable_type=deliverable_type,
    )


def create_subagent_stop_service(
    *,
    audit_writer_factory: Callable[[], AuditLogWriter] | None = None,
) -> SubagentStopService:
    """Create SubagentStopService with production dependencies.

    Args:
        audit_writer_factory: Optional callable returning an AuditLogWriter.
            Falls back to ``create_audit_writer`` if None.

    Returns:
        SubagentStopService configured for production use
    """
    from des.domain.log_integrity_validator import LogIntegrityValidator

    factory = audit_writer_factory or hook_protocol._audit_writer_factory
    time_provider = SystemTimeProvider()
    audit_writer = factory()
    schema = TDDSchemaLoader().load()

    return SubagentStopService(
        log_reader=JsonExecutionLogReader(),
        completion_validator=StepCompletionValidator(schema=schema),
        scope_checker=GitScopeChecker(),
        audit_writer=audit_writer,
        time_provider=time_provider,
        commit_verifier=GitCommitVerifier(),
        integrity_validator=LogIntegrityValidator(
            schema=schema, time_provider=time_provider
        ),
    )
