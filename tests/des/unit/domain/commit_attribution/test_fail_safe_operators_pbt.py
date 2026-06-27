"""Property + example tests for the rewrite-core review-revision fixes.

Covers the security/code-review findings (NEEDS_REVISION) on the rewrite core:

  * D3 — a bare ``&`` background operator must trigger fail-safe passthrough
    (splitting on it would background the commit AND run the injected ``-m`` as
    a separate failing command — real corruption).
  * D2 — a bare ``|`` pipe operator must trigger fail-safe passthrough (unusual
    + against the never-corrupt design; today it silently rewrites a pipe).
  * D6 — the punt-flag scan must be argument-aware: a ``-m`` VALUE that looks
    like a flag (``"-F"``, ``"--amend"``, ``"fix --file parsing"``) MUST mutate;
    a real punt flag (``-F file``, ``-C HEAD``) MUST passthrough.
  * D5 — the decline reason for a non-message-creating commit (``-F file``) is
    ``"non-message-creating commit"``, not ``"not a git commit"``.

Two-char operators ``&&`` / ``||`` are deliberately re-asserted UNAFFECTED so the
single-char fail-safe never regresses the chain operators.

The domain ``rewrite`` / ``split_top_level`` functions are their own driving
ports (pure functions — the signature IS the public interface), so calling them
directly is port-to-port testing at domain scope.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from des.domain.commit_attribution.shell_segments import split_top_level
from des.domain.commit_attribution.trailer_rewriter import rewrite


# ---------------------------------------------------------------------------
# D3 — bare `&` background operator → fail-safe passthrough
# ---------------------------------------------------------------------------


def test_d3_bare_ampersand_background_operator_passes_through() -> None:
    """A trailing bare ``&`` backgrounds the commit — must NOT be rewritten."""
    plan = rewrite('git commit -m "x" &')
    assert plan.action == "passthrough"
    assert plan.rewritten_command is None
    assert plan.reason == "ambiguous: background-operator"


def test_d3_split_top_level_flags_bare_ampersand_ambiguous() -> None:
    """The splitter itself declines a bare ``&`` (fail-safe at the core)."""
    split = split_top_level('git commit -m "x" &')
    assert split.ambiguous is True
    assert split.reason == "background-operator"


@given(
    message=st.text(
        alphabet=st.characters(
            min_codepoint=0x20, max_codepoint=0x7E, blacklist_characters='"\\$`&|'
        ),
        min_size=1,
        max_size=20,
    )
)
@settings(max_examples=50, deadline=None)
def test_d3_any_backgrounded_commit_passes_through(message: str) -> None:
    """No backgrounded commit shape is ever mutated (never-corrupt)."""
    plan = rewrite(f'git commit -m "{message}" &')
    assert plan.action == "passthrough"
    assert plan.rewritten_command is None


# ---------------------------------------------------------------------------
# D2 — bare `|` pipe operator → fail-safe passthrough
# ---------------------------------------------------------------------------


def test_d2_pipe_into_commit_passes_through() -> None:
    """``echo x | git commit -m "y"`` must NOT be rewritten (fail-safe)."""
    plan = rewrite('echo x | git commit -m "y"')
    assert plan.action == "passthrough"
    assert plan.rewritten_command is None
    assert plan.reason == "ambiguous: pipe-operator"


def test_d2_commit_piped_to_command_passes_through() -> None:
    """``git commit -m "x" | tee log`` must NOT be rewritten (fail-safe)."""
    plan = rewrite('git commit -m "x" | tee log')
    assert plan.action == "passthrough"
    assert plan.rewritten_command is None
    assert plan.reason == "ambiguous: pipe-operator"


def test_d2_split_top_level_flags_bare_pipe_ambiguous() -> None:
    """The splitter itself declines a bare ``|`` (fail-safe at the core)."""
    split = split_top_level('echo x | git commit -m "y"')
    assert split.ambiguous is True
    assert split.reason == "pipe-operator"


# ---------------------------------------------------------------------------
# `&&` / `||` UNAFFECTED — single-char fail-safe must not regress chains
# ---------------------------------------------------------------------------


def test_two_char_and_operator_still_mutates() -> None:
    """``&&`` chains are unaffected by the bare-``&`` fail-safe."""
    plan = rewrite('git add -A && git commit -m "x"')
    assert plan.action == "mutate"
    assert plan.rewritten_command is not None


def test_two_char_or_operator_still_mutates() -> None:
    """``||`` chains are unaffected by the bare-``&`` fail-safe."""
    plan = rewrite('git commit -m "x" || true')
    assert plan.action == "mutate"
    assert plan.rewritten_command is not None


def test_split_top_level_preserves_double_operators() -> None:
    """The splitter still splits on ``&&`` / ``||`` (not the bare forms)."""
    split = split_top_level('git add -A && git commit -m "x" || true')
    assert split.ambiguous is False
    assert split.operators == ("&&", "||")


# ---------------------------------------------------------------------------
# D6 — punt-flag scan is argument-aware (flag-like message MUTATES)
# ---------------------------------------------------------------------------


def test_d6_message_that_looks_like_template_flag_mutates() -> None:
    """``git commit -m "-F"`` — the value ``-F`` is a MESSAGE, must mutate."""
    plan = rewrite('git commit -m "-F"')
    assert plan.action == "mutate"
    assert plan.rewritten_command is not None


def test_d6_message_that_looks_like_amend_flag_mutates() -> None:
    """``git commit -m "--amend"`` — the value is a MESSAGE, must mutate."""
    plan = rewrite('git commit -m "--amend"')
    assert plan.action == "mutate"
    assert plan.rewritten_command is not None


def test_d6_message_containing_flag_text_mutates() -> None:
    """``git commit -m "fix --file parsing"`` — message text, must mutate."""
    plan = rewrite('git commit -m "fix --file parsing"')
    assert plan.action == "mutate"
    assert plan.rewritten_command is not None


def test_d6_message_that_looks_like_reuse_flag_mutates() -> None:
    """``git commit -m "-C"`` — the value ``-C`` is a MESSAGE, must mutate."""
    plan = rewrite('git commit -m "-C"')
    assert plan.action == "mutate"
    assert plan.rewritten_command is not None


# ---------------------------------------------------------------------------
# D6 guardrail — real punt flags MUST still passthrough
# ---------------------------------------------------------------------------


def test_d6_real_template_file_flag_passes_through() -> None:
    """``git commit -F changelog.txt`` is a real ``-F`` punt — passthrough."""
    plan = rewrite("git commit -F changelog.txt")
    assert plan.action == "passthrough"
    assert plan.rewritten_command is None


def test_d6_real_reuse_message_flag_passes_through() -> None:
    """``git commit -C HEAD`` is a real ``-C`` punt — passthrough."""
    plan = rewrite("git commit -C HEAD")
    assert plan.action == "passthrough"
    assert plan.rewritten_command is None


def test_d6_real_lowercase_reuse_flag_passes_through() -> None:
    """``git commit -c HEAD`` is a real ``-c`` punt — passthrough."""
    plan = rewrite("git commit -c HEAD")
    assert plan.action == "passthrough"
    assert plan.rewritten_command is None


def test_d6_amend_no_edit_passes_through() -> None:
    """``git commit --amend --no-edit`` reuses HEAD's message — passthrough."""
    plan = rewrite("git commit --amend --no-edit")
    assert plan.action == "passthrough"
    assert plan.rewritten_command is None


def test_d6_bare_editor_commit_passes_through() -> None:
    """``git commit`` opens the editor (no ``-m``) — passthrough."""
    plan = rewrite("git commit")
    assert plan.action == "passthrough"
    assert plan.rewritten_command is None


# ---------------------------------------------------------------------------
# D5 — decline reason for a non-message-creating commit
# ---------------------------------------------------------------------------


def test_d5_decline_reason_for_template_file_commit() -> None:
    """``git commit -F file`` declines as a non-message-creating commit."""
    plan = rewrite("git commit -F msg.txt")
    assert plan.action == "passthrough"
    assert plan.reason == "non-message-creating commit"


def test_d5_decline_reason_for_global_flag_template_file_commit() -> None:
    """``git -C /repo commit -F file`` — global flags do not lose the reason."""
    plan = rewrite("git -C /repo commit -F msg.txt")
    assert plan.action == "passthrough"
    assert plan.reason == "non-message-creating commit"


def test_d5_decline_reason_for_non_git_command() -> None:
    """A genuinely non-git command still reports ``not a git commit``."""
    plan = rewrite("echo hello")
    assert plan.action == "passthrough"
    assert plan.reason == "not a git commit"
