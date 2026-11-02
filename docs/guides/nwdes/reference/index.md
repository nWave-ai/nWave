# nwdes command reference

This reference is checked against actual help output. Each linked page covers one top-level verb group. Recording commands write the handoff and declared outputs; commit operates on Git and keeps close receipts and its lock in Git metadata, never the worktree. Lane commands manage worktrees. The coding host runs roles and verification.

| Group | Purpose |
|---|---|
| [feature](feature.md) | Create a handoff |
| [slice](slice.md) | Set minimal-route facts |
| [work](work.md) | Set size and value |
| [rework](rework.md) | Set or clear rework |
| [product](product.md) | Record product facts |
| [design](design.md) | Record design facts |
| [acceptance](acceptance.md) | Record acceptance rows |
| [expectations](expectations.md) | Fix or revise expectations |
| [charter](charter.md) | Record the complete Feature's charter |
| [examine](examine.md) | Record examiner verdicts |
| [document](document.md) | Render briefs |
| [delta](delta.md) | Compare handoffs |
| [prompt](prompt.md) | Render role prompts |
| [packet](packet.md) | Render review or examination packets |
| [lane](lane.md) | Optionally isolate work; integrate also removes the lane without force |
| [commit](commit.md) | Commit only the calling role's owned files with configured identity and hooks |
| [measure](#measure) | Read supplied intervals or qualify native delivery measurement |

## Common write options

Run every nwdes command from the top level of the checkout. Roots default to cwd and the repository root; lane verbs resolve the main worktree. These options select the destination for feature, slice, work, rework, CLI role-recording verbs, document and commit.

| Option | Meaning |
|---|---|
| `--repo-root` | Repository root; defaults to cwd |
| `--project-root` | Project root for destination configuration; defaults to the repository root |
| `--global-config` | Global configuration file; default is `~/.nwave/config.json` |
| `--feature` | Feature identity; see each command's help for omission behavior |

IDs use lowercase letters, digits, and hyphens, starting with a letter or digit. nwdes assigns record IDs such as P1, S1, and E1. Single-line values cannot contain line boundaries or surrounding whitespace. nwdes writes the handoff; roles supply typed values, not JSON.

The default feature handoff is `docs/feature/ID/handoff.json`. The default briefs are `brief.md`, `architecture.md`, and `acceptance.md` beside it, with HTML versions. [Configuration](#configuration) selects their directory, not individual filenames. Read the paths printed by the command.

## Role recording

`nwdes prompt` prints the complete role bundle ending with its generated verb reference. Every recording call uses the kind's nwdes CLI verbs and common write options. All recording roles use this one channel; roles never write JSON.

| Owner | Recording surface |
|---|---|
| Product owner: product or charter | `nwdes product` or `nwdes charter` CLI |
| Examiner: expectations or examine | `nwdes expectations` or `nwdes examine` CLI |
| Architect: design | `nwdes design` CLI |
| Acceptance designer: acceptance | `nwdes acceptance` CLI |
| Crafter: implementation or prefactoring | `nwdes craft` CLI |
| Reviewer | `nwdes review` CLI |

The first `add`, `set` or `remove` creates an empty scoped draft. Use `open --from-current` to seed an authority replacement from current rows. nwdes assigns new IDs. `close` requires `--outcome` and `--diagnostic` (or `--diagnostic-file` on the CLI); with no draft it validates empty values. Expectations revisions use `close --revise`.

CLI example for root-recorded product facts:

```sh
nwdes product promise add --feature search --kind Outcome --text 'The search result is returned'
nwdes product slice add --feature search --observation Find --promise P1
nwdes product close --feature search --outcome accepted --diagnostic 'Public facts recorded.'
```

A successful close publishes and removes the draft. A refusal preserves the draft unchanged so the owning role can correct its values. `abort` removes the draft; abort with no draft refuses. Every recording verb takes a per-draft lock and refuses without waiting when held. The root does not submit role replies.

Inside a Git worktree, each role close writes a private receipt under the Git directory. Authority closes and `nwdes commit` use the same nonblocking OS lock; nwdes never refuses a close because another role's close is uncommitted. Outside Git, authority closes preserve their existing outputs and create no lock or receipt; commit refuses `InputUnreadable` naming Git. See the [commit reference](commit.md) for ownership, message fields and every refusal.

Crafters record with the common write options and their assigned `--slice`; reviewers name `--subject oracle`, `slice` or `candidate`, with `--slice` required for oracle and slice and omitted for candidate. nwdes writes `runs/craft.S<n>.json`, `runs/review.oracle.S<n>.json`, `runs/review.slice.S<n>.json` or `runs/review.candidate.json` next to the handoff, without changing it. New run records end with one newline; earlier records without it remain readable. The root keeps no reply copy.

| Kind | Verbs and fields |
|---|---|
| `craft` | `file add --path PATH --change Created\|Modified\|Deleted`; `command add --command COMMAND --exit NUMBER`; `close --outcome accepted\|rejected --diagnostic TEXT [--blocked-by TEXT] [--role {nw-software-crafter,nw-functional-software-crafter}]`; inside Git `--role` is required before any publication, and it is stored only in the close receipt, never the run record |
| `review` | `observation add --text TEXT` or `--text-file PATH`; `observation set\|remove --id R<n>` or `--at N`; `finding add --location LOCATION --obligation TEXT --observation TEXT --remediation TEXT --owner oracle\|design\|implementation\|product`; `close --outcome accepted\|rejected --diagnostic TEXT` refuses `ReviewUnobserved` without an observation and `StaleObservation` for dirty or mismatched commit stamps; `findings --owner OWNER` reads only that owner's findings |


## Measure

```text
nwdes measure --host-sessions ROOT_SESSION_FILE [--candidate COMMIT] [--rework FILE] [--objective-minutes N] [--repo-root ROOT] [--project-root ROOT] [--global-config FILE] [--feature ID | --epic ID]
nwdes measure --requests FILE [--objective-minutes N]
```

Choose exactly one source; each flag may appear once. `--requests` accepts a nonempty JSON array with `role`, nullable `task` and `slice`, UTC `start` and `end`, and boolean `continuation` and `rework`. Its report is explicitly supplied, not host-recorded. The objective is a positive integer printed without a success verdict.

Host mode uses OMP version-3 native request and tool-result clocks. Feature elapsed starts at the earliest linked architect request; a no-architect bugfix starts at the root's first user request. The endpoint is the latest successful examination close, bound by native value-verb replay to a committed postimage or a qualifying current handoff, with exactly the nonempty fixed expectations and every verdict met. The candidate must be a full lowercase commit ID committed before the examination prompt; equality of those seconds is ambiguous. Record-only commits may follow the candidate on the committed path. Current-handoff fallback requires HEAD exactly at the candidate and no changed or untracked path outside the handoff directory.

Roots use the role-verb destination configuration; omitted feature/epic scope must be unambiguous in the native delivery commands. Each role close is reported separately. Recorded command exits are claims, printed apart from native command success/failure. A numeric native exit is reported only from an explicit integer in the harness-owned tool result's `message.details.exitCode`; program output, footer text and recorded exits never supply that number. Missing or malformed exit metadata supplies no numeric exit, not a default zero. Lifecycle qualification is separate from elapsed; integration tail is separate from both role effort and design/intake-to-examination elapsed. Lane-free delivery has no fabricated integration receipt.

Measurement counts only the accepted candidate review, never an embedded review, when any recorded review invocation supplies `--subject`; pre-change deliveries with no such invocation retain their legacy review rule.

Native `--help` reads do not change a draft or publish a close and are excluded from lifecycle replay. The candidate gate uses the latest eligible root examination prompt before the examiner session's first user request; a continuation or later re-prompt cannot replace that association. Opaque observation/output paths do not replace the root prompt clock with an examiner request clock. Draft-start ownership follows successful opens or first edits across linked sessions for the same kind and DraftKey scope until close or abort; a close in another session is not replayable.

| Native command shape | Treatment |
|---|---|
| `nwdes A && nwdes B` with every segment a literal-argv nwdes invocation | Replay each segment in order; quoted or escaped separators remain argument text. |
| Read-only prompt with literal role, task and handoff, opaque `$OUT` observation/output paths, and the observed read-only shell wrapper | Retain its native occurrence/time without expanding parameters or reading observation contents. |
| Review invocation with `--subject oracle`, `slice` or `candidate` | Bind its own subject-and-slice record; only an accepted candidate review satisfies whole-candidate qualification. |
| Pre-change review invocation without `--subject` | Bind its legacy `review.json` or `review.<slice>.json` file; the pre-change review rule applies only when no review invocation in the delivery supplies a subject. |
| Value chain containing a non-nwdes segment, including `cd` | Not replayable; no cwd inference. |
| Unexpanded state-value parameters/substitutions, unknown file-backed values, cross-session drafts, or unbindable evidence | Not bound; never recover values from mutable files or guess another run filename. |

Native `--host-sessions` measurement has been qualified only against a small set of recorded OMP deliveries and their observed command shapes; it is not evidence of general host compatibility or of measurement qualification beyond them. Failed and partial trials on other models are negative results, not successes. When in doubt, prefer `--requests` mode: its report is explicitly supplied rather than replayed.

Role effort is the union of half-open request intervals, not CPU time. Continuations and unanswered requests are counted independently. `--rework` declares `(session, request)` objects with zero-based request indices; undeclared rework is `unknown (not declared)`. Tokens, costs and quality scores are not inferred.

Missing, malformed, unreadable or unbindable host evidence prints `not measured` with its cause and exits zero. Argument grammar errors refuse; supplied-file errors remain refusals. Every host report states: `observation provenance is not verified beyond commit order`. Observations captured before a candidate but supplied later cannot be detected. Measurement is an observation report, not a formal proof.


## Configuration

Destination configuration uses nested JSON objects. The dotted names below describe that object nesting, not literal JSON property names. nwdes reads its configuration keys without interpreting unrelated producers' settings.

### Tier files and precedence

For feature or epic writes, nwdes reads these tiers in ascending precedence. A later tier overrides an earlier value for the same key; omitted keys inherit earlier values or defaults. A missing tier file supplies no overrides.

| Precedence | Tier | File |
|---|---|---|
| Lowest | Global | `--global-config FILE`, default `~/.nwave/config.json` |
| Next | Repository | `<project-root>/.nwave/config.json` |
| Highest, for a feature | Feature | `<project-root>/.nwave/features/<ID>/config.json` |
| Highest, for an epic | Epic | `<project-root>/.nwave/epics/<ID>/config.json` |

`<project-root>` defaults to the repository root. Feature and epic tiers are alternatives selected by the invocation's scope, not two tiers combined. Project-level product rendering uses only global and repository tiers. Output directories are relative to the repository root.

Lane commands instead read global `~/.nwave/config.json` and the resolved main worktree's `.nwave/config.json`; feature and epic tiers do not configure lanes.

### Keys

| Key | Allowed tiers | Value and default |
|---|---|---|
| `nwdes.feature.directory` | Global, repository | Base directory string, default `docs/feature`; appends `/<ID>` |
| `nwdes.epic.directory` | Global, repository | Base directory string, default `docs/epic`; appends `/<ID>` |
| `nwdes.project.directory` | Global, repository | Directory string, default `docs/product`; no ID appended |
| `nwdes.directory` | Feature or epic only | Complete directory string for that scope; overrides its base-directory-plus-ID destination; no extra ID appended |
| `adr.directory` | Global, repository | Repository-wide ADR directory string, default `docs/product/architecture`; refused in feature/epic tiers |
| `lanes.trunk` | Global, repository | Nonempty single-line branch string; no built-in trunk; refused in feature/epic tiers |
| `lanes.disposable` | Global, repository | List of nonempty pattern strings, default empty; refused in feature/epic tiers |
| `jev` | Global, repository | Jev consent: `authorized` or `unauthorized`; persistent, user-owned consent used by `nwdes prompt` when `--jev` is omitted (the flag wins, then the repository tier, then the global tier); with no value declared consent is `authorized` by default; any other value refuses with `ConfigurationMalformed`; nwdes never writes this key; refused in feature/epic tiers |

Directory values must be nonempty repository-relative POSIX paths: no leading slash, backslash, line boundary, edge whitespace, empty path segment, `.` segment or `..` segment. Invalid directory strings refuse with `DestinationInvalid`; wrong value types refuse with `ConfigurationMalformed`. For example, `../escape` is invalid.

Configuration does not rename individual output files. The command's fixed names within its selected directory are `handoff.json`, `brief.md`, `architecture.md`, `acceptance.md` and the corresponding HTML briefs. ADRs use their separate `adr.directory`.

### JSON examples

Merge settings into an existing configuration rather than replacing unrelated settings.

Global file, passed explicitly with `--global-config`:

```json
{
  "nwdes": {
    "feature": {"directory": "global/features"},
    "epic": {"directory": "global/epics"},
    "project": {"directory": "global/product"}
  },
  "adr": {"directory": "docs/decisions"},
  "lanes": {"trunk": "main", "disposable": ["build/"]}
}
```

With no repository or feature override, creating feature `global-example` wrote its handoff to `global/features/global-example/handoff.json`, with briefs beside it. `main` is an example, not a default: choose the project's intended existing trunk. Declare `build/` disposable only if its contents are intentionally safe to delete; this authorizes lane finalization to remove them, not merely ignore them. See [lane](lane.md).

Repository file, `<project-root>/.nwave/config.json`:

```json
{
  "nwdes": {"feature": {"directory": "design/features"}}
}
```

With that repository override, creating feature `repository-example` wrote to `design/features/repository-example/`, overriding the global feature base while inheriting the other global keys.

Feature file, `<project-root>/.nwave/features/scoped-example/config.json`:

```json
{
  "nwdes": {"directory": "special/scoped-docs"}
}
```

With both earlier tiers present, creating feature `scoped-example` wrote to `special/scoped-docs/`, without appending the feature ID. For an epic, place the same scoped shape in `.nwave/epics/<ID>/config.json`.


## Standard results

Write commands report written or unchanged outputs. Read commands print help, prompts, packets, or deltas. A refusal reports WHAT, WHY, and HOW for each detected defect. A successful command is not a workflow approval.

Common refusal names are `MissingFact`, `PartInvalid`, `ConfigurationMalformed`, `HandoffInvalid`, and `DanglingReference`. Closing can also report `RoleNotAccepted`. Read the group's help for its exact list. I/O or missing-asset failures are distinct from invalid supplied facts.

Successful product or design closes, expectations revisions, and owned-promise replacement through `slice set` can report withdrawals. Each notice identifies the removed entry, its retired references, and the role that can record replacement facts. The root chooses whether and when to invoke that role.

These lines accompany existing `WROTE`/`UNCHANGED` path lines only after successful output writing. A successful replacement exits 0 without a refusal on stderr. Failed writes publish no withdrawal notices; identical replay emits none.

Each removed structured entry has one notice, even when it has several retired references. WHAT uses pre-replacement paths and indexes. Parent removal is reported once, not again for its children. Notices follow canonical part/schema order and original array order; cause IDs follow deterministic identity order. Cascading verdict WHY identifies the original withdrawn expectation row and E ID.

Withdrawal removes the dependent entry, not just its citation. It neither aliases retired identities to replacements nor transfers evidence. There is no withdrawal verb, readiness gate, or automatic dispatch: HOW names possible repair roles and submission commands, while the root alone chooses whether and when to invoke them. Existing common write options still select repository and feature. Retained identities do not certify semantic freshness.

For worked commands with observed results, see the [tutorial](../../tutorial-nwdes-first-feature/). For a real delivery, see [Deliver a feature](../deliver-feature.md).
