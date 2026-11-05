"""The runtime freshness gate: probe, verdicts, canonical tree hash, and the
PROCEED / warn-loud / REFUSE decision.

Moved verbatim from the removed DES runtime (S5-OQ6 closure, F209): the gate
(once ``nwave_ai.runtime.freshness``), the freshness probe port (once
the freshness port), its production and null adapters
the retired driven freshness adapter)
probe hashes with (once ``nwave_ai.runtime.tree_hash``). One module, because only
this closure is reached from the kept hook handlers.

The gate is imported by every hook process, so the concrete probe is imported
AT POINT OF USE, not at module scope: in a developer checkout the gate
auto-skips, and paying for the filesystem edge on import charged every skipped
run for a check that never ran.

Exit code 78 = EX_CONFIG (sysexits.h) — configuration error, distinct from
logic (1) and protocol (2) errors.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import UTC
from pathlib import Path
from typing import Any, Literal, Protocol

from nwave_ai.hooks.audit import (
    AuditEvent,
    AuditLogPathResolver,
    EventType,
    JsonlAuditLogWriter,
)


# ---------------------------------------------------------------------------
# Freshness probe port (once freshness_port)
# ---------------------------------------------------------------------------

# The four-state truth table verdict labels. DEGRADED is the sentinel
# for "manifest absent or malformed" — REFUSE. STALE is the #58 `*.py`-content
# drift (degrade-loud). CONFIG_DRIFT is the SYS-4 / AD-27 config-asset content
# drift — a shipped `lib/nWave/` config asset diverged from its install snapshot
# (degrade-loud on the hook path), distinct from the `*.py` STALE state.
FreshnessStateLabel = Literal["A", "B", "C", "D", "STALE", "CONFIG_DRIFT", "DEGRADED"]


@dataclass(frozen=True)
class FreshnessVerdict:
    """Verdict returned by a FreshnessProbe.

    Carries the state label, a human-readable reason, and the optional
    cause-appropriate remediation. ``remediation`` is an optional fix string a
    :class:`FreshnessProbe` MAY supply per branch (e.g. ``RepoSourceProbe``
    names the dev-editable-no-manifest cause explicitly). ``None`` means "no
    probe-supplied override" — the caller falls back to a reason-keyed
    default, then the blanket remediation string.
    """

    state: FreshnessStateLabel
    reason: str
    remediation: str | None = None


class FreshnessProbe(Protocol):
    """Driven port — produces a FreshnessVerdict for the current process."""

    def probe(self) -> FreshnessVerdict: ...


# ---------------------------------------------------------------------------
# Canonical tree-hash normalisation (once tree_hash)
# ---------------------------------------------------------------------------

# Two files compared on two hosts MUST hash identically when their *content*
# matches, irrespective of mtime, file-mode noise, or ``__pycache__``. Algorithm:
# ``rglob`` over the tree, sort by relative path, md5 of the bytes per file,
# concatenate ``<rel_path>\0<md5>\n`` lines, SHA-256 of the stream. Returns the
# prefix-tagged form ``"sha256:<hex>"``.


# Config-asset envelope (SYS-4 / AD-27): the freshness gate hashed ONLY `*.py`,
# so a drifted shipped config asset drifted SILENTLY. The config-asset hash
# covers the shipped declarative config siblings of the package under the
# assets root.
_CONFIG_ASSET_SUFFIXES = (".yaml", ".yml", ".json")


def canonical_config_assets_hash(assets_root: Path) -> str:
    """Return ``"sha256:<hex>"`` for the canonical hash of the config assets.

    The SYS-4 config-asset envelope variant of :func:`canonical_tree_hash`: same
    algorithm shape (sorted POSIX rel-path + md5-of-bytes → sha256) but over the
    shipped declarative config glob (``*.yaml`` / ``*.yml`` / ``*.json``) under
    ``assets_root`` instead of ``*.py``. Pure function, GIT-FREE, cross-OS.
    """
    sha = hashlib.sha256()
    assets = sorted(
        (
            p
            for p in assets_root.rglob("*")
            if p.is_file() and p.suffix in _CONFIG_ASSET_SUFFIXES
        ),
        key=lambda p: p.relative_to(assets_root).as_posix(),
    )
    for asset in assets:
        rel = asset.relative_to(assets_root).as_posix()
        digest = hashlib.md5(asset.read_bytes()).hexdigest()
        sha.update(f"{rel}\0{digest}\n".encode())
    return f"sha256:{sha.hexdigest()}"


def canonical_tree_hash(tree_root: Path) -> str:
    """Return ``"sha256:<hex>"`` for the canonical hash of ``tree_root``.

    Pure function — reads ``*.py`` files under ``tree_root`` once each.
    """
    sha = hashlib.sha256()
    py_files = sorted(tree_root.rglob("*.py"), key=lambda p: p.relative_to(tree_root))
    for py_file in py_files:
        rel = py_file.relative_to(tree_root).as_posix()
        digest = hashlib.md5(py_file.read_bytes()).hexdigest()
        sha.update(f"{rel}\0{digest}\n".encode())
    return f"sha256:{sha.hexdigest()}"


# ---------------------------------------------------------------------------
# NullProbe — the test/opt-out FreshnessProbe adapter
# ---------------------------------------------------------------------------


class NullProbe:
    """Stub FreshnessProbe — always PROCEEDS with state ``A``.

    Used by tests that need a probe with no filesystem dependencies.
    """

    def probe(self) -> FreshnessVerdict:
        return FreshnessVerdict(state="A", reason="null-probe")


# ---------------------------------------------------------------------------
# RepoSourceProbe — the production FreshnessProbe adapter
# ---------------------------------------------------------------------------

# The installed package root the gate inspects. Resolved from this module's
# location at import time: ``…/lib/python/nwave_ai/hooks/freshness.py`` →
# the installed ``nwave_ai`` package root is one parent up.
_INSTALLED_PACKAGE_ROOT = Path(__file__).resolve().parents[1]
_MANIFEST_FILENAME = "_install_manifest.json"
# Known manifest schema versions. v1 = the eight-field shape. v2 = the
# SYS-4 / AD-27 shape that ADDS ``config_assets_tree_hash`` (the install-time
# snapshot of the shipped ``lib/nWave/`` config assets). Any other value →
# DEGRADED (the installer corruption AT pins ``999`` → REFUSE).
_KNOWN_SCHEMA_VERSIONS = frozenset({1, 2})
_CONFIG_ASSETS_SCHEMA_VERSION = 2
_CONFIG_ASSETS_FIELD = "config_assets_tree_hash"
# Install manifest schema — the 8 required fields. Missing any of these
# yields a DEGRADED verdict citing the missing field(s).
_REQUIRED_FIELDS = (
    "schema_version",
    "installed_version",
    "installed_at_iso",
    "source_tree",
    "source_commit",
    "source_dirty",
    "source_kind",
    "tree_hash",
)

# The DEGRADED "no manifest" reason text + its cause-appropriate remediation
# (RCA fix-des-silent-config-failure, root cause B): the dev-editable-binary-
# from-a-non-project-cwd topology has nothing to reinstall — the fix is
# running from a project/source checkout. Exported (not `_`-prefixed) so the
# gate can key its reason->remediation fallback map off the same SSOT text,
# keeping a directly-constructed `FreshnessVerdict` (e.g. in tests, or another
# `FreshnessProbe` adapter) correctly differentiated even without going
# through this probe.
NO_MANIFEST_REASON = "no install manifest — reinstall required"
NO_MANIFEST_REMEDIATION = "run from a project directory or the nWave source checkout"


class RepoSourceProbe:
    """Production FreshnessProbe — reads ``_install_manifest.json``."""

    def __init__(self, installed_root: Path | None = None) -> None:
        # Default to the installed package this module was loaded from. Tests
        # may inject a tmp_path-scoped root; the acceptance tests do not (they
        # rely on PYTHONPATH pointing at the synthetic installed tree, so
        # ``__file__`` resolves there naturally).
        self._installed_root = installed_root or _INSTALLED_PACKAGE_ROOT

    def probe(self) -> FreshnessVerdict:
        manifest_path = self._installed_root / _MANIFEST_FILENAME
        loaded = self._load_and_validate_manifest(manifest_path)
        if isinstance(loaded, FreshnessVerdict):
            return loaded
        return self._classify_state(loaded)

    def _load_and_validate_manifest(
        self, manifest_path: Path
    ) -> FreshnessVerdict | dict:
        """Read + parse + schema-validate the manifest file.

        Returns a DEGRADED ``FreshnessVerdict`` when the file is absent,
        empty, non-JSON, has an unknown ``schema_version``, or omits one of
        the required fields. Returns the parsed manifest dict when the
        load + validation succeeded.
        """
        if not manifest_path.exists():
            return FreshnessVerdict(
                state="DEGRADED",
                reason=NO_MANIFEST_REASON,
                remediation=NO_MANIFEST_REMEDIATION,
            )
        raw_text = manifest_path.read_text(encoding="utf-8")
        if not raw_text:
            return FreshnessVerdict(
                state="DEGRADED",
                reason="cannot parse install manifest: file is empty",
            )
        try:
            manifest = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            return FreshnessVerdict(
                state="DEGRADED",
                reason=f"cannot parse install manifest: {exc.msg}",
            )
        if manifest.get("schema_version") not in _KNOWN_SCHEMA_VERSIONS:
            return FreshnessVerdict(
                state="DEGRADED",
                reason=(
                    f"unknown manifest schema_version="
                    f"{manifest.get('schema_version')!r}"
                ),
            )
        missing = [field for field in _REQUIRED_FIELDS if field not in manifest]
        if missing:
            return FreshnessVerdict(
                state="DEGRADED",
                reason=f"missing required field(s) in install manifest: {missing}",
            )
        return manifest

    def _classify_state(self, manifest: dict) -> FreshnessVerdict:
        """Discriminate state A / C / D / STALE from a validated manifest.

        Installed-side first (states A/C/D, unchanged): a divergence between the
        installed tree and the manifest snapshot is state D (someone edited the
        installed copy → REFUSE).

        Gap B (#58 repo-moved-on) then refines state C: even when the installed
        tree matches the manifest, the dev may have edited the REPO source tree
        after install. Re-hashing ``source_tree`` (rewrite-aware, so the
        pre-rewrite repo tree compares symmetrically to the post-rewrite manifest
        snapshot) detects that content divergence → state STALE (degrade-loud).
        This makes the gate compare CONTENT, not the coarse ``.git/`` presence.
        """
        source_tree = manifest.get("source_tree", "")
        if not source_tree or not Path(source_tree).exists():
            return FreshnessVerdict(
                state="A",
                reason="customer install — source tree not reachable",
            )
        manifest_tree_hash = manifest.get("tree_hash", "")
        installed_tree_hash = canonical_tree_hash(self._installed_root)
        if installed_tree_hash != manifest_tree_hash:
            return FreshnessVerdict(
                state="D",
                reason=(
                    f"installed tree_hash={installed_tree_hash} "
                    f"!= manifest tree_hash={manifest_tree_hash}"
                ),
            )
        source_tree_hash = canonical_tree_hash(Path(source_tree), rewrite_imports=True)
        if source_tree_hash != manifest_tree_hash:
            return FreshnessVerdict(
                state="STALE",
                reason=(
                    f"installed spine is stale: repo source_tree_hash="
                    f"{source_tree_hash} != installed manifest tree_hash="
                    f"{manifest_tree_hash}"
                ),
            )
        config_drift = self._classify_config_assets(manifest)
        if config_drift is not None:
            return config_drift
        return FreshnessVerdict(state="C", reason="developer install — fresh")

    def _classify_config_assets(self, manifest: dict) -> FreshnessVerdict | None:
        """Detect SYS-4 / AD-27 shipped config-asset drift (schema v2 only).

        v1 manifests carry no ``config_assets_tree_hash`` snapshot → no
        config-asset envelope (returns ``None``, the caller proceeds to state C).

        v2 manifests snapshot the shipped ``lib/nWave/`` config assets at install
        time. Re-hash the installed config tree and compare: a divergence means a
        maintainer edited a shipped config asset (``flavors/atdd_pure.yaml``, the
        gate-composition SSOT, or ``framework-catalog.yaml``) after install → a
        CONFIG_DRIFT verdict the hook names LOUD + degrades-loud on. The config
        tree sits beside ``lib/python`` as ``lib/nWave`` (``installed_root`` is
        ``lib/python/nwave_ai``), exactly where the installer ships it.
        """
        if manifest.get("schema_version") != _CONFIG_ASSETS_SCHEMA_VERSION:
            return None
        snapshot = manifest.get(_CONFIG_ASSETS_FIELD, "")
        assets_root = self._installed_root.parent.parent / "nWave"
        if not snapshot or not assets_root.exists():
            return None
        installed_config_hash = canonical_config_assets_hash(assets_root)
        if installed_config_hash != snapshot:
            return FreshnessVerdict(
                state="CONFIG_DRIFT",
                reason=(
                    f"shipped config asset is stale: installed "
                    f"config_assets_tree_hash={installed_config_hash} "
                    f"!= manifest config_assets_tree_hash={snapshot}"
                ),
            )
        return None


# ---------------------------------------------------------------------------
# The gate: PROCEED silently, warn-loud on stale, or REFUSE
# ---------------------------------------------------------------------------

# Exit code 78 = EX_CONFIG (sysexits.h) — configuration error, distinct from
# logic (1) and protocol (2) errors.
_REFUSE_EXIT_CODE = 78

# Env var name + the legal-value set. Anything else → REFUSE as DEGRADED.
# The sentinel `__unset__` is a Gherkin-table convention for "do not set the
# var at all"; the actual env-var absence is handled by `os.environ.get`
# returning None and short-circuits ahead of the legal-value check.
_OPT_OUT_ENV_VAR = "NWAVE_FRESHNESS"
_OPT_OUT_SKIP = "skip"
_LEGAL_OPT_OUT_VALUES = frozenset({"skip", "verbose", "enforce", ""})

# Test-only override: when `NWAVE_FRESHNESS_FORCE_GATE=1`, the dev-checkout
# autoskip short-circuit (CWD `.git/` adjacency probe) is BYPASSED so the
# four-state classifier runs end-to-end against the installed-tree probe.
# Required by the installer-side freshness ATs whose customer-scenario
# subprocess spawns inherit the repo's CWD and would otherwise trigger the
# autoskip regardless of the scenario under test. Production code defaults
# preserved (env var unset → autoskip behaves byte-identically). DOES NOT
# bypass the `NWAVE_FRESHNESS=skip` operator opt-out or the legal-values
# check above — only the autoskip short-circuit.
_FORCE_GATE_ENV_VAR = "NWAVE_FRESHNESS_FORCE_GATE"
_FORCE_GATE_ENABLED = "1"


def is_git_checkout_marker(marker: Path) -> bool:
    """Return whether ``marker`` identifies an actual Git checkout.

    A directory merely named ``.git`` is not evidence of a checkout.  Normal
    repositories have a ``HEAD`` file in that directory.  Linked worktrees use
    a small ``.git`` file whose ``gitdir:`` target has its own ``HEAD``.  The
    distinction prevents unrelated ancestor artefacts from disabling the
    installed-runtime freshness check.
    """
    if marker.is_dir():
        return (marker / "HEAD").is_file()
    if not marker.is_file():
        return False
    try:
        prefix, target_text = (
            marker.read_text(encoding="utf-8").strip().split(":", maxsplit=1)
        )
    except (OSError, UnicodeError, ValueError):
        return False
    if prefix != "gitdir" or not target_text.strip():
        return False
    target = Path(target_text.strip())
    if not target.is_absolute():
        target = marker.parent / target
    return target.is_dir() and (target / "HEAD").is_file()


def _emit_event(payload: dict[str, Any]) -> None:
    """Print one single-line structured JSON event to stderr (telemetry)."""
    print(json.dumps(payload), file=sys.stderr)


_REMEDIATION = "nwave-ai install"


# Reason-keyed remediation overrides (RCA fix-des-silent-config-failure, root
# cause B): the blanket `_REMEDIATION` ("reinstall") is wrong for a DEGRADED
# cause with nothing to reinstall. Keyed off `NO_MANIFEST_REASON` (the SSOT
# text `RepoSourceProbe` returns for the dev-editable-binary-from-non-
# project-cwd topology) so a `FreshnessVerdict` that reproduces this exact
# reason — whether or not it went through `RepoSourceProbe` — still resolves
# to the differentiated fix. Extend this map as more DEGRADED causes gain a
# cause-appropriate remediation; unmapped reasons keep the blanket fallback.
def _reason_remediation_overrides() -> dict[str, str]:
    """The reason->remediation map, built where it is READ rather than at import.

    It was a module-level constant, and building it required importing the
    adapter's texts -- which is what dragged the concrete probe into every
    process that so much as imports a CLI submodule. The map is consumed
    in exactly one place (`_resolve_remediation`), and only on the failure path,
    so paying for it at import time charged every successful command for a
    lookup table that a successful command never reads.
    """
    return {NO_MANIFEST_REASON: NO_MANIFEST_REMEDIATION}


def _resolve_remediation(verdict: FreshnessVerdict) -> str:
    """Cause-appropriate remediation: probe-supplied > reason-mapped > blanket."""
    if verdict.remediation:
        return verdict.remediation
    return _reason_remediation_overrides().get(verdict.reason, _REMEDIATION)


def _refuse(verdict: FreshnessVerdict) -> None:
    """Emit the structured refusal event + human diagnostic, then exit 78."""
    remediation = _resolve_remediation(verdict)
    _emit_event(
        {
            "event": "nwave_ai.runtime.freshness.refused",
            "state": verdict.state,
            "reason": verdict.reason,
            "remediation": remediation,
        }
    )
    print(
        f"⚠ freshness check refused — {verdict.reason}. Fix: {remediation}",
        file=sys.stderr,
    )
    sys.exit(_REFUSE_EXIT_CODE)


# Advisory-throttle finding (measured 2026-07-28): the hook adapter fires this
# gate as an IMPORT-TIME side effect on every matching hook subprocess. In an
# actively-edited multi-lane repo, the installed spine diverges from the shared
# install within minutes of a reinstall and STAYS diverged until the next
# manual reinstall — nothing auto-clears it, and re-announcing an UNCHANGED
# verdict on every hook call defeats "loud" through sheer repetition.
#
# Throttle to one emission per (state) per window; a STATE TRANSITION (STALE ->
# fresh, STALE -> CONFIG_DRIFT, a reinstall clearing the drift) is NEVER
# throttled — it always breaks through immediately. Suppress an unchanged
# repeat, never a change.
_DEGRADE_THROTTLE_SECONDS = 1800
_DEGRADE_SENTINEL_FILENAME = "_freshness_degrade_sentinel.json"


def _degrade_sentinel_path() -> Path:
    """Resolve the throttle sentinel next to this project's own audit sink.

    Reuses ``AuditLogPathResolver`` (project-local ``.nwave/des/logs/`` by
    default, honoring ``DES_AUDIT_LOG_DIR``) so the throttle's SCOPE matches the
    audit sink's own scope — per-project, exactly like the records it throttles.
    This also means tests that already redirect ``DES_AUDIT_LOG_DIR`` to a
    ``tmp_path`` get an isolated, empty sentinel for free, with no new env var
    or fixture plumbing required.
    """
    return AuditLogPathResolver().resolve() / _DEGRADE_SENTINEL_FILENAME


def _should_emit_degrade(state: str) -> bool:
    """True iff ``state`` merits a fresh degrade-loud emission right now.

    Fail-OPEN (returns True) on a missing sentinel, a corrupt/unreadable one, or
    any parse error — a throttle-machinery bug must never cost the FIRST
    occurrence of a real condition its visibility (degrade-loud, never
    silently-wrong). Only an EXACT, RECENT repeat of the same ``state`` is
    suppressed; a different state (including one never seen before) always
    emits.
    """
    from datetime import datetime

    path = _degrade_sentinel_path()
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        last_emitted = datetime.fromisoformat(record["last_emitted_iso"])
        elapsed_seconds = (datetime.now(UTC) - last_emitted).total_seconds()
        if record.get("state") == state and elapsed_seconds < _DEGRADE_THROTTLE_SECONDS:
            return False
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        # Absent file (nothing recorded yet), corrupt JSON, missing/malformed
        # key, or an unparsable timestamp all mean "no valid throttle state" —
        # fail open to emitting rather than silently swallowing a first-seen or
        # ambiguous condition.
        pass
    return True


def _record_degrade_emitted(state: str) -> None:
    """Persist ``(state, now)`` so a later call can throttle an unchanged repeat.

    Best-effort: a write failure here must not block the emission that just
    happened, and must not raise — the worst case (sentinel unwritable, e.g. a
    read-only filesystem) is reverting to pre-throttle behavior (every call
    emits again), never silence.
    """
    from datetime import datetime

    path = _degrade_sentinel_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "state": state,
                    "last_emitted_iso": datetime.now(UTC).isoformat(),
                }
            ),
            encoding="utf-8",
        )
    except OSError:
        pass


def _degrade_loud(
    verdict: FreshnessVerdict, *, stderr_event: str, audit_event_name: str
) -> None:
    """Degrade-loud: warn on stderr + persist to the SSOT audit sink, then PROCEED.

    The single degrade-loud path behind both the stale-install (#58) and the
    config-drift (SYS-4 / AD-27) verdicts. Dual-emit: a LOUD ``stderr_event`` on
    stderr (the operator reads it in-flow) AND a persisted record under
    ``audit_event_name`` in the SSOT audit sink (the single
    ``JsonlAuditLogWriter`` daily log under the ``AuditLogPathResolver`` dir —
    the queryable KPI sink). NEVER exits non-zero — a freshness miss must not
    brick an in-flight session.

    The two callers differ ONLY in their event names: the stderr telemetry
    string and the audit ``EventType`` value. Everything else (state / reason /
    remediation payload, the audit sink) is identical, so both ride one helper.

    Throttled per ``verdict.state`` (see ``_should_emit_degrade``): an unchanged
    repeat within the window is a silent no-op (still PROCEED, just no re-emit);
    a state transition always emits regardless of the window.
    """
    if not _should_emit_degrade(verdict.state):
        return
    _emit_event(
        {
            "event": stderr_event,
            "state": verdict.state,
            "reason": verdict.reason,
            "remediation": _REMEDIATION,
        }
    )
    _persist_audit_record(verdict, audit_event_name=audit_event_name)
    _record_degrade_emitted(verdict.state)


def _warn_stale(verdict: FreshnessVerdict) -> None:
    """Degrade-loud on a stale installed spine (#58): warn + PROCEED."""
    _degrade_loud(
        verdict,
        stderr_event="nwave_ai.runtime.freshness.stale",
        audit_event_name=EventType.HEALTH_GATE_INSTALL_FRESHNESS_STALE.value,
    )


def _warn_config_drift(verdict: FreshnessVerdict) -> None:
    """Degrade-loud on a drifted shipped config asset (SYS-4 / AD-27): warn + PROCEED."""
    _degrade_loud(
        verdict,
        stderr_event="nwave_ai.runtime.freshness.config-drift",
        audit_event_name=EventType.HEALTH_GATE_INSTALL_FRESHNESS_CONFIG_DRIFT.value,
    )


def _persist_audit_record(verdict: FreshnessVerdict, *, audit_event_name: str) -> None:
    """Append one freshness-degrade record to the SSOT audit sink (DV-5, KPI-1).

    Emits through the existing ``JsonlAuditLogWriter`` — the SINGLE audit sink
    the reader, the KPI query path, and rotation all read
    (``audit-YYYY-MM-DD.log`` under the ``AuditLogPathResolver`` dir, honoring
    ``DES_AUDIT_LOG_DIR``). The caller passes the ``EventType`` value as the
    event-name SSOT; the ``remediation`` business-name rides in ``data`` so the
    writer surfaces it as a top-level field. No second sink, no hardcoded
    event-name string.
    """
    from datetime import datetime

    event = AuditEvent(
        event_type=audit_event_name,
        timestamp=datetime.now(UTC).isoformat(),
        data={
            "state": verdict.state,
            "reason": verdict.reason,
            "remediation": _REMEDIATION,
        },
    )
    JsonlAuditLogWriter().log_event(event)


def assert_fresh_or_explain(
    probe: FreshnessProbe | None = None,
    *,
    suppress_git_autoskip: bool = False,
) -> None:
    """Run the freshness gate; PROCEED silently, warn-loud on stale, or REFUSE.

    Honors ``NWAVE_FRESHNESS=skip`` ahead of the probe — emits the
    audit-bearing ``skipped`` event and returns. This is the F3 bootstrap-blind
    closure: without it, every run against a repo dev tree without a fresh
    install would deterministically REFUSE.

    ``suppress_git_autoskip`` (DV-2): when True, the ``.git/``-adjacency autoskip
    is bypassed so the content probe RUNS even on a developer checkout. The hook
    hot path passes True — that is the #58 topology (installed-tree drift on a
    project that has ``.git/``) where the coarse autoskip would otherwise neuter
    the gate. The opt-out check above still takes precedence.
    """
    opt_out_value = os.environ.get(_OPT_OUT_ENV_VAR)
    if opt_out_value == _OPT_OUT_SKIP:
        _emit_event(
            {
                "event": "nwave_ai.runtime.freshness.skipped",
                "reason": f"{_OPT_OUT_ENV_VAR}={_OPT_OUT_SKIP}",
            }
        )
        return
    if opt_out_value is not None and opt_out_value not in _LEGAL_OPT_OUT_VALUES:
        _refuse(
            FreshnessVerdict(
                state="DEGRADED",
                reason=(f"unrecognised {_OPT_OUT_ENV_VAR} value: {opt_out_value!r}"),
            )
        )

    # Developer-checkout auto-skip (friction #16): if invoked from anywhere
    # inside a git checkout (CWD or any ancestor has `.git/`), the operator is
    # in a dev tree and the installed-tree freshness check is structurally
    # irrelevant. Walks parents because subprocess invocations may have CWD
    # different from project root. The normal success path stays silent so a
    # machine-readable command keeps stdout/stderr uncontaminated. Operators
    # can request the existing structured `autoskipped` diagnostic with
    # NWAVE_FRESHNESS=verbose. Customer installs (no `.git/` in any ancestor)
    # preserve fail-closed DEGRADED REFUSE byte-identical.
    #
    # Test-only bypass: when NWAVE_FRESHNESS_FORCE_GATE=1, skip the autoskip
    # probe entirely and run the four-state classifier. Required by
    # installer-side freshness ATs that exercise the customer-scenario topology
    # via subprocess spawns whose CWD inherits the repo's `.git/` adjacency.
    # Production callers never set this env var; default behavior unchanged.
    if (
        not suppress_git_autoskip
        and os.environ.get(_FORCE_GATE_ENV_VAR) != _FORCE_GATE_ENABLED
    ):
        cwd = Path.cwd()
        while True:
            if is_git_checkout_marker(cwd / ".git"):
                if opt_out_value == "verbose":
                    _emit_event(
                        {
                            "event": "nwave_ai.runtime.freshness.autoskipped",
                            "reason": (
                                "developer checkout detected via .git adjacency at "
                                f"{str(cwd)!r}"
                            ),
                        }
                    )
                return
            parent = cwd.parent
            if parent == cwd:
                break  # reached filesystem root, no .git/ found
            cwd = parent

    if probe is None:
        # Resolved HERE, past every early return above: an injected probe never
        # needs the concrete one, and a run that auto-skips never reaches this
        # line at all. Importing it at module scope charged both cases for a
        # class neither of them uses.
        probe = RepoSourceProbe()
    verdict = probe.probe()
    if verdict.state in ("DEGRADED", "D"):
        # Degrade-loud contract (feature-delta DISCUSS D1 / DEVOPS DV-2/DV-4):
        # "the HOOK degrades LOUD (warns + proceeds, exit 0). It NEVER
        # hard-blocks the session ... The CLI keeps its exit-78 REFUSE." The
        # hook path is the `suppress_git_autoskip=True` caller; on a
        # DEGRADED/D verdict it warns + proceeds (never sys.exit) so a bare
        # in-process import of the hook adapter (e.g. during pytest collection
        # of a manifest-less source tree) cannot brick the session. The CLI
        # path (suppress_git_autoskip=False) keeps the fail-closed exit-78
        # REFUSE byte-identical.
        if suppress_git_autoskip:
            _warn_stale(verdict)
            return
        _refuse(verdict)
    if verdict.state == "STALE":
        _warn_stale(verdict)
        return
    if verdict.state == "CONFIG_DRIFT":
        # SYS-4 / AD-27 degrade-loud (DISCUSS D1 / DEVOPS DV-2/DV-4): the hook
        # path (suppress_git_autoskip=True) warns + proceeds (exit 0) so a stale
        # shipped config asset is named LOUD but never bricks the session. The
        # CLI path keeps the fail-closed exit-78 REFUSE.
        if suppress_git_autoskip:
            _warn_config_drift(verdict)
            return
        _refuse(verdict)
    if verdict.state == "C" and not suppress_git_autoskip:
        # CLI path (AT-02-B): emit a developer-fresh structured event so the
        # installer slice-02 AT can observe state C through stderr. The hook hot
        # path (suppress_git_autoskip=True) stays SILENT on a fresh install —
        # the freshness wiring adds zero noise when the install is current.
        _emit_event(
            {
                "event": "nwave_ai.runtime.freshness.proceed",
                "state": verdict.state,
                "reason": verdict.reason,
            }
        )


__all__ = [
    "NO_MANIFEST_REASON",
    "NO_MANIFEST_REMEDIATION",
    "FreshnessProbe",
    "FreshnessStateLabel",
    "FreshnessVerdict",
    "NullProbe",
    "RepoSourceProbe",
    "assert_fresh_or_explain",
    "canonical_config_assets_hash",
    "canonical_tree_hash",
    "is_git_checkout_marker",
]
