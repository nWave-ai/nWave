"""Pinned manifest value for a certified capture run."""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePath

from .contracts import (
    PartitionRef,
    RepositoryRef,
    RunRef,
    UsageObservationSemantics,
    _digest,
    _string,
)


def _utc(value: object) -> None:
    if not isinstance(value, datetime):
        raise TypeError("expected datetime")
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("expected UTC datetime")


def _strings(values: object) -> None:
    if not isinstance(values, tuple):
        raise TypeError("expected tuple")
    if not values:
        raise ValueError("tuple must be non-empty")
    for value in values:
        _string(value)


@dataclass(frozen=True)
class RunManifest:
    capture_schema_version: str
    run: RunRef
    task_case_contract_digest: str
    metric_vocabulary: tuple[str, ...]
    usage_observation_semantics: tuple[UsageObservationSemantics, ...]
    root_partition: PartitionRef
    interval_start: datetime
    interval_end: datetime
    reconciliation_deadline: datetime
    canonical_capture_root: PurePath
    runtime_digest: str
    hook_digest: str
    executable_digest: str
    config_digest: str
    primary_writer_version: str
    retention_target: str
    retention_deadline: datetime
    repository: RepositoryRef
    provider_namespace_versions: tuple[str, ...]
    manifest_digest: str

    def __post_init__(self):
        _string(self.capture_schema_version)
        if not isinstance(self.run, RunRef):
            raise TypeError("run must be RunRef")
        _digest(self.task_case_contract_digest)
        _strings(self.metric_vocabulary)
        if not isinstance(self.usage_observation_semantics, tuple):
            raise TypeError("semantics must be tuple")
        if not self.usage_observation_semantics:
            raise ValueError("semantics must be non-empty")
        for value in self.usage_observation_semantics:
            if not isinstance(value, UsageObservationSemantics):
                raise TypeError("semantics member")
        if len({x.provider_namespace for x in self.usage_observation_semantics}) != len(
            self.usage_observation_semantics
        ):
            raise ValueError("provider namespaces unique")
        if not isinstance(self.root_partition, PartitionRef):
            raise TypeError("root partition")
        for value in (
            self.interval_start,
            self.interval_end,
            self.reconciliation_deadline,
            self.retention_deadline,
        ):
            _utc(value)
        if not isinstance(self.canonical_capture_root, PurePath):
            raise TypeError("capture root")
        if not self.canonical_capture_root.is_absolute():
            raise ValueError("capture root absolute")
        for value in (
            self.runtime_digest,
            self.hook_digest,
            self.executable_digest,
            self.config_digest,
            self.manifest_digest,
        ):
            _digest(value)
        _string(self.primary_writer_version)
        _string(self.retention_target)
        if not isinstance(self.repository, RepositoryRef):
            raise TypeError("repository")
        _strings(self.provider_namespace_versions)
        if (
            not self.interval_start
            < self.interval_end
            <= self.reconciliation_deadline
            <= self.retention_deadline
        ):
            raise ValueError("invalid interval order")
        if self.task_case_contract_digest != self.run.study.task_case_contract_digest:
            raise ValueError("task digest mismatch")
        if (
            self.root_partition.run_id != self.run.run_id
            or self.root_partition.parent_partition_id is not None
        ):
            raise ValueError("invalid root partition")
