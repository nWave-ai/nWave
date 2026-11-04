# DES Markers Reference (historical)

**Status: historical record, no live instructions.** The DES task-prompt markers
belong to a retired orchestration. The current route uses `nwdes`: `nwdes prompt`
builds each role bundle and emits no marker, and roles record typed values with
their kind verbs. No step of the current route writes the markers on this page.
Keep this page to read old logs, ADRs and audit records; never follow it to
configure or run a delivery. Use `nwdes --help` and the
[nwdes command reference](../guides/nwdes/reference/index.md) instead.

The records this page mentions are gone in v4. Delivery state lives in the nwdes
handoff (`docs/feature/ID/handoff.json`) with its run records. `roadmap.json` and
`execution-log.json` were removed with no converter, and the installed hooks block
every direct write to `execution-log.json`. See
[Migrate from nWave 3.x](../guides/migrating-from-3x.md).

Task prompts dispatched through the retired DES orchestrator embedded HTML-comment
markers that carried execution context. Hooks (`pre_tool_use`,
`subagent_stop`, `deliver_progress`) parsed them via
`des.domain.des_marker_parser.DesMarkerParser` to validate, route, and
audit each Task invocation.

## Syntax

```
<!-- DES-{NAME} : {VALUE} -->
```

Whitespace around the colon and inside the comment is tolerated; values
must be single tokens (no spaces).

## Markers

### `DES-VALIDATION`

| Value | Semantics |
|---|---|
| `required` | Prompt is a DES Task; hooks MUST enforce validation gates |

Absent marker: prompt bypasses DES (non-DES agent passthrough).

### `DES-MODE`

| Value | Semantics |
|---|---|
| `orchestrator` | Caller is the DES orchestrator (allowed to write `execution-log.json`) |

Absent marker: caller is a sub-agent (execution-log writes restricted).

### `DES-PROJECT-ID`

Feature identifier. Required when `DES-VALIDATION=required`. Value: kebab-case
slug matching the `docs/feature/<id>/` directory name.

Example: `<!-- DES-PROJECT-ID : fix-des-worktree-project-root-marker -->`

### `DES-STEP-ID`

Roadmap step identifier. Required when `DES-VALIDATION=required`. Format:
`<phase>-<step>` (e.g. `01-01`, `03-04`). Matches `phases[].steps[].id` in
`roadmap.json`.

### `DES-PROJECT-ROOT` *(added 2026-05-19, Rex RCA F-DES-WORKTREE-EXECUTION-LOG-RESOLUTION)*

Absolute path to the worktree-rooted project directory.

**Purpose**: declare the executing worktree's filesystem root so hook
resolvers find the correct `execution-log.json` when the orchestrator's
startup CWD differs from the worktree where the crafter runs (e.g.
multi-feature parallel dispatch from a long-running orchestrator).

**Validation** (applied by
`des.adapters.drivers.hooks.project_root_validator.validate_project_root`):

1. Value MUST be an absolute path (rejects relative / `~` / unset).
2. Path MUST exist on disk.
3. Path MUST be a git work tree (`git rev-parse --git-common-dir` succeeds).
4. Path MUST share `git-common-dir` with the hook's fallback CWD — i.e.
   belong to the same repository (direct same-repo or sibling worktree of
   the same `.git/`). Prevents path-injection redirecting validation to an
   unrelated repo.

**Resolution priority** (hook handlers `subagent_stop_handler` +
`deliver_progress_handler`):

```
validated DES-PROJECT-ROOT marker  >  hook_input["cwd"]  (fallback)
```

Invalid / absent marker degrades to the previous cwd-only behaviour. The
hook does NOT block on an invalid marker; it logs and falls back.

**Audit trail**: `subagent_stop_handler` emits a `HOOK_INVOKED` event with
handler `subagent_stop_resolved` carrying the resolved
`execution_log_path` and the raw `des_project_root_marker` value (whether
honored or rejected). Post-hoc analysis can trace why a particular
execution-log was chosen.

**Example**:

```
<!-- DES-VALIDATION : required -->
<!-- DES-PROJECT-ID : fix-des-worktree-project-root-marker -->
<!-- DES-STEP-ID : 01-01 -->
<!-- DES-PROJECT-ROOT : /home/u/worktrees/fix-des-worktree -->
```

**Producer**: NONE in the current route. From 2026-07-28 until its retirement,
a retired dispatch command wrote the marker from its `--repo-root` value,
resolved to an absolute path with `Path.resolve()`, the same `resolve()` the
hook-side validator applied, so generator and consumer agreed by construction
rather than by coincidence. That command no longer exists and no surviving step
emits this marker; a replacement producer is not named here because none has
been authored.

The CONSUMER, `project_root_validator.py`, is described above as it behaved
when the markers were live; this page does not promise it still runs.

### `DES-SWARM-ISOLATED-DISPATCH` *(added 2026-07-28)*

Declares that this dispatch runs in an ISOLATED parallel worktree, which DEFERS
the carpaccio slice-order check to integration time. Needed because a swarm
worktree's local ledger carries no `SliceCommitVerified` record for predecessor
slices — those live on trunk — so the order check would otherwise refuse a
legitimately-ready slice.

**Value**: free text naming which worktree this is, and which predecessor
`SliceCommitVerified` record lands at integration.

**Status**: RETIRED — historical marker, with no live producer and no live
consumer. A retired dispatch command wrote it from two flags that were
required together (either flag alone was refused at exit 2 at the authoring
surface), and `carpaccio_intercept.py` read it through `des_marker_parser.py`.
Neither module is part of the current route, so this section records what the
declaration meant, not a surface anything can use today. No replacement
exists; do not treat any current step as emitting it.

The isolation is a DECLARED fact, never inferred: the CLI does not sniff whether
`.git` is a file or a directory, nor inspect the shape of the cwd. A gate decides
on declared facts, never on inferred signals.

```
<!-- DES-SWARM-ISOLATED-DISPATCH : wt/df-slice-05; predecessor slice-04's SliceCommitVerified lands at integration -->
```

## Empirical anchor

Rex RCA 2026-05-19 (feature `fix-des-worktree-project-root-marker`,
wave-decisions record) — audit-2026-05-19.log:270,365 showed
false-positive validation halts where the orchestrator running on master
dispatched a crafter on a worktree; the stop hook read `execution-log`
from master's `docs/feature/...` rather than the worktree's, then
blocked on a non-existent log.
