"""Domain types for the PreToolUse commit-attribution feature.

Every domain noun used in the `.feature` files is expressed once here as a typed
enum or NewType (Mandate-12 criterion 1). Step bodies and the composition consume
these typed parameters — no raw `str` where a domain enum exists.

The feature has two driving surfaces:

  * the pure rewrite core, exercised through `CommitAttributionService.plan_rewrite`
    (Layer 3 composition root, return-only) — `Decision` is its observable;
  * the PreToolUse hook adapter, exercised through the real `pre-tool-use` entry
    point via subprocess (Layer 4 wiring_e2e) — `HookOutcome` is its observable.

`CommandShape` enumerates the command shapes the rewrite must classify: the
MUTATE family (a message-creating `git commit`, standalone or in a flat chain)
and the PASSTHROUGH family (ambiguous/unsafe shapes, non-message-creating
commits, non-commit commands, already-attributed commands).
"""

from __future__ import annotations

from enum import Enum
from typing import NewType


# A raw Bash command string as it arrives in `tool_input.command`.
BashCommand = NewType("BashCommand", str)


class Decision(str, Enum):
    """The user-observable decision the rewrite core returns for a command.

    MUTATE      — the command is a message-creating `git commit`; the rewrite
                  injects the dual trailer into that commit's segment.
    PASSTHROUGH — the command runs unchanged (no trailer): non-commit, ambiguous,
                  non-message-creating, or already-attributed.
    """

    MUTATE = "mutate"
    PASSTHROUGH = "passthrough"


class CommandShape(str, Enum):
    """The Bash command shapes the rewrite core must classify.

    MUTATE family (a message-creating git commit lands the dual trailer):
      STANDALONE       — `git commit -m "x"`.
      NO_VERIFY        — `git commit --no-verify -m "x"` (git flag is orthogonal).
      COMPOUND_AND     — `git add -A && git commit -m "x"` (rewrite commit only).
      CD_AND           — `cd repo && git commit -m "x"`.
      ENV_PREFIX       — `FOO=bar git commit -m "x"` (env prefix skipped).
      OR_TRUE          — `git commit -m "x" || true` (operator preserved).
      COMMIT_NOT_FIRST — `git status ; git commit -m "x"` (commit later in chain).

    PASSTHROUGH family (the command runs unchanged):
      ALREADY_ATTRIBUTED — the command already carries the nWave sentinel.
      SUBSHELL           — a `$(...)` / backtick command-substitution anywhere.
      UNBALANCED_QUOTE   — an unparseable command (shlex error).
      MULTI_COMMIT       — more than one `git commit` segment in the chain.
      REUSE_MESSAGE      — `git commit -C HEAD` / `-c` (reuses an existing msg).
      AMEND_NO_EDIT      — `git commit --amend --no-edit` (reuses HEAD's msg).
      TEMPLATE_FILE      — `git commit -F msg.txt` (message off the command line).
      BARE_EDITOR        — `git commit` (opens the editor; no `-m`).
      NON_COMMIT_BASH    — a Bash command that is not a git commit (`git status`).
    """

    # MUTATE family
    STANDALONE = "standalone"
    NO_VERIFY = "no_verify"
    COMPOUND_AND = "compound_and"
    CD_AND = "cd_and"
    ENV_PREFIX = "env_prefix"
    OR_TRUE = "or_true"
    COMMIT_NOT_FIRST = "commit_not_first"
    # MUTATE family — POSIX short-flag shapes (fix-attribution-short-flag-parsing)
    SHORT_ALL_MESSAGE = "short_all_message"  # `git commit -am "x"` (combined)
    SHORT_SIGNOFF_MESSAGE = "short_signoff_message"  # `git commit -sm "x"`
    SHORT_ATTACHED_VALUE = "short_attached_value"  # `git commit -m"x"` → `-mx`
    SHORT_COMBINED_ATTACHED = "short_combined_attached"  # `git commit -amx`
    SHORT_FLAG_LIKE_MESSAGE = "short_flag_like_message"  # `-am "-F"` (value guard)
    # MUTATE family — heredoc / $() shapes (ADR-CA-008, increment 1)
    HEREDOC_STANDALONE = "heredoc_standalone"  # `commit -m "$(cat <<'EOF'…EOF)"`
    SUBST_STANDALONE = "subst_standalone"  # `commit -m "$(printf …)"` (no heredoc)
    HEREDOC_CHAINED_BEFORE = "heredoc_chained_before"  # `add . && commit -m "$(…)"`
    HEREDOC_CD_BEFORE = "heredoc_cd_before"  # `cd x && commit -m "$(…heredoc…)"`
    HEREDOC_ENV_BEFORE = "heredoc_env_before"  # `FOO=bar commit -m "$(…heredoc…)"`
    HEREDOC_BODY_PAREN_STANDALONE = "heredoc_body_paren_standalone"  # body `foo(bar)`
    HEREDOC_BODY_PAREN_CHAINED_BEFORE = (
        "heredoc_body_paren_chained_before"  # `add . && …foo(bar)…`
    )

    # PASSTHROUGH family
    ALREADY_ATTRIBUTED = "already_attributed"
    SUBSHELL = "subshell"
    UNBALANCED_QUOTE = "unbalanced_quote"
    MULTI_COMMIT = "multi_commit"
    REUSE_MESSAGE = "reuse_message"
    AMEND_NO_EDIT = "amend_no_edit"
    TEMPLATE_FILE = "template_file"
    BARE_EDITOR = "bare_editor"
    NON_COMMIT_BASH = "non_commit_bash"
    # PASSTHROUGH family — short-flag shapes that must STILL passthrough
    SHORT_TEMPLATE_FILE = "short_template_file"  # `git commit -aF file` (punt)
    SHORT_NO_MESSAGE_VALUE = "short_no_message_value"  # `git commit -am` (tightening)
    # PASSTHROUGH family — heredoc / $() scope boundary (ADR-CA-008 DDD-5/6/2)
    HEREDOC_CHAINED_AFTER = (
        "heredoc_chained_after"  # `commit -m "$(…)" && push` (DDD-5)
    )
    HEREDOC_INTO_TEMPLATE_FILE = (
        "heredoc_into_template_file"  # `commit -F "$(…)"` (DDD-6)
    )
    BACKTICK_SUBST = "backtick_subst"  # `commit -m "\`whoami\`"` (DDD-1 bail)
    HEREDOC_UNTERMINATED = "heredoc_unterminated"  # `<<EOF` with no terminator (DDD-2)
    SUBST_UNBALANCED_PAREN = (
        "subst_unbalanced_paren"  # `$(` with no closing `)` (DDD-2)
    )
    HEREDOC_STACKED = "heredoc_stacked"  # two heredocs on one line (DDD-2 decline)
    HERESTRING = "herestring"  # `<<<` here-string (DDD-2 decline)
    HEREDOC_DASH_INDENT = (
        "heredoc_dash_indent"  # `<<-EOF` tab-strip form (DDD-2 decline)
    )


class HookOutcome(str, Enum):
    """The observable outcome of the PreToolUse hook adapter (subprocess).

    REWRITES_COMMAND — the hook emitted `updatedInput` on stdout carrying the
                       rewritten command (the agent's `git commit` is rewritten
                       before it runs).
    RUNS_UNCHANGED   — the hook produced no `updatedInput` (empty stdout, exit
                       0); the agent's original command runs unchanged.
    """

    REWRITES_COMMAND = "rewrites_command"
    RUNS_UNCHANGED = "runs_unchanged"


# The nWave co-author line — the user-observable trailer the rewrite must land.
# Expressed test-side (not imported from the domain) so the AT asserts on the
# OBSERVABLE output, never on a production internal (S2 — driving-port-only).
# The ALREADY_ATTRIBUTED literal carries it so the rewrite recognizes an
# already-attributed command as a passthrough.
NWAVE_COAUTHOR = "Co-Authored-By: nWave <nwave@nwave.ai>"

# The full dual trailer block the rewrite injects as a second `-m`. Expressed
# test-side as the expected observable so the never-corrupt assertion can strip
# exactly the injected argument and restore the original command.
DUAL_TRAILER_BLOCK = (
    "\U0001f916 Generated with Claude Code\n\n"
    "Co-Authored-By: Claude <noreply@anthropic.com>\n"
    "Co-Authored-By: nWave <nwave@nwave.ai>"
)

COMMAND_BY_SHAPE: dict[CommandShape, str] = {
    CommandShape.STANDALONE: 'git commit -m "feat: add login"',
    CommandShape.NO_VERIFY: 'git commit --no-verify -m "fix: guard null"',
    CommandShape.COMPOUND_AND: 'git add -A && git commit -m "feat: ship it"',
    CommandShape.CD_AND: 'cd repo && git commit -m "chore: tidy"',
    CommandShape.ENV_PREFIX: 'FOO=bar git commit -m "feat: env prefix"',
    CommandShape.OR_TRUE: 'git commit -m "feat: best effort" || true',
    CommandShape.COMMIT_NOT_FIRST: 'git status ; git commit -m "feat: later"',
    CommandShape.SHORT_ALL_MESSAGE: 'git commit -am "feat: stage and ship"',
    CommandShape.SHORT_SIGNOFF_MESSAGE: 'git commit -sm "feat: signed off"',
    CommandShape.SHORT_ATTACHED_VALUE: 'git commit -m"feat: attached"',
    CommandShape.SHORT_COMBINED_ATTACHED: "git commit -amx",
    CommandShape.SHORT_FLAG_LIKE_MESSAGE: 'git commit -am "-F"',
    CommandShape.SHORT_TEMPLATE_FILE: "git commit -aF msg.txt",
    CommandShape.SHORT_NO_MESSAGE_VALUE: "git commit -am",
    # --- heredoc / $() MUTATE shapes (ADR-CA-008, increment 1) ---
    # Claude Code's real standalone shape: $() + quoted heredoc delimiter.
    CommandShape.HEREDOC_STANDALONE: (
        "git commit -m \"$(cat <<'EOF'\nfeat: add login\nEOF\n)\""
    ),
    # Command-substitution without a heredoc (printf) — same append-outside path.
    CommandShape.SUBST_STANDALONE: "git commit -m \"$(printf 'feat: ship')\"",
    # Claude Code's other common shape: operator BEFORE the substitution.
    CommandShape.HEREDOC_CHAINED_BEFORE: (
        "git add . && git commit -m \"$(cat <<'EOF'\nfeat: ship it\nEOF\n)\""
    ),
    CommandShape.HEREDOC_CD_BEFORE: (
        "cd repo && git commit -m \"$(cat <<'EOF'\nchore: tidy\nEOF\n)\""
    ),
    CommandShape.HEREDOC_ENV_BEFORE: (
        "FOO=bar git commit -m \"$(cat <<'EOF'\nfeat: env\nEOF\n)\""
    ),
    # The BLOCKING-bug regressions: a bare `)` in the heredoc body must NOT
    # mis-close the $() (DDD-2 stage-1 body-skip protects the DDD-1 counter).
    CommandShape.HEREDOC_BODY_PAREN_STANDALONE: (
        "git commit -m \"$(cat <<'EOF'\nfix the foo(bar) call\nEOF\n)\""
    ),
    CommandShape.HEREDOC_BODY_PAREN_CHAINED_BEFORE: (
        "git add . && git commit -m \"$(cat <<'EOF'\nfix the foo(bar)\nEOF\n)\""
    ),
    # --- heredoc / $() PASSTHROUGH scope boundary ---
    # Operator AFTER the substitution (DDD-5 — deferred to increment 2).
    CommandShape.HEREDOC_CHAINED_AFTER: (
        "git commit -m \"$(cat <<'EOF'\nfeat: x\nEOF\n)\" && echo done"
    ),
    # Heredoc/$() into -F: message off the command line (DDD-6).
    CommandShape.HEREDOC_INTO_TEMPLATE_FILE: (
        "git commit -F \"$(cat <<'EOF'\nfeat: x\nEOF\n)\""
    ),
    # Backtick substitution keeps bail-on-first-sight (DDD-1, OQ-3).
    CommandShape.BACKTICK_SUBST: 'git commit -m "build `whoami`"',
    # Unbounded/unterminated shapes the scanner cannot bound (DDD-2 decline).
    CommandShape.HEREDOC_UNTERMINATED: (
        "git commit -m \"$(cat <<'EOF'\nno terminator here\n)\""
    ),
    CommandShape.SUBST_UNBALANCED_PAREN: 'git commit -m "$(echo unclosed"',
    CommandShape.HEREDOC_STACKED: (
        "git commit -m \"$(cat <<'A' <<'B'\none\nA\ntwo\nB\n)\""
    ),
    CommandShape.HERESTRING: 'git commit -m "$(cat <<< inline)"',
    CommandShape.HEREDOC_DASH_INDENT: (
        "git commit -m \"$(cat <<-'EOF'\n\tfeat: indented\n\tEOF\n)\""
    ),
    CommandShape.ALREADY_ATTRIBUTED: (
        'git commit -m "feat: done" -m "' + NWAVE_COAUTHOR + '"'
    ),
    CommandShape.SUBSHELL: 'git commit -m "release $(date +%F)"',
    CommandShape.UNBALANCED_QUOTE: 'git commit -m "unterminated',
    CommandShape.MULTI_COMMIT: ('git commit -m "first" && git commit -m "second"'),
    CommandShape.REUSE_MESSAGE: "git commit -C HEAD",
    CommandShape.AMEND_NO_EDIT: "git commit --amend --no-edit",
    CommandShape.TEMPLATE_FILE: "git commit -F msg.txt",
    CommandShape.BARE_EDITOR: "git commit",
    CommandShape.NON_COMMIT_BASH: "git status --short",
}


# Gherkin-phrase → typed-value lookups. Module-level dicts keep each step body a
# single typed lookup + a single composition call (Mandate-12 criterion 3).

SHAPE_BY_PHRASE: dict[str, CommandShape] = {
    "a standalone git commit with a message": CommandShape.STANDALONE,
    "a git commit skipping verification with a message": CommandShape.NO_VERIFY,
    "a staged-then-commit chain": CommandShape.COMPOUND_AND,
    "a change-directory-then-commit chain": CommandShape.CD_AND,
    "an environment-prefixed git commit with a message": CommandShape.ENV_PREFIX,
    "a git commit with a best-effort fallback": CommandShape.OR_TRUE,
    "a status-then-commit chain": CommandShape.COMMIT_NOT_FIRST,
    "a stage-all-and-message git commit with combined short flags": (
        CommandShape.SHORT_ALL_MESSAGE
    ),
    "a sign-off-and-message git commit with combined short flags": (
        CommandShape.SHORT_SIGNOFF_MESSAGE
    ),
    "a git commit with an attached short message value": (
        CommandShape.SHORT_ATTACHED_VALUE
    ),
    "a git commit with combined short flags and an attached value": (
        CommandShape.SHORT_COMBINED_ATTACHED
    ),
    "a combined-short-flag git commit whose message looks like a flag": (
        CommandShape.SHORT_FLAG_LIKE_MESSAGE
    ),
    "a combined-short-flag git commit reading its message from a file": (
        CommandShape.SHORT_TEMPLATE_FILE
    ),
    "a combined-short-flag git commit with no message value": (
        CommandShape.SHORT_NO_MESSAGE_VALUE
    ),
    "a git commit already carrying the nWave co-author": (
        CommandShape.ALREADY_ATTRIBUTED
    ),
    "a git commit whose message embeds a command substitution": (CommandShape.SUBSHELL),
    "a git commit with an unbalanced quote": CommandShape.UNBALANCED_QUOTE,
    "a chain with two separate git commits": CommandShape.MULTI_COMMIT,
    "a git commit reusing an existing message": CommandShape.REUSE_MESSAGE,
    "a git commit amending without editing the message": CommandShape.AMEND_NO_EDIT,
    "a git commit reading its message from a file": CommandShape.TEMPLATE_FILE,
    "a bare git commit that opens the editor": CommandShape.BARE_EDITOR,
    "a Bash command that is not a git commit": CommandShape.NON_COMMIT_BASH,
    # heredoc / $() MUTATE shapes (ADR-CA-008 increment 1)
    "a standalone git commit whose message is a heredoc": (
        CommandShape.HEREDOC_STANDALONE
    ),
    "a standalone git commit whose message is a command substitution": (
        CommandShape.SUBST_STANDALONE
    ),
    "a staged-then-commit chain whose message is a heredoc": (
        CommandShape.HEREDOC_CHAINED_BEFORE
    ),
    "a change-directory-then-commit chain whose message is a heredoc": (
        CommandShape.HEREDOC_CD_BEFORE
    ),
    "an environment-prefixed git commit whose message is a heredoc": (
        CommandShape.HEREDOC_ENV_BEFORE
    ),
    "a standalone heredoc git commit whose body contains a parenthesis": (
        CommandShape.HEREDOC_BODY_PAREN_STANDALONE
    ),
    "a staged-then-commit heredoc chain whose body contains a parenthesis": (
        CommandShape.HEREDOC_BODY_PAREN_CHAINED_BEFORE
    ),
    # heredoc / $() PASSTHROUGH scope boundary
    "a heredoc git commit followed by another command": (
        CommandShape.HEREDOC_CHAINED_AFTER
    ),
    "a git commit reading a heredoc message from a file": (
        CommandShape.HEREDOC_INTO_TEMPLATE_FILE
    ),
    "a git commit whose message embeds a backtick substitution": (
        CommandShape.BACKTICK_SUBST
    ),
    "a git commit with an unterminated heredoc": CommandShape.HEREDOC_UNTERMINATED,
    "a git commit with an unbalanced command substitution": (
        CommandShape.SUBST_UNBALANCED_PAREN
    ),
    "a git commit with two stacked heredocs": CommandShape.HEREDOC_STACKED,
    "a git commit whose message is a here-string": CommandShape.HERESTRING,
    "a git commit with a tab-indented heredoc": CommandShape.HEREDOC_DASH_INDENT,
}
