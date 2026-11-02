"""
DES Configuration Adapter - Driven Port Implementation.

Loads configuration from the unified global and repository ``config.json`` files.
Falls back to safe defaults (audit logging ON) when file is missing or invalid.

Hexagonal Architecture:
- DRIVEN ADAPTER: Implements configuration port (driven by business logic)
- ON BY DEFAULT: Audit logging enabled unless explicitly disabled in config
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from nwave_ai.platform.artifact_versioning import ArtifactVersioningKernel
from nwave_ai.platform.blast_radius import (
    BlastRadiusConfigRejected,
    BlastRadiusThresholds,
)
from nwave_ai.platform.config_merge import (
    declared_enabled,
    merge_config_with_sources,
    resolve_attribution,
)
from nwave_ai.platform.document_scope import (
    DocumentScope,
    Epic,
    Feature,
    Project,
    Slice,
)
from nwave_ai.platform.feature_documents import (
    DEFAULT_TEMPLATES,
    FeatureDocumentsInvalid,
    merge_feature_destinations,
    require_feature_id,
)
from nwave_ai.platform.locations import NWaveLocations, resolve_nwave_root
from nwave_ai.platform.repository_config_root import (
    resolve_repository_config_root,
)
from nwave_ai.platform.result import Failure
from nwave_ai.platform.roles import RoleRuntime, resolve_role_runtime


# Closed set of declarable deliverable types (ADR-PST-002). A declared value
# outside this set is treated as absent -> safe default (``None``).
_KNOWN_DELIVERABLE_TYPES = frozenset({"application", "plugin", "skill"})

# Positive deliverable markers from FS detection. ``"application"`` is the
# absence of a marker, so it resolves to the ``None`` sentinel, NOT itself.
_POSITIVE_DELIVERABLE_MARKERS = frozenset({"plugin", "skill"})

# ``config.json`` is the versioned persisted configuration artifact. v1's
# entire purpose is introducing the ``schema-version`` field itself -- the
# kernel stamps that field automatically once the chain runs, so the v0->v1
# upcaster body is an identity copy; there is no other shape change yet.
_GLOBAL_CONFIG_ARTIFACT_TYPE = "global-config"


def _global_config_v0_to_v1(doc: dict[str, Any]) -> dict[str, Any]:
    """v0 (no schema-version key) -> v1 (schema-version introduced). No other change."""
    return dict(doc)


_GLOBAL_CONFIG_VERSIONING = ArtifactVersioningKernel(
    upcasters={_GLOBAL_CONFIG_ARTIFACT_TYPE: (_global_config_v0_to_v1,)}
)

# Public on/off -> merge_config's internal {"enabled": bool} shape (ADR-CFG-001
# Slice 2, PublicStartRecipe step 1). ``config_merge.py`` itself stays untouched
# (REUSE_CANDIDATE): only the boundary's own tier dict is reshaped before the
# pure law's well-typed check ever sees it. Any other attribution shape (an
# already-well-typed dict, an unrecognized string, absent) passes through
# unchanged -- merge_config's own law decides what happens to it.
_ATTRIBUTION_PUBLIC_VALUES = {"on": True, "off": False}


def _translate_public_attribution(config: dict[str, Any]) -> dict[str, Any]:
    if "attribution" not in config:
        return config
    value = config["attribution"]
    # `value` must be checked as a str BEFORE any dict lookup/membership test:
    # `_ATTRIBUTION_PUBLIC_VALUES.get(value)` (or `value in _ATTRIBUTION_PUBLIC_VALUES`)
    # hashes `value` first, and a dict/list-shaped attribution (the legacy
    # pre-unification dict shape) is unhashable -- ``isinstance`` short-circuits
    # the `or` below before that hash ever happens, restoring totality for any
    # JSON value (ADR-CFG-002).
    if not isinstance(value, str) or value not in _ATTRIBUTION_PUBLIC_VALUES:
        return config
    return {**config, "attribution": {"enabled": _ATTRIBUTION_PUBLIC_VALUES[value]}}


@dataclass(frozen=True)
class VerificationReusePolicy:
    """One-decode view of the project ``verification.reuse`` block.

    ``outputs`` and ``workspace`` are decoded from the SAME raw bytes by
    ``NWaveConfig.verification_reuse_policy`` -- never mixed across two
    reads; ``None`` marks an undeclared field. Constructed only by that
    kernel; never cached.
    """

    outputs: tuple[str, ...] | None
    workspace: dict[str, Any] | None


class NWaveConfig:
    """
    Configuration loader for DES settings.

    Loads configuration from .nwave/config.json with on-by-default audit logging.
    Supports global configuration via ~/.nwave/config.json for cross-project
    rigor preferences. Does NOT auto-create config files.

    Rigor cascade: project rigor -> global rigor -> standard defaults.
    """

    # Explicit test-only override seam (`monkeypatch.setattr(NWaveConfig,
    # "_DEFAULT_GLOBAL_CONFIG_PATH", ...)`). ``None`` means "no override" --
    # the ordinary path is resolved dynamically below, never frozen at
    # import/class-definition time. A test that sets this to a concrete
    # ``Path`` wins over the dynamic ``NWaveLocations`` resolution entirely,
    # preserving the pre-existing explicit class-level override behaviour.
    _DEFAULT_GLOBAL_CONFIG_PATH: Path | None = None

    @staticmethod
    def _default_global_config_path() -> Path:
        """Resolve the NWAVE_AGENTS_HOME-aware unified config default.

        An explicit ``NWaveConfig._DEFAULT_GLOBAL_CONFIG_PATH`` override (set by
        a test via ``monkeypatch.setattr``) wins unconditionally. Otherwise
        the ordinary default is computed HERE, at construction time, through
        the same ``NWaveLocations.resolve`` agents-home channel ``nwave-ai
        mode`` writes through -- never a class-level ``Path.home()`` constant
        frozen once at module import. That freeze is exactly what let
        ``nwave-ai status`` keep reading the operator's real home after
        ``nwave-ai mode`` had already written a ``NWAVE_AGENTS_HOME``-
        isolated destination.

        Total, never raises: refusing a relative override before a write
        is ``NWaveInstaller``'s construction-time obligation, not this
        read-only loader's -- an invalid channel here degrades to the
        native home default instead of failing a read.
        """
        if NWaveConfig._DEFAULT_GLOBAL_CONFIG_PATH is not None:
            return NWaveConfig._DEFAULT_GLOBAL_CONFIG_PATH
        result = NWaveLocations.resolve(
            home=Path.home(),
            repo_root=Path.cwd(),
            agents_home_override=os.environ.get("NWAVE_AGENTS_HOME"),
            claude_config_override=os.environ.get("CLAUDE_CONFIG_DIR"),
            codex_config_override=os.environ.get("CODEX_HOME"),
        )
        agents_home = (
            Path.home() if isinstance(result, Failure) else result.unwrap().agents_home
        )
        return agents_home / ".nwave" / "config.json"

    def __init__(
        self,
        config_path: Path | None = None,
        cwd: Path | None = None,
        *,
        global_config_path: Path | None = None,
    ):
        """
        Initialize NWaveConfig.

        Args:
            config_path: Optional explicit path to project config file
            cwd: Optional working directory (defaults to Path.cwd());
                 used to resolve .nwave/config.json when config_path is None
            global_config_path: Optional explicit path to global config file
                (keyword-only; defaults to ~/.nwave/config.json)
        """
        if config_path is None:
            effective_cwd = cwd or resolve_nwave_root()
            # `effective_cwd` may be RELATIVE (e.g. `Path(".")`, exactly what
            # `--repo .` / `--repo-dir .` produce). `_nearest_marker`'s
            # ascend-loop walks up via `.parent` and stops when
            # `current == current.parent` -- but `Path(".").parent ==
            # Path(".")` is pathlib's own behaviour for the trivial relative
            # path, so an un-resolved relative cwd self-loops the exit check
            # on the FIRST iteration and the walk-up never inspects the real
            # repo root. Resolve to absolute HERE, before `_config_path` is
            # built, so every downstream consumer (including
            # `_nearest_marker`) always ascends real directories regardless
            # of whether the caller passed a relative or absolute cwd.
            #
            # CONFIGURATION FOLLOWS THE REPOSITORY. A git worktree checkout is
            # a distinct working directory of the SAME repository, so the
            # repository-root `.nwave/config.json` governs it too.
            # `resolve_repository_config_root` ascends git's own
            # `gitdir:`/`commondir` marker chain in pure Python (no `git`
            # binary) and returns the start directory UNCHANGED for an
            # ordinary checkout at any depth -- so this is the single place
            # the project config path is derived, and no call site moves.
            project_root = effective_cwd.resolve()
            config_path = (
                resolve_repository_config_root(project_root) / ".nwave" / "config.json"
            )
        else:
            # An explicitly supplied config_path is honoured verbatim and is
            # never re-resolved; its grandparent is the project root exactly
            # as every pre-existing consumer already derived it.
            project_root = config_path.parent.parent

        self._config_path = config_path
        # The EXECUTING checkout, kept distinct from `_config_path`'s
        # grandparent now that the config may live in another directory.
        # Under an ordinary checkout the two coincide, byte-for-byte as before.
        self._project_root = project_root
        self._config_data = self._load_json_file(self._config_path)

        global_path = (
            global_config_path
            if global_config_path is not None
            else self._default_global_config_path()
        )
        self._global_config_path = global_path
        self._global_config_data = self._load_versioned_global_config(
            self._global_config_path
        )
        # A present-but-unreadable tier may hold an explicit off; it must never
        # fall through to the default (ADR-CFG-005). See `resolve_attribution`.
        self._config_tier_unreadable = self._tier_unreadable(self._config_path)
        self._global_tier_unreadable = self._tier_unreadable(self._global_config_path)

    @staticmethod
    def feature_config_path(
        root: Path, feature_id: Epic | Feature | Slice | str
    ) -> Path:
        """Shared repository-config location of one feature's overrides."""
        base = NWaveConfig(cwd=root)._config_path.parent
        if isinstance(feature_id, Epic):
            return base / "epics" / feature_id.epic_id / "config.json"
        if isinstance(feature_id, (Feature, Slice)):
            feature_id = feature_id.feature_id
        require_feature_id(feature_id)
        return base / "features" / feature_id / "config.json"

    def feature_document_tiers(
        self, feature_id: Epic | Feature | Slice | str
    ) -> tuple[object, object]:
        """``(global_documents, project_documents)`` as feature destinations merge them.

        The ONE tier kernel shared by the reader
        (:meth:`feature_document_destinations`) and the writer
        (``ConfigWriter.set_feature_document``): a per-feature override is
        validated against the SAME effective cascade that later resolves it,
        never against the built-in defaults, so the writer can never refuse
        what the reader would accept. Epic templates enter through the same
        transformation on both sides.
        """
        if isinstance(feature_id, (Feature, Slice)):
            feature_id = feature_id.feature_id
        epic = feature_id if isinstance(feature_id, Epic) else None
        global_tier, repo_tier = self._unified_upcast_tiers()
        if epic is None:
            return global_tier.get("documents"), repo_tier.get("documents")

        def epic_tier(tier):
            documents = tier.get("documents", {})
            if not isinstance(documents, dict):
                raise FeatureDocumentsInvalid(
                    "EpicConfigMalformed",
                    "documents must be an object",
                    "repair the configuration",
                )
            block = documents.get("epic", {})
            if not isinstance(block, dict):
                raise FeatureDocumentsInvalid(
                    "EpicConfigMalformed",
                    "documents.epic must be an object",
                    "repair the configuration",
                )
            templates = {
                wave: {"destination": path.replace("docs/feature/", "docs/epic/")}
                for wave, path in DEFAULT_TEMPLATES.items()
            }
            for wave, entry in block.items():
                if (
                    wave not in templates
                    or not isinstance(entry, dict)
                    or set(entry) != {"destination"}
                ):
                    raise FeatureDocumentsInvalid(
                        "EpicConfigMalformed",
                        "invalid epic wave configuration",
                        "supply a wave destination template",
                    )
                template = entry["destination"]
                if not isinstance(template, str) or "{epic}" not in template:
                    raise FeatureDocumentsInvalid(
                        "InvalidEpicTemplate",
                        "epic template must contain {epic}",
                        "include {epic} in the destination",
                    )
                templates[wave] = {
                    "destination": template.replace("{epic}", "{feature}")
                }
            return {"documents": {**documents, "feature": templates}}

        # Defaults enter once; project overrides preserve global epic values.
        global_tier = epic_tier(global_tier)
        merged_epic = dict(global_tier["documents"]["feature"])
        project_epic = repo_tier.get("documents", {}).get("epic", {})
        project_tier = epic_tier(repo_tier)
        for wave in project_epic:
            merged_epic[wave] = project_tier["documents"]["feature"][wave]
        repo_tier = {"documents": {**project_tier["documents"], "feature": merged_epic}}
        return global_tier.get("documents"), repo_tier.get("documents")

    @staticmethod
    def feature_document_destinations(
        root: Path, feature_id: Epic | Feature | Slice | str
    ) -> dict[str, str]:
        """Resolve every wave's FEATURE destination or raise FeatureDocumentsInvalid.

        A selected feature file that is present but corrupt is refused, never
        treated as absent; a destination crossing a symlink is refused before
        any producer writes.
        """
        if isinstance(feature_id, (Feature, Slice)):
            feature_id = feature_id.feature_id
        epic = feature_id if isinstance(feature_id, Epic) else None
        config = NWaveConfig(cwd=root)
        # The tier kernel receives the ORIGINAL scope (Epic included): the
        # epic template transformation must apply exactly as it did when it
        # lived inline -- calling it after the id was unwrapped to a string
        # silently skipped the transformation and routed epic documents
        # into the wrong namespace.
        global_documents, project_documents = config.feature_document_tiers(feature_id)
        path = NWaveConfig.feature_config_path(root, feature_id)
        if epic is not None:
            feature_id = epic.epic_id
        feature_documents: object = None
        if path.exists():
            try:
                parsed = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
                raise FeatureDocumentsInvalid(
                    "FeatureConfigMalformed",
                    f"{path} cannot be read as JSON: {error}",
                    "repair the file or set it with nwave-ai project feature-document",
                ) from error
            if not isinstance(parsed, dict) or not set(parsed) <= {
                "documents",
                "schema-version",
            }:
                raise FeatureDocumentsInvalid(
                    "FeatureConfigMalformed",
                    "a feature config holds only a documents object",
                    "remove other keys from the feature config",
                )
            feature_documents = parsed.get("documents", {})
            if not isinstance(feature_documents, dict):
                raise FeatureDocumentsInvalid(
                    "FeatureConfigMalformed",
                    "documents must be an object",
                    "repair the feature config",
                )
        resolved = merge_feature_destinations(
            feature_id,
            global_documents=global_documents,
            project_documents=project_documents,
            feature_documents=feature_documents,
        )
        top = root.resolve()
        for destination in resolved.values():
            current = root
            for part in destination.split("/"):
                current = current / part
                if current.is_symlink() or (
                    current.exists() and not current.resolve().is_relative_to(top)
                ):
                    raise FeatureDocumentsInvalid(
                        "FeatureDestinationSymlink",
                        f"{destination} crosses a symlink at {part}",
                        "use a real repository-local directory",
                    )
        return resolved

    @staticmethod
    def design_document_destination(
        root: Path, feature_id: DocumentScope | str | None = None
    ) -> str | None:
        """Resolve DESIGN's destination from the existing effective config."""
        if isinstance(feature_id, Project):
            feature_id = None
        if feature_id is not None:
            return NWaveConfig.feature_document_destinations(root, feature_id)["design"]
        documents = NWaveConfig(cwd=root).effective_config().get("documents")
        design = documents.get("design") if isinstance(documents, dict) else None
        value = design.get("destination") if isinstance(design, dict) else None
        return (
            value
            if isinstance(value, str) and value.strip()
            else "docs/product/architecture/brief.md"
        )

    @staticmethod
    def operational_document_destination(
        root: Path, feature_id: DocumentScope | str | None = None
    ) -> str | None:
        """Resolve DEVOPS's destination through the same effective cascade."""
        if isinstance(feature_id, Project):
            feature_id = None
        if feature_id is not None:
            return NWaveConfig.feature_document_destinations(root, feature_id)["devops"]
        documents = NWaveConfig(cwd=root).effective_config().get("documents")
        devops = documents.get("devops") if isinstance(documents, dict) else None
        value = devops.get("destination") if isinstance(devops, dict) else None
        return (
            value
            if isinstance(value, str) and value.strip()
            else "docs/product/operations/brief.md"
        )

    @staticmethod
    def evolution_document_destination(root: Path, date: str, feature_id: str) -> str:
        documents = NWaveConfig(cwd=root).effective_config().get("documents")
        evolution = documents.get("evolution") if isinstance(documents, dict) else None
        value = evolution.get("destination") if isinstance(evolution, dict) else None
        return (
            value
            if isinstance(value, str) and value.strip()
            else f"docs/evolution/{date}-{feature_id}.md"
        )

    @staticmethod
    def discuss_document_destination(
        root: Path, feature_id: DocumentScope | str | None = None
    ) -> str:
        if isinstance(feature_id, Project):
            feature_id = None
        if feature_id is not None:
            return NWaveConfig.feature_document_destinations(root, feature_id)[
                "discuss"
            ]
        documents = NWaveConfig(cwd=root).effective_config().get("documents")
        discuss = documents.get("discuss") if isinstance(documents, dict) else None
        value = discuss.get("destination") if isinstance(discuss, dict) else None
        return (
            value
            if isinstance(value, str) and value.strip()
            else "docs/product/brief.md"
        )

    @staticmethod
    def distill_document_destination(
        root: Path, feature_id: DocumentScope | str | None = None
    ) -> str:
        if isinstance(feature_id, Project):
            feature_id = None
        if feature_id is not None:
            return NWaveConfig.feature_document_destinations(root, feature_id)[
                "distill"
            ]
        documents = NWaveConfig(cwd=root).effective_config().get("documents")
        distill = documents.get("distill") if isinstance(documents, dict) else None
        value = distill.get("destination") if isinstance(distill, dict) else None
        return (
            value
            if isinstance(value, str) and value.strip()
            else "docs/product/acceptance/brief.md"
        )

    @staticmethod
    def _load_json_file(path: Path) -> dict[str, Any]:
        """
        Load configuration from a JSON file.

        Returns empty dict when the file is missing, corrupt, or unreadable.
        Pure function: no side effects beyond filesystem read.

        Args:
            path: Path to the JSON file to load

        Returns:
            Configuration dictionary, empty dict if loading fails
        """
        if not path.exists():
            return {}

        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            return {}
        # Valid JSON that is not an object (``null``, ``[]``, ``123``, ``"x"``)
        # would crash every ``.get(...)`` caller. Coerce to ``{}`` so callers
        # fail open to safe defaults rather than raising on a malformed config.
        return parsed if isinstance(parsed, dict) else {}

    @staticmethod
    def _load_versioned_global_config(path: Path) -> dict[str, Any]:
        """Load a unified ``config.json`` tier through the versioning kernel.

        A genuinely ABSENT file stays ``{}`` (no phantom schema-version is
        fabricated for a file that does not exist) -- the kernel only runs
        over content that was actually read from disk, mirroring
        ``_config_present_and_parseable``'s existing missing-vs-malformed
        split elsewhere in this class. A present file -- versioned already,
        legacy/unversioned, or malformed-to-``{}`` -- is upcast to the
        current ``global-config`` shape, so every downstream ``.get(...)``
        cascade in this class keeps reading the latest shape regardless of
        which release wrote the file.
        """
        data = NWaveConfig._load_json_file(path)
        if not path.exists():
            return data
        return _GLOBAL_CONFIG_VERSIONING.upcast_to_current(
            data, _GLOBAL_CONFIG_ARTIFACT_TYPE
        )

    @property
    def skill_tracking_enabled(self) -> bool:
        """
        Check if skill loading tracking is enabled.

        Priority: DES_SKILL_TRACKING env var > config file > default (False).

        Returns:
            True if skill tracking enabled, False otherwise (defaults to False)
        """
        env_override = os.environ.get("DES_SKILL_TRACKING")
        if env_override is not None:
            return env_override.lower() in ("true", "1", "yes")
        strategy = self._config_data.get("skill_tracking", "disabled")
        return strategy != "disabled"

    @property
    def skill_tracking_strategy(self) -> str:
        """
        Get skill tracking strategy.

        Returns:
            Strategy string: "disabled", "passive-logging", or "token-tracking"
        """
        return self._config_data.get("skill_tracking", "disabled")

    @property
    def coverage_map_adoption(self) -> str:
        """Repo-wide coverage-map adoption switch: ``"active"`` | ``"inactive"``.

        fix-feature-end-ws-gate-applicability slice-04 (DDD-3). The feature-end
        cycle reads this from ``repo_root/.nwave/config.json`` (the SAME
        repo-level path no individual feature can shadow -- the LOAD-BEARING
        un-per-feature-gameability invariant) to decide whether an absent
        ``distill/coverage-map.md`` may be granted NOT_APPLICABLE.

        Two failure modes degrade in OPPOSITE directions (CONCERN-2): a key that
        is ABSENT from a present-and-parseable config ⇒ ``"inactive"`` (the
        permissive NA, the designed 0/74 pre-adoption default); a config file
        that is MALFORMED / unreadable ⇒ ``"active"`` (hard-verify, degrade
        toward MORE rigour -- an unreadable switch must never silently grant NA).

        The standard ``_load_json_file`` collapses absent and corrupt files to
        ``{}`` (it cannot itself distinguish them), so this property closes the
        gap with an explicit present-and-parseable pre-check rather than reading
        an empty load as "key absent". No second full read path is forked: the
        pre-check only classifies success vs failure of the SAME config file.
        """
        if not self._config_present_and_parseable():
            return "active"
        value = self._config_data.get("coverage_map_adoption", "inactive")
        return value if isinstance(value, str) else "inactive"

    def _config_present_and_parseable(self) -> bool:
        """True iff the project config file exists and parses as a JSON object.

        Distinguishes "key absent" (file present + parseable, returns True) from
        "file malformed/unreadable" (returns False) -- the
        ``_load_json_file:85-91`` absent==corrupt collapse the coverage-map
        adoption switch must NOT conflate. An absent file is also treated as
        present-and-parseable (no config ⇒ the designed inactive default), so
        ONLY a genuinely malformed/unreadable present file returns False.
        """
        if not self._config_path.exists():
            return True
        try:
            json.loads(self._config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return False
        return True

    @property
    def audit_logging_enabled(self) -> bool:
        """
        Check if audit logging is enabled.

        Priority: DES_AUDIT_LOGGING_ENABLED env var > config file > default (True).

        Returns:
            True if audit logging enabled, False otherwise (defaults to True)
        """
        env_override = os.environ.get("DES_AUDIT_LOGGING_ENABLED")
        if env_override is not None:
            return env_override.lower() in ("true", "1", "yes")
        return self._config_data.get("audit_logging_enabled", True)

    # ------------------------------------------------------------------
    # Activation gating (EXTEND, ADR-AG-002 / DDD-3).
    # ``activation_mode`` reads ``activation.mode`` from the global unified
    # config (default ``"opt-in"``). ``enabled_for_repo`` returns the
    # declared enablement opinion across the two unified tiers -- ``None``
    # when no tier declares one.
    # Both fail-to-default; neither mutates.
    # ------------------------------------------------------------------

    @property
    def activation_mode(self) -> str:
        """Global ``activation.mode`` (``"opt-in"`` | ``"all"``); default ``"opt-in"``."""
        activation = self._global_config_data.get("activation", {})
        if not isinstance(activation, dict):
            return "opt-in"
        mode = activation.get("mode", "opt-in")
        return mode if mode in ("opt-in", "all") else "opt-in"

    @property
    def enabled_for_repo(self) -> bool | None:
        """The DECLARED per-repo enablement opinion, or ``None`` for no opinion.

        TRI-STATE (P-SSOT-1 P5-bis). The first tier that explicitly declares a
        well-typed bool wins, in the ONE precedence chain
        :func:`nwave_ai.platform.config_merge.declared_enabled` owns:

        1. ``<repo>/.nwave/config.json`` -> ``enabled``;
        2. ``~/.nwave/config.json`` -> ``enabled``.

        ``None`` (no tier has an opinion) is REQUIRED, not incidental: it is
        the input on which ``activation_policy.resolve_activation`` defers to
        the global ``activation.mode``. Collapsing it to a ``bool`` (the
        ADR-CFG-001 Slice-2 shape this replaces) made that ``mode`` branch
        unreachable and left the ADR-AG-002 truth table decidable only by
        ``ENABLED_DEFAULT`` -- ``F-ADR-AG-002-TRUTH-TABLE-BROKEN-BOTH-DEFAULTS``.

        :meth:`effective_config` still reports a plain ``bool`` for the same
        chain, substituting ``ENABLED_DEFAULT`` for ``None`` -- the two never
        disagree where an opinion exists.
        """
        global_upcast, repo_upcast = self._unified_upcast_tiers()
        return declared_enabled(global_upcast, repo_upcast)

    def _unified_upcast_tiers(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """Load and version-upcast the two unified ``config.json`` tiers.

        Reads ``~/.nwave/config.json`` and ``<repo>/.nwave/config.json``,
        upcasts each raw dict through the existing
        ``_GLOBAL_CONFIG_VERSIONING`` kernel (REUSE_CANDIDATE -- no second
        kernel instance), then translates each through
        ``_translate_public_attribution``. Shared by ``effective_config`` and
        ``attribution_enabled`` -- one read/translate kernel, not two. Never
        raises: a missing, corrupt, or non-object file at either tier
        collapses to ``{}``, exactly the existing ``_load_json_file``
        fail-open convention.
        """
        global_upcast = self._global_config_data
        repo_upcast = self._config_data
        return (
            _translate_public_attribution(global_upcast),
            _translate_public_attribution(repo_upcast),
        )

    @staticmethod
    def _tier_unreadable(path: Path) -> bool:
        """True when a tier file exists but is not a readable JSON object.

        Absent is not unreadable. Corrupt, non-UTF-8, unreadable or non-object
        content is: its declaration is unknown (ADR-CFG-005 fail-safe).
        """
        try:
            if not path.exists():
                return False
            parsed = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            return True
        return not isinstance(parsed, dict)

    def role_runtime(
        self, role_id: str, *, framework_root: Path | None = None
    ) -> RoleRuntime:
        """Return the atomically selected provider/model for ``role_id``.

        Unlike the existing three-field configuration merge, model selection
        cannot merge individual fields across tiers: an operator's provider and
        model are one runtime declaration.  A present malformed declaration is
        therefore surfaced by ``resolve_role_runtime`` rather than skipped.
        """
        global_tier, repo_tier = self._unified_upcast_tiers()
        return resolve_role_runtime(
            role_id,
            global_tier=global_tier,
            repo_tier=repo_tier,
            repo_root=self._project_root,
            framework_root=framework_root,
        )

    def _verification_reuse(self) -> dict[str, Any] | None:
        """The project ``verification.reuse`` block, or ``None`` when absent.

        One read/shape kernel for every reuse key: the same file, the same
        error algebra, the same repo-tier-only stance -- global preferences
        cannot grant ownership over this repository's directories.
        """
        try:
            project = json.loads(self._config_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, ValueError) as error:
            raise ValueError(
                f"cannot read project verification policy at {self._config_path}: {error}"
            ) from error
        if not isinstance(project, dict):
            raise ValueError(f"{self._config_path} must contain a JSON object")
        if "verification" not in project:
            return None
        verification = project["verification"]
        if not isinstance(verification, dict):
            raise ValueError("verification must be an object")
        if "reuse" not in verification:
            return None
        reuse = verification["reuse"]
        if not isinstance(reuse, dict) or not set(reuse) <= {"outputs", "workspace"}:
            raise ValueError(
                "verification.reuse must contain only outputs and workspace"
            )
        return reuse

    def verification_reuse_policy(self) -> "VerificationReusePolicy | None":
        """Decode the project ``verification.reuse`` block exactly once.

        One read, one JSON parse, one validation pass: outputs and
        workspace are a single kernel view and can never mix bytes from
        two reads (F6). Returns ``None`` when no reuse policy is declared.
        Never cached -- every call re-reads the live file, so live read
        contexts keep their existing semantics. The per-field properties
        delegate here, so their error behaviour is byte-identical.
        """
        reuse = self._verification_reuse()
        if reuse is None:
            return None
        outputs: tuple[str, ...] | None = None
        if "outputs" in reuse:
            declared_outputs = reuse["outputs"]
            if (
                not isinstance(declared_outputs, list)
                or not declared_outputs
                or any(
                    not isinstance(path, str) or not path for path in declared_outputs
                )
                or len(set(declared_outputs)) != len(declared_outputs)
            ):
                raise ValueError(
                    "verification.reuse.outputs must be a nonempty list of "
                    "distinct repository-relative generated directories"
                )
            outputs = tuple(declared_outputs)
        workspace: dict[str, Any] | None = None
        if "workspace" in reuse:
            raw = reuse["workspace"]
            if not isinstance(raw, dict):
                raise ValueError("verification.reuse.workspace must be an object")
            unknown = set(raw) - {
                "root",
                "cache_limit_bytes",
                "automatic",
                "adopt_outputs",
            }
            if unknown:
                raise ValueError(
                    "verification.reuse.workspace has unsupported keys: "
                    f"{sorted(unknown)}"
                )
            workspace = {}
            if "root" in raw:
                value = raw["root"]
                if not isinstance(value, str) or not value:
                    raise ValueError(
                        "verification.reuse.workspace.root must be a nonempty string"
                    )
                workspace["root"] = value
            if "cache_limit_bytes" in raw:
                value = raw["cache_limit_bytes"]
                if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                    raise ValueError(
                        "verification.reuse.workspace.cache_limit_bytes must "
                        "be a positive integer"
                    )
                workspace["cache_limit_bytes"] = value
            if "automatic" in raw:
                value = raw["automatic"]
                if not isinstance(value, bool):
                    raise ValueError(
                        "verification.reuse.workspace.automatic must be a boolean"
                    )
                workspace["automatic"] = value
            if "adopt_outputs" in raw:
                value = raw["adopt_outputs"]
                if (
                    not isinstance(value, list)
                    or not value
                    or any(not isinstance(entry, str) or not entry for entry in value)
                    or len(set(value)) != len(value)
                ):
                    raise ValueError(
                        "verification.reuse.workspace.adopt_outputs must be a "
                        "nonempty list of distinct repository-relative "
                        "directories"
                    )
                workspace["adopt_outputs"] = list(value)
        return VerificationReusePolicy(outputs=outputs, workspace=workspace)

    @property
    def verification_reuse_outputs(self) -> tuple[str, ...] | None:
        """Project-owned output roots; global preferences cannot grant ownership."""
        policy = self.verification_reuse_policy()
        return None if policy is None else policy.outputs

    @property
    def verification_reuse_workspace(self) -> dict[str, Any] | None:
        """Project-owned workspace placement; global preferences cannot grant ownership.

        Delegates to :meth:`verification_reuse_policy` -- the one-decode
        kernel -- so outputs and workspace are never read from different
        raw bytes. Key meanings live with the path algebra in
        ``workspace_paths.resolve_workspace_paths``.
        """
        policy = self.verification_reuse_policy()
        return None if policy is None else policy.workspace

    def effective_config(self) -> dict[str, Any]:
        """Merge the global and per-repo unified ``config.json`` tiers.

        The values of :meth:`effective_config_with_sources`, without provenance.

        The installer migrates legacy state before construction, so this
        reader has exactly two inputs and no compatibility tail.
        """
        return self.effective_config_with_sources()[0]

    def effective_config_with_sources(
        self,
    ) -> tuple[dict[str, Any], dict[str, str]]:
        """Read effective config and its per-field project/global/default provenance.

        Every field resolves through ``config_merge.merge_config_with_sources``
        except ``attribution``, which resolves through the one fail-safe decision
        ``config_merge.resolve_attribution`` (ADR-CFG-005). The value and its
        source name the tier that actually decided it.
        """
        global_upcast, repo_upcast = self._unified_upcast_tiers()
        values, sources = merge_config_with_sources(global_upcast, repo_upcast)
        values["attribution"], sources["attribution"] = resolve_attribution(
            global_upcast,
            repo_upcast,
            global_unreadable=self._global_tier_unreadable,
            repo_unreadable=self._config_tier_unreadable,
        )
        return values, sources

    @property
    def attribution_enabled(self) -> bool:
        """Resolved ``attribution.enabled`` (ADR-CFG-003 correction 1, ADR-CFG-005).

        Repo tier, then global tier, then the single ``ATTRIBUTION_DEFAULT`` (on).
        An explicit off in any tier wins. Never raises; a missing tier is
        undeclared, and an unreadable tier fails safe to off (see
        ``config_merge.resolve_attribution``).
        """
        return self.effective_config()["attribution"]

    @property
    def deliverable_type(self) -> str | None:
        """Resolved project deliverable type (ADR-PST-002) -- RED scaffold.

        DISTILL scaffold (feature plugin-skill-deliverable-type, issue #66).
        Resolution precedence (first match wins), implemented by DELIVER:
          1. declared ``.nwave/config.json`` -> ``deliverable_type`` (if in
             the known set ``{application, plugin, skill}``);
          2. declared global ``~/.nwave/config.json`` ->
             ``defaults.deliverable_type``;
          3. root-only FS detection (``deliverable_type_detector``) -- fallback
             ONLY when the declaration is FULLY ABSENT;
          4. unknown / typo'd declared value (present-but-bad, project OR global)
             -> SAFE DEFAULT (enforcement ON; returns ``None``) + a config-load
             warning. It does NOT fall through to detection (revised 2026-06-26,
             review non-blocker 2). Mirrors the ``activation_mode`` pattern
             (``des_config.py``: bad value -> hardcoded safe default, no detection
             fallback). A typo'd repo with a root ``skills/`` dir therefore stays
             enforced -- detection must not silently rescue a malformed declaration.

        Returns ``None`` (NOT ``"application"``) when nothing resolves -- the
        unresolved state is distinguishable from a positive ``application``
        declaration (HIGH-1 adapter contract). The enforcement fail-safe does NOT
        depend on this return value: the policy's closed exempt set
        (ADR-PST-001) is the load-bearing guarantee.

        Pure read over a bounded universe ``{declared_project, declared_global,
        ROOT-ONLY dir_listing}`` -- never mutates, never recurses nested dirs.

        Implemented to date (steps 01-01 + 01-03 -- positive resolution path):
          - project declaration in the known set -> that value (authoritative);
          - project declaration PRESENT-but-bad (typo'd) -> safe default ``None``,
            WITHOUT falling through (a malformed declaration is never silently
            rescued -- the typo fail-safe edge is finalised in step 03-02);
          - project declaration ABSENT -> fall through to the global
            ``defaults.deliverable_type`` (machine-wide default);
          - global default in the known set -> that value;
          - nothing resolves -> ``None``.
        Root-only FS detection (precedence step 3) is phase 02 -- the seam is the
        fall-through that currently terminates at ``None`` once the global default
        is exhausted; detection slots in there without disturbing the declared
        branches above.
        """
        declared = self._config_data.get("deliverable_type")
        if declared is not None:
            # Present -> the project's word is authoritative (good or typo'd);
            # a typo'd value never falls through to the global default.
            return declared if declared in _KNOWN_DELIVERABLE_TYPES else None
        # Project silent: the machine-wide default stands in (precedence step 2).
        defaults = self._global_config_data.get("defaults", {})
        global_default = (
            defaults.get("deliverable_type") if isinstance(defaults, dict) else None
        )
        if global_default in _KNOWN_DELIVERABLE_TYPES:
            return global_default
        # Nothing declared (project or global): fall through to root-only FS
        # detection (precedence step 3, ADR-PST-002). Reached ONLY when the
        # declaration is FULLY ABSENT -- a present-but-typo'd value short-circuits
        # to ``None`` above and never arrives here.
        return self._detect_deliverable_type()

    def _detect_deliverable_type(self) -> str | None:
        """Root-only FS detection rung; ``None`` for an unmarked (application) tree.

        Delegates to ``deliverable_type_detector`` over the project root (the
        ``.nwave/config.json``'s grandparent). An ``"application"`` detection
        means "no positive marker" -> ``None`` (HIGH-1: the unresolved sentinel,
        distinguishable from a declared ``application``). A positive
        ``plugin``/``skill`` marker resolves to that type.
        """
        from nwave_ai.platform.deliverable_type import (
            detect_deliverable_type,
        )

        detected = detect_deliverable_type(self._project_root)
        # Only a POSITIVE marker resolves; an ``"application"`` detection means
        # "no positive marker" -> ``None`` (HIGH-1 sentinel). Using
        # ``_KNOWN_DELIVERABLE_TYPES`` here would wrongly return ``"application"``.
        return detected if detected in _POSITIVE_DELIVERABLE_MARKERS else None

    def _housekeeping(self) -> dict:
        """Return housekeeping sub-config dict, defaulting to empty dict."""
        return self._config_data.get("housekeeping", {})

    @property
    def housekeeping_enabled(self) -> bool:
        """Check if housekeeping is enabled. Default: True."""
        return self._housekeeping().get("enabled", True)

    @property
    def housekeeping_audit_retention_days(self) -> int:
        """Get audit log retention period in days. Default: 7."""
        return self._housekeeping().get("audit_retention_days", 7)

    @property
    def housekeeping_signal_staleness_hours(self) -> int:
        """Get signal file staleness threshold in hours. Default: 4."""
        return self._housekeeping().get("signal_staleness_hours", 4)

    @property
    def housekeeping_skill_log_max_bytes(self) -> int:
        """Get maximum skill log size in bytes before rotation. Default: 1 MiB."""
        return self._housekeeping().get("skill_log_max_bytes", 1_048_576)

    # ------------------------------------------------------------------
    # Blast-radius thresholds (EXTEND, feature blast-radius-measured-tier
    # slice-02). `_blast_radius()` is a sibling cascade to `_rigor()` /
    # `_housekeeping()`: project -> global -> empty dict, full-block
    # override (a project `blast_radius` key -- even empty -- shadows the
    # entire global block, same discipline as `_rigor()`).
    #
    # Per-key resolution (feature-delta "Floor/ceiling validation"):
    #   - ABSENT key -> the canonical hardcoded default, unchanged.
    #   - PRESENT but WRONG TYPE -> the canonical default (malformed, not
    #     deliberate -- mirrors `_scan_atdd_pure_int`'s non-int-degrades
    #     precedent in `carpaccio_format.py`).
    #   - PRESENT, well-typed, OUTSIDE its floor/ceiling -> HARD FAIL
    #     (`BlastRadiusConfigRejected`, GDP-3/GDP-6) -- never a silent
    #     clamp, never a silent fallback.
    # ------------------------------------------------------------------

    _BLAST_RADIUS_DEFAULTS = BlastRadiusThresholds()

    def _blast_radius(self) -> dict[str, Any]:
        """Return blast_radius sub-config via cascade: project -> global -> {}."""
        if "blast_radius" in self._config_data:
            return cast("dict[str, Any]", self._config_data["blast_radius"])
        return cast("dict[str, Any]", self._global_config_data.get("blast_radius", {}))

    def _resolve_blast_radius_int(
        self, key: str, default: int, *, floor: int, ceiling: int
    ) -> int:
        """Resolve one numeric `blast_radius.<key>` threshold (see class docstring)."""
        block = self._blast_radius()
        if key not in block:
            return default
        value = block[key]
        if not isinstance(value, int) or isinstance(value, bool):
            return default
        if value < floor or value > ceiling:
            raise BlastRadiusConfigRejected(
                f"blast_radius.{key}={value} in .nwave/config.json is "
                f"outside its valid range [{floor}, {ceiling}] -- fix the "
                f"value, or remove the key to use the framework default "
                f"({default})"
            )
        return value

    @property
    def blast_radius_small_max_files(self) -> int:
        """Threshold `blast_radius.small_max_files`. Floor 1, ceiling 20."""
        return self._resolve_blast_radius_int(
            "small_max_files",
            self._BLAST_RADIUS_DEFAULTS.small_max_files,
            floor=1,
            ceiling=20,
        )

    @property
    def blast_radius_small_max_lines(self) -> int:
        """Threshold `blast_radius.small_max_lines`. Floor 1, ceiling 500."""
        return self._resolve_blast_radius_int(
            "small_max_lines",
            self._BLAST_RADIUS_DEFAULTS.small_max_lines,
            floor=1,
            ceiling=500,
        )

    @property
    def blast_radius_small_max_consumers(self) -> int:
        """Threshold `blast_radius.small_max_consumers`. Floor 1, ceiling 50."""
        return self._resolve_blast_radius_int(
            "small_max_consumers",
            self._BLAST_RADIUS_DEFAULTS.small_max_consumers,
            floor=1,
            ceiling=50,
        )

    @property
    def blast_radius_large_min_consumers(self) -> int:
        """Threshold `blast_radius.large_min_consumers`.

        Floor is DYNAMIC: `small_max_consumers + 1` (the resolved value, not
        the canonical constant) -- the M band between them must never
        collapse to empty. Ceiling 1000.

        The floor is enforced against the EFFECTIVE resolved value, whether
        it came from an explicit config entry or fell through to the
        canonical default -- `_resolve_blast_radius_int` alone only checks
        the floor on the explicit-value path, so an ABSENT (or malformed)
        `large_min_consumers` key whose silent default now conflicts with an
        explicitly-raised `small_max_consumers` would otherwise slip through
        as a silently incoherent pair (D7).
        """
        small_max = self.blast_radius_small_max_consumers
        floor = small_max + 1
        value = self._resolve_blast_radius_int(
            "large_min_consumers",
            self._BLAST_RADIUS_DEFAULTS.large_min_consumers,
            floor=floor,
            ceiling=1000,
        )
        if value < floor:
            small_source = self._blast_radius_key_source("small_max_consumers")
            large_source = self._blast_radius_key_source("large_min_consumers")
            raise BlastRadiusConfigRejected(
                f"blast_radius.small_max_consumers={small_max} (effective, "
                f"{small_source}) and blast_radius.large_min_consumers="
                f"{value} (effective, {large_source}) in "
                ".nwave/config.json are incoherent -- large_min_consumers "
                "must be strictly greater than small_max_consumers so the M "
                "band never collapses to empty. Fix: raise "
                "blast_radius.large_min_consumers above "
                f"{small_max} in .nwave/config.json, or lower "
                "blast_radius.small_max_consumers."
            )
        return value

    def _blast_radius_key_source(self, key: str) -> str:
        """Report whether `blast_radius.<key>`'s effective value is explicit
        config or the canonical default -- for GDP-3 rejection messages."""
        block = self._blast_radius()
        if key not in block:
            return "its canonical default"
        raw = block[key]
        if not isinstance(raw, int) or isinstance(raw, bool):
            return "its canonical default (configured value malformed)"
        return "configured"

    @property
    def blast_radius_boundary_globs(self) -> tuple[str, ...]:
        """`blast_radius.boundary_globs` -- TYPE-only validation (feature-delta).

        A non-list, empty list, or a list containing any non-string/empty
        entry is malformed and falls back to the canonical default list
        WHOLESALE (never a partial/filtered list). A well-typed list
        REPLACES the default wholesale (D5) -- never merged/appended.
        """
        block = self._blast_radius()
        value = block.get("boundary_globs")
        if (
            isinstance(value, list)
            and value
            and all(isinstance(entry, str) and entry for entry in value)
        ):
            return tuple(value)
        return self._BLAST_RADIUS_DEFAULTS.boundary_globs

    def resolve_blast_radius_thresholds(self) -> BlastRadiusThresholds:
        """Assemble the full `BlastRadiusThresholds` from the cascade above.

        Raises `BlastRadiusConfigRejected` (propagated from any of the four
        numeric properties) when a present, well-typed value breaches its
        floor/ceiling -- the caller (the application-layer measurement
        orchestration) lets this propagate to the CLI's `BlastRadiusConfigRejected`
        handler unchanged.
        """
        return BlastRadiusThresholds(
            small_max_files=self.blast_radius_small_max_files,
            small_max_lines=self.blast_radius_small_max_lines,
            small_max_consumers=self.blast_radius_small_max_consumers,
            large_min_consumers=self.blast_radius_large_min_consumers,
            boundary_globs=self.blast_radius_boundary_globs,
        )

    # --- Observability (NWave unified logging) ---

    @property
    def log_level(self) -> str:
        """Log level: NW_LOG_LEVEL env > config log_level > default WARN."""
        env = os.environ.get("NW_LOG_LEVEL")
        if env:
            return env.upper()
        return self._config_data.get("log_level", "WARN").upper()

    @property
    def log_enabled(self) -> bool:
        """Log enabled: NW_LOG env > config log_enabled > default False."""
        env = os.environ.get("NW_LOG")
        if env is not None:
            return env.lower() in ("true", "1", "yes")
        return bool(self._config_data.get("log_enabled", False))


def effective_config(root: Path) -> dict[str, Any]:
    """The effective configuration of ``root``: the mapping ``NWaveConfig`` reads."""
    return NWaveConfig(cwd=root).effective_config()
