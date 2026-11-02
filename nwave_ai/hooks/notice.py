"""SessionStart hook handler -- the route notice, read-only.

An agent beginning a session in an enabled nWave project must find, in its OWN
starting context, a short notice naming the available routes and what each one
leaves behind, without opening any project file.

The route notice remains read-only. The session's entry in the global activity
registry is written by ``nwave_ai.hooks.lifecycle`` before this handler runs;
separately consented update actions may then run at startup after the local
work-state preflight and the global idle proof.

ONE WORDING, ONE SOURCE. The notice text is the already-shipped
``nWave/templates/delivery-route-fragment.md`` -- the same bytes the installer
splices into the project's managed ``CLAUDE.md`` section. No second wording is
authored here, so the injected notice and the project's guidance file cannot
state different routes.

HOST CONTRACT. Standard output is EXACTLY ONE JSON object of the wrapped form
``{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext":
...}}``. The bare ``{"additionalContext": ...}`` form is not honored by current
Claude Code, and several independent ``print(json.dumps(...))`` calls in one
invocation produce output that is not valid JSON as a whole -- so there is
exactly one print here. Normal route notices have no ``systemMessage``. Failed
admission is a separate safety reply: it emits both agent context and a
user-visible warning before route notice validation or activation can suppress it.

ROUTE-NOTICE FAILURE ALGEBRA. A route-notice refusal means no stdout plus exit
0. An absent or ambiguous asset, an unreadable or undecodable file, an empty
template and a notice grown past its declared ceiling yield one WHAT/WHY/HOW
line on stderr. Admission warnings are not route notices and bypass this
refusal family. Native hooks do not establish that the host blocked work;
controlled host launchers own that boundary.

A DECLARED, MEASURED SIZE. The notice is a standing tax on every session's
context, so its cost is reported as a measured fact on EVERY invocation, and the
text refuses to grow past a ceiling declared here and nowhere else. The report
rides on stderr because stdout is reserved for exactly one JSON object.

BYTES ARE PRIMITIVE, TOKENS ARE DERIVED. Bytes are the exact UTF-8 length of the
``additionalContext`` actually written to stdout. Tokens are ``ceil(bytes / 4)``
and are ALWAYS reported with that provenance named, because a SessionStart hook
must never touch the network and no tokenizer is reachable from it at runtime.

DESCRIPTIVE, NEVER COMMANDING -- AND GUARDED HERE, AT RUNTIME. The notice is
resolved AT RUNTIME from a tree that can legitimately drift (see
``nwave_ai.platform.assets``), so the same closed set of commanding phrases is
declared here and decided over the exact bytes this handler is about to write.

THE POSITIVE HALF IS LOAD-BEARING. Forbidding commands is not enough: a notice
can command nothing and still quietly drop the fact that working directly stays
an available answer. The notice must therefore carry at least one SENTENCE
pairing the direct route with a still-open token.
"""

from __future__ import annotations

import json
import math
import re
import sys

from nwave_ai.platform.assets import resolve_packaged_asset


#: The shipped notice, authored once and spliced into every managed host file.
ROUTE_NOTICE_ASSET = "nWave/templates/delivery-route-fragment.md"

#: The single declaration of how much starting context the notice may spend.
#: MEASURED, not chosen: the shipped text is 1179 B, and the identical bytes are
#: spliced into a managed ``CLAUDE.md`` section capped at 4096 B, whose measured
#: headroom admits at most 1964 notice bytes. 1536 B therefore sits 357 B above
#: today's text and 428 B below that hard limit, so this ceiling can never be
#: satisfied while breaking the older section guard.
NOTICE_CEILING_BYTES = 1536

#: The same ceiling in the derived unit, so the two are one declaration.
NOTICE_CEILING_TOKENS = math.ceil(NOTICE_CEILING_BYTES / 4)

#: Tokens may only ever be presented as what they are.
TOKEN_PROVENANCE = (
    "derived as ceil(bytes/4), a conservative upper bound -- notice measurement "
    "uses no tokenizer"
)

#: The closed forbidden set, REUSED rather than redefined: these are the same
#: seven phrases the install-time section guard already decides over, at
#: tests/installer/acceptance/route_choice_block/public_oracle.py:72-80. They are
#: copied rather than shared because a production module cannot import an
#: acceptance oracle. MEMBERSHIP MUST STAY IDENTICAL to that list; comparison is
#: case-insensitive substring containment. Declaration ORDER is meaningful: it is
#: the order in which an offence is named.
COMMANDING_PHRASES = (
    "you must",
    "must route",
    "always route",
    "never bypass",
    "mandatory",
    "is required",
    "do not work directly",
)

#: The direct route, and the still-open tokens that keep it stated as an answer.
#: Also reused verbatim from the same install-time guard (its ``:117``).
DIRECT_ROUTE_TOKEN = "working directly"
STILL_OPEN_TOKENS = ("legitimate", "remains open")

#: Sentence boundaries, applied AFTER flattening the template's hard wraps.
#: MEASURED: the shipped text satisfies the positive predicate under both the
#: newline-preserving and the flattened split, so where the template happens to
#: wrap never decides the verdict.
SENTENCE_BOUNDARY = re.compile(r"[.;:!?]")

HOOK_EVENT_NAME = "SessionStart"


def _refuse(what: str, why: str, how: str) -> int:
    """Degrade loud on stderr, never on stdout, and never block the session."""
    print(f"WHAT: {what} WHY: {why} HOW: {how}", file=sys.stderr)
    return 0


def _read_route_notice() -> str | None:
    """The shipped route notice, or None when it cannot be read unambiguously."""
    resolution = resolve_packaged_asset(ROUTE_NOTICE_ASSET)
    if not resolution.is_usable or resolution.path is None:
        _refuse(
            f"the session-start route notice was not resolved ({resolution.detail}).",
            "the notice must come from exactly one shipped copy, never from a "
            "guess between a developer checkout and an installed tree.",
            "reinstall nWave so the shipped template resolves unambiguously.",
        )
        return None

    try:
        text = resolution.path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        _refuse(
            f"the session-start route notice at {resolution.path} could not be "
            f"read ({error}).",
            "an unreadable notice must not be replaced by an invented one.",
            "restore the shipped template, then start a new session.",
        )
        return None

    notice = text.strip()
    if not notice:
        _refuse(
            f"the session-start route notice at {resolution.path} is empty.",
            "an empty additionalContext would tell the agent nothing while "
            "looking like a delivered notice.",
            "restore the shipped template's content, then start a new session.",
        )
        return None
    return notice


def measure_notice(notice: str) -> tuple[int, int]:
    """The notice's cost in both units: measured bytes, derived token bound.

    Pure: a function of the text alone, so the reported number and the injected
    number cannot drift apart.
    """
    measured_bytes = len(notice.encode("utf-8"))
    return measured_bytes, math.ceil(measured_bytes / 4)


def _report(measured_bytes: int, derived_tokens: int) -> str:
    """The measurement, labelled so an operator and a check read one number."""
    return (
        f"bytes={measured_bytes} tokens={derived_tokens} ({TOKEN_PROVENANCE}); "
        f"permitted={NOTICE_CEILING_BYTES} "
        f"(a {NOTICE_CEILING_TOKENS} token upper bound)"
    )


def sentences_of(notice: str) -> tuple[str, ...]:
    """The notice cut into sentences, with the template's hard wraps flattened.

    Pure. Flattening first is what keeps the verdict independent of where the
    shipped template happens to wrap a line.
    """
    flattened = " ".join(notice.split())
    parts = (part.strip() for part in SENTENCE_BOUNDARY.split(flattened))
    return tuple(part for part in parts if part)


def first_commanding_phrase(notice: str) -> str | None:
    """The first DECLARED phrase the notice carries, in declaration order.

    Pure, and decidable: membership in a closed list, never a judgement about
    whether some wording reads as commanding.
    """
    folded = notice.lower()
    for phrase in COMMANDING_PHRASES:
        if phrase in folded:
            return phrase
    return None


def states_direct_route_remains_open(notice: str) -> bool:
    """Does some ONE sentence keep working directly stated as an answer?

    Pure. Sentence-level co-occurrence, because the words "working directly"
    also open the third route entry: whole-text presence would not discriminate.
    """
    for sentence in sentences_of(notice):
        folded = sentence.lower()
        if DIRECT_ROUTE_TOKEN in folded and any(
            token in folded for token in STILL_OPEN_TOKENS
        ):
            return True
    return False


def _descriptive_report(verdict: str) -> str:
    """State that the guard RAN, and over how much -- unfired is not evidence.

    Carries none of ``bytes=``, ``tokens=`` or ``permitted=``: the size
    observation reads each of those as a label occurring exactly once in this
    same stderr, so a second occurrence would break it.
    """
    return f"descriptive={verdict} phrases-checked={len(COMMANDING_PHRASES)}"


def emit_admission_warning(registration: object) -> int:
    """Deliver one safety reply; native hosts may still proceed after exit 0."""
    warning = getattr(registration, "notice", "") or (
        "nWave session admission is unknown; installation safety was not "
        "established. Close this session and inspect the update state."
    )
    print(warning, file=sys.stderr)
    print(
        json.dumps(
            {
                "systemMessage": warning,
                "hookSpecificOutput": {
                    "hookEventName": HOOK_EVENT_NAME,
                    "additionalContext": warning,
                },
            }
        )
    )
    return 0


def handle_session_start(registration: object | None = None) -> int:
    """Emit the route notice into the agent's starting context. Always exit 0."""
    if registration is not None and not getattr(registration, "admitted", False):
        return emit_admission_warning(registration)
    notice = _read_route_notice()
    if notice is None:
        return 0

    measured_bytes, derived_tokens = measure_notice(notice)
    measurement = _report(measured_bytes, derived_tokens)
    if measured_bytes > NOTICE_CEILING_BYTES:
        # Oversize is the fifth member of the existing refusal family, not a
        # new algebra: no stdout, one WHAT/WHY/HOW line, exit 0.
        return _refuse(
            f"the session-start route notice measures {measurement}, so it "
            "exceeds its declared ceiling and was not injected.",
            "the notice is a standing tax on every session's starting context, "
            "and text that quietly outgrows its budget spends the agent's "
            "context on itself.",
            "shorten the shipped delivery-route notice back within the "
            "permitted size, or raise the declared ceiling deliberately.",
        )

    # The declared order: oversize (above), then commanding wording, then
    # missing legitimacy, then injection. A notice breaking several rules yields
    # exactly ONE refusal, naming the first offence in this order.
    commanding = first_commanding_phrase(notice)
    if commanding is not None:
        print(
            f"nWave session-start route notice: {measurement}; "
            f"{_descriptive_report('refused')}.",
            file=sys.stderr,
        )
        # The sixth member of the existing refusal family, not a new algebra.
        return _refuse(
            f"the session-start route notice commands the route: it carries the "
            f'phrase "{commanding}", so it was not injected.',
            "the notice must DESCRIBE the available routes and never command "
            "one, so that working directly remains an answer the agent can "
            "still give.",
            "restore the shipped delivery-route notice, or deliberately amend "
            "the declared set of forbidden phrases in the session-start notice "
            "handler.",
        )

    if not states_direct_route_remains_open(notice):
        print(
            f"nWave session-start route notice: {measurement}; "
            f"{_descriptive_report('refused')}.",
            file=sys.stderr,
        )
        # The seventh member of the same family, named by its missing property.
        return _refuse(
            "no sentence in the session-start route notice keeps working "
            "directly stated as a still-open answer, so it was not injected.",
            "a notice that names three routes but never says working directly "
            "remains available describes a choice while pushing one answer.",
            "restore the shipped delivery-route notice's sentence stating that "
            "working directly remains open as an answer.",
        )

    print(
        f"nWave session-start route notice: {measurement}; "
        f"{_descriptive_report('pass')}.",
        file=sys.stderr,
    )
    try:
        envelope = sys.stdin.read()
    except (OSError, ValueError):
        envelope = ""
    try:
        event = json.loads(envelope)
        startup = isinstance(event, dict) and event.get("source") == "startup"
    except (TypeError, json.JSONDecodeError):
        startup = False
    check_consent = False
    if startup:
        try:
            from nwave_ai.update.permissions import update_permissions

            check_consent, _install_consent = update_permissions()
        except Exception:
            pass
    try:
        if check_consent:
            from nwave_ai.update.startup import startup_update_context

            update_context = startup_update_context(envelope)
        else:
            update_context = ""
    except Exception as exc:
        update_context = (
            f"Automatic update refused: the consented startup updater could not run ({exc}). "
            "Inspect the selected installation and retry explicitly."
        )
    if update_context:
        print(f"nWave {update_context}", file=sys.stderr)
    additional_context = (
        notice if not update_context else f"{notice}\n\n{update_context}"
    )

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": HOOK_EVENT_NAME,
                    "additionalContext": additional_context,
                }
            }
        )
    )
    return 0
