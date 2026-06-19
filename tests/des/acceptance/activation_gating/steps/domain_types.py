"""Domain types for the project-activation-gating acceptance suite (Mandate-12 criterion 1).

Every domain noun used in the Gherkin scenarios is expressed here ONCE as a
typed enum / dataclass / NewType. Composition-service signatures (in
``composition.py``) consume these types — never raw ``str`` where an enum
exists. Step bodies coerce Gherkin literals into these types via
``pytest_bdd.parsers`` converters, so the DSL emerges from the type system
rather than from a decorator-per-literal explosion.

Feature contract source of truth:
- ``AUTONOMOUS-SESSION-2026-06-18.md`` (DISCUSS, locked)
- ``docs/feature/nwave-project-activation-gating/feature-delta.md`` (DESIGN, DDD-1..16)
- ``docs/product/architecture/ADR-AG-00{1,2,3,4}-*.md``
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import NewType


class GlobalMode(Enum):
    """Global activation mode at ``~/.nwave/global-config.json`` → ``activation.mode``.

    ``ABSENT`` and ``CORRUPT`` model the two "no readable opinion" shapes that
    DDD-16 / ADR-AG-002 collapse to the fresh-install default (``opt-in``).
    """

    OPT_IN = "opt-in"
    ALL = "all"
    ABSENT = "absent"
    CORRUPT = "corrupt"


class MarkerState(Enum):
    """Per-project marker ``.nwave/local-config.json`` → ``enabled_for_repo``.

    ``ABSENT`` covers file-missing OR key-missing OR corrupt — all three resolve
    to "no opinion → defer to mode" per the ADR-AG-002 truth table. ``ENABLED``
    / ``DISABLED`` are the two explicit-present values; ``DISABLED`` is the
    sticky opt-out.
    """

    ENABLED = "enabled"
    DISABLED = "disabled"
    ABSENT = "absent"


class Activation(Enum):
    """The resolved verdict of the activation policy."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class HookCommand(Enum):
    """The hook command dispatched through ``hook_router.main()``.

    Names mirror ``hook_definitions.py`` / ``hook_router.py`` argv tokens.
    ``SESSION_START`` is the gate-exempt command (DDD-5); ``PRE_TASK`` is the
    adopt-and-proceed command (DDD-9).
    """

    SESSION_START = "session-start"
    PRE_TASK = "pre-task"
    PRE_TOOL_USE = "pre-tool-use"
    POST_TOOL_USE = "post-tool-use"
    SUBAGENT_STOP = "subagent-stop"
    DELIVER_PROGRESS = "deliver-progress"
    PRE_WRITE = "pre-write"
    SUBAGENT_START = "subagent-start"


class GateOutcome(Enum):
    """What the gate did with a hook invocation (observable at the router port)."""

    ALLOWED_EXIT_0 = "allowed-exit-0"  # inactive → sys.exit(0), handler skipped
    DISPATCHED = "dispatched"  # active → handler ran normally
    ADOPTED_AND_DISPATCHED = "adopted-and-dispatched"  # pre-task detect-and-adopt


class PriorUseEvidence(Enum):
    """A single prior-use signal under the project root (DDD-8 / ADR-AG-003).

    ``BARE_DES_CONFIG`` is the named false-positive guard: it must NOT count as
    evidence (DISCUSS L5). ``NONE`` is the empty fixture.
    """

    AUDIT_LOG_NONEMPTY = "audit-log-nonempty"
    EXECUTION_LOG = "execution-log"
    DELIVER_DIR = "deliver-dir"
    FEATURE_DELTA = "feature-delta"
    BARE_DES_CONFIG = "bare-des-config"
    NONE = "none"


class AdoptionTrigger(Enum):
    """Which auto-marking trigger fired (DDD-7)."""

    PRIOR_USE = "prior-use"  # Trigger 1, SessionStart
    REAL_FEATURE_USE = "real-feature-use"  # Trigger 2, pre-task nw-* dispatch


class AdoptionResult(Enum):
    """Outcome of ``AutoMarkingService.adopt_if_warranted`` (ADR-AG-003)."""

    ADOPTED = "adopted"  # marker written
    NOT_WARRANTED = "not-warranted"  # no evidence → no write
    NO_OP_STICKY = "no-op-sticky"  # marker already present (any value) → no write


class GitignoreVariant(Enum):
    """Catalogue of root ``.gitignore`` ``.nwave`` line shapes (OQ-4).

    The transform intent (ADR-AG-004) is "match any whole-dir ``.nwave`` exclude,
    else append the re-include under an nWave banner". This repo's actual shipped
    line is ``SLASH_TRAILING`` (verified: root ``.gitignore:14`` == ``.nwave/``).
    """

    SLASH_TRAILING = "slash-trailing"  # ".nwave/"  (the shipped variant, verified)
    NO_SLASH = "no-slash"  # ".nwave"
    LEADING_SLASH = "leading-slash"  # "/.nwave/"
    LEADING_NO_TRAILING = "leading-no-trailing"  # "/.nwave"
    NO_NWAVE_LINE = "no-nwave-line"  # user-customized; no .nwave exclude at all
    ALREADY_FIXED = "already-fixed"  # ".nwave/*" + "!.nwave/local-config.json" present


class CompletionShell(Enum):
    """Shell for which completion is generated (OQ-2: bash + zsh default)."""

    BASH = "bash"
    ZSH = "zsh"


class CliResult(Enum):
    """Observable shape of a CLI verb invocation."""

    SUCCESS = "success"  # exit 0
    USAGE_ERROR = "usage-error"  # nonzero exit + usage text on stderr


class FsMode(Enum):
    """Filesystem condition for fault injection (C7a)."""

    WRITABLE = "writable"
    READ_ONLY = "read-only"


# ---------------------------------------------------------------------------
# Typed scalars + records
# ---------------------------------------------------------------------------

ExitCode = NewType("ExitCode", int)
SubagentType = NewType("SubagentType", str)


@dataclass(frozen=True)
class ResolutionCase:
    """One row of the 9-row activation truth table (ADR-AG-002)."""

    marker: MarkerState
    mode: GlobalMode
    expected: Activation
    note: str = ""


@dataclass(frozen=True)
class CompletionExpectation:
    """The vocabulary a generated completion script MUST and MUST NOT surface.

    ``must_contain`` are the verbs/options surfaced by ``--help`` (no drift,
    DDD-14). ``must_not_contain`` enforces the "no 'hooks' term" rule (DISCUSS).
    """

    must_contain: frozenset[str]
    must_not_contain: frozenset[str]


# The canonical 9-row truth table, expressed once as data (consumed by the
# parametrized resolution scenarios). Mirrors ADR-AG-002 exactly.
TRUTH_TABLE: tuple[ResolutionCase, ...] = (
    ResolutionCase(
        MarkerState.ENABLED, GlobalMode.OPT_IN, Activation.ACTIVE, "marker wins"
    ),
    ResolutionCase(
        MarkerState.ENABLED, GlobalMode.ALL, Activation.ACTIVE, "marker agrees"
    ),
    ResolutionCase(
        MarkerState.ENABLED, GlobalMode.ABSENT, Activation.ACTIVE, "marker wins"
    ),
    ResolutionCase(
        MarkerState.DISABLED, GlobalMode.OPT_IN, Activation.INACTIVE, "sticky opt-out"
    ),
    ResolutionCase(
        MarkerState.DISABLED,
        GlobalMode.ALL,
        Activation.INACTIVE,
        "sticky wins over all",
    ),
    ResolutionCase(
        MarkerState.DISABLED, GlobalMode.ABSENT, Activation.INACTIVE, "sticky opt-out"
    ),
    ResolutionCase(
        MarkerState.ABSENT, GlobalMode.OPT_IN, Activation.INACTIVE, "default-silent"
    ),
    ResolutionCase(
        MarkerState.ABSENT, GlobalMode.ALL, Activation.ACTIVE, "globally opted in"
    ),
    ResolutionCase(
        MarkerState.ABSENT,
        GlobalMode.ABSENT,
        Activation.INACTIVE,
        "fresh-install default = opt-in",
    ),
)

# Completion vocabulary expectation (DDD-14 / OQ-2). "hooks" is the forbidden
# term per the DISCUSS naming convention (gh-style resource<->action, no "hooks").
COMPLETION_EXPECTATION = CompletionExpectation(
    must_contain=frozenset(
        {"project", "mode", "status", "enable", "disable", "all", "opt-in"}
    ),
    must_not_contain=frozenset({"hooks"}),
)


@dataclass
class HookEnvelope:
    """The stdin JSON envelope a hook process receives (DDD-6 buffer/rewind).

    ``cwd`` is the field the gate parses to resolve the project. ``raw`` lets a
    scenario assert byte-identical re-injection (the rewind contract).
    """

    command: HookCommand
    cwd: str | None
    subagent_type: SubagentType | None = None
    raw: str | None = None  # explicit non-JSON / malformed stdin override
    extra: dict[str, object] = field(default_factory=dict)
