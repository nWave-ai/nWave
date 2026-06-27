"""Property-based unit tests for the commit-attribution rewrite core.

DELIVER-authored PBT (ADR-025): the domain `rewrite` function is its own driving
port (a pure function — its signature IS the public interface), so calling it
directly is port-to-port testing at domain scope. These properties generalize
the by-example invariants the acceptance scenarios assert:

  * idempotency — re-applying never doubles the trailer;
  * never-corrupt — stripping the injected ``-m`` restores the original chain;
  * trailer validity — a mutate message carries exactly one Claude + one nWave
    ``Co-Authored-By`` trailer;
  * fail-safe — ambiguous shapes (subshell / ``$(...)`` / backtick / unbalanced
    quote) ALWAYS passthrough.

The strip used by never-corrupt removes the single injected ``-m <trailer>``
argument from the raw chain text (production appends exactly ``" -m " +
shlex.quote(TRAILER_BLOCK)`` to the commit segment), so the assertion is the
byte-preservation contract (D8) — not a lossy shlex round-trip.
"""

from __future__ import annotations

import shlex

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from des.domain.commit_attribution.trailer_rewriter import (
    SENTINEL,
    TRAILER_BLOCK,
    rewrite,
)


# The exact argument production appends to the commit segment.
_INJECTED_SUFFIX = " -m " + shlex.quote(TRAILER_BLOCK)
_CLAUDE_COAUTHOR = "Co-Authored-By: Claude <noreply@anthropic.com>"


# ---------------------------------------------------------------------------
# Strategies — commit messages and the message-creating commit shapes
# ---------------------------------------------------------------------------

# Printable messages with neither a double quote, a backslash, nor a `$`/backtick
# (those would either break the double-quoted literal or trip the fail-safe
# command-substitution guard — covered separately by the fail-safe property).
_message = st.text(
    alphabet=st.characters(
        min_codepoint=0x20,
        max_codepoint=0x7E,
        blacklist_characters='"\\$`',
    ),
    min_size=1,
    max_size=40,
).filter(lambda message: SENTINEL not in message)


@st.composite
def _mutating_commit(draw: st.DrawFn) -> str:
    """A message-creating ``git commit`` shape that production must mutate."""
    message = draw(_message)
    prefix = draw(
        st.sampled_from(
            [
                "git commit -m",
                "git commit --no-verify -m",
                "git add -A && git commit -m",
                "cd repo && git commit -m",
                "FOO=bar git commit -m",
                "git status ; git commit -m",
            ]
        )
    )
    suffix = draw(st.sampled_from(["", " || true"]))
    return f'{prefix} "{message}"{suffix}'


@st.composite
def _ambiguous_command(draw: st.DrawFn) -> str:
    """A shape the splitter must decline (fail-safe passthrough)."""
    message = draw(_message)
    return draw(
        st.sampled_from(
            [
                'git commit -m "release $(date +%F)"',
                'git commit -m "build `whoami`"',
                f'git commit -m "{message}',  # unbalanced quote
                f'(git commit -m "{message}")',  # subshell
            ]
        )
    )


# Heredoc-body lines that exercise the DDD-2 stage-1 body-skip: bare `)`,
# parentheses, dangling quotes, stray operators. None may carry the sentinel, and
# none may close the heredoc (so no line is the bare terminator `EOF`).
_heredoc_body_line = st.text(
    alphabet=st.characters(
        min_codepoint=0x20,
        max_codepoint=0x7E,
        blacklist_characters="\n",
    ),
    min_size=0,
    max_size=48,
).filter(lambda line: SENTINEL not in line and line.strip() != "EOF")


@st.composite
def _mutating_heredoc_commit(draw: st.DrawFn) -> str:
    """A standalone / operator-before heredoc commit production MUST mutate.

    Covers ADR-CA-008 increment 1: the standalone `$()`+heredoc shape and the
    operator-before-chained shape, with bodies that deliberately contain `)`,
    parentheses, dangling quotes and stray operators to exercise the DDD-2
    stage-1 body-skip (the counter alone is fooled by a body `)`).
    """
    body = "\n".join(draw(st.lists(_heredoc_body_line, min_size=1, max_size=4)))
    prefix = draw(
        st.sampled_from(
            [
                "git commit -m",
                "git add . && git commit -m",
                "cd repo && git commit -m",
                "FOO=bar git commit -m",
            ]
        )
    )
    return f"{prefix} \"$(cat <<'EOF'\n{body}\nEOF\n)\""


@st.composite
def _heredoc_passthrough_command(draw: st.DrawFn) -> str:
    """A heredoc/substitution shape OUTSIDE the safe boundary — must passthrough.

    The never-corrupt scope cut: operator-after (DDD-5), heredoc-into-`-F`
    (DDD-6), backtick (DDD-1), and shapes the scanner cannot bound (DDD-2):
    unterminated, stacked, here-string, tab-indented, unbalanced `$(`.
    """
    return draw(
        st.sampled_from(
            [
                "git commit -m \"$(cat <<'EOF'\nfeat\nEOF\n)\" && echo done",
                "git commit -F \"$(cat <<'EOF'\nfeat\nEOF\n)\"",
                'git commit -m "build `whoami`"',
                "git commit -m \"$(cat <<'EOF'\nno terminator\n)\"",
                'git commit -m "$(echo unclosed"',
                "git commit -m \"$(cat <<'A' <<'B'\n1\nA\n2\nB\n)\"",
                'git commit -m "$(cat <<< inline)"',
                "git commit -m \"$(cat <<-'EOF'\n\tfeat\n\tEOF\n)\"",
            ]
        )
    )


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------


@given(command=_mutating_commit())
@settings(max_examples=150, deadline=None)
def test_idempotency_never_doubles_the_trailer(command: str) -> None:
    """Re-applying the rewrite to its own output never adds a second trailer."""
    first = rewrite(command)
    assert first.action == "mutate"
    assert first.rewritten_command is not None
    assert first.rewritten_command.count(SENTINEL) == 1

    second = rewrite(first.rewritten_command)
    assert second.action == "passthrough"
    assert second.rewritten_command is None
    # The sentinel still appears exactly once across the (unchanged) command.
    assert first.rewritten_command.count(SENTINEL) == 1


@given(command=_mutating_commit())
@settings(max_examples=150, deadline=None)
def test_never_corrupt_stripping_injection_restores_original(command: str) -> None:
    """Removing the single injected ``-m <trailer>`` restores the original."""
    plan = rewrite(command)
    assert plan.action == "mutate"
    assert plan.rewritten_command is not None

    rewritten = plan.rewritten_command
    # The injection is a single contiguous suffix on the commit segment; removing
    # exactly one occurrence yields the byte-identical original (D8).
    assert _INJECTED_SUFFIX in rewritten
    restored = rewritten.replace(_INJECTED_SUFFIX, "", 1)
    assert restored == command


@given(command=_mutating_commit())
@settings(max_examples=150, deadline=None)
def test_trailer_validity_one_claude_one_nwave(command: str) -> None:
    """A mutate result credits exactly one Claude and one nWave co-author."""
    plan = rewrite(command)
    assert plan.action == "mutate"
    assert plan.rewritten_command is not None
    assert plan.rewritten_command.count(_CLAUDE_COAUTHOR) == 1
    assert plan.rewritten_command.count(SENTINEL) == 1


@given(command=_ambiguous_command())
@settings(max_examples=150, deadline=None)
def test_fail_safe_ambiguous_always_passthrough(command: str) -> None:
    """Ambiguous / unsafe shapes always passthrough with a recorded reason."""
    # Guard: the generated literal must not already carry the sentinel (that is
    # a different passthrough cause, covered by idempotency).
    assume(SENTINEL not in command)
    plan = rewrite(command)
    assert plan.action == "passthrough"
    assert plan.rewritten_command is None
    assert plan.reason != ""


# ---------------------------------------------------------------------------
# Regression — POSIX short-flag normalization (fix-attribution-short-flag-parsing)
# ---------------------------------------------------------------------------
#
# The single-token exact-match flag scan leaked the most common commit forms:
# combined short flags (`-am`, `-sm`) and the attached short value (`-m"x"` →
# `-mx`) were never normalized to `-a -m`, so `-m` was never seen and the commit
# fell through to passthrough. These example-based regressions pin the four leak
# shapes (MUTATE), the value-skip guard, the punt shapes that must STILL
# passthrough through the value-aware path, the no-value tightening, and
# idempotency on a mutated combined-flag command.


@pytest.mark.parametrize(
    "command",
    [
        'git commit -am "x"',  # combined boolean+message short flags
        'git commit -sm "x"',  # signoff + message
        'git commit -m"x"',  # attached short value (shlex → `-mx`)
        "git commit -amx",  # combined + attached value
        'git commit -am "-F"',  # value-skip guard: message is literally `-F`
    ],
)
def test_short_flag_message_commit_is_mutated(command: str) -> None:
    """Combined / attached short-flag commits carry the dual trailer."""
    plan = rewrite(command)
    assert plan.action == "mutate"
    assert plan.rewritten_command is not None
    # Exactly one nWave + one Claude trailer — never doubled, never dropped.
    assert plan.rewritten_command.count(SENTINEL) == 1
    assert plan.rewritten_command.count(_CLAUDE_COAUTHOR) == 1


@pytest.mark.parametrize(
    "command",
    [
        "git commit -aF file",  # template-file punt bundled with -a
        "git commit -F -",  # heredoc/stdin template
        "git commit",  # bare editor
        "git commit -am",  # tightening: no message value → passthrough
    ],
)
def test_short_flag_non_message_commit_is_passthrough(command: str) -> None:
    """Bundled punt shapes and the no-value `-am` run unchanged with a reason."""
    plan = rewrite(command)
    assert plan.action == "passthrough"
    assert plan.rewritten_command is None
    assert plan.reason != ""


def test_short_flag_value_guard_message_is_not_a_punt_flag() -> None:
    """`-am "-F"` injects: the `-F` is the message value, never a template punt."""
    plan = rewrite('git commit -am "-F"')
    assert plan.action == "mutate"
    assert plan.rewritten_command is not None
    assert plan.rewritten_command.count(SENTINEL) == 1


@pytest.mark.parametrize(
    "command",
    [
        'git commit -m "-nC"',  # falsifying example: cluster-lookalike value
        'git commit -m "-aF"',  # boolean-prefixed value resembling template punt
        'git commit -m "-sc"',  # resembles reedit-message punt
    ],
)
def test_message_value_that_looks_like_short_flag_cluster_is_mutated(
    command: str,
) -> None:
    """A `-m` value that resembles a short-flag cluster is a MESSAGE, not flags."""
    plan = rewrite(command)
    assert plan.action == "mutate"
    assert plan.rewritten_command is not None
    assert plan.rewritten_command.count(SENTINEL) == 1
    assert plan.rewritten_command.count(_CLAUDE_COAUTHOR) == 1


def test_short_flag_idempotency_never_doubles_the_trailer() -> None:
    """Re-running a mutated combined-flag commit passes through (sentinel)."""
    first = rewrite('git commit -am "x"')
    assert first.action == "mutate"
    assert first.rewritten_command is not None

    second = rewrite(first.rewritten_command)
    assert second.action == "passthrough"
    assert second.rewritten_command is None
    assert first.rewritten_command.count(SENTINEL) == 1


# ---------------------------------------------------------------------------
# Heredoc / command-substitution coverage (ADR-CA-008 increment 1)
# ---------------------------------------------------------------------------
#
# The standalone `$()`+heredoc shape AND the operator-before-chained shape carry
# the dual trailer deterministically. The semantic placement invariant (byte-prefix
# + trailing-token identity) is the heredoc-body-skip correctness pin — `bash -n`
# syntax alone passes a body-`)` mis-split, so it is NOT the assertion here.

# The exact argument production appends — reused for the byte-prefix assertion.
_HEREDOC_INJECTED = " -m " + shlex.quote(TRAILER_BLOCK)


@given(command=_mutating_heredoc_commit())
@settings(max_examples=200, deadline=None)
def test_heredoc_commit_is_mutated_with_correct_placement(command: str) -> None:
    """A heredoc / $() commit mutates with the trailer placed as a top-level -m.

    The two-part semantic invariant (ADR-CA-008 §8 Layer 2): (1) the original
    command is a byte-prefix of the rewrite up to the appended ` -m <trailer>`;
    (2) ``shlex.split``'s last token is the trailer block verbatim — proving it
    landed as a real argument on the commit, not absorbed into the heredoc body.
    """
    plan = rewrite(command)
    assert plan.action == "mutate"
    assert plan.rewritten_command is not None
    rewritten = plan.rewritten_command
    # (1) byte-prefix: nothing in the original — heredoc body included — mangled.
    assert rewritten == command + _HEREDOC_INJECTED
    # (2) trailing-token identity: the trailer is the last top-level argument.
    # The `_heredoc_body_line` strategy deliberately admits dangling-quote bodies
    # (its docstring exercises "dangling quotes"), on which `shlex` — not being
    # heredoc-aware — raises ValueError. For that class the byte-prefix (1) already
    # proves correct placement (original untouched + trailer appended verbatim), so
    # the trailing-token identity is asserted only when shlex can parse the rewrite
    # — mirroring `last_argv_token` in the acceptance harness's composition.py.
    try:
        tokens = shlex.split(rewritten)
    except ValueError:
        tokens = None
    if tokens is not None:
        assert tokens[-1] == TRAILER_BLOCK
    # Exactly one Claude + one nWave trailer.
    assert rewritten.count(SENTINEL) == 1
    assert rewritten.count(_CLAUDE_COAUTHOR) == 1


@given(command=_mutating_heredoc_commit())
@settings(max_examples=200, deadline=None)
def test_heredoc_idempotency_never_doubles_the_trailer(command: str) -> None:
    """Re-applying the rewrite to a mutated heredoc output passes through."""
    first = rewrite(command)
    assert first.action == "mutate"
    assert first.rewritten_command is not None
    second = rewrite(first.rewritten_command)
    assert second.action == "passthrough"
    assert second.rewritten_command is None
    assert first.rewritten_command.count(SENTINEL) == 1


@given(command=_heredoc_passthrough_command())
@settings(max_examples=100, deadline=None)
def test_heredoc_outside_safe_boundary_passes_through(command: str) -> None:
    """Operator-after / -F / backtick / unbounded heredoc shapes passthrough."""
    plan = rewrite(command)
    assert plan.action == "passthrough"
    assert plan.rewritten_command is None
    assert plan.reason != ""


# --- AB-14 / AB-15: the BLOCKING-bug crafter-pins (body-`)` mis-split class) ---


def test_ab14_body_paren_standalone_lands_trailer_as_top_level_argument() -> None:
    """AB-14 — a bare `)` in the heredoc body must not mis-close the $().

    The body line `fix the foo(bar) call` carries a `)`. Without the DDD-2
    stage-1 body-skip the counter decrements to 0 early and the $() mis-closes,
    mis-splitting the command. This pins the CORRECT mutate: byte-prefix holds AND
    the trailer is the last top-level argument.
    """
    command = "git commit -m \"$(cat <<'EOF'\nfix the foo(bar) call\nEOF\n)\""
    plan = rewrite(command)
    assert plan.action == "mutate"
    assert plan.rewritten_command is not None
    assert plan.rewritten_command == command + _HEREDOC_INJECTED
    assert shlex.split(plan.rewritten_command)[-1] == TRAILER_BLOCK


def test_ab15_body_paren_chained_before_lands_trailer_as_top_level_argument() -> None:
    """AB-15 — body-`)` inside the operator-before-chained shape.

    Pairs with AB-14 to prove the body-skip across both shapes: the `&&` splits at
    depth 0 before `$(`, the body-skip protects the counter through the body `)`,
    and the trailer appends to the commit segment as a top-level argument.
    """
    command = "git add . && git commit -m \"$(cat <<'EOF'\nfix the foo(bar)\nEOF\n)\""
    plan = rewrite(command)
    assert plan.action == "mutate"
    assert plan.rewritten_command is not None
    assert plan.rewritten_command == command + _HEREDOC_INJECTED
    assert shlex.split(plan.rewritten_command)[-1] == TRAILER_BLOCK
