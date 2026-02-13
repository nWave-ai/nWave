# nWave: Acceptance Test Driven Development with AI

A framework for systematic software development using ATDD (Acceptance Test Driven Development) with intelligent AI agent orchestration. nWave guides you through a 6-wave workflow (DISCOVER, DISCUSS, DESIGN, DISTILL, DEVELOP, DELIVER) with 22 specialized agents providing evidence-based decision making, architecture design, test-driven implementation, and production readiness validation.

## Install

```bash
pipx install nwave-ai
nwave-ai install
```

Close and reopen Claude Code. The nWave agents and slash commands will appear in your command palette.

## Quick Start

After installation, use nWave commands in any Claude Code project:

```bash
# Product discovery and requirements gathering
/nw:discover "market research for feature X"
/nw:discuss "feature requirements"

# Design and testing
/nw:design --architecture=hexagonal
/nw:distill "acceptance test scenarios"

# Implementation and quality assurance
/nw:baseline "measure current state"
/nw:roadmap "create implementation plan"
/nw:split "break into atomic tasks"
/nw:execute "run individual task"
/nw:review "quality check"
/nw:deliver "production readiness"
```

For guidance on workflow selection, see the [Jobs To Be Done Guide](https://github.com/nwave-ai/nwave/tree/main/docs/guides/jobs-to-be-done-guide.md).

## Core Concepts

### 6-Wave ATDD Workflow

Each wave produces validated artifacts with input from specialized agents:

- **DISCOVER** - Evidence-based product discovery
- **DISCUSS** - Requirements gathering and business analysis
- **DESIGN** - Architecture design with technology selection
- **DISTILL** - BDD acceptance tests that define "done"
- **DEVELOP** - Outside-in TDD implementation with atomic tasks
- **DELIVER** - Production readiness validation

### 22 Specialized Agents

- **11 Primary Agents**: One per wave plus cross-wave specialists (researcher, troubleshooter, data-engineer, documentarist, agent-builder)
- **11 Reviewer Agents**: Peer review with equal expertise reducing bias

### 18 Slash Commands

Wave commands (/nw:discover, /nw:discuss, /nw:design, /nw:distill, /nw:deliver, /nw:devops); execution commands (/nw:roadmap, /nw:execute, /nw:review, /nw:finalize); cross-wave commands (/nw:research, /nw:document, /nw:root-why, /nw:refactor, /nw:mikado, /nw:mutation-test); and utilities (/nw:diagram, /nw:forge).

### DES: Deterministic Execution System

DES enforces execution discipline through Claude Code hooks:

- Pre-task validation and post-tool-use monitoring
- Comprehensive audit logging for compliance and debugging
- Configurable per-project via `.nwave/des-config.json`

### 5-Layer Quality Assurance

Layer 1: Unit testing; Layer 2: Integration testing; Layer 3: Adversarial validation; Layer 4: Peer review; Layer 5: Mutation testing.

## What Gets Installed

The installer configures 22 agents, 18 commands, templates, skills, and DES hooks in `~/.claude/`, making them available across all Claude Code projects.

Installation layout includes:

- Agent specifications in `~/.claude/agents/nw/`
- Command definitions in `~/.claude/commands/nw/`
- Templates and skills in `~/.claude/templates/` and `~/.claude/skills/`
- DES runtime and hooks in `~/.claude/`

## Requirements

- **Python 3.10+**
- **Claude Code CLI**

## Usage

```bash
# Install nWave framework
nwave-ai install

# Preview changes without installing
nwave-ai install --dry-run

# Backup before updating
nwave-ai install --backup-only

# Restore from backup
nwave-ai install --restore

# Show version
nwave-ai version

# Uninstall
nwave-ai uninstall
```

For detailed installation instructions and troubleshooting, see the [Installation Guide](https://github.com/nwave-ai/nwave/tree/main/docs/guides/installation-guide.md).

## Documentation

- **[Installation Guide](https://github.com/nwave-ai/nwave/tree/main/docs/guides/installation-guide.md)** - Step-by-step setup
- **[Jobs To Be Done Guide](https://github.com/nwave-ai/nwave/tree/main/docs/guides/jobs-to-be-done-guide.md)** - When to use each workflow
- **[Commands Reference](https://github.com/nwave-ai/nwave/tree/main/docs/reference/nwave-commands-reference.md)** - All commands and agents
- **[5-Layer Testing Guides](https://github.com/nwave-ai/nwave/tree/main/docs/guides/)** - Quality assurance workflows
- **[DES API Reference](https://github.com/nwave-ai/nwave/tree/main/docs/reference/des-orchestrator-api.md)** - Execution system API
- **[Plugin Architecture](https://github.com/nwave-ai/nwave/tree/main/docs/reference/nwave-plugin-architecture.md)** - Plugin system reference
- **[Troubleshooting Guide](https://github.com/nwave-ai/nwave/tree/main/docs/guides/troubleshooting-guide.md)** - Common issues and solutions

Complete documentation: [github.com/nwave-ai/nwave/tree/main/docs](https://github.com/nwave-ai/nwave/tree/main/docs)

## Community

Join the **[nWave Discord community](https://discord.gg/DeYdSNk6)** for help, discussions, and to share your experience.

## License

MIT License. See [LICENSE](https://github.com/nwave-ai/nwave/blob/main/LICENSE) for details.

## Source

[github.com/nwave-ai/nwave](https://github.com/nwave-ai/nwave)
