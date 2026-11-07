"""The sole writer for nWave's two persisted configuration tiers.

Migration is deliberately a write-time concern.  Readers consume only
``~/.nwave/config.json`` and ``<repo>/.nwave/config.json``; an upgrade turns
the three retired files into those two documents before a reader is used.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from nwave_ai.platform.artifact_versioning import ArtifactFromFutureRuntime
from nwave_ai.platform.config import (
    _GLOBAL_CONFIG_ARTIFACT_TYPE,
    _GLOBAL_CONFIG_VERSIONING,
    NWaveConfig,
    _translate_public_attribution,
)
from nwave_ai.platform.config_merge import ATTRIBUTION_DEFAULT, VERBOSITY_VALUES


if TYPE_CHECKING:
    from collections.abc import Callable


class ConfigMigrationError(RuntimeError):
    """A legacy configuration cannot safely be made the unified authority."""


@dataclass(frozen=True)
class ConfigBootstrapResult:
    global_path: Path
    repo_path: Path
    migrated_legacy_paths: tuple[Path, ...]
    created_paths: tuple[Path, ...]
    dry_run: bool


class ConfigWriter:
    """Bootstrap and migrate the global and repository configuration atomically.

    Atomicity is per file: each replacement is an ``os.replace`` of a flushed
    sibling temporary file.  The two paths cannot be one filesystem
    transaction, so every input is parsed, reconciled and version-validated
    before either target is touched.  Existing and legacy bytes are copied to
    adjacent ``*.unified-config.bak`` files before their source is replaced or
    retired, making a failed external operation recoverable.
    """

    _GLOBAL_LEGACY = "global-config.json"
    _REPO_LEGACY = "des-config.json"
    _MARKER_LEGACY = "local-config.json"
    _BACKUP_SUFFIX = ".unified-config.bak"
    _REPO_DEFAULTS: dict[str, Any] = {
        "audit_logging_enabled": True,
        "audit_log_dir": ".nwave/des/logs",
    }
    # Only operational preferences are published on first install.
    _GLOBAL_DEFAULTS: dict[str, Any] = {
        "attribution": {
            "enabled": ATTRIBUTION_DEFAULT,
            "trailer": "Co-Authored-By: nWave <nwave@nwave.ai>",
        },
    }

    def __init__(
        self,
        *,
        home_dir: Path | None = None,
        repo_root: Path,
        global_dir: Path | None = None,
    ) -> None:
        self._home_dir = (home_dir or Path.home()).expanduser()
        self._repo_root = repo_root.resolve()
        self.global_dir = (
            global_dir if global_dir is not None else self._home_dir / ".nwave"
        )
        self.repo_dir = self._repo_root / ".nwave"
        self.global_path = self.global_dir / "config.json"
        self.repo_path = self.repo_dir / "config.json"

    def bootstrap(self, *, dry_run: bool = False) -> ConfigBootstrapResult:
        """Create the two authorities or migrate all legacy input exactly once.

        Invalid JSON, non-object JSON, future schemas, and conflicting values
        are refused before writing.  A successful call removes each legacy
        source after its backup and both unified documents have been verified.
        Repeating it sees only the two canonical files and makes no mutation.
        """
        global_legacy = self.global_dir / self._GLOBAL_LEGACY
        repo_legacy = self.repo_dir / self._REPO_LEGACY
        marker_legacy = self.repo_dir / self._MARKER_LEGACY
        legacy_paths = tuple(
            path
            for path in (global_legacy, repo_legacy, marker_legacy)
            if path.exists()
        )

        existing_global = self._read_object(self.global_path, role="unified config")
        existing_repo = self._read_object(self.repo_path, role="unified config")
        legacy_global = self._read_object(global_legacy, role="legacy config")
        legacy_repo = self._read_object(repo_legacy, role="legacy config")
        legacy_marker = self._read_object(marker_legacy, role="legacy marker")

        # Validate every versioned source independently before reconciliation.
        # Validating only the merged result would allow an incompatible legacy
        # document to be hidden by a same-named canonical field.
        for document in (existing_global, existing_repo, legacy_global, legacy_repo):
            self._validate_supported_version(document)

        if legacy_marker and "enabled_for_repo" in legacy_marker:
            value = legacy_marker["enabled_for_repo"]
            if not isinstance(value, bool):
                raise ConfigMigrationError(
                    f"Cannot migrate {marker_legacy}: enabled_for_repo must be a boolean"
                )
            if "enabled" in legacy_repo and legacy_repo["enabled"] != value:
                raise ConfigMigrationError(
                    "Cannot migrate conflicting activation declarations in "
                    f"{repo_legacy} and {marker_legacy}"
                )
            legacy_repo = {**legacy_repo, "enabled": value}

        global_doc = self._versioned(
            self._without_retired_update_check(
                self._with_global_defaults(
                    self._reconcile(existing_global, legacy_global, global_legacy)
                )
            )
        )
        repo_doc = self._versioned(
            self._without_retired_update_check(
                self._reconcile(existing_repo, legacy_repo, repo_legacy)
            )
        )
        if not existing_repo and not legacy_repo:
            repo_doc = self._versioned({**repo_doc, **self._REPO_DEFAULTS})

        created = tuple(
            dict.fromkeys(
                path
                for path, existed in (
                    (self.global_path, self.global_path.exists()),
                    (self.repo_path, self.repo_path.exists()),
                )
                if not existed
            )
        )
        if dry_run:
            return ConfigBootstrapResult(
                self.global_path, self.repo_path, legacy_paths, created, True
            )

        # A normal reinstall must only validate an existing unified document.
        # Re-serializing it would manufacture a backup on every install and
        # make a user's later edit collide with that old recovery snapshot.
        # Writes are reserved for bootstrap absence and the one legacy cutover.
        if self.global_path == self.repo_path:
            shared_doc = self._reconcile(global_doc, repo_doc, self.repo_path)
            target_documents = (
                (
                    self.repo_path,
                    shared_doc,
                    not self.repo_path.exists()
                    or global_legacy.exists()
                    or repo_legacy.exists()
                    or marker_legacy.exists(),
                ),
            )
        else:
            target_documents = (
                (
                    self.global_path,
                    global_doc,
                    not self.global_path.exists() or global_legacy.exists(),
                ),
                (
                    self.repo_path,
                    repo_doc,
                    not self.repo_path.exists()
                    or repo_legacy.exists()
                    or marker_legacy.exists(),
                ),
            )
        target_bytes = {
            path: self._json_bytes(document)
            for path, document, must_write in target_documents
            if must_write
        }
        old_targets = {
            path: path.read_bytes() if path.exists() else None for path in target_bytes
        }
        legacy_bytes = {path: path.read_bytes() for path in legacy_paths}

        try:
            for path, previous in old_targets.items():
                if previous is not None and previous != target_bytes[path]:
                    self._backup(path, previous)
            for path, previous in legacy_bytes.items():
                self._backup(path, previous)
            for path, content in target_bytes.items():
                if old_targets[path] != content:
                    self._atomic_write(path, content)
            if self.global_path == self.repo_path:
                self._validate_written(
                    self.repo_path,
                    shared_doc
                    if self.repo_path in target_bytes
                    else self._versioned(existing_repo),
                )
            else:
                self._validate_written(
                    self.global_path,
                    global_doc
                    if self.global_path in target_bytes
                    else self._versioned(existing_global),
                )
                self._validate_written(
                    self.repo_path,
                    repo_doc
                    if self.repo_path in target_bytes
                    else self._versioned(existing_repo),
                )
        except OSError as exc:
            self._restore_targets(old_targets)
            raise ConfigMigrationError(
                f"Could not write unified configuration: {exc}"
            ) from exc

        try:
            for path in legacy_paths:
                path.unlink()
        except OSError as exc:
            raise ConfigMigrationError(
                f"Unified config is valid but could not retire legacy file {path}; "
                f"its backup remains at {self._backup_path(path)}: {exc}"
            ) from exc

        return ConfigBootstrapResult(
            self.global_path, self.repo_path, legacy_paths, created, False
        )

    def update_global(self, mutate: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        """Bootstrap, mutate, validate and atomically replace the global authority."""
        legacy = self.global_dir / self._GLOBAL_LEGACY
        existing = self._read_object(self.global_path, role="unified config")
        legacy_document = self._read_object(legacy, role="legacy config")
        self._validate_supported_version(existing)
        self._validate_supported_version(legacy_document)
        document = self._versioned(
            self._with_global_defaults(
                self._reconcile(
                    existing,
                    legacy_document,
                    legacy,
                )
            )
        )
        mutate(document)
        return self._commit_authority(self.global_path, document, (legacy,))

    def update_repo(self, mutate: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        """Bootstrap, mutate, validate and atomically replace the repo authority."""
        legacy = self.repo_dir / self._REPO_LEGACY
        marker = self.repo_dir / self._MARKER_LEGACY
        existing = self._read_object(self.repo_path, role="unified config")
        legacy_document = self._read_object(legacy, role="legacy config")
        marker_document = self._read_object(marker, role="legacy marker")
        self._validate_supported_version(existing)
        self._validate_supported_version(legacy_document)
        if marker_document and "enabled_for_repo" in marker_document:
            value = marker_document["enabled_for_repo"]
            if not isinstance(value, bool):
                raise ConfigMigrationError(
                    f"Cannot migrate {marker}: enabled_for_repo must be a boolean"
                )
            if "enabled" in legacy_document and legacy_document["enabled"] != value:
                raise ConfigMigrationError(
                    "Cannot migrate conflicting activation declarations in "
                    f"{legacy} and {marker}"
                )
            legacy_document = {**legacy_document, "enabled": value}
        document = self._versioned(
            self._reconcile(
                existing,
                legacy_document,
                legacy,
            )
        )
        mutate(document)
        return self._commit_authority(self.repo_path, document, (legacy, marker))

    def set_repo_override(self, field: str, value: bool | str) -> dict[str, Any]:
        """Atomically publish one well-typed public project override.

        The repository tier intentionally has only three public override
        fields.  ``attribution`` is accepted as its public boolean value and
        stored in the merged reader's ``{"enabled": bool}`` shape; callers
        therefore cannot accidentally publish an untyped partial document.
        """
        if field == "enabled" and isinstance(value, bool):
            return self.update_repo(lambda document: document.update(enabled=value))
        if (
            field == "verbosity"
            and isinstance(value, str)
            and value in VERBOSITY_VALUES
        ):
            return self.update_repo(lambda document: document.update(verbosity=value))
        if field == "attribution" and isinstance(value, bool):
            return self.update_repo(
                lambda document: document.update(attribution={"enabled": value})
            )
        raise ValueError(f"Invalid project override: {field}={value!r}")

    def _feature_config_root(self) -> Path:
        """The repository-config root DES reads feature config from.

        From any subdirectory, ascend to the checkout root (first ``.git``
        entry), then apply the SAME resolver the reader uses so a linked
        worktree writes where DES reads.
        """
        from nwave_ai.platform.repository_config_root import (
            resolve_repository_config_root,
        )

        checkout = next(
            (
                d
                for d in (self._repo_root, *self._repo_root.parents)
                if (d / ".git").exists()
            ),
            self._repo_root,
        )
        return resolve_repository_config_root(checkout)

    def set_feature_document(
        self, feature_id: str, wave: str, destination: str
    ) -> Path:
        """Publish one FEATURE wave destination into the shared feature config.

        The file is ``<repo config root>/.nwave/features/<id>/config.json``
        and holds only ``documents``; the same pure law that resolves it at
        read time validates it before the atomic write.
        """
        from nwave_ai.platform.feature_documents import (
            WAVES,
            FeatureDocumentsInvalid,
            merge_feature_destinations,
            require_feature_id,
        )

        require_feature_id(feature_id)
        if wave not in WAVES:
            raise ValueError(f"wave must be one of {WAVES}")
        path = (
            self._feature_config_root()
            / ".nwave"
            / "features"
            / feature_id
            / "config.json"
        )
        document = self._read_object(path, role="feature config")
        documents = document.get("documents", {})
        if not isinstance(documents, dict):
            raise ConfigMigrationError(f"{path}: documents must be an object")
        documents = {**documents, wave: {"destination": destination}}
        try:
            # Validate against the SAME effective cascade the reader resolves
            # (feature_document_tiers), never the built-in defaults: a valid
            # override under a declared project template must not be refused
            # here, and an override the reader would refuse must not land.
            global_documents, project_documents = NWaveConfig(
                cwd=self._feature_config_root()
            ).feature_document_tiers(feature_id)
            merge_feature_destinations(
                feature_id,
                global_documents=global_documents,
                project_documents=project_documents,
                feature_documents=documents,
            )
        except FeatureDocumentsInvalid as error:
            raise ValueError(f"{error.why}; {error.how}") from error
        self._atomic_write(path, self._json_bytes({**document, "documents": documents}))
        return path

    def set_feature_template(self, wave: str, template: str) -> dict[str, Any]:
        """Publish a project-tier ``documents.feature.<wave>.destination`` template."""
        from nwave_ai.platform.feature_documents import (
            WAVES,
            FeatureDocumentsInvalid,
            merge_feature_destinations,
        )

        if wave not in WAVES:
            raise ValueError(f"wave must be one of {WAVES}")

        def mutate(document: dict[str, Any]) -> None:
            documents = document.get("documents")
            documents = dict(documents) if isinstance(documents, dict) else {}
            feature = dict(documents.get("feature") or {})
            feature[wave] = {"destination": template}
            documents["feature"] = feature
            try:
                # Same reader/writer tier kernel as set_feature_document: the
                # declared global tier participates exactly as it will when
                # the template resolves a real feature id.
                global_documents, _ = NWaveConfig(
                    cwd=self._feature_config_root()
                ).feature_document_tiers("probe")
                merge_feature_destinations(
                    "probe",
                    global_documents=global_documents,
                    project_documents=documents,
                )
            except FeatureDocumentsInvalid as error:
                raise ValueError(f"{error.why}; {error.how}") from error
            document["documents"] = documents

        return ConfigWriter(
            home_dir=self._home_dir, repo_root=self._feature_config_root()
        ).update_repo(mutate)

    def _commit_authority(
        self, path: Path, document: dict[str, Any], legacy_paths: tuple[Path, ...]
    ) -> dict[str, Any]:
        versioned = self._versioned(self._without_retired_update_check(document))
        old = path.read_bytes() if path.exists() else None
        legacy_bytes = {
            legacy: legacy.read_bytes() for legacy in legacy_paths if legacy.exists()
        }
        content = self._json_bytes(versioned)
        try:
            for legacy, legacy_content in legacy_bytes.items():
                self._backup(legacy, legacy_content)
            if old != content:
                self._atomic_write(path, content)
            self._validate_written(path, versioned)
        except OSError as exc:
            self._restore_targets({path: old})
            raise ConfigMigrationError(
                f"Could not write unified configuration: {exc}"
            ) from exc
        for legacy in legacy_bytes:
            try:
                legacy.unlink()
            except OSError as exc:
                raise ConfigMigrationError(
                    f"Unified config is valid but could not retire legacy file {legacy}; "
                    f"its backup remains at {self._backup_path(legacy)}: {exc}"
                ) from exc
        return versioned

    @staticmethod
    def _read_object(path: Path, *, role: str) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ConfigMigrationError(
                f"Cannot migrate {path}: invalid {role} JSON"
            ) from exc
        if not isinstance(raw, dict):
            raise ConfigMigrationError(
                f"Cannot migrate {path}: {role} must be a JSON object"
            )
        return raw

    @classmethod
    def _reconcile(
        cls, existing: dict[str, Any], legacy: dict[str, Any], legacy_path: Path
    ) -> dict[str, Any]:
        merged_overrides: dict[str, Any] = {}
        for key in existing.keys() & legacy.keys():
            if key in ("schema-version", "update_check"):
                continue
            if key == "attribution":
                merged_overrides["attribution"] = cls._reconcile_attribution(
                    existing[key], legacy[key], legacy_path
                )
                continue
            if existing[key] != legacy[key]:
                raise ConfigMigrationError(
                    f"Cannot migrate conflicting values in {legacy_path}: key {key!r} "
                    "already differs in config.json"
                )
        return {**legacy, **existing, **merged_overrides}

    @staticmethod
    def _attribution_translated(value: Any) -> Any:
        """Reuse ``des_config``'s public on/off translation (V4-24) so an
        attribution value is compared and merged by its real boolean
        meaning, not by its raw on-disk shape (string vs legacy dict).
        """
        return _translate_public_attribution({"attribution": value})["attribution"]

    @classmethod
    def _reconcile_attribution(
        cls, existing_value: Any, legacy_value: Any, legacy_path: Path
    ) -> Any:
        """Semantically reconcile one ``attribution`` field (V4-24).

        Both sides are translated through ``_translate_public_attribution``
        first, so ``"on"`` vs ``{"enabled": True}`` is the same fact rather
        than a raw-string/raw-dict false conflict. When both translate to a
        dict, every field the two sides SHARE must agree -- including a
        disagreeing ``trailer`` alongside a matching ``enabled`` -- and
        disjoint extra fields merge, preserving legacy's own extras. When
        either side does not translate to a dict (an unrecognised public
        value), an unknown shape is compared verbatim rather than treated as
        an absent, always-compatible fact.
        """
        translated_existing = cls._attribution_translated(existing_value)
        translated_legacy = cls._attribution_translated(legacy_value)
        if not (
            isinstance(translated_existing, dict)
            and isinstance(translated_legacy, dict)
        ):
            if existing_value != legacy_value:
                raise ConfigMigrationError(
                    f"Cannot migrate conflicting values in {legacy_path}: key "
                    "'attribution' already differs in config.json"
                )
            return existing_value
        for key in translated_existing.keys() & translated_legacy.keys():
            if translated_existing[key] != translated_legacy[key]:
                raise ConfigMigrationError(
                    f"Cannot migrate conflicting values in {legacy_path}: key "
                    f"'attribution.{key}' already differs in config.json"
                )
        legacy_extra = {
            k: v for k, v in translated_legacy.items() if k not in translated_existing
        }
        if not legacy_extra:
            return existing_value
        return {**translated_legacy, **translated_existing}

    @staticmethod
    def _without_retired_update_check(document: dict[str, Any]) -> dict[str, Any]:
        """Retire the inert preference only when publishing a config document."""
        return {key: value for key, value in document.items() if key != "update_check"}

    @classmethod
    def _with_global_defaults(cls, document: dict[str, Any]) -> dict[str, Any]:
        """Add only absent first-install defaults to the global authority.

        Existing user-owned values, including a deliberately malformed value,
        are retained for the reader's normal fail-safe handling; bootstrap does
        not silently repair or replace a declared preference.
        """
        result = dict(document)
        for key, value in cls._GLOBAL_DEFAULTS.items():
            if key not in result:
                result[key] = dict(value)
        return result

    @staticmethod
    def _versioned(document: dict[str, Any]) -> dict[str, Any]:
        try:
            return _GLOBAL_CONFIG_VERSIONING.upcast_to_current(
                document, _GLOBAL_CONFIG_ARTIFACT_TYPE
            )
        except ArtifactFromFutureRuntime as exc:
            raise ConfigMigrationError(str(exc)) from exc

    @staticmethod
    def _validate_supported_version(document: dict[str, Any]) -> None:
        """Refuse a source written by a runtime newer than this one.

        The kernel owns the project's version interpretation; this probe is
        deliberately performed for each input before the merge loses source
        provenance.  Its returned upcast is not used here because
        reconciliation must preserve the source fields until the canonical
        document is assembled.
        """
        ConfigWriter._versioned(document)

    @staticmethod
    def _json_bytes(document: dict[str, Any]) -> bytes:
        return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")

    def _backup_path(self, path: Path) -> Path:
        return path.with_name(f"{path.name}{self._BACKUP_SUFFIX}")

    def _backup(self, path: Path, content: bytes) -> None:
        backup = self._backup_path(path)
        if backup.exists():
            if backup.read_bytes() != content:
                raise ConfigMigrationError(
                    f"Cannot overwrite recovery backup {backup}; inspect it before retrying"
                )
            return
        self._atomic_write(backup, content)

    @staticmethod
    def _atomic_write(path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(path)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    def _validate_written(self, path: Path, expected: dict[str, Any]) -> None:
        actual = self._versioned(self._read_object(path, role="unified config"))
        if actual != expected:
            raise ConfigMigrationError(f"Validation failed after writing {path}")

    def _restore_targets(self, old_targets: dict[Path, bytes | None]) -> None:
        for path, previous in old_targets.items():
            try:
                if previous is None:
                    path.unlink(missing_ok=True)
                else:
                    self._atomic_write(path, previous)
            except OSError:
                # The adjacent backup is already the recovery authority.
                pass
