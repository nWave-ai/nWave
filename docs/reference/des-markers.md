# DES Markers Reference

Task prompts dispatched through the DES orchestrator embed HTML-comment
markers that carry execution context. Hooks (`pre_tool_use`,
`subagent_stop`, `deliver_progress`) parse them via
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
<!-- DES-PROJECT-ROOT : /home/alex/worktrees/fix-des-worktree -->
```

**Scope** (this iteration): marker honored on the hook side. Orchestrator-
side injection (DISPATCH and DELIVER skills emitting the marker) is
tracked under follow-up backlog item `F-DES-WORKTREE-ORCHESTRATOR-
INJECTION`.

## Markers under `workflow.mode = atdd_pure`

The markers above describe the **classic** roadmap-based DELIVER spine. nWave
also ships a roadmap-free sibling spine selected per-feature via
`.nwave/config.yaml:workflow.mode = atdd_pure` (ADR-028). Both spines are
documented here; classic remains the default.

Under `atdd_pure` the marker contract narrows:

- `DES-VALIDATION` and `DES-PROJECT-ID` are unchanged — every `atdd_pure` Task
  still declares them.
- `DES-STEP-ID` no longer references `roadmap.json` (the `atdd_pure` spine
  creates none). Its value is a **carpaccio slice** identifier (`slice-NN`); the
  trailer key name `Step-Id:` is retained for parser compatibility with
  `src/des/cli/verify_commit_trailers.py`.
- `DES-MODE=orchestrator` no longer authorises an `execution-log.json` write:
  the `atdd_pure` spine creates no per-step `execution-log.json`. The phase
  record is instead the **AT-completion ledger** — an append-only per-feature
  JSONL at `.nwave/telemetry/atdd-pure/{feature_id}.jsonl`, carrying `slice_id`
  and `at_ids` at each phase boundary of each slice's `A→G` run. The
  AT-completion ledger is the `atdd_pure` audit artifact that replaces the
  per-step `execution-log.json`; `des-verify-integrity` under `atdd_pure`
  treats an absent AT-completion ledger as a verification failure (exit 1).

Classic-mode marker semantics are byte-for-byte unchanged: a `workflow.mode`
that is `classic` or absent keeps the `roadmap.json` / `execution-log.json`
contract described above.

## Empirical anchor

`docs/feature/fix-des-worktree-project-root-marker/discuss/wave-decisions.md`
(Rex RCA 2026-05-19) — audit-2026-05-19.log:270,365 showed
false-positive validation halts where the orchestrator running on master
dispatched a crafter on a worktree; the stop hook read `execution-log`
from master's `docs/feature/...` rather than the worktree's, then
blocked on a non-existent log.
