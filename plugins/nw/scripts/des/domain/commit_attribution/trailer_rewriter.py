"""Pure command→command dual-trailer rewrite + fail-safe decision.

The DES-domain rewrite core (ADR-CA-006 / Reuse row R1). Given a Bash command,
decides whether it is a message-creating `git commit` (standalone or inside a
flat `&&`/`;` chain) and, if so, returns a :class:`CommitRewritePlan` whose
``rewritten_command`` injects a second ``-m`` carrying the dual ``Co-Authored-By``
trailer block. On any doubt it returns a passthrough Plan (a missed trailer is
recoverable; a corrupted multi-command commit is not).

Carries the SPIKE Part-A proven mechanism verbatim: inject a *separate* ``-m``
argument (git joins multiple ``-m`` as paragraphs), then ``shlex.join`` the argv
so the emoji/`<email>`/`\\n\\n` payload survives with zero hand-escaping.
Idempotency keys on the sentinel ``Co-Authored-By: nWave <nwave@nwave.ai>``.

Pure, stdlib-only (`shlex`, `dataclasses`) + intra-domain
``des.domain.commit_attribution.shell_segments``. Zero adapter imports
(hexagonal purity, F-D-09).
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from typing import Literal

from des.domain.commit_attribution.shell_segments import (
    SUBSTITUTION_MARKER,
    SegmentSplit,
    mask_substitutions,
    split_top_level,
)


# The dual trailer block. \U0001F916 == 🤖. Body line + blank + two trailers.
# Carried verbatim from the SPIKE (Part A proven).
TRAILER_BLOCK = (
    "\U0001f916 Generated with Claude Code\n\n"
    "Co-Authored-By: Claude <noreply@anthropic.com>\n"
    "Co-Authored-By: nWave <nwave@nwave.ai>"
)

# Idempotency sentinel: presence of this exact trailer means already-attributed.
SENTINEL = "Co-Authored-By: nWave <nwave@nwave.ai>"


@dataclass(frozen=True)
class CommitRewritePlan:
    """The Plan-value the pure core returns (Principle 12 — never an effect).

    Attributes:
        action: ``"mutate"`` when the command is a message-creating git commit
            that should carry the dual trailer; ``"passthrough"`` otherwise.
        rewritten_command: the full rewritten Bash command (commit segment
            extended with a second ``-m``, chain otherwise byte-identical) when
            ``action == "mutate"``; ``None`` on passthrough.
        reason: a short explanation of the decision (e.g. ``"sentinel present"``,
            ``"ambiguous: subshell"``, ``"non-message-creating: -C"``). Always
            populated — drives diagnostics and the passthrough audit trail.
    """

    action: Literal["mutate", "passthrough"]
    rewritten_command: str | None
    reason: str


def rewrite(command: str) -> CommitRewritePlan:
    """Plan the dual-trailer rewrite for a Bash ``command``.

    Returns a mutate Plan (with the rewritten command) when ``command`` is a
    message-creating ``git commit`` — standalone or the commit segment of a flat
    ``&&``/``||``/``;``/``|`` chain — that does not already carry the nWave
    sentinel. Returns a passthrough Plan otherwise: non-git-commit commands,
    non-message-creating commits (`-F`, `-C`/`-c`, `--amend --no-edit`, bare
    editor), already-attributed commands, and every ambiguous/unsafe shape
    (subshell, command-substitution, heredoc, multiple commit segments,
    unbalanced quotes).

    Idempotent by the sentinel: ``rewrite(rewrite(c).rewritten_command)`` is a
    passthrough, so re-applying the rewrite never doubles the trailer.

    Args:
        command: the raw Bash command string from ``tool_input.command``.

    Returns:
        A :class:`CommitRewritePlan`.
    """
    # Idempotency guard. NOTE: this scans the RAW command text, so a commit whose
    # MESSAGE literally contains the sentinel string false-positives to passthrough
    # (accepted — CA-004's belt-and-suspenders may still attribute, and a missed
    # trailer is recoverable; a doubled trailer is the failure we guard against).
    if SENTINEL in command:
        return _passthrough("sentinel present")

    split = split_top_level(command)
    if split.ambiguous:
        return _passthrough(f"ambiguous: {split.reason}")

    commit_indexes = [
        index
        for index, segment in enumerate(split.segments)
        if _is_message_creating_commit(segment)
    ]
    if not commit_indexes:
        return _passthrough(_decline_reason(split.segments))
    if len(commit_indexes) > 1:
        return _passthrough("multiple commit segments")

    commit_index = commit_indexes[0]
    if _has_substitution_after_commit(split, commit_index):
        # Operator-after a `$()`/heredoc commit — DDD-5 deferred residue.
        return _passthrough("operator-after-substitution")
    rewritten = _inject_into_segment(split, commit_index)
    return CommitRewritePlan(
        action="mutate", rewritten_command=rewritten, reason="dual trailer injected"
    )


def _has_substitution_after_commit(split: SegmentSplit, commit_index: int) -> bool:
    """True iff a `$()`-bearing commit has a top-level operator AFTER it (DDD-5).

    A heredoc/`$()` commit is only safe to append to when it is the LAST top-level
    segment — a trailing ``-m`` on a non-final substitution commit would land
    before the later chained command's text, so the operator-AFTER shape declines
    (DDD-5, ``F-HEREDOC-CHAIN-COVERAGE``). The plain ``-m``/``&&`` path — a commit
    segment with no command substitution — keeps CA-006's existing operator-after
    tolerance (``git commit -m "x" || true`` still mutates).
    """
    if commit_index == len(split.segments) - 1:
        return False
    return "$(" in split.segments[commit_index]


def _passthrough(reason: str) -> CommitRewritePlan:
    """Build the decline Plan; ``reason`` is always populated for the audit trail."""
    return CommitRewritePlan(
        action="passthrough", rewritten_command=None, reason=reason
    )


# git global options that take a following value (skipped when locating `commit`).
_GIT_GLOBAL_VALUE_FLAGS = frozenset(
    {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}
)

# Flags that mark a commit whose message is NOT on the command line (O-5 punt).
_REUSE_MESSAGE_FLAGS = frozenset({"-C", "--reuse-message", "-c", "--reedit-message"})
_TEMPLATE_FILE_FLAGS = frozenset({"-F", "--file"})

# `git commit` options that consume the FOLLOWING token as their value. The scan
# must skip that value so a message like ``-m "-F"`` never reads ``-F`` as a real
# flag (D6 — the punt scan is argument-aware, not a flat token sweep).
_COMMIT_VALUE_FLAGS = frozenset(
    {
        "-m",
        "--message",
        "-F",
        "--file",
        "-C",
        "--reuse-message",
        "-c",
        "--reedit-message",
    }
)

# POSIX short-flag normalization (fix-attribution-short-flag-parsing). The flag
# scan is single-token exact-match, so combined short flags (``-am`` → ``-a -m``)
# and attached short values (``-mx`` → ``-m x``) must be expanded into their
# canonical separate-token form BEFORE _commit_options / _flag_in / _is_punted
# see them. Only an allow-listed cluster is expanded; any unknown char aborts the
# expansion for that token (fail-safe — a missed trailer is recoverable, a
# corrupted command is not).

# Boolean short flags that carry no value (each emits as ``-<char>``).
_BOOLEAN_SHORT_FLAGS = frozenset("asvqenSop")
# Value-taking short flags: the cluster stops here; the rest of the token (or, if
# none, the following token via _commit_options) is the value.
_VALUE_SHORT_FLAGS = frozenset("mFCc")


def _is_message_creating_commit(segment: str) -> bool:
    """True iff ``segment`` is a ``git commit`` that takes ``-m`` on the line.

    First masks every top-level `$()` command-substitution to the inert
    :data:`SUBSTITUTION_MARKER` (ADR-CA-008): the heredoc body inside a `$()` may
    carry a dangling quote / `)` that ``shlex.split`` cannot parse, so the
    substitution becomes ONE clean token before the scan runs. When the segment
    carries a `$()`, the mutate predicate additionally requires the ``-m`` value to
    be EXACTLY one substitution — i.e. it masks to the marker ALONE. A substitution
    embedded in surrounding message text (``-m "release $(date +%F)"`` masks to
    ``release MARKER``) stays out of scope and declines (the trailing-append safety
    is only proven when the message value IS the substitution). Then skips
    ``VAR=val`` env prefixes and git global value-flags to locate ``commit``, and
    scans the commit flags argument-aware to require a command-line message (``-m``)
    and the absence of every O-5-punted shape (``-F``, ``-C``/``-c``, ``--amend
    --no-edit``, editor).
    """
    masked = mask_substitutions(segment)
    if masked is None:
        return False
    tokens = _safe_split(masked)
    if tokens is None:
        return False
    tokens = _strip_env_prefix(tokens)
    if not tokens or tokens[0] != "git":
        return False
    rest = _after_git_globals(tokens[1:])
    if not rest or rest[0] != "commit":
        return False
    commit_flags = _expand_short_flags(rest[1:])
    options = _commit_options(commit_flags)
    if not _has_message_with_value(commit_flags):
        return False
    if _is_punted(options):
        return False
    # A `$()` present while the message value is not EXACTLY one substitution is
    # out of increment-1 scope (DDD-3a) — decline (fail-safe).
    return not (
        "$(" in segment and not _message_value_is_lone_substitution(commit_flags)
    )


def _message_value_is_lone_substitution(flags: list[str]) -> bool:
    """True iff a ``-m``/``--message`` value is exactly the masked substitution marker.

    After :func:`mask_substitutions`, a message value that was a single `$()` is the
    bare :data:`SUBSTITUTION_MARKER`; a value that merely embeds a substitution in
    other text masks to ``... MARKER ...`` (the marker is a substring, not the whole
    token). Only the lone-marker form is the provably-safe append shape (DDD-3a).
    """
    last = len(flags) - 1
    for index, token in enumerate(flags):
        if token in {"-m", "--message"} and index < last:
            if flags[index + 1] == SUBSTITUTION_MARKER:
                return True
        if token == f"--message={SUBSTITUTION_MARKER}":
            return True
    return False


def _has_message_with_value(flags: list[str]) -> bool:
    """True iff a ``-m``/``--message`` flag carries a value (attached or following).

    Folds in the user-approved tightening: bare ``git commit -am`` (no message
    value) is NOT message-creating — it would otherwise produce a trailer-only
    commit. After :func:`_expand_short_flags`, a value short flag without a value
    surfaces as a trailing ``-m`` with no following token; ``--message`` requires a
    following token too, while ``--message=...`` carries its value inline.
    """
    last = len(flags) - 1
    for index, token in enumerate(flags):
        if token in {"-m", "--message"} and index < last:
            return True
        if token.startswith("--message="):
            return True
    return False


def _expand_short_flags(flags: list[str]) -> list[str]:
    """Normalize POSIX combined / attached short flags into separate tokens.

    Applied to the commit flags (after ``commit``) so the downstream exact-match
    scan (:func:`_commit_options`, :func:`_flag_in`, :func:`_is_punted`) sees the
    canonical separate-token form. Each short-flag cluster (``-`` + one or more
    chars, not ``--``) is expanded left-to-right:

      * an allow-listed boolean char emits ``-<char>`` and continues;
      * an allow-listed value char emits ``-<char>``, and the cluster STOPS — the
        remainder of the cluster (if any) is emitted as that flag's value token
        (``-mx`` → ``-m`` ``x``; ``-amx`` → ``-a`` ``-m`` ``x``); with no
        remainder the value is the following token (consumed by
        :func:`_commit_options`).

    Argument-aware (value-skip): when an expanded chunk ENDS in a bare value flag
    (its value is the FOLLOWING token, no inline remainder), that following token
    is the flag's VALUE and is kept VERBATIM — never re-interpreted as a flag
    cluster. This mirrors the skip :func:`_commit_options` already performs, so a
    ``-m`` value that merely resembles a cluster (``-m "-nC"``) is not expanded
    into spurious option tokens. Inline-value forms (``-mx`` → ``-m`` ``x``) end
    their chunk with the value itself, so no skip fires and the next real flag
    still expands.

    Fail-safe: the first unrecognized char aborts expansion for that token — the
    ORIGINAL token is kept verbatim (a missed trailer is recoverable; corrupting
    an unknown flag shape is not). Long flags (``--``), values, and bare ``-`` are
    passed through untouched.
    """
    expanded: list[str] = []
    skip_value = False
    for token in flags:
        if skip_value:
            expanded.append(token)  # value token: kept verbatim, never expanded
            skip_value = False
            continue
        chunk = _expand_one_short_flag(token)
        expanded.extend(chunk)
        if chunk and chunk[-1] in _COMMIT_VALUE_FLAGS:
            skip_value = True
    return expanded


def _expand_one_short_flag(token: str) -> list[str]:
    """Expand a single token; return the original (single-element) on any miss."""
    if not _is_short_flag_cluster(token):
        return [token]
    cluster = token[1:]
    parts: list[str] = []
    for position, char in enumerate(cluster):
        if char in _BOOLEAN_SHORT_FLAGS:
            parts.append(f"-{char}")
            continue
        if char in _VALUE_SHORT_FLAGS:
            parts.append(f"-{char}")
            remainder = cluster[position + 1 :]
            if remainder:
                parts.append(remainder)
            return parts
        return [token]  # fail-safe: unknown char → leave token unchanged
    return parts


def _is_short_flag_cluster(token: str) -> bool:
    """True iff ``token`` is a single-dash short-flag cluster (``-x``, not ``--x``)."""
    return len(token) >= 2 and token[0] == "-" and token[1] != "-"


def _commit_options(flags: list[str]) -> list[str]:
    """Return only the OPTION tokens of a commit, dropping each flag's value.

    Walks the tokens left-to-right; when a token is a value-taking option
    (``-m``/``-F``/``-C``/``-c`` and long forms, in their separate-token shape),
    the FOLLOWING token is its value and is skipped — so a message that looks like
    a flag (``-m "-F"``) is never re-classified as a punt flag (D6). The
    ``--flag=value`` attached form carries its value inline, so no skip is needed.
    """
    options: list[str] = []
    index = 0
    while index < len(flags):
        token = flags[index]
        options.append(token)
        if token in _COMMIT_VALUE_FLAGS:
            index += 2
            continue
        index += 1
    return options


def _is_punted(options: list[str]) -> bool:
    """True iff the commit carries an O-5-punted shape we must not rewrite.

    ``options`` is the argument-aware option list from :func:`_commit_options`
    (flag values already dropped), so a flag-like message value cannot trip a
    false punt.
    """
    if any(_flag_in(token, _TEMPLATE_FILE_FLAGS) for token in options):
        return True
    if any(_flag_in(token, _REUSE_MESSAGE_FLAGS) for token in options):
        return True
    return "--amend" in options and "--no-edit" in options


def _flag_in(token: str, flag_set: frozenset[str]) -> bool:
    """Match a token against a flag set, allowing the ``--flag=value`` form."""
    if token in flag_set:
        return True
    return any(
        token.startswith(flag + "=") for flag in flag_set if flag.startswith("--")
    )


def _strip_env_prefix(tokens: list[str]) -> list[str]:
    """Drop leading ``VAR=val`` environment-assignment prefixes."""
    index = 0
    while index < len(tokens) and _is_env_assignment(tokens[index]):
        index += 1
    return tokens[index:]


def _is_env_assignment(token: str) -> bool:
    """True iff ``token`` is a ``NAME=value`` shell env assignment."""
    name, separator, _ = token.partition("=")
    if not separator or not name:
        return False
    if not (name[0].isalpha() or name[0] == "_"):
        return False
    return all(char.isalnum() or char == "_" for char in name)


def _after_git_globals(tokens: list[str]) -> list[str]:
    """Skip git global options to reach the subcommand (e.g. ``commit``)."""
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in _GIT_GLOBAL_VALUE_FLAGS:
            index += 2
            continue
        if token.startswith("-"):
            index += 1
            continue
        break
    return tokens[index:]


def _decline_reason(segments: tuple[str, ...]) -> str:
    """Explain a no-commit-segment passthrough for the audit trail.

    Distinguishes a non-message-creating ``git commit`` (``-F``/``-C``/bare
    editor) from a command that is not a git commit at all. Env-strips first,
    requires ``git`` as the leading token, then skips git globals to look for the
    ``commit`` subcommand — so ``git -C /repo commit -F file`` is still reported
    as a non-message-creating commit, not "not a git commit".
    """
    for segment in segments:
        tokens = _safe_split(segment)
        if tokens is None:
            continue
        stripped = _strip_env_prefix(tokens)
        if not stripped or stripped[0] != "git":
            continue
        after_globals = _after_git_globals(stripped[1:])
        if after_globals and after_globals[0] == "commit":
            return "non-message-creating commit"
    return "not a git commit"


def _inject_into_segment(split: SegmentSplit, commit_index: int) -> str:
    """Append a second ``-m <trailer>`` to the commit segment, re-join the chain.

    The non-commit segments and the operators are preserved byte-for-byte; only
    the commit segment grows by a single ``-m`` argument carrying the dual
    trailer block, serialized via :func:`shlex.quote` so the emoji / ``<email>``
    / ``\\n\\n`` payload survives with zero hand-escaping.
    """
    segments = list(split.segments)
    commit = segments[commit_index]
    trailing_space = len(commit) - len(commit.rstrip())
    body = commit[: len(commit) - trailing_space] if trailing_space else commit
    suffix = commit[len(body) :]
    segments[commit_index] = f"{body} -m {shlex.quote(TRAILER_BLOCK)}{suffix}"
    return _rejoin(segments, split.operators)


def _rejoin(segments: list[str], operators: tuple[str, ...]) -> str:
    """Reassemble segments and operators into the original chain text."""
    parts: list[str] = [segments[0]]
    for operator, segment in zip(operators, segments[1:], strict=True):
        parts.append(operator)
        parts.append(segment)
    return "".join(parts)


def _safe_split(segment: str) -> list[str] | None:
    """``shlex.split`` the segment, returning None on an unparseable shape."""
    try:
        return shlex.split(segment)
    except ValueError:
        return None
