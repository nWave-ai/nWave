# Activating nWave in a Project

nWave hooks install globally to `~/.claude/settings.json`, so they fire in every repository you open. This guide explains why activation is opt-in per project, how the mechanism works, and how to enable or disable nWave for specific repositories.

## The Mental Model

### Why opt-in?

nWave ships with global hooks that provide TDD enforcement, execution auditing, and phase validation. To keep nWave non-invasive in repos where you are not using it yet, hooks are **opt-in per project by default**. In an inactive project, hooks silently exit with status 0 (success) — you never know nWave is installed.

### The activation gate (resolution policy)

Activation is resolved by a simple two-input policy:

1. **Per-project marker**: `.nwave/local-config.json` containing `{"enabled_for_repo": true}` or `{"enabled_for_repo": false}`
2. **Global default mode**: `activation.mode` in `~/.nwave/global-config.json` — either `opt-in` (default) or `all`

The policy is pure and deterministic. Given these two inputs, nWave decides:

| Per-Project Marker | Global Mode | Result |
|---|---|---|
| `enabled_for_repo: true` | any | **ACTIVE** |
| `enabled_for_repo: false` | any | **INACTIVE** (sticky) |
| (absent) | `"opt-in"` | **INACTIVE** |
| (absent) | `"all"` | **ACTIVE** |
| (absent) | (missing/corrupt) | **INACTIVE** (fail-safe) |

**Key principle**: A marker set to `false` is **sticky** — auto-marking never overwrites a deliberate opt-out.

### Why version-control the marker?

The marker `.nwave/local-config.json` is intentionally **tracked in git**. Your activation intent travels with every clone, so teammates inherit the same nWave state. nWave fixes `.gitignore` (two layers: root and nested) so the marker stays tracked while other `.nwave/` contents are ignored.

After you enable nWave:

```bash
git check-ignore .nwave/local-config.json
# (no output = NOT ignored; marker is tracked)
```

### Special case: SessionStart hook is always active

One hook is exempt from the activation gate: the `SessionStart` hook. It runs update checks, housekeeping, and adoption detection even in unmarked (inactive) repos. Other hooks (pre-tool-use, subagent-stop, deliver-progress, post-tool-use) respect the gate.

### Silent auto-marking (backward compatibility)

An unmarked repo gets adopted automatically (marker written `{"enabled_for_repo": true}`) in two cases:

1. **At session start** if there is prior nWave use evidence (non-empty audit log, prior feature directories).
2. **On the first dispatch of any `nw-*` agent** in that repo.

This ensures repos with existing nWave work are not left inactive unexpectedly. Once you write an explicit marker (`true` or `false`), auto-marking stops — your choice is sticky.

### Walk-up resolution

Running a command from a subdirectory finds the nearest `.nwave/local-config.json` in a parent directory (nearer-wins), stopping at `$HOME`. The global `~/.nwave/` directory is never treated as a project marker.

---

## How-To: Activate and Deactivate nWave

### Task 1: Enable nWave for the current project

```bash
nwave-ai project enable
```

**Output**:
```
nWave activation for this project: enabled.
```

**What this does**:
- Writes `.nwave/local-config.json` with `{"enabled_for_repo": true}`
- Fixes both layers of `.gitignore` so the marker stays tracked
- Sets the marker to sticky (auto-marking will not overwrite it)

**Next step**: Commit the marker and `.gitignore` changes to version control:

```bash
git add .nwave/local-config.json .gitignore .nwave/.gitignore
git commit -m "feat(activation): enable nWave for this project"
git push
```

Teammates who pull this commit will have nWave active automatically.

---

### Task 2: Disable nWave for the current project (sticky opt-out)

```bash
nwave-ai project disable
```

**Output**:
```
nWave activation for this project: disabled (sticky opt-out).
```

**What this does**:
- Writes `.nwave/local-config.json` with `{"enabled_for_repo": false}`
- Marks the repo as permanently inactive (auto-marking will never overwrite this)
- Commits the opt-out so teammates also have nWave inactive

**When to use**:
- You are in a repo where nWave is not (yet) needed.
- You want to silence hooks for a time and prevent auto-adoption on the first `nw-*` command.

Disable is sticky by design — if you change your mind later, you must run `enable` again to re-activate.

---

### Task 3: Set the global default mode (one-time per machine)

By default, nWave uses `opt-in` mode: unmarked repos stay inactive. You can change this machine-wide to `all` if you prefer nWave active everywhere:

```bash
nwave-ai mode opt-in
```

or

```bash
nwave-ai mode all
```

**Output**:
```
Global nWave activation mode set to 'opt-in'.
```

**When to set `mode: all`**:
- You want nWave active in every repo by default, even unmarked ones.
- Your entire team works in nWave projects and inactive repos are the exception.

**When to stay with `mode: opt-in`** (recommended):
- You have a mix of nWave and non-nWave projects.
- You prefer explicit, repo-level control over opt-in intent.

---

### Task 4: Check activation state (read-only, no writes)

```bash
nwave-ai status
```

**Output**:
```
Global activation mode: opt-in
This project is inactive.
```

or (when active):

```
Global activation mode: opt-in
This project is active.
```

This command **never writes anything** — it is safe to run anywhere. It confirms the global default and shows whether the current directory's project is active or inactive.

---

## Common Workflows

### Workflow 1: I have a mix of nWave and non-nWave projects

**Setup**:
- Keep global mode at `opt-in` (default).
- Run `nwave-ai project enable` in nWave projects.
- Never run `disable`; unmarked repos stay inactive.

**Result**: Each project that needs nWave is explicitly opted in; others are silent.

---

### Workflow 2: My whole team uses nWave

**Setup**:
- Set global mode to `all` once: `nwave-ai mode all`.
- Repos are active by default; no per-project marker needed.
- If a repo should NOT use nWave, run `nwave-ai project disable` and commit the marker.

**Result**: nWave is the default everywhere; exceptions are marked.

---

### Workflow 3: I want nWave active in this repo but not on another machine

**Setup**:
- Run `nwave-ai project enable` in the repo.
- Commit `.nwave/local-config.json`.
- When teammates (or you on another machine) clone the repo, they inherit the marker automatically.
- No need to run `enable` again — the committed marker carries the state.

**Result**: nWave activation travels with the repo code.

---

## What Gets Committed

After enabling nWave, you commit two files/changes:

1. **`.nwave/local-config.json`** — The activation marker. Contains `{"enabled_for_repo": true}` or `{"enabled_for_repo": false}`. Always tracked.

2. **`.gitignore` changes** — The root `.gitignore` and `.nwave/.gitignore` are updated to:
   - Ignore `.nwave/` contents **except** `.nwave/local-config.json`
   - Keep the marker readable and trackable

The nested `.nwave/.gitignore` is regenerated at runtime and need not be tracked (though it often is, harmlessly).

---

## Verification

After enabling nWave, confirm the marker is tracked:

```bash
# Should return no output (marker is NOT ignored)
git check-ignore .nwave/local-config.json

# Should show the marker file
git ls-files | grep local-config.json
```

Then confirm activation state:

```bash
nwave-ai status
```

---

## Troubleshooting

### Q: I ran `nwave-ai project enable` but hooks still don't fire. Why?

**A**: Check three things:

1. **Is nWave installed?** Run `nwave-ai version` to confirm the CLI is on PATH.

2. **Is the marker committed?** The marker is per-project; only hooks in active projects fire. Run `nwave-ai status` to confirm this project is active.

3. **Are you in a subdirectory?** Walk-up resolution looks for the nearest `.nwave/local-config.json` in parent directories. If you have multiple `.nwave/` directories, the nearest one wins.

### Q: I set the global mode to `all` but some repos are still inactive. Why?

**A**: Check for an explicit `enabled_for_repo: false` marker:

```bash
cat .nwave/local-config.json
```

A marker set to `false` is sticky and overrides the global mode. To re-activate, run:

```bash
nwave-ai project enable
```

### Q: I disabled a project, but I want to re-enable it. What do I do?

**A**: Simply run:

```bash
nwave-ai project enable
```

This overwrites the `false` marker with `true`. Commit the change.

### Q: Can I manually edit `.nwave/local-config.json`?

**A**: Yes, but don't. Always use `nwave-ai project enable|disable` and let the CLI fix `.gitignore` and apply the sticky guard. Manual edits are unsupported and may leave the repo in an inconsistent state.

---

## Related Guides and References

- **[nWave Global Config Reference](../reference/global-config.md)** — `activation` key documentation
- **[Installation Guide](./installation-guide/README.md)** — how nWave installs globally and what gets created
