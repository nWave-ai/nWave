# nwdes commit

Commit a recording role's owned files, using the repository's configured Git author identity and enabled hooks. nwdes imposes no commit after a close; the orchestrator decides when and how a slice is committed, and the root keeps lane open, compose and integrate. Plain Git commits remain available to humans and outside nwdes deliveries.

## Invocation

Run from the checkout top level. Root and destination options are the [common write options](index.md#common-write-options).

```text
nwdes commit --role ROLE [--feature ID | --epic ID] [--slice S<n>]
  [--repo-root ROOT] [--project-root ROOT] [--global-config FILE]
  [--path FILE ...] --type TYPE --description TEXT [--scope SCOPE] [--body TEXT]
```

| Option | Meaning |
|---|---|
| `--role` | Required recording role from the ownership table below |
| `--slice` | Narrow slice targets, oracles, supports and slice run records; omission selects all designed slices |
| `--path` | Repeatable explicit leaf path; replaces the default selection, never adds a directory or sweeps unrelated files |
| `--type` | Required: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore` or `revert` |
| `--description` | Required subject description |
| `--scope` | Optional conventional-commit message scope, not the delivery's feature or slice scope |
| `--body` | Optional message body |

The message is `TYPE(SCOPE): TEXT`, or `TYPE: TEXT` without a scope. A supplied body follows a blank line. Supply any repository-required trailers in the body; nwdes invents no attribution or review trailer. The repository's hooks still decide whether the message is acceptable. nwdes never passes `--no-verify` or sets author, committer or `SKIP` variables.

A crafter commits a refactor alone with `--type refactor` first, then the behavior change with `--type feat`.

```sh
nwdes commit --feature search --role nw-functional-software-crafter --slice S1 --type feat --scope search --description 'return matching results'
```

Success prints `COMMITTED <sha>` followed by every committed repository-relative path.

## Ownership and selection

With `F` the configured feature directory:

| Role | Owned paths |
|---|---|
| `nw-product-owner` | `F/brief.md`, `F/brief.html`, `F/handoff.json` |
| `nw-solution-architect` | `F/architecture.md`, `F/architecture.html`, `F/handoff.json`, files under the configured ADR destination, and files under `F/design/` |
| `nw-acceptance-designer` | Selected slices' oracle and supports, `F/acceptance.md`, `F/acceptance.html`, `F/handoff.json` |
| `nw-user-examiner` | `F/acceptance.md`, `F/acceptance.html`, `F/handoff.json` |
| `nw-software-crafter` | Any lane file except protected paths (below), including `F/runs/craft.S<n>.json` |
| `nw-functional-software-crafter` | Any lane file except protected paths (below), including `F/runs/craft.S<n>.json` |
| `nw-software-crafter-reviewer` | `F/runs/review.candidate.json` and selected `F/runs/review.slice.S<n>.json` records |
| `nw-acceptance-designer-reviewer` | Selected `F/runs/review.oracle.S<n>.json` records |

The default is the tracked or untracked, nonignored changed files in this owned set, including the role's run record. A crafter's default is instead every changed lane file except protected paths, which are left out silently. `review.candidate.json` remains in its owner's set even when `--slice` narrows slice records. Legacy `review.json` and `review.S<n>.json` files have no owner.

An explicit list commits only those paths. Each named path must be owned by a delivery role, or be a lane file a crafter may commit; one refused path refuses the whole request and lists all such paths. For a crafter, protected paths are refused: each designed oracle or support file the oracle review has not approved, and every file under `F` except its own craft run record. A path owned by another role commits when the requesting role holds its close receipt. Ownership alone does not replace the requesting role's close receipt.

Selected paths are literal filenames, including glob characters. This does not change Git's pathspec mode in repository hooks: a hook can still select tracked files with patterns such as `*.json`.

## Close receipts and the commit lock

Inside Git, a role close records its role, delivery scope, HEAD and the SHA-256 digest of every published path under `<git-dir>/nwdes/closes/<role>.json`. Receipts and the nonblocking OS lock `<git-dir>/nwdes/commit.lock` live in Git metadata, never in the worktree. The OS releases a held lock when its process exits.

In a Git worktree, `nwdes craft close` requires its declared `--role nw-software-crafter` or `--role nw-functional-software-crafter`. Omission refuses `MissingFact: --role` before any lock, write or publication; there is no default and the paradigm never supplies the actor. Outside Git the absent actor remains admitted without a receipt, and a valid supplied actor is otherwise ignored. A craft close writes one actor's receipt, never both, and never adds an actor field to `runs/craft.S<n>.json`.

Every commit and authority close uses that lock. In a Git worktree, an authority close and a typed `nwdes work set` read the handoff and the ADR register once, under that lock. The own-receipt check, which decides the re-close exemption and the work-set refresh, digests the handoff from that read, and the render uses the same handoff and register. Authority closes never wait for one another: several receipts may stand uncommitted at once. In a Git worktree, a typed `nwdes work set` runs under the same lock and refreshes the product owner's receipt for that scope to the bytes it generated, only when that receipt still matches disk and already covers the handoff and every generated path. It never changes another role's receipt, and a held lock refuses it with `CommitInProgress` before any write. A successful commit consumes its receipt. A receipt is retired when every listed file's worktree bytes equal that file at the current lane HEAD, whether committed by nwdes, committed by a human, or reverted; retirement does not compare against the receipt's older HEAD.

A commit requires the requesting role's receipt for this delivery. When `--slice S<n>` is supplied its receipt must name that slice; omission does not narrow the receipt's slice. A changed HEAD refuses `StaleBase`. Selected files are committed as they stand on disk; nwdes does not compare a shared file or ADR with the bytes the receipt recorded, so a hand edit made after the close is committed with the rest.

When Git cannot start or the root is not a Git checkout, authority closes keep their previous outputs and create no lock or receipt. `nwdes commit` instead refuses `InputUnreadable` naming the Git step and reason, with exit 1.

## Refusals and index effects

| Refusal | Cause and remedy |
|---|---|
| `CommitInProgress` | Another invocation holds the OS lock; let it finish, then rerun. Never remove a live lock. |
| `IndexNotClean` | Paths are already staged; use the printed `git restore --staged` command without discarding working-tree changes. |
| `MissingCloseReceipt` | This role and scope have no receipt; close the role's draft first. `StaleBase` is explicitly not run without that receipt. |
| `StaleBase` | Receipt HEAD and current HEAD differ; reconcile the intervening revision and close again. |
| `UnownedFile` | Explicit paths have no owner or are directories; name owned leaf files instead. |
| `ProtectedFile` | A crafter named an unapproved oracle or support file, or a feature record; approve the oracle first. |
| `NothingToCommit` | No owned file was selected. |
| `CommitRejected` | Git or a hook refused the native commit; correct the printed reason and rerun with hooks enabled. |
| `InputUnreadable` | Git or required files cannot be read; correct the reported condition. |

Independent semantic failures are reported together before staging. The initial index must be empty. Only validated present files are added; deleted owned files are removed from the index. A Git or hook rejection restores only the paths this invocation staged, leaving foreign working-tree files alone. Semantic refusals exit 2; input failures exit 1.

Plain Git writers and hooks that themselves stage other paths remain outside the role-commit guarantee. If a role commit changes a candidate identity already printed by compose, compose again and reassess the affected verification, review or examination evidence before integration; never reuse stale identities blindly.
