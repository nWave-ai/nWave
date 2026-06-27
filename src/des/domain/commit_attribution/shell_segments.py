"""Quote-aware top-level shell-operator split + ambiguity detection.

The compound-command core (ADR-CA-006 D2 / Reuse row R2). Splits a Bash command
on top-level `&&` / `||` / `;` operators *outside* quotes and escapes, and
signals fail-safe on any ambiguity the splitter cannot safely resolve: subshell
`(...)`, backtick command-substitution, unbalanced quote, a bare `&` background
operator, or a bare `|` pipe. The single-char `&` / `|` fail-safe is deliberately
distinct from the two-char `&&` / `||` chain operators, which split normally —
splitting on a bare `&` would background the commit and run the injected `-m` as
a separate command (corruption), and a bare `|` pipes the commit (an unusual
shape the never-corrupt design declines).

ADR-CA-008 increment 1 (DDD-1 + DDD-2 stage 1): `$()` command-substitution is now
DEPTH-TRACKED rather than bailed-on — `$(` increments ``subst_depth``, the matching
`)` decrements, and top-level operators split only at ``subst_depth == 0``. When a
heredoc (`<<` / `<<-`, quoted or unquoted delimiter) opens, its body is skipped as
OPAQUE text up to the terminator line — so a bare `)`/quote/operator inside the body
never corrupts the depth counter (the DDD-2 stage-1 body-skip). Anything the scanner
cannot bound (unterminated / stacked / parameter-expanded / `<<<` here-string
heredoc, backtick, bare subshell `(`) still returns ``ambiguous`` ⇒ caller passes
through. Operator-AFTER-substitution (DDD-5) is delimited correctly by depth and is
left for ``rewrite`` to decline.

Pure, stdlib-only. Zero adapter imports (hexagonal purity, F-D-09).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SegmentSplit:
    """Result of splitting a Bash command on top-level shell operators.

    Attributes:
        segments: the command segments in order, operators stripped. Empty when
            ``ambiguous`` is True.
        operators: the operators joining consecutive segments, in order (one
            fewer than ``segments`` for a well-formed chain). Empty when
            ``ambiguous`` is True.
        ambiguous: True when the command contains a shape the splitter declines
            to resolve (subshell, command-substitution, heredoc, unbalanced
            quote, bare `&` background operator, bare `|` pipe, unrecognized
            nesting). The caller MUST fail-safe (passthrough) when this is True.
        reason: human-readable explanation when ``ambiguous`` is True.
    """

    segments: tuple[str, ...]
    operators: tuple[str, ...]
    ambiguous: bool
    reason: str = ""


def _ambiguous(reason: str) -> SegmentSplit:
    """Build the fail-safe result the caller passes through unchanged."""
    return SegmentSplit(segments=(), operators=(), ambiguous=True, reason=reason)


def split_top_level(command: str) -> SegmentSplit:
    """Split ``command`` on top-level `&&`/`||`/`;` outside quotes/escapes.

    Returns a :class:`SegmentSplit`. Top-level operators (`&&`/`||`/`;`) split
    only OUTSIDE quotes and at ``$()`` depth zero (DDD-1). A `$(` increments the
    depth, its matching `)` decrements it; an unbalanced `$(` is fail-safe. When a
    `<<` / `<<-` heredoc opens, its body is consumed as opaque text up to the
    terminator (DDD-2 stage 1), so a body `)`/quote/operator never corrupts the
    depth counter. On any ambiguity the scanner cannot resolve (subshell `(...)`,
    backtick command-substitution, an unbounded / stacked / parameter-expanded /
    here-string heredoc, unbalanced quote or `$(`, a bare `&` background operator,
    a bare `|` pipe), returns ``ambiguous=True`` with an explanatory ``reason`` —
    the caller passes the command through unchanged.

    Args:
        command: the raw Bash command string from ``tool_input.command``.

    Returns:
        SegmentSplit with the ordered segments and joining operators, or an
        ambiguous result signaling fail-safe.
    """
    segments: list[str] = []
    operators: list[str] = []
    buffer: list[str] = []
    quote: str | None = None
    subst_depth = 0
    index = 0
    length = len(command)
    while index < length:
        char = command[index]
        if quote == "'":
            buffer.append(char)
            if char == "'":
                quote = None
            index += 1
            continue
        if quote == '"':
            # Backtick substitution is live inside double quotes — fail-safe
            # (backticks do not nest, so depth-tracking is unsafe — DDD-1).
            if char == "`":
                return _ambiguous("command-substitution: backtick")
            if char == "$" and _opens_substitution(command, index):
                buffer.append("$(")
                subst_depth += 1
                index += 2
                continue
            # `<<` is a heredoc opener ONLY in command position inside a `$()`;
            # inside a plain double-quoted value (depth 0) it is literal text
            # (e.g. the message ``"<<"``). Guard on depth so the body-skip never
            # fires on a quoted literal.
            if subst_depth > 0 and char == "<" and _opens_heredoc(command, index):
                consumed = _skip_heredoc(command, index, buffer)
                if consumed is None:
                    return _ambiguous("heredoc: unbounded")
                index = consumed
                continue
            if char == ")" and subst_depth > 0:
                buffer.append(char)
                subst_depth -= 1
                index += 1
                continue
            buffer.append(char)
            if char == '"':
                quote = None
            index += 1
            continue
        if char == "\\":
            buffer.append(char)
            if index + 1 < length:
                buffer.append(command[index + 1])
                index += 2
                continue
            index += 1
            continue
        if char in ("'", '"'):
            quote = char
            buffer.append(char)
            index += 1
            continue
        if char == "`":
            return _ambiguous("command-substitution: backtick")
        if char == "$" and _opens_substitution(command, index):
            buffer.append("$(")
            subst_depth += 1
            index += 2
            continue
        # Heredoc only inside a `$()` (depth > 0). A bare `<<` on the real
        # top-level command is an unusual redirect shape — decline (never-corrupt).
        if subst_depth > 0 and char == "<" and _opens_heredoc(command, index):
            consumed = _skip_heredoc(command, index, buffer)
            if consumed is None:
                return _ambiguous("heredoc: unbounded")
            index = consumed
            continue
        if char == "<" and _opens_heredoc(command, index):
            return _ambiguous("heredoc")
        if char == ")" and subst_depth > 0:
            buffer.append(char)
            subst_depth -= 1
            index += 1
            continue
        if char == "(":
            return _ambiguous("subshell")
        if subst_depth > 0:
            # Inside a substitution: no top-level split, copy through verbatim.
            buffer.append(char)
            index += 1
            continue
        two_char = command[index : index + 2]
        if two_char in ("&&", "||"):
            segments.append("".join(buffer))
            operators.append(two_char)
            buffer = []
            index += 2
            continue
        # A bare `&` (NOT `&&`) is a background operator: splitting on it would
        # background the commit AND run the injected `-m` as a separate failing
        # command — real corruption. A bare `|` (NOT `||`) pipes the commit, an
        # unusual shape against the never-corrupt design. Both fail-safe.
        if char == "&":
            return _ambiguous("background-operator")
        if char == "|":
            return _ambiguous("pipe-operator")
        if char == ";":
            segments.append("".join(buffer))
            operators.append(char)
            buffer = []
            index += 1
            continue
        buffer.append(char)
        index += 1
    if quote is not None:
        return _ambiguous("unbalanced-quote")
    if subst_depth != 0:
        return _ambiguous("command-substitution: unbalanced $()")
    segments.append("".join(buffer))
    return SegmentSplit(
        segments=tuple(segments),
        operators=tuple(operators),
        ambiguous=False,
    )


def _opens_substitution(command: str, index: int) -> bool:
    """True iff ``command[index:]`` starts a ``$(`` command-substitution."""
    return index + 1 < len(command) and command[index + 1] == "("


def _opens_heredoc(command: str, index: int) -> bool:
    """True iff ``command[index:]`` starts a `<<` heredoc (not a `<` redirect).

    A `<<<` here-string is NOT a heredoc the body-skip can bound, so it is left
    for :func:`_skip_heredoc` to decline (it reads ``<<<`` as a delimiter ``<…``
    and fails to find a terminator ⇒ unbounded ⇒ ambiguous).
    """
    return index + 1 < len(command) and command[index + 1] == "<"


def _skip_heredoc(command: str, index: int, buffer: list[str]) -> int | None:
    """Copy a `<<` heredoc opener + opaque body to ``buffer``; return the next index.

    Extracts the delimiter (handling `<<'EOF'` / `<<"EOF"` quoted forms and bare
    `<<EOF`), copies the rest of the opener line verbatim, then consumes every
    subsequent line as OPAQUE body until the terminator line (the delimiter alone).
    The body bytes are copied to ``buffer`` but NEVER interpreted, so a body
    `)`/quote/operator cannot disturb the caller's depth/quote state (DDD-2).

    Returns the index just past the terminator line. Returns ``None`` when the
    heredoc cannot be bounded so the caller fail-safes:
      * the `<<-` tab-stripping form (declined this increment — the authored spec
        treats tab-indented heredocs as out of the safe boundary);
      * a here-string (`<<<`), parameter-expanded / empty delimiter;
      * a stacked second `<<` heredoc on the same opener line;
      * an unterminated body.
    """
    length = len(command)
    if command[index + 2 : index + 3] == "-":
        return None  # `<<-` declined — tab-indented heredoc out of scope.
    delimiter, opener_end = _read_heredoc_delimiter(command, index + 2)
    if delimiter is None:
        return None
    # Copy the opener (`<<` + raw delimiter token) verbatim.
    buffer.append(command[index:opener_end])
    cursor = opener_end
    # Copy the remainder of the opener line verbatim (it is NOT body yet). A
    # second `<<` on this line is a stacked heredoc the body-skip cannot bound.
    while cursor < length and command[cursor] != "\n":
        if command[cursor] == "<" and command[cursor + 1 : cursor + 2] == "<":
            return None  # stacked heredoc on one opener line — declined.
        buffer.append(command[cursor])
        cursor += 1
    if cursor >= length:
        return None  # heredoc opened but no body/terminator — unbounded.
    # cursor sits on the newline that ends the opener line; body starts after it.
    while cursor < length:
        buffer.append(command[cursor])  # the newline
        cursor += 1
        line_start = cursor
        while cursor < length and command[cursor] != "\n":
            cursor += 1
        line = command[line_start:cursor]
        buffer.append(line)
        if line == delimiter:
            return cursor  # leave the trailing newline (if any) to the caller.
    return None  # ran off the end without seeing the terminator — unbounded.


def _read_heredoc_delimiter(command: str, start: int) -> tuple[str | None, int]:
    """Read the heredoc delimiter token; return ``(delimiter, end_index)``.

    Handles the quoted forms ``'EOF'`` / ``"EOF"`` (the delimiter is the inner
    text) and the bare ``EOF`` form (delimiter chars run until whitespace or a
    shell metacharacter). Returns ``(None, start)`` for an unbounded / empty /
    parameter-expanded delimiter the body-skip cannot trust.
    """
    length = len(command)
    if start >= length:
        return None, start
    opener = command[start]
    if opener in ("'", '"'):
        end = command.find(opener, start + 1)
        if end == -1:
            return None, start
        delimiter = command[start + 1 : end]
        if not delimiter:
            return None, start
        return delimiter, end + 1
    end = start
    while end < length and command[end] not in _DELIMITER_STOP_CHARS:
        end += 1
    delimiter = command[start:end]
    if not delimiter or "$" in delimiter:
        # Empty or parameter-expanded delimiter — cannot bound safely.
        return None, start
    return delimiter, end


# Characters that end a bare (unquoted) heredoc delimiter token.
_DELIMITER_STOP_CHARS = frozenset(" \t\n\"'`)|&;<>(")


# The inert quote-free marker a masked `$()` substitution becomes. Sitting inside
# the existing double quotes, a bare alnum token is a single clean ``shlex`` token,
# so the downstream scan sees ONE value where the opaque heredoc body (which may
# carry dangling quotes / `)` / operators) used to sit. The marker is also the
# exact ``-m`` value the mutate predicate matches: a value that masks to the marker
# ALONE is exactly one substitution (mutate); a value that masks to the marker
# embedded in other text (``release MARKER``) is NOT (passthrough).
SUBSTITUTION_MARKER = "NW0SUBSTITUTION0MARKER"


def mask_substitutions(segment: str) -> str | None:
    """Replace each top-level `$()` in ``segment`` with :data:`SUBSTITUTION_MARKER`.

    The heredoc body inside a `$()` may carry bytes ``shlex.split`` cannot parse
    (a dangling ``"``), so the commit-recognition scan masks each balanced `$()`
    substitution to a single clean marker before shlex sees it. Returns ``None``
    when a substitution is unbounded / unbalanced / encloses an unboundable
    heredoc (the caller fail-safes), mirroring :func:`split_top_level`'s decline.

    Backtick substitution and bare subshells are NOT masked — they keep their raw
    text, so a segment carrying them parses (or fails) exactly as before; the
    mutate predicate only fires on the `$()` shape.
    """
    result: list[str] = []
    quote: str | None = None
    index = 0
    length = len(segment)
    while index < length:
        char = segment[index]
        if quote == "'":
            result.append(char)
            if char == "'":
                quote = None
            index += 1
            continue
        if quote == '"':
            if char == "$" and _opens_substitution(segment, index):
                consumed = _consume_substitution(segment, index)
                if consumed is None:
                    return None
                result.append(SUBSTITUTION_MARKER)
                index = consumed
                continue
            result.append(char)
            if char == '"':
                quote = None
            index += 1
            continue
        if char == "\\":
            result.append(char)
            if index + 1 < length:
                result.append(segment[index + 1])
                index += 2
                continue
            index += 1
            continue
        if char in ("'", '"'):
            quote = char
            result.append(char)
            index += 1
            continue
        if char == "$" and _opens_substitution(segment, index):
            consumed = _consume_substitution(segment, index)
            if consumed is None:
                return None
            result.append(SUBSTITUTION_MARKER)
            index = consumed
            continue
        result.append(char)
        index += 1
    if quote is not None:
        return None
    return "".join(result)


def _consume_substitution(segment: str, index: int) -> int | None:
    """Scan a balanced `$(...)` from ``index``; return the index just past it.

    Tracks `$()` depth and skips heredoc bodies opaquely (DDD-1 + DDD-2) so a body
    `)`/quote never mis-closes the substitution. Returns ``None`` when the
    substitution is unbalanced or encloses an unboundable heredoc.
    """
    sink: list[str] = []
    depth = 1
    quote: str | None = None
    cursor = index + 2  # past the opening `$(`
    length = len(segment)
    while cursor < length:
        char = segment[cursor]
        if quote == "'":
            if char == "'":
                quote = None
            cursor += 1
            continue
        if quote == '"':
            if char == "<" and _opens_heredoc(segment, cursor):
                consumed = _skip_heredoc(segment, cursor, sink)
                if consumed is None:
                    return None
                cursor = consumed
                continue
            if char == '"':
                quote = None
            cursor += 1
            continue
        if char in ("'", '"'):
            quote = char
            cursor += 1
            continue
        if char == "$" and _opens_substitution(segment, cursor):
            depth += 1
            cursor += 2
            continue
        if char == "<" and _opens_heredoc(segment, cursor):
            consumed = _skip_heredoc(segment, cursor, sink)
            if consumed is None:
                return None
            cursor = consumed
            continue
        if char == ")":
            depth -= 1
            cursor += 1
            if depth == 0:
                return cursor
            continue
        cursor += 1
    return None
