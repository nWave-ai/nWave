# The nWave bundle

This directory contains the agents, skills, templates, and other assets that nWave installs into a selected coding host. It is part of the source tree, not a separate installation target. Start with the [repository README](../README.md) for the current v4 beta route and first-use steps.

The bundle supports [Claude Code](https://claude.com/product/claude-code) and [Codex CLI](https://developers.openai.com/codex/cli). Choose a host during installation, then activate nWave in the project where you work. The [installation guide](../docs/guides/installation-guide/) explains the host-specific install and validation paths.

## Find the right entry

| Need | Read |
|---|---|
| Complete a first feature | [Your First Feature](../docs/guides/tutorial-first-feature/) |
| Choose waves or a direct route | [Wave Routing Guide](../docs/guides/wave-routing-and-entry-points/) |
| Look up commands and agents | [Commands Reference](../docs/reference/commands/index.md) and [Agents Reference](../docs/reference/agents/index.md) |
| Select a provider and model | [`nw-rigor` guidance](skills/nw-rigor/SKILL.md) and [Global Config Reference](../docs/reference/global-config.md) |
| Understand native role execution | [`nw-role-invocation`](skills/nw-role-invocation/SKILL.md): the host runs models and verification; nwdes builds documents |
| Understand where artifacts go | [Wave Directory Structure](../docs/guides/wave-directory-structure/) |
| Diagnose installation issues | [Installation Guide](../docs/guides/installation-guide/) and [Troubleshooting](../docs/guides/troubleshooting-guide/) |

For a whole feature, the spine waves retain applicable decisions and evidence in the handoff and briefs. nwdes is a deterministic builder, not a workflow state machine. Direct work carries no nWave gate or retained authority. The [root README](../README.md#choose-a-route) explains when each route fits.
