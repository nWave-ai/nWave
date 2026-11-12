"""Pure decision core of the ``nwave-ai rigor`` command.

Functional core: total functions over immutable data. Every effect (files,
terminal, environment) stays in the shell (``nwave_ai.cli``). Errors are
returned values in ``nwave_ai.platform.result``.

Owned invariants (design record):
- INV1 resolution: project over global over built-in for every value.
- INV2 validation completes before any write plan is composed.
- INV3 the mutate function touches only rigor-owned keys.
- INV5 the review-round default has exactly one definition (this constant).
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from typing import Any

from nwave_ai.platform.result import Failure, Success


#: The single definition of the built-in review-round default (S27, INV5).
DEFAULT_REVIEW_ROUNDS = 2
REVIEW_ROUNDS_RANGE = (1, 5)

#: The Git sentence about the project file; the repository's .gitignore decides it.
PROJECT_FILE_GIT_LINE = (
    "The project file .nwave/config.json: this file may be tracked by Git, "
    "depending on your .gitignore."
)

#: What no examine level checks, stated once for every surface. A row not examined is never green.
NOT_COVERED_ANYWHERE = "security, load or checks on other machines"
NEVER_GREEN = "a row not examined is never green"

#: Width of every line the conversation prints, for screen readers.
TEXT_WIDTH = 78
QUESTION_COUNT = 6

GROUPS = ("producers", "reviewers", "executors")


@dataclass(frozen=True)
class ExamineLevel:
    """One examine level: its name and the repair rounds it grants, and nothing else."""

    name: str
    repair_rounds: int

    @property
    def examinations(self) -> int:
        return 1 + self.repair_rounds


#: The examine levels a person chooses. nwdes keeps its own copy in
#: src/nwdes/contracts.py; a parity test pins the two copies equal.
EXAMINE_LEVELS = (
    ExamineLevel("quick", 0),
    ExamineLevel("standard", 1),
    ExamineLevel("extended", 2),
)
DEFAULT_EXAMINE_LEVEL = "standard"
EXAMINE_LEVEL_NAMES = tuple(level.name for level in EXAMINE_LEVELS)


@dataclass(frozen=True)
class ModelFact:
    """One provider/model pair aimed at a group or a published role."""

    target: str
    provider: str
    model: str


@dataclass(frozen=True)
class RigorAnswers:
    """Answers to the four questions, each Keep or an explicit value."""

    models: tuple[ModelFact, ...] | None  # None = unanswered; () = keep
    review_rounds: int | str | None  # None = unanswered; "current" = keep
    documents: str | None  # None = unanswered; "keep"|"yes"|"no"
    document_language: str | None
    hosts: str | None  # None = unanswered; "keep"|"none"|comma list
    confirmed: bool  # --yes or the interactive confirmation
    examine_level: str | None = None  # None = not answered; "current" = keep


@dataclass(frozen=True)
class Refusal:
    what: str
    why: str = ""
    how: str = ""

    def render(self) -> str:
        parts = [f"WHAT: {self.what}"]
        if self.why:
            parts.append(f"WHY: {self.why}")
        if self.how:
            parts.append(f"HOW: {self.how}")
        return "\n".join(
            line for part in parts for line in _wrapped(part, subsequent="      ")
        )


@dataclass(frozen=True)
class EffectiveScope:
    """The effective result with its sources, the one projection everyone reads."""

    roles: tuple[tuple[str, tuple[str, str]], ...]
    review_rounds: tuple[int, str]
    documents: tuple[dict[str, Any], str]
    examine_level: tuple[str, str] = (DEFAULT_EXAMINE_LEVEL, "built-in default")


@dataclass(frozen=True)
class HostResolution:
    """One host's outcome in the write plan."""

    name: str
    refusal: Refusal | None = None
    disclosure: str = ""  # printed before confirmation
    files: tuple[tuple[str, bytes], ...] = ()  # path (home-relative) -> new bytes
    backup: str | None = None  # path whose previous bytes move to path + ".nwave-bak"


def in_group(group: str, name: str, tools: str) -> bool:
    """Group membership: producers write, reviewers end in -reviewer, crafters end in -crafter.

    The groups overlap by name: a crafter that declares a write tool is both a
    producer and an executor, exactly as the request words them.
    """
    lowered = name.lower()
    if group == "reviewers":
        return lowered.endswith("-reviewer")
    if group == "executors":
        return lowered.endswith("-crafter")
    if group == "producers":
        declared = {part.strip().upper() for part in tools.split(",")}
        return "WRITE" in declared or "EDIT" in declared
    return False


def parse_model_set(
    token: str,
    published_roles: set[str] | frozenset[str] | dict[str, Any],
    groups: tuple[str, ...] = GROUPS,
) -> Success[ModelFact] | Failure[Refusal]:
    """Parse ``GROUP_OR_ROLE=PROVIDER/MODEL``; the pair is stored verbatim."""
    if "=" not in token:
        return Failure(
            Refusal(
                f"--model-set {token} is not target=provider/model.",
                "A model fact must name its target and one provider/model pair.",
                "Use --model-set producers=claude/opus-4-6 or "
                "--model-set nw-code-reviewer=codex/gpt-5.6.",
            )
        )
    target, _, pair = token.partition("=")
    if "/" not in pair:
        return Failure(
            Refusal(
                f"--model-set {token} carries no provider/model pair.",
                "The pair is stored verbatim; without a provider it cannot be read back.",
                "Write provider/model after the equals sign.",
            )
        )
    provider, _, model = pair.partition("/")
    if target in groups:
        return Success(ModelFact(target, provider, model))
    if target in published_roles:
        return Success(ModelFact(target, provider, model))
    return Failure(
        Refusal(
            f"The role name {target!r} is not published.",
            "Only published role names may receive a model fact.",
            "Publish the role under nWave/agents or pick a published role name "
            f"(published: {', '.join(sorted(published_roles))}).",
        )
    )


def _rounds_refusal(token: str) -> Refusal:
    return Refusal(
        f"{token!r} is not valid for review rounds. Valid answers are 1, 2, 3, 4, 5 "
        "and current.",
        "A count is a limit; a number outside 1 to 5 has no meaning.",
        "Supply a whole number from 1 to 5, or current to keep the value in effect.",
    )


def parse_review_rounds(token: str, effective: int) -> Success[int] | Failure[Refusal]:
    """A whole number from 1 to 5, or ``current`` for the value in effect."""
    if token == "current":
        return Success(effective)
    try:
        value = int(token)
    except ValueError:
        return Failure(_rounds_refusal(token))
    low, high = REVIEW_ROUNDS_RANGE
    if not low <= value <= high:
        return Failure(_rounds_refusal(token))
    return Success(value)


def parse_documents(token: str) -> Success[str] | Failure[Refusal]:
    if token in {"keep", "yes", "no"}:
        return Success(token)
    return Failure(
        Refusal(
            f"{token!r} is not valid for documents. Valid answers are keep, yes and no.",
            "The documents choice is a three-way answer.",
            "Supply yes, no or keep.",
        )
    )


def parse_hosts_answer(
    token: str, known: tuple[str, ...]
) -> Success[str] | Failure[Refusal]:
    """keep (or empty), none, or comma-separated declared host names."""
    text = token.strip()
    if text in {"", "keep"}:
        return Success("keep")
    if text == "none":
        return Success("none")
    names = [part.strip() for part in text.split(",") if part.strip()]
    unknown = [name for name in names if name not in known]
    if unknown:
        quoted = ", ".join(repr(name) for name in unknown)
        verb = "is not a known host" if len(unknown) == 1 else "are not known hosts"
        return Failure(
            Refusal(
                f"{quoted} {verb}. Known hosts: {', '.join(known)}.",
                "Only the hosts this installation declares can receive model choices.",
                "Answer again with known host names, or none.",
            )
        )
    return Success(text)


_EXAMPLE_ANSWER = {
    "--models": "keep",
    "--review-rounds": "current",
    "--examine-level": "current",
    "--documents": "keep",
    "--hosts": "none",
    "--document-language": "en",
}


def closed_terminal_refusal(remaining: tuple[str, ...]) -> Refusal:
    """The refusal when input ends: every question still without an answer, named."""
    count = len(remaining)
    noun = "question" if count == 1 else "questions"
    example = " ".join(f"{option} {_EXAMPLE_ANSWER[option]}" for option in remaining)
    return Refusal(
        f"no answer arrived for {count} {noun}: {', '.join(remaining)}. "
        "The terminal closed.",
        "A closed terminal cannot be asked, and a missing answer must not silently "
        "keep the old value.",
        "run the command again with one answer for each option, for example: "
        f"{example}. Or run the command on a terminal and answer the questions.",
    )


def not_covered_here(name: str) -> str:
    """What the level in effect leaves out: the repair rounds beyond its own, from its table row."""
    level = level_named(name)
    if level.repair_rounds == 0:
        return "any repair round"
    plural = "" if level.repair_rounds == 1 else "s"
    return f"more than {level.repair_rounds} repair round{plural}"


def summary_examine_lines(
    chosen: str | None, previous_name: str, previous_source: str
) -> tuple[str, ...]:
    """The examine level rows of the final summary: value, source, what it gives and misses.

    ``chosen`` None or ``current`` keeps the level in effect, and the rows say so.
    """
    changed = chosen not in (None, "current")
    name = chosen if changed else previous_name
    if changed:
        head = f"  examine level: {name} (was {previous_name}, {previous_source})"
    else:
        head = f"  examine level: keep ({previous_name}, {previous_source})"
    return (
        *_wrapped(head, subsequent="    "),
        *_wrapped(f"gives: {describe_examine_level(name)}", "    ", "      "),
        *_wrapped(
            f"not covered: {not_covered_here(name)}, {NOT_COVERED_ANYWHERE}",
            "    ",
            "      ",
        ),
        *_wrapped(NEVER_GREEN, "    ", "      "),
    )


def project_file_git_lines() -> tuple[str, ...]:
    """The Git sentence about the project file, wrapped at the printed width."""
    return tuple(_wrapped(PROJECT_FILE_GIT_LINE))


def _wrapped(text: str, initial: str = "", subsequent: str = "") -> list[str]:
    return textwrap.wrap(
        text,
        width=TEXT_WIDTH,
        initial_indent=initial,
        subsequent_indent=subsequent,
        break_on_hyphens=False,
        break_long_words=False,
    )


def _detail(text: str) -> list[str]:
    indent = "  " if text.startswith("  ") else ""
    continuation = indent + "  " if indent else ""
    return _wrapped(text.strip(), initial=indent, subsequent=continuation)


@dataclass(frozen=True)
class QuestionWords:
    """The words of one question: what it is, why change it, its answers, default and later."""

    what: str
    why: str
    answers: str
    default: str
    later: str
    details: tuple[str, ...] = ()


def question_block(number: int, name: str, words: QuestionWords) -> tuple[str, ...]:
    """One question: its title, the labelled paragraphs, and a blank line; the answer line follows."""
    lines = [f"Question {number} of {QUESTION_COUNT}: {name}", ""]
    lines += _wrapped(f"What it is: {words.what}")
    lines += _wrapped(f"Why change it: {words.why}")
    lines += _wrapped(f"Answers: {words.answers}")
    for detail in words.details:
        lines += _detail(detail)
    lines += _wrapped(f"Default: {words.default}")
    lines += _wrapped(f"Later: {words.later}")
    lines.append("")
    return tuple(lines)


def question(
    option: str, known_hosts: tuple[str, ...], current_language: str
) -> tuple[tuple[str, ...], str]:
    """The block and the answer line of the question an option stands for."""
    if option == "--models":
        return (
            question_block(
                1,
                "model per role",
                QuestionWords(
                    what="the model one role uses for its work. A target is a role name, "
                    "or a group: producers, reviewers, executors.",
                    why="strong models for hard work, fast models for routine work.",
                    answers="keep changes nothing. target=provider/model sets one role or "
                    "group, for example producers=claude/opus-4-6. The value is stored as "
                    "written; nWave does not check it, so a wrong name shows only as a fail "
                    "when the role runs.",
                    default="keep, which leaves the models in effect.",
                    later="run nwave-ai rigor again to change it; --show lists each model "
                    "with its source.",
                ),
            ),
            "Answer (keep, or target=provider/model; Enter = keep): ",
        )
    if option == "--review-rounds":
        return (
            question_block(
                2,
                "review rounds",
                QuestionWords(
                    what="the maximum number of review passes over one piece of work. "
                    "Each round is one check by a reviewer who is not the author.",
                    why="few rounds can leave defects unseen; many rounds can find new "
                    "things and never stop.",
                    answers="a whole number from 1 to 5, or current. Each round costs one "
                    "reviewer run. When a finding is still open at the limit, the work "
                    "stops and the finding goes to its owner. Reaching the limit is never "
                    "an approval.",
                    default=f"{DEFAULT_REVIEW_ROUNDS}, the built-in default.",
                    later="--show prints the rounds with their source.",
                ),
            ),
            "Answer (1-5 or current; Enter = keep): ",
        )
    if option == "--examine-level":
        levels = tuple(
            f"  {level.name}: {describe_examine_level(level.name)}."
            for level in EXAMINE_LEVELS
        )
        return (
            question_block(
                3,
                "examine level",
                QuestionWords(
                    what="EXAMINE: practical check by an examiner who has not seen the code.",
                    why="it finds what automatic tests miss.",
                    answers="quick, standard, extended or current.",
                    details=(
                        *levels,
                        "A longer level is not safer. Repairs used up: NOT EXAMINED, "
                        "never a pass.",
                    ),
                    default=f"{DEFAULT_EXAMINE_LEVEL}: balances cost and risk.",
                    later="--show prints the level with its source.",
                ),
            ),
            "Answer (quick, standard, extended or current; Enter = keep): ",
        )
    if option == "--documents":
        return (
            question_block(
                4,
                "documents for people",
                QuestionWords(
                    what="a readable HTML page for people who do not read code, written "
                    "at the charter close. It uses plain language.",
                    why="share the result with the people who decide, or keep the output "
                    "for engineers only.",
                    answers="yes writes the page at each charter close and asks the "
                    "language next. Only yes asks the language, as question 5; no and "
                    "keep skip it. no writes no page. keep changes nothing.",
                    default="yes: a readable page per charter close; a broken diagram "
                    "refuses the run. Off: --documents no.",
                    later="--show prints the documents choice with its source.",
                ),
            ),
            "Answer (keep, yes or no; Enter = keep): ",
        )
    if option == "--document-language":
        return (
            question_block(
                5,
                "document language",
                QuestionWords(
                    what="the language the readable page is written in.",
                    why="write for the people who read the page, in their language.",
                    answers="a language code, for example en, de or it. The value is "
                    "stored as written.",
                    default=f"{current_language}, the language in effect.",
                    later="--show prints the language with the documents line.",
                ),
            ),
            "Answer (a language code; Enter = keep): ",
        )
    if option == "--hosts":
        return (
            question_block(
                6,
                "hosts",
                QuestionWords(
                    what="the tools on this machine that can also receive the model "
                    "choices.",
                    why="your tool reads its own files, not the project file.",
                    answers="host names separated by commas. The write changes files in "
                    "your home directory. A copy of each changed file is kept beside it, "
                    "with the ending .nwave-bak. codex and devin take no per-role model, "
                    "so they refuse. none and keep write no file.",
                    details=(f"Known hosts: {', '.join(known_hosts)}.",),
                    default="keep, which writes no host file; none does the same.",
                    later="rerun this command with a host list.",
                ),
            ),
            "Answer (host names, none or keep; Enter = keep): ",
        )
    raise ValueError(f"not a rigor question: {option!r}")


def opening_lines(state: tuple[str, ...]) -> tuple[str, ...]:
    """The opening text, printed once, then the values in effect with their sources."""
    return (
        "Quality scope for this project - nwave-ai rigor",
        "",
        *_wrapped(
            "You will answer 6 questions, one at a time. Each question says what it "
            "is, why change it and its default. Press Enter to keep the value in "
            "effect. A wrong answer asks the same question again. Question 5 is asked "
            "only when documents is yes. Nothing is written until you confirm at the "
            "end. The answers go to .nwave/config.json in this repository. The global "
            "file is read, never written."
        ),
        "",
        "What is in effect now:",
        *(f"  {line}" for line in state),
        "",
    )


def group_members(group: str, published: dict[str, str]) -> tuple[str, ...]:
    """Published role names in a group, from their name and declared tools."""
    return tuple(
        name
        for name, tools in sorted(published.items())
        if in_group(group, name, tools)
    )


def validate_answers(
    answers: RigorAnswers, published: dict[str, str]
) -> Success[RigorAnswers] | Failure[Refusal]:
    """INV2: every answer validates before any write plan exists.

    Returns Success of the validated answers or Failure carrying every missing
    question's option, so a script learns all of what it must supply.
    """
    missing: list[str] = []
    if answers.models is None:
        missing.append("--models")
    if answers.review_rounds is None:
        missing.append("--review-rounds")
    if answers.documents is None:
        missing.append("--documents")
    if answers.hosts is None:
        missing.append("--hosts")
    if missing:
        return Failure(
            Refusal(
                "Answers are missing for "
                + ", ".join(missing)
                + ", and no terminal is available to ask.",
                "A script cannot be asked questions; an unanswered question would "
                "silently keep the current value.",
                "Supply every option (" + ", ".join(missing) + ") or run the "
                "command on a terminal.",
            )
        )
    for fact in answers.models or ():
        parsed = parse_model_set(
            f"{fact.target}={fact.provider}/{fact.model}", set(published)
        )
        if isinstance(parsed, Failure):
            return Failure(parsed.error)
    if answers.documents in {"yes"} and not answers.document_language:
        if answers.confirmed:
            return Failure(
                Refusal(
                    "--documents yes requires --document-language.",
                    "The document language cannot be inferred without a terminal.",
                    "Supply --document-language, for example en or de.",
                )
            )
    return Success(answers)


def resolved_review_rounds(
    repo_tier: dict[str, Any], global_tier: dict[str, Any]
) -> tuple[int, str]:
    """INV1: project over global over the built-in default, with its source."""
    review = repo_tier.get("review") if isinstance(repo_tier, dict) else None
    if isinstance(review, dict) and isinstance(review.get("max_rounds"), int):
        return review["max_rounds"], "project"
    review = global_tier.get("review") if isinstance(global_tier, dict) else None
    if isinstance(review, dict) and isinstance(review.get("max_rounds"), int):
        return review["max_rounds"], "global"
    return DEFAULT_REVIEW_ROUNDS, "built-in default"


def resolved_documents(
    repo_tier: dict[str, Any], global_tier: dict[str, Any]
) -> tuple[dict[str, Any], str]:
    """The readable-brief choice with its source; absent means enabled in English."""
    for tier, source in ((repo_tier, "project"), (global_tier, "global")):
        documents = tier.get("documents") if isinstance(tier, dict) else None
        if isinstance(documents, dict):
            brief = documents.get("readable_brief")
            if isinstance(brief, dict) and isinstance(brief.get("enabled"), bool):
                return brief, source
    return {"enabled": True, "language": "en"}, "built-in default"


def resolved_role_model(
    role: str,
    repo_tier: dict[str, Any],
    global_tier: dict[str, Any],
    declared: str,
) -> tuple[str, str]:
    """The role model with its source; ``declared`` is the spec's own model."""
    for tier, source in ((repo_tier, "project"), (global_tier, "global")):
        runtime = tier.get("model_runtime") if isinstance(tier, dict) else None
        if isinstance(runtime, dict):
            roles = runtime.get("roles")
            if isinstance(roles, dict):
                pair = roles.get(role)
                if isinstance(pair, dict):
                    return (
                        f"{pair.get('provider')}/{pair.get('model')}",
                        source,
                    )
    if declared:
        return declared, "built-in default"
    return "none declared in project or global", "built-in default"


def examine_level_line(name: str, source: str) -> str:
    """The examine line the bundle prints: pinned as parity text by tests/nwdes.

    The rigor surfaces print the same level as separate rows; this string is the
    shared description, so a change to the level table shows in both packages.
    """
    return f"examine level: {name} ({source}) - {describe_examine_level(name)}"


def level_named(name: str) -> ExamineLevel:
    """The level a validated name stands for; any other name is a programming error."""
    for level in EXAMINE_LEVELS:
        if level.name == name:
            return level
    raise ValueError(f"not an examine level: {name!r}")


def describe_examine_level(name: str) -> str:
    """The examinations and repair rounds a level grants: the text every surface prints."""
    level = level_named(name)
    examinations = f"{level.examinations} examination" + (
        "" if level.examinations == 1 else "s"
    )
    if level.repair_rounds == 0:
        repairs = "no repair round"
    else:
        repairs = f"{level.repair_rounds} repair round" + (
            "" if level.repair_rounds == 1 else "s"
        )
    return f"{examinations}, {repairs}"


def parse_examine_level(token: str) -> Success[str] | Failure[Refusal]:
    """A level name, or current for the level in effect; every other text is refused."""
    if token == "current" or token in EXAMINE_LEVEL_NAMES:
        return Success(token)
    return Failure(
        Refusal(
            f"examine level {token!r} is not valid. Valid values are quick, "
            "standard, extended and current.",
            "Only three levels exist; each fixes how many examinations a delivery admits.",
            "Supply quick, standard or extended, or current to keep the level in effect.",
        )
    )


def _examine_refusal(source: str, value: object) -> Refusal:
    return Refusal(
        f"examine.level in the {source} file is {value!r}, which is not a level name.",
        "Only quick, standard and extended are levels; each fixes how many examinations a delivery admits.",
        "Set examine.level to quick, standard or extended in that file, or remove it.",
    )


def resolved_examine_level(
    repo_tier: dict[str, Any], global_tier: dict[str, Any]
) -> Success[tuple[str, str]] | Failure[Refusal]:
    """INV1, INV2: project over global over the built-in default; a non-level refuses."""
    for tier, source in ((repo_tier, "project"), (global_tier, "global")):
        examine = tier.get("examine") if isinstance(tier, dict) else None
        if examine is None:
            continue
        if not isinstance(examine, dict):
            return Failure(_examine_refusal(source, examine))
        if "level" not in examine:
            continue
        level = examine["level"]
        if isinstance(level, str) and level in EXAMINE_LEVEL_NAMES:
            return Success((level, source))
        return Failure(_examine_refusal(source, level))
    return Success((DEFAULT_EXAMINE_LEVEL, "built-in default"))


def show_lines(effective: EffectiveScope) -> list[str]:
    """The ``--show`` projection: per role model, review limit, examine level, documents."""
    lines: list[str] = []
    if not effective.roles:
        lines.append("(no published roles found)")
    for role, (pair, source) in effective.roles:
        lines.append(f"role {role}: {pair} ({source})")
    rounds, source = effective.review_rounds
    lines.append(f"review rounds: {rounds} ({source})")
    name, source = effective.examine_level
    lines.append(f"examine level: {name} ({source})")
    lines += _wrapped(f"gives: {describe_examine_level(name)}", "  ", "    ")
    lines += _wrapped(
        f"not covered at this level: {not_covered_here(name)}", "  ", "    "
    )
    lines.append(f"  not covered at any level: {NOT_COVERED_ANYWHERE}")
    lines.append(f"  {NEVER_GREEN}")
    brief, source = effective.documents
    if brief.get("enabled"):
        lines.append(f"documents: yes, language {brief.get('language')} ({source})")
    else:
        lines.append(f"documents: no ({source})")
    return lines


def rigor_mutate(document: dict[str, Any], plan: dict[str, Any]) -> None:
    """INV3: touch only rigor-owned keys; the writer replaces the whole document.

    ``plan`` carries the validated answers; keeps write nothing for their area.
    """
    if plan["review_rounds"] is not None:
        document["review"] = {"max_rounds": plan["review_rounds"]}
    if plan["examine_level"] is not None:
        document["examine"] = {"level": plan["examine_level"]}
    if plan["documents_enabled"] is not None:
        document["documents"] = {
            "readable_brief": {
                "enabled": plan["documents_enabled"],
                "language": plan["documents_language"],
            }
        }
    if plan["role_pairs"]:
        runtime = document.get("model_runtime")
        runtime = dict(runtime) if isinstance(runtime, dict) else {}
        roles = runtime.get("roles")
        roles = dict(roles) if isinstance(roles, dict) else {}
        for role, pair in plan["role_pairs"].items():
            roles[role] = {"provider": pair[0], "model": pair[1]}
        runtime["roles"] = roles
        document["model_runtime"] = runtime


def write_plan(answers: RigorAnswers, published: dict[str, str]) -> dict[str, Any]:
    """The pure project-side plan: which keys change, which roles get pairs."""
    role_pairs: dict[str, tuple[str, str]] = {}
    role_facts: list[ModelFact] = []
    for fact in answers.models or ():
        if fact.target in GROUPS:
            for role in group_members(fact.target, published):
                role_pairs[role] = (fact.provider, fact.model)
                role_facts.append(ModelFact(role, fact.provider, fact.model))
        else:
            role_pairs[fact.target] = (fact.provider, fact.model)
            role_facts.append(fact)
    documents_enabled = None
    documents_language = None
    if answers.documents == "yes":
        documents_enabled = True
        documents_language = answers.document_language or "en"
    elif answers.documents == "no":
        documents_enabled = False
        documents_language = answers.document_language or "en"
    review_rounds = (
        answers.review_rounds if answers.review_rounds != "current" else None
    )
    examine_level = (
        answers.examine_level
        if answers.examine_level not in (None, "current")
        else None
    )
    return {
        "review_rounds": review_rounds,
        "examine_level": examine_level,
        "documents_enabled": documents_enabled,
        "documents_language": documents_language,
        "role_pairs": role_pairs,
        "role_facts": tuple(role_facts),
    }


@dataclass(frozen=True)
class Options:
    """The parsed command line: which question carries which option value."""

    show: bool
    yes: bool
    model_sets: tuple[str, ...] | None
    review_rounds: str | None
    documents: str | None
    document_language: str | None
    hosts: str | None
    examine_level: str | None


def parse_options(argv: tuple[str, ...]) -> Success[Options] | Failure[Refusal]:
    """The pure command-line grammar; the shell renders its refusals."""
    show = False
    yes = False
    model_sets: tuple[str, ...] | None = None
    review_rounds: str | None = None
    documents: str | None = None
    document_language: str | None = None
    hosts: str | None = None
    examine_level: str | None = None
    index = 0
    while index < len(argv):
        option = argv[index]
        if option == "--show":
            show = True
            index += 1
            continue
        if option == "--yes":
            yes = True
            index += 1
            continue
        if option in {
            "--model-set",
            "--review-rounds",
            "--documents",
            "--document-language",
            "--hosts",
            "--examine-level",
            "--models",
        }:
            if index + 1 >= len(argv):
                return Failure(
                    Refusal(
                        f"{option} needs a value.",
                        "Every option carries exactly one value.",
                        "Supply the value after the option.",
                    )
                )
            value = argv[index + 1]
            if option == "--model-set":
                values = [value]
                index += 1
                while index + 1 < len(argv) and not argv[index + 1].startswith("--"):
                    index += 1
                    values.append(argv[index])
                model_sets = (*(model_sets or ()), *values)
                index += 1
                continue
            elif option == "--examine-level" and examine_level is None:
                examine_level = value
            elif option == "--review-rounds" and review_rounds is None:
                review_rounds = value
            elif option == "--documents" and documents is None:
                documents = value
            elif option == "--document-language" and document_language is None:
                document_language = value
            elif option == "--hosts" and hosts is None:
                hosts = value
            elif option == "--models" and value == "keep" and model_sets is None:
                model_sets = ()
            else:
                return Failure(
                    Refusal(
                        f"{option} is given twice or contradicts another option.",
                        "Each question takes one answer.",
                        "Give the option once.",
                    )
                )
            index += 2
            continue
        return Failure(
            Refusal(
                f"Unknown option {option}.",
                "The rigor command does not know it.",
                "Check the usage line and correct the option.",
            )
        )
    return Success(
        Options(
            show=show,
            yes=yes,
            model_sets=model_sets,
            review_rounds=review_rounds,
            documents=documents,
            document_language=document_language,
            hosts=hosts,
            examine_level=examine_level,
        )
    )
