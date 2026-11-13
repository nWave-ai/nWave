"""The Jev section the executor prompt appends, and the resolution of the consent it states.

Consent comes from the first declared source in this order: the --jev flag, the repository
configuration, the global configuration, then authorized. Every declared value is checked,
whichever one wins, so a malformed value is refused rather than ignored. Jev never gates a
step: this section is guidance for the executor, and its outcome is recorded data.
"""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

from nwstep.domain.jev_consent import JevConsent
from nwstep.domain.refusal import Refusal


class Declaration(NamedTuple):
    """One consent source: its name and the raw jev values it declares, none or one."""

    source: str
    values: tuple[object, ...]


AUTHORIZED_SECTION = """
## JEV CONSENT: authorized
Jev is authorized for this run. Before you settle any choice, put each supported semantic question to Jev instead of deciding it by reading alone. Read {skill}/SKILL.md first, then ask with python {skill}/scripts/jev_decide.py --request request.json --output result.json, giving the question and only permitted, minimized state. Batch independent questions and record each answer with the decision it informed.
Never send secrets, personal data, source-blind material or logs with secrets; redact first, and when redaction removes what the question needs, do not send it.
In the craft record, state the Jev outcome as typesafe: requested: REFERENCE to the record of the question, or typesafe: unavailable: REASON when TYPESAFE_API_KEY, the skill path or the service is unavailable. Then continue locally. An unavailable service never blocks the step, and no call is invented. When no choice stayed open, state typesafe: no open choice.
"""

UNAUTHORIZED_SECTION = """
## JEV CONSENT: unauthorized
Jev is refused for this run: transmit nothing to Jev and make no Jev call. In the craft record, state the Jev outcome as typesafe: refused: REASON, naming the source that refused it. Continue locally.
"""


def section(consent: JevConsent, skill: Path) -> str:
    if consent is JevConsent.AUTHORIZED:
        return AUTHORIZED_SECTION.format(skill=skill)
    return UNAUTHORIZED_SECTION


def resolve(declarations: tuple[Declaration, ...]) -> JevConsent:
    """The consent of the first declaring source; every declared value is checked first."""
    return JevConsent.first(*(_declared(declaration) for declaration in declarations))


def _declared(declaration: Declaration) -> JevConsent | None:
    if not declaration.values:
        return None
    raw = declaration.values[0]
    try:
        return JevConsent.parse(raw)
    except ValueError:
        raise Refusal(
            what=f"{declaration.source} declares jev {raw!r}, which is not a Jev consent value",
            why="only authorized and unauthorized are declared consent; any other value is refused rather than ignored, so a typo cannot silently change consent",
            how='declare "authorized" or "unauthorized" in that source (pass --jev authorized or --jev unauthorized, or set "jev" in the file named in WHAT)',
        ) from None
