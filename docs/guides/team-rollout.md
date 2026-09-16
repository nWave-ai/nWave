# Team Rollout Guide

## Who This Is For

Team leads and second-plus developers joining an existing nWave project. You have at least one developer already using nWave and want to extend that workflow to the full team.

## Mental Model: Per-Developer Install, Team-Shared Artifacts

nWave has two separate concerns:

**Per-developer (not shared via git):**
- `~/.claude/agents/` — agent definitions
- `~/.claude/skills/` — skill files
- `~/.claude/tasks/` — command definitions
- `~/.nwave/` — personal config, audit logs, rigor profile

Each developer installs nWave independently. The install modifies their local Claude Code setup. There is no shared server, no team account.

**Team-shared (tracked in git):**
- `docs/feature/<feature-name>/` — all wave artifacts (journey, design, acceptance tests)
- `.nwave/des-config.json` — project-level rigor and config (commit this)

Wave artifacts travel via git. A second developer clones the repo, runs their own `nwave-ai install`, and reads the latest artifact in `docs/feature/` to understand where the feature is in the wave sequence.

## First Developer: Project Owner Setup

If you are the first developer on the project:

```bash
# 1. Install nWave (installs the CLI, deploys agents, runs doctor)
sh -c "$(curl -fsSL https://raw.githubusercontent.com/nWave-ai/nWave/main/scripts/install/install.sh)"

# 2. Run your first wave on a real feature
# (inside Claude Code)
/nw-discuss "user login with email and password"

# 3. Commit the artifacts so teammates can see them
git add docs/feature/
git commit -m "docs(feature): add discuss artifacts for user-login"
git push
```

The `docs/feature/` directory is the handoff surface. Whatever you commit there is what your teammates will read.

> **Note**: If `git status` shows `docs/feature/` as untracked but not staged, check whether your `.gitignore` excludes it. Some project templates include broad `docs/` exclusions that prevent wave artifacts from being committed.

If the project has a `.nwave/des-config.json` (rigor profile), commit that too:

```bash
git add .nwave/des-config.json
git commit -m "chore(config): add nwave project rigor config"
```

## Second Developer: Joining an Existing nWave Project

```bash
# 1. Clone the repo (or pull latest if already cloned)
git clone <repo-url>
cd <repo>

# 2. Install nWave on your machine
sh -c "$(curl -fsSL https://raw.githubusercontent.com/nWave-ai/nWave/main/scripts/install/install.sh)"

# 3. Verify your install is healthy
nwave-ai doctor
```

If `nwave-ai doctor` reports any issues, fix them before proceeding. Common first-run issues are listed in [Common Team Issues](#common-team-issues) below.

```bash
# 4. See where the feature is
ls docs/feature/
# Example output: user-login/

ls docs/feature/user-login/
# Example: discuss/  design/  distill/
# The subdirectories tell you which waves have been completed.

# 5. Read the latest artifact to get context
cat docs/feature/user-login/discuss/journey.md

# 6. Open Claude Code and join at the current wave
# (inside Claude Code)
/nw-buddy What is the current state of the user-login feature?
```

The buddy reads your project files including `docs/feature/` and tells you which wave to run next.

## Working on the Same Feature Simultaneously

**One feature, one branch.** The canonical setup:

```bash
git checkout -b feature/user-login
# Both developers work on this branch
# Wave artifacts go to docs/feature/user-login/
```

**Artifact conflict resolution:**

Wave artifacts are prose files. Git merge conflicts in `docs/feature/` are normal and resolved the same way as any prose conflict: read both versions, keep the correct one. Wave artifacts follow a progression: discuss before design, design before distill. If two developers edited the same artifact concurrently, the artifact at the furthest wave in the sequence is authoritative for downstream waves; for same-wave conflicts, resolve as a normal prose merge and agree on content before proceeding.

**When to split work:**

Split into parallel branches only if two developers are working on entirely different features. A single feature should have one active branch. Splitting a feature mid-wave (e.g., one developer at DISTILL, another back at DISCUSS) creates wave artifact divergence that is painful to reconcile.

**Handoff mid-wave:**

If developer A is in the middle of `/nw-distill` and developer B needs to continue:
1. Developer A commits whatever partial artifacts exist: `git commit -m "wip(distill): partial acceptance tests for user-login"`
2. Developer B pulls, reads the artifacts, and runs `/nw-buddy` to get context before continuing
3. Developer B does not re-run earlier waves: the buddy will tell them to continue from DISTILL

## Common Team Issues

**Mismatched `nwave-ai` versions**

Symptom: one developer sees commands the other does not, or `/nw-buddy` behaves differently between machines.

Fix:
```bash
nwave-ai --version          # check your version
uv tool upgrade nwave-ai    # upgrade
nwave-ai install            # re-install agents and commands
nwave-ai doctor             # verify
```

Pin the minimum version in your project `README.md`: "Requires nwave-ai >= X.Y.Z".

---

**Diverged `~/.claude/skills/`**

Symptom: `nwave-ai doctor` passes on one machine but not another. Or agents behave inconsistently.

Fix: skills are installed from the PyPI package. If versions match, skills match. Run `nwave-ai install` again to reset to the package version. Do not manually edit `~/.claude/skills/` files: edits there are local only and will be overwritten on next install.

---

**Stale hook paths after reinstall**

Symptom: DES messages stop appearing in Claude Code. Or `nwave-ai doctor` reports a hook registration issue.

Fix:
```bash
nwave-ai uninstall
nwave-ai install
nwave-ai doctor
```

This resets hook paths to match your current Python environment.

---

**Mid-wave handoff: new developer does not know which wave to run**

Symptom: second developer runs `/nw-discuss` on a feature that is already at DISTILL, creating duplicate artifacts.

Fix: always read `docs/feature/<name>/` before running a wave command. The directory structure is the state machine. Alternatively:
```bash
/nw-buddy What wave should I run next for <feature-name>?
```

---

**`nwave-ai doctor` fails on SessionStart advisory**

Symptom: you see an advisory in your Claude Code session context warning that doctor checks failed.

Fix: run `nwave-ai doctor` from the terminal. It prints the specific check that failed and the fix command. The most common cause is a Python version mismatch or a hook path pointing to a deleted virtualenv.

---

**`docs/feature/` not committed**

Symptom: second developer clones the repo and sees an empty `docs/feature/` directory or no directory at all.

Fix: wave artifacts must be explicitly committed. They are not created automatically by `nwave-ai install`. The first developer must `git add docs/feature/ && git commit` after each wave.

## Workshop Format (90-Minute Team Session)

Use this format when introducing nWave to a team that has not used it before.

**Before the session (10 minutes prep):**
- Choose one real, small feature from your backlog (not a toy example)
- Have one laptop with nWave already installed and `nwave-ai doctor` green

**Session structure:**

| Time | Activity |
|------|----------|
| 0-15 min | Everyone installs: `sh -c "$(curl -fsSL https://raw.githubusercontent.com/nWave-ai/nWave/main/scripts/install/install.sh)"` |
| 15-25 min | Facilitator runs `/nw-discuss` on the chosen feature, narrates decisions aloud |
| 25-35 min | Team reviews the `docs/feature/` artifact together, edits if needed, commits |
| 35-50 min | Facilitator runs `/nw-distill`, team reviews acceptance tests |
| 50-70 min | Facilitator runs `/nw-deliver`, team watches RED_ACCEPTANCE test produced and the start of GREEN (a full TDD cycle is longer than this slot — stop after the acceptance test) |
| 70-85 min | Q&A: common issues, rigor profiles, how to hand off tomorrow |
| 85-90 min | Assign: each attendee picks a feature and runs DISCUSS solo before next session |

**Key points to make during the session:**
- The agents produce drafts: the team reviews and edits before the next wave
- `~/.claude/` is yours alone; `docs/feature/` is the team's shared memory
- `nwave-ai doctor` is the first diagnostic: run it before filing a bug

## Where to Learn More

- **[Your First Feature](tutorial-first-feature/)** — end-to-end tutorial, zero to working code
- **[Wave Directory Structure](wave-directory-structure/)** — how artifacts are organized
- **[Jobs To Be Done](jobs-to-be-done-guide/)** — which wave fits your task
- **[Agents and Commands Reference](../reference/index.md)** — full agent and command list
- **[Troubleshooting](troubleshooting-guide/)** — broader issue reference
- **[Discord](https://discord.gg/Cywj3uFdpd)** — team questions and community support
