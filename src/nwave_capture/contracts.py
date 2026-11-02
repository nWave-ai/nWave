"""Immutable, neutral certified-capture identity values."""

import re
from dataclasses import dataclass
from enum import Enum
from uuid import UUID


_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


def _string(value: object) -> None:
    if not isinstance(value, str):
        raise TypeError("expected str")
    if not value or value != value.strip():
        raise ValueError("expected trimmed non-empty str")


def _digest(value: object) -> None:
    _string(value)
    if not _DIGEST.fullmatch(value):
        raise ValueError("expected lowercase SHA-256 digest")


@dataclass(frozen=True)
class TaskCaseContractRef:
    task_case_id: str
    task_spec_digest: str
    initial_state_digest: str
    environment_contract_digest: str
    quality_evaluation_plan_digest: str

    def __post_init__(self):
        _string(self.task_case_id)
        for value in (
            self.task_spec_digest,
            self.initial_state_digest,
            self.environment_contract_digest,
            self.quality_evaluation_plan_digest,
        ):
            _digest(value)


@dataclass(frozen=True)
class StudyRef:
    study_id: str
    task_case_contract_digest: str
    comparator_id: str

    def __post_init__(self):
        _string(self.study_id)
        _digest(self.task_case_contract_digest)
        _string(self.comparator_id)


@dataclass(frozen=True)
class RunRef:
    run_id: UUID
    attempt_no: int
    study: StudyRef

    def __post_init__(self):
        if not isinstance(self.run_id, UUID):
            raise TypeError("run_id must be UUID")
        if isinstance(self.attempt_no, bool) or not isinstance(self.attempt_no, int):
            raise TypeError("attempt_no must be int")
        if self.attempt_no <= 0:
            raise ValueError("attempt_no must be positive")
        if not isinstance(self.study, StudyRef):
            raise TypeError("study must be StudyRef")


@dataclass(frozen=True)
class PartitionRef:
    partition_id: str
    run_id: UUID
    actor_id: str
    actor_kind: str
    parent_partition_id: str | None = None

    def __post_init__(self):
        _string(self.partition_id)
        if not isinstance(self.run_id, UUID):
            raise TypeError("run_id must be UUID")
        _string(self.actor_id)
        _string(self.actor_kind)
        if self.parent_partition_id is not None:
            _string(self.parent_partition_id)


@dataclass(frozen=True)
class RequestRef:
    provider_namespace: str
    request_id: str
    partition: PartitionRef
    model: str

    def __post_init__(self):
        _string(self.provider_namespace)
        _string(self.request_id)
        _string(self.model)
        if not isinstance(self.partition, PartitionRef):
            raise TypeError("partition must be PartitionRef")


@dataclass(frozen=True)
class RepositoryRef:
    repo_id: str
    worktree_id: str
    base_commit_sha: str
    observed_head_sha: str | None = None

    def __post_init__(self):
        _digest(self.repo_id)
        _digest(self.worktree_id)
        _string(self.base_commit_sha)
        if self.observed_head_sha is not None:
            _string(self.observed_head_sha)


class UsageObservationMode(Enum):
    CUMULATIVE_SNAPSHOT = "cumulative_snapshot"
    DELTA = "delta"
    OTHER = "other"


@dataclass(frozen=True)
class UsageObservationSemantics:
    provider_namespace: str
    schema_version: str
    mode: UsageObservationMode
    reducer_id_and_version: str

    def __post_init__(self):
        _string(self.provider_namespace)
        _string(self.schema_version)
        _string(self.reducer_id_and_version)
        if not isinstance(self.mode, UsageObservationMode):
            raise TypeError("mode must be UsageObservationMode")
