"""Driven function ports and explicit adapter failures."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from nwdes.contracts import Built, Defect, Refused
from nwdes.destinations import ConfigurationTier
from nwdes.documents import AdrEntry, OutputSet
from nwdes.handoff import Scope


@dataclass(frozen=True)
class Missing:
    path: str
    reason: str


@dataclass(frozen=True)
class Unreadable:
    path: str
    reason: str


@dataclass(frozen=True)
class IOFailure:
    unwritten: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class AssetMissing:
    path: str
    reason: str


@dataclass(frozen=True)
class AssetUnreadable(Refused):
    """An asset read or decode failure, reported with exit 1 by the shell."""


@dataclass(frozen=True)
class BrandUnavailable:
    failures: tuple[AssetMissing | AssetUnreadable, ...]


@dataclass(frozen=True)
class WriteResult:
    paths: tuple[tuple[str, str], ...]


ReadConfigurationTier = Callable[
    [str, Scope | None], Built[ConfigurationTier] | Refused
]
ReadFile = Callable[[str], bytes | Missing | Unreadable]
WriteOutputs = Callable[[OutputSet], WriteResult | IOFailure]
ReadAsset = Callable[[str], bytes | AssetMissing | AssetUnreadable]
ReadInput = Callable[[], bytes]
ReadRegister = Callable[[str], Built[tuple[AdrEntry, ...]] | Refused | Unreadable]


@dataclass(frozen=True)
class DocumentPorts:
    configuration: ReadConfigurationTier
    file: ReadFile
    outputs: WriteOutputs
    asset: ReadAsset
    register: ReadRegister
    confinement: Callable[[tuple[str, ...]], Built[None] | Refused]
    input: ReadInput
    asset_root: str


@dataclass(frozen=True)
class GitResult:
    code: int
    stdout: bytes
    stderr: bytes


RunGit = Callable[[str, tuple[str, ...]], GitResult | Unreadable]
RemovePaths = Callable[[str, tuple[str, ...]], WriteResult | IOFailure]
EnsureExclude = Callable[[str], Built[None] | IOFailure]


@dataclass(frozen=True)
class ConfigurationRead:
    values: Mapping[str, object]
    defects: tuple[Defect, ...]
    operational: bool
