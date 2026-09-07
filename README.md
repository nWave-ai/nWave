# nWave

AI agents that guide you from idea to working code, with human judgment at every gate.

nWave runs inside [Claude Code](https://claude.com/product/claude-code). It breaks feature delivery into seven waves (discover, diverge, discuss, design, devops, distill, deliver). Specialized agents produce artifacts at each wave. You review and approve before proceeding.

**Documentation**: [docs.nwave.ai](https://docs.nwave.ai) — guides, reference, and explanations, versioned per release.

## Install in 5 Minutes

**Requirements**: Python 3.10+ and Claude Code.

```bash
sh -c "$(curl -fsSL https://raw.githubusercontent.com/nWave-ai/nWave/main/scripts/install/install.sh)"
```

This installs the `nwave-ai` CLI and wires nWave into Claude Code in one step. It uses [uv](https://docs.astral.sh/uv/) when available (recommended); [pipx](https://pipx.pypa.io/) is supported but not recommended. Restart Claude Code when it finishes.

Need CLI flags, environment variables, CI/non-interactive use, or manual and offline steps? See the **[Installation Guide](docs/guides/installation-guide/README.md)**.

## Your First Command

Inside Claude Code, type:

```
/nw-buddy What should I do next?
```

The buddy reads your project and tells you which wave to start, where your artifacts are, and how to use nWave for your specific context. It works on day one with no configuration.

**Before nWave**: "Where do I start? Requirements doc or code first? Which agent?"
**After nWave**: The buddy reads your project and gives you a concrete next step.

Using pipx, OpenCode, or Codex instead? See the [Installation Guide](docs/guides/installation-guide/README.md).

## Learn More

| Resource | What it covers |
|----------|---------------|
| **[Your First Feature](docs/guides/tutorial-first-feature/)** | End-to-end walkthrough, zero to working code |
| **[Team Rollout Guide](docs/guides/team-rollout.md)** | Onboard a second developer onto an nWave project |
| **[Offline / Air-Gapped Install](docs/guides/offline-install.md)** | Install nWave on a machine without PyPI access |
| **[Jobs To Be Done](docs/guides/jobs-to-be-done-guide/)** | Which wave fits your task |
| **[Wave Directory Structure](docs/guides/wave-directory-structure/)** | How artifacts are organized per feature |
| **[Feature Delta Format (L7)](docs/guides/feature-delta-l7-format.md)** | Author features in the lean single-file model |
| **[Outcomes Registry](docs/reference/outcomes-cli.md)** | Catch duplicate rules and operations at design time |
| **[Configuring Doc Density](docs/guides/configuring-doc-density.md)** | Control lean vs full wave output |
| **[Agents and Commands Reference](docs/reference/index.md)** | All agents and commands |
| **[Troubleshooting](docs/guides/troubleshooting-guide/)** | Common issues and fixes |

---

## Latest Maintenance Release: v3.22.1

[nWave v3.22.1](https://github.com/nWave-ai/nWave/releases/tag/v3.22.1) is the current corrective maintenance release for the v3 line. It carries forward the twelve community fixes that are already present in published 3.22.0, across installation, configuration, finalization, diagnostics, repository hygiene, command discovery, and contributor guidance:

Thank you to everyone in the community who reported these problems and helped make nWave better.

- delivery guidance keeps the hand-off green for squash, rebase, and fast-forward-only workflows ([#56](https://github.com/nWave-ai/nWave/issues/56));
- the installed outcomes registry now includes the schema it needs ([#63](https://github.com/nWave-ai/nWave/issues/63));
- relative DES log paths are anchored to the worktree root ([#79](https://github.com/nWave-ai/nWave/issues/79));
- platform and delivery architecture work is routed to the appropriate specialist ([#81](https://github.com/nWave-ai/nWave/issues/81));
- finalization preserves feature workspace history while removing transient session state ([#83](https://github.com/nWave-ai/nWave/issues/83));
- supported documentation-density prompt modes are documented and validated ([#84](https://github.com/nWave-ai/nWave/issues/84));
- public repository dotfiles and local-only state receive the intended protection ([#90](https://github.com/nWave-ai/nWave/issues/90));
- generated documentation links no longer depend on which worktree produced them ([#91](https://github.com/nWave-ai/nWave/issues/91));
- Git verification failures now provide more actionable explanations ([#92](https://github.com/nWave-ai/nWave/issues/92));
- `/nw-execute` is easier to discover for a known single step ([#96](https://github.com/nWave-ai/nWave/issues/96));
- contributor guidance identifies the generated plugin payload and its canonical sources ([#97](https://github.com/nWave-ai/nWave/issues/97)); and
- a skipped commit no longer counts as completed work ([#99](https://github.com/nWave-ai/nWave/issues/99)).

Security hardening carried forward from 3.22.0 replaces legacy content fingerprints with SHA-256 and removes the vulnerable gitlint toolchain.

**Release scope:** Graphify ran only inside the release workflow's isolated verification environment; it is not included in the release artifacts or installed for users. No polyglot toolchain was added, and the installed polyglot templates are unchanged from v3.21. This remains a v3 release and does not include the experimental v4 line.

**Known limitation:** The commit-metadata correction reported in [#78](https://github.com/nWave-ai/nWave/issues/78) is not complete: some generated metadata may not be recognized as Git trailers. Please continue to track #78 rather than relying on that correction in v3.22.1.

## Previous Releases

### v3.22.0

The twelve fixes above shipped in [nWave v3.22.0](https://github.com/nWave-ai/nWave/releases/tag/v3.22.0).

### v3.19

- **Per-project activation (opt-in gate)** — nWave's globally-installed DES hooks are now **opt-in per repository**. Unmarked repos stay silent (hooks exit 0); a tracked `.nwave/local-config.json` marker plus a global `activation.mode` (`opt-in` default, or `all`) decide where nWave runs. Manage it with `nwave-ai project enable|disable`, `nwave-ai mode`, and `nwave-ai status`. Existing projects auto-adopt on first `/nw-` use, so nothing breaks. See **[Activating nWave in a Project](docs/guides/activating-nwave-per-project.md)**.
- **`nwave-ai` CLI reference** — the user-facing command surface (`install`, `uninstall`, `doctor`, `status`, `project`, `mode`, `attribution`, `completion`, `version`) is documented in one place, including the `install` flag pass-through to the underlying installer. See **[CLI Reference](docs/reference/cli.md)**.

See the full **[What's New in v3.19](docs/guides/whats-new-v319/)** for details.

### v3.15

- **3-Phase TDD Canon (Default)** — New canonical TDD methodology (RED → GREEN → COMMIT) replaces the legacy 5-phase contract (PREPARE → RED_ACCEPTANCE → RED_UNIT → GREEN → COMMIT). Documented in ADR-025. Dual-canon backward compatibility: existing audit logs and pre-2026-05-07 executions replay correctly under the legacy five-phase execution-log schema; new work uses 3-phase by default. Configured per rigor profile (lean mode uses RED → GREEN).
- **Codex CLI support** — Full nWave DES enforcement now works with [OpenAI Codex CLI](https://platform.openai.com/docs/guides/codex). Pre-tool-use hooks wire automatically; every Bash and file action validates against your TDD phase gates. See **[Installing for Codex CLI](docs/guides/installing-codex.md)**.

### v3.14

- **Lean wave docs (L7 single-file)** — Each feature lives in one `feature-delta.md` with schema-typed section headings (`## Wave: <WAVE> / [REF|WHY|HOW] <name>`). Tier-1 `[REF]` is auto-produced; Tier-2 `[WHY]` and `[HOW]` are opt-in via `--expand`. Downstream agents grep section headings instead of reading whole subdirectories. See **[Feature Delta Format (L7)](docs/guides/feature-delta-l7-format.md)**.
- **Feature-delta validator** — `nwave-ai validate-feature-delta <path>` checks structural rules (E1–E5) and emits JSON for CI integration. Vendor-neutral: no hooks auto-installed; pick a recipe from **[Enforcement Recipes](docs/guides/enforcement-recipes.md)** (12 platforms covered).
- **Outcomes registry** — Design-time deduplication. `nwave-ai outcomes register|check|check-delta` flags spec-level collisions before code is written, via type-shape + keyword Jaccard. See the **[Outcomes CLI reference](docs/reference/outcomes-cli.md)** and **[Your first outcome](docs/guides/outcomes-first-outcome/README.md)**.
- **Doc density config** — Per-project `lean` vs `full` density controls how much each wave emits. Tune token cost per wave. See **[Configuring Doc Density](docs/guides/configuring-doc-density.md)**.
- **Uninstall correctness fix (v3.14.0-rc1)** — `nwave-ai uninstall --force` now removes all installed artifacts (`skills/nw-*`, `lib/python/des/`, all 5 DES hook event types in `settings.json`) while preserving user-created skills. Previous versions left ~197 skill dirs and 3 hook entries behind. See **[Troubleshooting → Uninstall left files behind](docs/guides/troubleshooting-guide/#uninstall-left-files-behind-fixed-in-v314)**.

For upgrading from v3.3 or earlier, see [Breaking Changes](#breaking-changes) below.

## How It Works

```text
  machine        human         machine        human         machine
    │              │              │              │              │
    ▼              ▼              ▼              ▼              ▼
  Agent ──→ Documentation ──→ Review ──→ Decision ──→ Agent ──→ ...
 generates    artifacts      validates   approves    continues
```

Each wave produces artifacts that you review before the next wave begins. The machine never runs unsupervised end-to-end.

The workflow has seven waves. Entry point depends on your context:

| Wave | Command | Agent | Entry? |
|------|---------|-------|--------|
| DISCOVER | `/nw-discover` | product-discoverer | Greenfield: explore market and problem space |
| DIVERGE | `/nw-diverge` | nw-diverger | Greenfield: structured brainstorming before converging |
| DISCUSS | `/nw-discuss` | product-owner | All: write requirements and user journeys |
| DESIGN | `/nw-design` | system-designer, ddd-architect, solution-architect | All: architecture and domain model |
| DEVOPS | `/nw-devops` | platform-architect | All: infrastructure and deployment |
| DISTILL | `/nw-distill` | acceptance-designer | All: acceptance tests (Given-When-Then) |
| DELIVER | `/nw-deliver` | software-crafter | All: TDD implementation |

**Wave routing**: Entry points vary by context:
- **Greenfield project**: Start at DISCOVER or DIVERGE, proceed through all waves
- **Brownfield feature**: Start at DIVERGE or DISCUSS, skip to DESIGN
- **Bug fix**: Jump straight to DISTILL (write failing test) then DELIVER
- **Refactoring**: Jump to DELIVER (green already, refactor inside existing tests)

DISTILL then DELIVER is always the terminal pair. See the [Wave Routing Guide](docs/guides/wave-routing-and-entry-points/) for the full decision matrix.

40 agents total: 10 wave agents (including 3 DESIGN specialists), 1 concierge, 8 cross-wave specialists, 14 peer reviewers, 7 business agents. Full list: **[Commands Reference](docs/reference/commands/index.md)**

## Quick Start

### Requirements

- **Python 3.10+** — nWave's DES hooks use `match/case` statements and `X | Y` union type syntax introduced in Python 3.10. Verify with `python3 --version`.

### CLI Installer

Run the one-liner under **Install in 5 Minutes** at the top of this page. Agents and commands go to `~/.claude/`.

> **Don't have uv?** Install with: `curl -LsSf https://astral.sh/uv/install.sh | sh` or see [uv installation docs](https://docs.astral.sh/uv/getting-started/installation/). Alternatively, use [pipx](https://pipx.pypa.io/stable/installation/) (requires Python 3.10+): `pip install pipx && pipx ensurepath`.
> **Windows users**: Use WSL (Windows Subsystem for Linux). Install with: `wsl --install`

Full setup details: **[Installation Guide](https://github.com/nWave-ai/nWave/blob/main/docs/guides/installation-guide/README.md)**

### Other install methods

Looking for step-by-step instructions or a different setup? The **[Installation Guide](docs/guides/installation-guide/README.md)** covers every path — the single-script bootstrap, manual **uv** / **pipx** / **pip** steps, **Codex CLI**, **OpenCode**, and offline / air-gapped install.

### Plugin marketplace (not recommended)

> **DES enforcement does not work via the plugin marketplace and never will.** The plugin marketplace install path is blocked on an upstream Claude Code limitation ([anthropics/claude-code#24529](https://github.com/anthropics/claude-code/issues/24529)) where `${CLAUDE_PLUGIN_ROOT}` is not populated in plugin hook execution contexts. Without DES hooks, you lose phase enforcement, TDD validation, rigor profiles, and audit logging, which are the core of what nWave does.
>
> **Use the CLI installer above.** The plugin marketplace ships agents, commands, and skills only; consider it a degraded preview, not a supported install method.

> **OpenCode and Codex CLI** are supported too. Their step-by-step setup lives in the [Installation Guide](docs/guides/installation-guide/README.md).

### Which method?

| Scenario | Use | Why |
|----------|-----|-----|
| First time | CLI | Full features, full DES enforcement |
| Team rollout | CLI | Automation, full DES enforcement |
| Contributing | CLI | Dev scripts, internals access |

### Use (inside Claude Code, after reopening it)

**Start with the buddy:**

```
/nw-buddy What should I do next?
```

The buddy reads your project and gives contextual answers. Use it anytime you're unsure of the next step, where to find documents, or how a feature of nWave works.

**Ready to build? Follow the waves:**

```
/nw-diverge "user authentication approaches"       # Design exploration (optional for greenfield)
/nw-discuss "user login with email and password"   # Requirements
/nw-design --architecture=hexagonal                 # Architecture
/nw-distill "user-login"                            # Acceptance tests
/nw-deliver                                         # TDD implementation
```

Each wave produces artifacts you review. The machine never runs unsupervised end-to-end.

Full walkthrough: **[Your First Feature](docs/guides/tutorial-first-feature/)**

## Keeping nWave Updated

nWave checks for new versions when you open Claude Code. When available, you'll see a note in your context with version details and changes.

**CLI:**
```bash
uv tool upgrade nwave-ai     # or: pipx upgrade nwave-ai
nwave-ai install
```

**Adjust check frequency:**
```bash
# Edit ~/.nwave/des-config.json: "update_check.frequency" = "daily", "weekly", "every_session", or "never"
```

## Uninstalling

```bash
nwave-ai uninstall              # Remove agents, commands, config, DES hooks
uv tool uninstall nwave-ai      # or: pipx uninstall nwave-ai
```

Both methods remove agents, commands, and configuration from `~/.claude/`. Your project files are unaffected.

## Token Efficiency — Scale Quality to Stakes

nWave enforces proven engineering practices (TDD, peer review, mutation testing) at every step. Use `/nw-rigor` to adjust the depth of quality practices to match your task's risk level. A config tweak needs less rigor than a security-critical feature.

```
/nw-rigor                    # Interactive: compare profiles
/nw-rigor lean               # Quick switch to lean mode
/nw-rigor custom             # Build your own combination
```

| Profile | Agent | Reviewer | TDD | Mutation | Cost | Use When |
|---------|-------|----------|-----|----------|------|----------|
| **lean** | haiku | none | RED→GREEN | no | lowest | Spikes, config, docs |
| **standard** (default) | sonnet | haiku | 3-phase (RED→GREEN→COMMIT) | no | moderate | Most features |
| **thorough** | opus | sonnet | 3-phase (RED→GREEN→COMMIT) | no | higher | Critical features |
| **exhaustive** | opus | opus | 3-phase (RED→GREEN→COMMIT) | ≥80% kill | highest | Production core |
| **custom** | *you choose* | *you choose* | *you choose* | *you choose* | varies | Exact combination |

Picked once, persists across sessions. Every `/nw-deliver`, `/nw-design`, `/nw-review` respects your choice. Need to mix profiles? `/nw-rigor custom` walks through each setting.

```
/nw-rigor lean        # prototype fast
/nw-deliver           # haiku crafter, no review, RED→GREEN only
/nw-rigor standard    # ready to ship — bump up
/nw-deliver           # sonnet crafter, haiku reviewer, full TDD
```

## Understanding DES Messages

DES is nWave's quality enforcement layer. It monitors every Agent tool invocation during feature delivery to enforce TDD discipline and protect accidental edits. Most DES messages are normal enforcement, not errors. They appear when agents skip required safety checks or when your code contains patterns that look like step execution.

DES also runs automatic housekeeping at every session start: it removes audit logs beyond the retention window, cleans up signal files left by crashed sessions, and rotates the skill-loading log when it grows too large. This happens silently in the background and never blocks your session.

If `nwave-ai doctor` reports a problem at startup, you will see an advisory in your Claude Code session context. Run `nwave-ai doctor` from the terminal to get the specific fix.

| Message | What It Means | What To Do |
|---------|---------------|-----------|
| **DES_MARKERS_MISSING** | Agent prompt mentions a step ID (01-01 pattern) but lacks DES markers. | Either: add DES markers for step execution, OR add `<!-- DES-ENFORCEMENT : exempt -->` comment if it's not actually step work. |
| **Source write blocked** | You tried to edit a file during active `/nw-deliver` outside a DES task. | Edit requests must go through the active deliver session. If you need to make changes, finalize the current session first. |
| **TDD phase incomplete** | Sub-agent returned without finishing all required TDD phases. | Re-dispatch the same agent to complete missing phases (typically COMMIT or refactoring steps). |
| **nWave update available** | SessionStart detected a newer version available. | Optional. Run `uv tool upgrade nwave-ai && nwave-ai install` (or `pipx upgrade nwave-ai && nwave-ai install`) when ready to upgrade, or dismiss and continue working. |
| **False positive blocks** | Your prompt accidentally matches step-ID pattern (e.g., dates like "2026-02-09"). | Add `<!-- DES-ENFORCEMENT : exempt -->` comment to exempt the agent call from step-ID enforcement. |

These messages protect code quality but never prevent your work. They guide you toward the safe path.

## Documentation

### Getting Started

- **[Installation Guide](https://github.com/nWave-ai/nWave/blob/main/docs/guides/installation-guide/README.md)** — Setup instructions
- **[Your First Feature](docs/guides/tutorial-first-feature/)** — Build a feature end-to-end (tutorial)
- **[Team Rollout Guide](docs/guides/team-rollout.md)** — Onboard a second developer onto an nWave project
- **[Jobs To Be Done](docs/guides/jobs-to-be-done-guide/)** — Which workflow fits your task

### Guides and Reference

- **[Agents and Commands Reference](docs/reference/index.md)** — All agents, commands, skills, templates
- **[Wave Directory Structure](docs/guides/wave-directory-structure/)** — How wave outputs are organized per feature
- **[Invoke Reviewers](docs/guides/invoke-reviewer-agents/)** — Peer review workflow
- **[Troubleshooting](docs/guides/troubleshooting-guide/)** — Common issues and fixes

## Community

- **[Discord](https://discord.gg/Cywj3uFdpd)** — Questions, feedback, success stories
- **[GitHub Issues](https://github.com/nWave-ai/nWave/issues)** — Bug reports and feature requests
- **[Contributing](CONTRIBUTING.md)** — Development setup and guidelines

## Breaking Changes

### Command Format (v2.8.0)

**Starting with v2.8.0, all slash commands use hyphen format instead of colons.**

| Before (v2.7.x) | After (v2.8.0+) |
|---|---|
| `/nw:deliver` | `/nw-deliver` |
| `/nw:design` | `/nw-design` |
| `/nw:discuss` | `/nw-discuss` |
| `/nw:distill` | `/nw-distill` |
| `/nw:discover` | `/nw-discover` |
| *All other commands* | `/nw-{command}` |

**Why?** Commands migrated from Claude Code's dynamic `commands/` directory to the stable `skills/` system to prevent commands from disappearing during long sessions.

**To upgrade**: Run `uv tool upgrade nwave-ai && nwave-ai install` (or `pipx upgrade nwave-ai && nwave-ai install`). Old `/nw:` commands are automatically removed.

## Privacy

nWave does not collect user data. See [Privacy Policy](PRIVACY.md) for details.

## License

MIT — see [LICENSE](LICENSE) for details.
