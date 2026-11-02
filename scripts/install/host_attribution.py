"""Closed host attribution decisions, shared by installer, CLI and doctor."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Protocol

from scripts.install.attribution_utils import (
    GitDiscoveryFailure,
    UnreadableAttributionPreference,
    has_current_fallback,
    install_attribution_hook,
    read_attribution_preference,
    read_global_config,
    resolve_repository_hooks_dir,
)


if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path
    from typing import Self


REMEDIATION = "run nwave-ai attribution on inside the repository"


class HostCommandCapability(Enum):
    """Whether a host's pre-tool hook can modify a commit command."""

    REWRITES_COMMAND = "rewrites_command"
    CANNOT_REWRITE = "cannot_rewrite"
    UNESTABLISHED = "unestablished"

    @property
    def rewrites_command(self) -> bool:
        return self is HostCommandCapability.REWRITES_COMMAND


class InstalledHookPort(Enum):
    """Installed artifacts a host's rewrite mechanism needs verified."""

    CODEX_HOOKS = "codex_hooks"
    OMP_EXTENSION = "omp_extension"


class InstalledRewriteVerifier(Protocol):
    """Read-only inspection supplied by the caller, not by the host policy."""

    def verify(self, port: InstalledHookPort) -> str | None:
        """Return the reason verification failed, or None when in force."""
        ...


class AttributableHost(Enum):
    """The closed set of hosts and their evidenced attribution capabilities."""

    CURSOR = ("cursor", HostCommandCapability.UNESTABLISHED, None)
    DEVIN = ("devin", HostCommandCapability.CANNOT_REWRITE, None)
    CODEX = (
        "codex",
        HostCommandCapability.REWRITES_COMMAND,
        InstalledHookPort.CODEX_HOOKS,
    )
    OMP = (
        "omp",
        HostCommandCapability.REWRITES_COMMAND,
        InstalledHookPort.OMP_EXTENSION,
    )

    def __new__(
        cls,
        platform: str,
        capability: HostCommandCapability,
        rewrite_port: InstalledHookPort | None,
    ) -> AttributableHost:
        host = object.__new__(cls)
        host._value_ = platform
        host._capability = capability
        host._rewrite_port = rewrite_port
        return host

    @property
    def capability(self) -> HostCommandCapability:
        return self._capability

    @property
    def label(self) -> str:
        return self.value.capitalize()

    @property
    def rewrite_port(self) -> InstalledHookPort | None:
        return self._rewrite_port

    @classmethod
    def from_platform(cls, name: str) -> AttributableHost | None:
        """Parse a platform at the boundary; other platforms carry no host value."""
        try:
            return cls(name)
        except ValueError:
            return None

    def mechanism_in(self, repository: Path | None) -> AttributionMechanism:
        """Select a mechanism without claiming a failed discovery is a non-repo."""
        if self.capability.rewrites_command:
            return HookRewrite(self)
        return self._fallback_at(_repository_hooks_dir(repository))

    def _fallback_at(
        self, hooks_dir: Path | GitDiscoveryFailure | None
    ) -> AttributionMechanism:
        if isinstance(hooks_dir, GitDiscoveryFailure):
            return Unavailable(self, hooks_dir.reason)
        if hooks_dir is None:
            return Unavailable(self, "the working directory is not in a git repository")
        return CommitMessageFallback(self, hooks_dir)


class AttributionPreference(Enum):
    """The shared, saved attribution preference (one value for every host)."""

    UNSET = "unset"
    ENABLED = "enabled"
    DISABLED = "disabled"

    @classmethod
    def read(
        cls, config_dir: Path
    ) -> AttributionPreference | UnreadableAttributionPreference:
        saved = read_attribution_preference(config_dir)
        if isinstance(saved, UnreadableAttributionPreference):
            return saved
        if saved is None:
            return cls.UNSET
        return cls.ENABLED if saved else cls.DISABLED

    def after_install(self) -> AttributionPreference:
        """First install defaults to enabled; an explicit choice never changes."""
        if self is AttributionPreference.UNSET:
            return AttributionPreference.ENABLED
        return self

    @property
    def is_enabled(self) -> bool:
        return self is AttributionPreference.ENABLED


@dataclass(frozen=True)
class _HostMechanism(ABC):
    host: AttributableHost

    @property
    def label(self) -> str:
        return self.host.label

    @property
    def works(self) -> bool:
        return True

    @property
    def remediation(self) -> str | None:
        return None

    def report(self) -> str:
        if self.remediation is None:
            return self.describe()
        return f"{self.describe()}; {self.remediation}"

    @abstractmethod
    def describe(self) -> str:
        """Describe the installed mechanism or its unavailable cause."""

    def install(self, config_dir: Path) -> Self | Unavailable:
        return self

    def inspect(self, verifier: InstalledRewriteVerifier) -> Self | Unavailable:
        return self


@dataclass(frozen=True)
class HookRewrite(_HostMechanism):
    """The host's pre-tool hook rewrites the commit command."""

    def describe(self) -> str:
        return f"{self.label} attribution: hook rewrite"

    def inspect(self, verifier: InstalledRewriteVerifier) -> HookRewrite | Unavailable:
        port = self.host.rewrite_port
        if port is None:
            return Unavailable(
                self.host, "no installed-hook verification port is defined"
            )
        reason = verifier.verify(port)
        if reason is None:
            return self
        return Unavailable(
            self.host, reason, f"re-run the nWave installer for {self.host.value}"
        )


@dataclass(frozen=True)
class CommitMessageFallback(_HostMechanism):
    """A per-repository prepare-commit-msg shim marks every commit there."""

    hooks_dir: Path

    def describe(self) -> str:
        return f"{self.label} attribution: fallback in {self.hooks_dir}"

    def install(self, config_dir: Path) -> CommitMessageFallback | Unavailable:
        try:
            install_attribution_hook(config_dir, hooks_dir=self.hooks_dir)
        except OSError as error:
            return Unavailable(
                self.host, f"could not write the fallback in {self.hooks_dir}: {error}"
            )
        return self

    def inspect(
        self, verifier: InstalledRewriteVerifier
    ) -> CommitMessageFallback | Unavailable:
        if has_current_fallback(self.hooks_dir):
            return self
        return Unavailable(self.host, f"no fallback is installed in {self.hooks_dir}")


@dataclass(frozen=True)
class Unavailable(_HostMechanism):
    """No attribution can be provided for this host; the reason is stated."""

    reason: str
    repair: str = REMEDIATION

    @property
    def works(self) -> bool:
        return False

    @property
    def remediation(self) -> str:
        return self.repair

    def describe(self) -> str:
        return f"{self.label} attribution: unavailable ({self.reason})"


AttributionMechanism = HookRewrite | CommitMessageFallback | Unavailable


@dataclass(frozen=True)
class HostAttributionPolicy:
    """One parsed installation record and its closed attribution host values."""

    hosts: frozenset[AttributableHost]
    claude_expected: bool

    @classmethod
    def for_platforms(cls, platforms: Iterable[str]) -> HostAttributionPolicy:
        platform_names = frozenset(platforms)
        hosts = frozenset(
            host
            for name in platform_names
            if (host := AttributableHost.from_platform(name)) is not None
        )
        return cls(hosts, "claude_code" in platform_names)

    @classmethod
    def from_install_record(cls, config_dir: Path) -> HostAttributionPolicy:
        config = read_global_config(config_dir)
        installation = config.get("install") if isinstance(config, dict) else None
        recorded = (
            installation.get("target_platforms")
            if isinstance(installation, dict)
            else None
        )
        if not isinstance(recorded, list):
            return cls(frozenset(), True)
        return cls.for_platforms(name for name in recorded if isinstance(name, str))

    @property
    def has_hosts(self) -> bool:
        return bool(self.hosts)

    def mechanisms_in(
        self, repository: Path | None
    ) -> tuple[AttributionMechanism, ...]:
        return tuple(
            host.mechanism_in(repository)
            for host in sorted(self.hosts, key=lambda host: host.value)
        )


def _repository_hooks_dir(
    repository: Path | None,
) -> Path | GitDiscoveryFailure | None:
    if repository is None:
        return None
    try:
        return resolve_repository_hooks_dir(repository)
    except Exception as error:
        return GitDiscoveryFailure(f"repository hook discovery failed: {error}")
