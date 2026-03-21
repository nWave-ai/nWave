# nWave

AI agents that guide you from idea to working code — with you in control at every step.

nWave runs inside [Claude Code](https://claude.com/product/claude-code). You describe what to build. Specialized agents handle requirements, architecture, test design, and implementation. You review and approve at each stage.

## BREAKING CHANGE: Command Format (v2.8.0)

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

**To upgrade**: Run `pipx upgrade nwave-ai && nwave-ai install` (CLI) or `/plugin marketplace update nwave-marketplace` (plugin). Old `/nw:` commands are automatically removed.

## Quick Start

### Requirements

- **Python 3.10+** — nWave's DES hooks use `match/case` statements and `X | Y` union type syntax introduced in Python 3.10. Verify with `python3 --version`.

### Plugin (Recommended)

From Claude Code, run:

```
/plugin marketplace add nwave-ai/nwave
/plugin install nw@nwave-marketplace
```

Restart Claude Code and type `/nw-` to see all available commands.

### CLI Installer (Alternative)

Install from PyPI — useful for contributing or environments without plugin support:

```bash
pipx install nwave-ai
nwave-ai install
```

Agents and commands go to `~/.claude/`.

> **Don't have pipx?** Install with: `pip install pipx && pipx ensurepath`, then restart your terminal.
> **Windows users**: Use WSL (Windows Subsystem for Linux). Install with: `wsl --install`

Full setup details: **[Installation Guide](https://github.com/nWave-ai/nWave/blob/main/docs/guides/installation-guide.md)**

### OpenCode Support (Alternative IDE)

nWave also works with [OpenCode](https://github.com/opencode-dev/opencode), an open-source IDE for AI pair programming. Installation requires a few extra steps to configure OpenCode's environment.

**Install prerequisites:**
```bash
npm install -g opencode-ai
pipx install nwave-ai
```

**Configure OpenCode:**
```bash
mkdir -p ~/.config/opencode
echo '{"model": "openai/gpt-4o-mini"}' > ~/.config/opencode/opencode.json
```

**Set your OpenAI API key:**
```bash
export OPENAI_API_KEY=your-key-here
```

**Install nWave into OpenCode:**
```bash
nwave-ai install
```

**Compatibility notes:**
- ~67% of nWave features work natively on OpenCode via compatibility paths
- DES hooks integrate via OpenCode's `tool.execute.before` mechanism
- Some advanced subagent coordination may differ from Claude Code — use the core `/nw-discuss`, `/nw-design`, `/nw-distill`, `/nw-deliver` commands for best results
- For full feature parity and support, Claude Code remains the primary environment

### Which method?

| Scenario | Use | Why |
|----------|-----|-----|
| First time | Plugin | Zero dependencies, instant setup |
| Team rollout | Either | Plugin for simplicity, CLI for automation |
| Contributing | CLI | Dev scripts, internals access |
| Already on CLI | Either | Both coexist safely |

### Use (inside Claude Code, after reopening it)

```
/nw-discuss "user login with email and password"   # Requirements
/nw-design --architecture=hexagonal                 # Architecture
/nw-distill "user-login"                            # Acceptance tests
/nw-deliver                                         # TDD implementation
```

Four commands. Four human checkpoints. One working feature.

Full walkthrough: **[Your First Feature](https://github.com/nwave-ai/nwave/tree/main/docs/guides/tutorial-first-feature.md)**

## Staying Updated

nWave checks for new versions when you open Claude Code. When available, you'll see a note in Claude's context with version details and changes.

**Plugin (self-hosted marketplace):**
```
/plugin marketplace update nwave-marketplace
```

Updates are available immediately after each release — no review delay.

**Plugin (official Anthropic directory):**

The official directory pins plugins to reviewed versions. Updates go through Anthropic's review process before reaching users. If you installed from the official directory and want the latest version sooner, add the self-hosted marketplace:

```
/plugin marketplace add nwave-ai/nwave
/plugin install nw@nwave-marketplace
```

**CLI method:**
```bash
pipx upgrade nwave-ai
nwave-ai install
```

Control check frequency via `update_check.frequency` in `~/.nwave/des-config.json`: `daily`, `weekly`, `every_session`, or `never`.

## Uninstalling

**Plugin method:**
```
/plugin uninstall nw
```

**CLI method:**
```bash
nwave-ai uninstall              # Remove agents, commands, config, DES hooks
pipx uninstall nwave-ai        # Remove the Python package
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
| **standard** ⭐ | sonnet | haiku | full 5-phase | no | moderate | Most features |
| **thorough** | opus | sonnet | full 5-phase | no | higher | Critical features |
| **exhaustive** | opus | opus | full 5-phase | ≥80% kill | highest | Production core |
| **custom** | *you choose* | *you choose* | *you choose* | *you choose* | varies | Exact combo needed |

Picked once, persists across sessions. Every `/nw-deliver`, `/nw-design`, `/nw-review` respects your choice. Need to mix profiles? `/nw-rigor custom` walks through each setting.

```
/nw-rigor lean        # prototype fast
/nw-deliver           # haiku crafter, no review, RED→GREEN only
/nw-rigor standard    # ready to ship — bump up
/nw-deliver           # sonnet crafter, haiku reviewer, full TDD
```

## Understanding DES Messages

DES is nWave's quality enforcement layer — it monitors every Agent tool invocation during feature delivery to enforce TDD discipline and protect accidental edits. Most DES messages are normal enforcement, not errors. They appear when agents skip required safety checks or when your code contains patterns that look like step execution.

DES also runs automatic housekeeping at every session start: it removes audit logs beyond the retention window, cleans up signal files left by crashed sessions, and rotates the skill-loading log when it grows too large. This happens silently in the background and never blocks your session.

| Message | What It Means | What To Do |
|---------|---------------|-----------|
| **DES_MARKERS_MISSING** | Agent prompt mentions a step ID (01-01 pattern) but lacks DES markers. | Either: add DES markers for step execution, OR add `<!-- DES-ENFORCEMENT : exempt -->` comment if it's not actually step work. |
| **Source write blocked** | You tried to edit a file during active `/nw-deliver` outside a DES task. | Edit requests must go through the active deliver session. If you need to make changes, finalize the current session first. |
| **TDD phase incomplete** | Sub-agent returned without finishing all required TDD phases. | Re-dispatch the same agent to complete missing phases (typically COMMIT or refactoring steps). |
| **nWave update available** | SessionStart detected a newer version available. | Optional. Run `pipx upgrade nwave-ai && nwave-ai install` when ready to upgrade, or dismiss and continue working. |
| **False positive blocks** | Your prompt accidentally matches step-ID pattern (e.g., dates like "2026-02-09"). | Add `<!-- DES-ENFORCEMENT : exempt -->` comment to exempt the agent call from step-ID enforcement. |

These messages protect code quality but never prevent your work — they guide you toward the safe path.

## How It Works

```text
  machine        human         machine        human         machine
    │              │              │              │              │
    ▼              ▼              ▼              ▼              ▼
  Agent ──→ Documentation ──→ Review ──→ Decision ──→ Agent ──→ ...
 generates    artifacts      validates   approves    continues
```

Each wave produces artifacts that you review before the next wave begins. The machine never runs unsupervised end-to-end.

The full workflow has six waves. Use all six for greenfield projects, or jump straight to `/nw-deliver` for brownfield work.

| Wave | Command | Agent | Produces |
|------|---------|-------|----------|
| DISCOVER | `/nw-discover` | product-discoverer | Market validation |
| DISCUSS | `/nw-discuss` | product-owner | Requirements |
| DESIGN | `/nw-design` | solution-architect | Architecture + ADRs |
| DEVOPS | `/nw-devops` | platform-architect | Infrastructure readiness |
| DISTILL | `/nw-distill` | acceptance-designer | Given-When-Then tests |
| DELIVER | `/nw-deliver` | software-crafter | Working implementation |

23 agents total: 6 wave agents, 6 cross-wave specialists, 11 peer reviewers. Full list: **[Commands Reference](https://github.com/nwave-ai/nwave/tree/main/docs/reference/commands/index.md)**

## Documentation

### Getting Started

- **[Installation Guide](https://github.com/nWave-ai/nWave/blob/main/docs/guides/installation-guide.md)** — Setup instructions
- **[Your First Feature](https://github.com/nwave-ai/nwave/tree/main/docs/guides/tutorial-first-feature.md)** — Build a feature end-to-end (tutorial)
- **[Jobs To Be Done](https://github.com/nwave-ai/nwave/tree/main/docs/guides/jobs-to-be-done-guide.md)** — Which workflow fits your task

### Guides & Reference

- **[Agents & Commands Reference](https://github.com/nwave-ai/nwave/tree/main/docs/reference/index.md)** — All agents, commands, skills, templates
- **[Wave Directory Structure](https://github.com/nwave-ai/nwave/tree/main/docs/guides/wave-directory-structure.md)** — How wave outputs are organized per feature
- **[Invoke Reviewers](https://github.com/nwave-ai/nwave/tree/main/docs/guides/invoke-reviewer-agents.md)** — Peer review workflow
- **[Troubleshooting](https://github.com/nwave-ai/nwave/tree/main/docs/guides/troubleshooting-guide.md)** — Common issues and fixes

## Community

- **[Discord](https://discord.gg/Cywj3uFdpd)** — Questions, feedback, success stories
- **[GitHub Issues](https://github.com/nWave-ai/nWave/issues)** — Bug reports and feature requests
- **[Contributing](CONTRIBUTING.md)** — Development setup and guidelines

## Privacy

nWave does not collect user data. See [Privacy Policy](PRIVACY.md) for details.

## License

MIT — see [LICENSE](LICENSE) for details.
