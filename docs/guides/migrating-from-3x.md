# Migrate from nWave 3.x

Use this guide if you installed the public `nwave-ai` 3.x package. **v3.22.2 is the last public 3.x release.** Keep work in progress separate from the upgrade.

## Requirements

1. Python 3.11 or newer. The installer requires Python >= 3.11, and the package declares `requires-python = ">=3.11"`.
2. Git requirements vary by verb. The lane actions (`lane open`, `lane compose`, `lane rekey`, `lane integrate`) require Git 2.38 or newer and a declared `lanes.trunk` in the project's `.nwave/config.json`. `nwdes commit` is a Git operation: when Git cannot start or the root is not a Git checkout, it refuses `InputUnreadable` and creates no effect, so it requires a Git checkout. The recording and reading verbs that do not commit have no additional documented Git requirement. An isolated checkout or single bugfix may run without a lane; there is no lane-free flag.

## Before the upgrade

1. Record the installed version and installation method. Save any local changes to installed nWave assets outside their managed installation directories.
2. Decide how to finish each open 3.x delivery. Finish it with v3.22.2, or restart it as a new nwdes feature from the original request. There is no converter from the old roadmap and execution log to a canonical nwdes handoff.
3. Close coding-host sessions before changing installed assets. Do not let old sessions continue with a mixture of role and command versions.

## Upgrade the package and host assets

Upgrade the **`nwave-ai`** package with the same Python package manager and environment that installed it. Select a published release that includes nwdes. A local candidate wheel or source tag is not proof that the release is public. Do not switch a source checkout to a package-managed upgrade without a deliberate installation change.

Then run `nwave-ai install` for your selected host, using its supported platform option. Preview it with `--dry-run` first if you need to inspect the installation; the dry run also surfaces Codex ownership-collision refusals safely before a real install. Restart that host and confirm that `nwdes --help` is available — the one `nwdes` command you run at setup. On native-skill hosts, also confirm that the installed `nw-nwdes` skill teaches the new route. On hook-only hosts such as Cursor and Copilot, use `nwdes --help` and that host's installation validation instead; no native skill is installed. The [installation guide](installation-guide/) covers host setup and recovery.

### What the v4 install puts on your host

The installer installs the nWave assets into host-specific directories: specialized agents, the `/nw-*` command interface, and native skills — for example `~/.claude/agents/nw/` and `~/.omp/agent/skills/`. On OMP it also installs `~/.omp/agent/extensions/nwave-hooks.ts`, the tool-call guard extension, and the `/nw-*` commands. The exact per-host directory list is printed by `nwave-ai install --help`.

The **DES runtime** — DES being the name of nWave's predecessor delivery runtime, with no documented expansion of the name — is retired in v4: the source tree is removed, `nwave-ai doctor` no longer checks a DES module, and the installer writes no runtime copy. Rerunning the installer after the package upgrade removes the predecessor's footprint, including any legacy copy a 3.x install left at `~/.nwave/runtime/`. Delivery runs through the `nwdes` command shipped by the package; after the install, confirm that `nwdes --help` is available (see the upgrade section above). For how the delivery method works, see nwdes and its guides; this guide does not restate the TDD canon here.

## What changes

### Delivery workflow

| 3.x behavior | nwdes behavior |
|---|---|
| 3.x artifact formats and runtime workflow | One canonical handoff per feature and derived Markdown/HTML documents |
| Old commands and state determine delivery details | The host chooses route, size, sequencing, and rework |
| 3.x verification records | The host runs each declared verification command once and retains attributed observations; nwdes stores no RED/GREEN ledger |
| Old prompt and artifact formats | Generated role prompts and JSON output schemas |
| Existing delivery files | Not read or converted by nwdes |

The host invokes the roles. nwdes constructs forms, IDs, briefs, prompts, and packets. It does not start models or run supplied verification commands.

### Commands

The 3.x delivery commands are replaced by the nwdes verb set (as listed by `nwdes --help`):

- Feature and work: `nwdes feature new`, `nwdes slice set`, `nwdes work set`, `nwdes rework set`, `nwdes rework clear`.
- Documents and review: `nwdes document`, `nwdes delta`, `nwdes prompt`, `nwdes packet`, `nwdes measure`.
- Lanes (optional; require Git 2.38+ and `lanes.trunk`): `nwdes lane open`, `nwdes lane compose`, `nwdes lane rekey`, `nwdes lane integrate`.
- Commits: `nwdes commit` commits only the role's owned files with the configured Git author identity; the root never commits for another role.
- Product and design recording: `nwdes product …`, `nwdes design …` (promise, scope-in/out, decision, journey, slice, paradigm, constraint, reuse, impact, boundaries, observation, equality, constructor; drafts are nwdes-owned).

Run every nwdes command from the top level of the checkout; lane actions resolve the main project worktree.

These verbs are your assistant's to run, not commands you type: you run the
`nwave-ai` install and upgrade steps and decide scope; point your assistant
at [Deliver a feature](nwdes/deliver-feature.md) with the sentence in
[For your assistant](README.md#for-your-assistant).

## Delivery cutover

nwdes is the delivery tool; its predecessor is being removed, and a v3 delivery in progress is finished on 3.22.2 or restarted with `nwdes feature new --feature ID --request '…' --size M --value '…'` from the original request.

For new work, the root chooses among spine waves, host-led nwdes steps, and working directly by what must survive the session and the cost of a late refusal, never by S, M, or L size; state the choice. nwdes is the host-led route, not a requirement for all new work.

Before cleanup, move any hand-written files out of nWave-managed installation paths; ownership by installation location can cause their removal. No automatic conversion of in-progress work is planned.

## Upgrade from release v3.22.2

If you installed release v3.22.2 of the `nwave-ai` package, upgrade the package and run `nwave-ai install` as described in the sections above. The upgrade moves you to the nwdes route. It also does the following to what v3.22.2 left on your machine.

- The predecessor delivery tool's footprint is removed from the installation.
- Existing nWave backup snapshots are kept, subject to the configured retention limit.
- After a successful run the installer warns you about existing backup snapshots. It prints one block per backup root, headed by `nWave backup snapshot(s) kept under <root>:`, and lists each snapshot under that line. A snapshot that holds a legacy-codex-dev copy — a backup of assets from a legacy Codex development install — is renamed with the prefix `legacy-hold-`, and its listing line is marked `held`.
- A held legacy-codex-dev copy is kept regardless of the retention limit. Retention never removes a held snapshot.

A held copy is retired only after a passing comparison, using the `verify_nwave.py` helper that ships with the installed package (`scripts/install/verify_nwave.py`). First compare it with the declared folder. Verify mode only reads:

```text
verify_nwave.py --verify-legacy-copy <snapshot>/legacy-codex-dev --against DIR
```

Then run `verify_nwave.py --retire-legacy-copy <snapshot>/legacy-codex-dev --against DIR`. Retire mode runs the comparison again at the moment of deletion and deletes the copy only when that comparison passes; it does not reuse the result of the verify run.

`DIR` is the declared folder: each asset of the copy is compared with the matching asset under it. Exit code 0 means the comparison passed. Exit code 1 means it failed, 2 is a usage error such as a missing `--against`, and 3 means the copy was refused and nothing was compared or deleted. On a failed retire the command prints `NOT RETIRED COPY:` and `Nothing was deleted.`; on success it prints `RETIRED COPY:`.

After the upgrade, nwave-ai install, nwdes and code-fact keep working.

## Rollback and backup

The installer supports backing up and restoring the previous installation:

- `nwave-ai install --backup-only` snapshots the existing Claude Code and Codex installations without installing anything. Run it before upgrading if you want a recovery point.
- `nwave-ai install --restore` restores the most recent Claude Code backup; on a Codex-only install it currently finds nothing to restore, and no backup or restore exists for OpenCode, Cursor, Copilot, OMP or Devin.

Back up before the first v4 install; the backup reflects the installation present at backup time.

## Start new work

Follow [First feature](tutorial-nwdes-first-feature/) for isolated command practice. Use [Deliver a feature](nwdes/deliver-feature.md) or [Fix a bug](nwdes/fix-bug.md) for real work. To isolate a feature in its own worktree, see [Use lanes](nwdes/use-lanes.md) and the [lane reference](nwdes/reference/lane.md).

**Done:** the selected host has the chosen package's assets and `nwdes --help` is available. Native-skill hosts also have the installed `nw-nwdes` skill; hook-only hosts instead pass their host-specific installation validation. Each old delivery has an explicit finish-on-3.x or restart-with-nwdes decision.
