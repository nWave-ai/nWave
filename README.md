# nWave

AI agents that guide you from idea to working code — with you in control at every step.

nWave runs inside [Claude Code](https://claude.com/product/claude-code). You describe what to build. Specialized agents handle requirements, architecture, test design, and implementation. You review and approve at each stage.

## Quick Start

**1. Install** (in your terminal — not inside Claude Code):

```bash
pipx install nwave-ai
nwave-ai install
```

No repository clone needed. This installs nWave from PyPI and sets up agents and commands in `~/.claude/`.

> **Don't have pipx?** Install it first: `pip install pipx && pipx ensurepath`, then restart your terminal. [pipx docs](https://pipx.pypa.io).
> **Windows users**: Use WSL, not cmd.exe or PowerShell. Install WSL first: `wsl --install`

Full setup details: **[Installation Guide](https://github.com/nWave-ai/nWave/blob/main/docs/guides/installation-guide.md)**

**2. Use** (inside Claude Code, after reopening it):

```
/nw:discuss "user login with email and password"   # Requirements
/nw:design --architecture=hexagonal                 # Architecture
/nw:distill "user-login"                            # Acceptance tests
/nw:deliver                                         # TDD implementation
```

Four commands. Four human checkpoints. One working feature.

Full walkthrough: **[Your First Feature](https://github.com/nwave-ai/nwave/tree/main/docs/guides/tutorial-first-feature.md)**

## How It Works

```text
  machine        human         machine        human         machine
    │              │              │              │              │
    ▼              ▼              ▼              ▼              ▼
  Agent ──→ Documentation ──→ Review ──→ Decision ──→ Agent ──→ ...
 generates    artifacts      validates   approves    continues
```

Each wave produces artifacts that you review before the next wave begins. The machine never runs unsupervised end-to-end.

The full workflow has six waves. Use all six for greenfield projects, or jump straight to `/nw:deliver` for brownfield work.

| Wave | Command | Agent | Produces |
|------|---------|-------|----------|
| DISCOVER | `/nw:discover` | product-discoverer | Market validation |
| DISCUSS | `/nw:discuss` | product-owner | Requirements |
| DESIGN | `/nw:design` | solution-architect | Architecture + ADRs |
| DEVOPS | `/nw:devops` | platform-architect | Infrastructure readiness |
| DISTILL | `/nw:distill` | acceptance-designer | Given-When-Then tests |
| DELIVER | `/nw:deliver` | software-crafter | Working implementation |

22 agents total: 6 wave agents, 5 cross-wave specialists, 11 peer reviewers. Full list: **[Commands Reference](https://github.com/nwave-ai/nwave/tree/main/docs/reference/nwave-commands-reference.md)**

## Documentation

### Getting Started

- **[Installation Guide](https://github.com/nWave-ai/nWave/blob/main/docs/guides/installation-guide.md)** — Setup instructions
- **[Your First Feature](https://github.com/nwave-ai/nwave/tree/main/docs/guides/tutorial-first-feature.md)** — Build a feature end-to-end (tutorial)
- **[Jobs To Be Done](https://github.com/nwave-ai/nwave/tree/main/docs/guides/jobs-to-be-done-guide.md)** — Which workflow fits your task

### Guides & Reference

- **[All Commands & Agents](https://github.com/nwave-ai/nwave/tree/main/docs/reference/nwave-commands-reference.md)** — Complete reference
- **[Invoke Reviewers](https://github.com/nwave-ai/nwave/tree/main/docs/guides/invoke-reviewer-agents.md)** — Peer review workflow
- **[Troubleshooting](https://github.com/nwave-ai/nwave/tree/main/docs/guides/troubleshooting-guide.md)** — Common issues and fixes
- **[Full Documentation Index](https://github.com/nwave-ai/nwave/tree/main/docs/reference/DOCUMENTATION_STRUCTURE.md)** — DIVIO-organized docs

## Community

- **[Discord](https://discord.gg/DeYdSNk6)** — Questions, feedback, success stories
- **[GitHub Issues](https://github.com/nWave-ai/nWave/issues)** — Bug reports and feature requests
- **[Contributing](CONTRIBUTING.md)** — Development setup and guidelines

## License

MIT — see [LICENSE](LICENSE) for details.
