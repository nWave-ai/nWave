# How-To Guides

Task-oriented, step-by-step procedures. Each guide solves one specific
problem and assumes you know the basics ([tutorials](./TUTORIALS.md) teach
them).

The `nwdes` how-tos below are written for your assistant to run — see
[For your assistant](./README.md#for-your-assistant) for the sentence to
paste and who runs what.

## Deliver and fix

| Guide | Description | Level |
|-------|-------------|-------|
| [Deliver a feature](./nwdes/deliver-feature.md) | Walk one Request through the nwdes route: handoff, product facts, design, oracle, craft, review, examination, integration | Intermediate |
| [Fix a bug](./nwdes/fix-bug.md) | Route one observed defect through the lean nwdes route | Intermediate |
| [Use feature lanes](./nwdes/use-lanes.md) | Isolate one feature in its own worktree and integrate it without rewriting trunk | Intermediate |
| [Run features in parallel](./nwdes/throughput-and-swarm.md) | Throughput and swarm on one box: when to open lanes, capacity admission, integrate and close | Advanced |
| [Deliver a slice with scenario-to-row mapping](./how-to-deliver-wave-step-scenario-mapping/) | One acceptance scenario per acceptance row, observed RED then GREEN, on the nwdes route | Intermediate |
| [Resolve an outcomes collision](./howto-resolve-outcomes-collision.md) | Triage an `nwave-ai outcomes check` flag against an existing outcome | Intermediate |
| [Invoke reviewer agents](./invoke-reviewer-agents/) | Request peer reviews from reviewer agents | Intermediate |

## Install and set up

| Guide | Description | Level |
|-------|-------------|-------|
| [Installation guide](./installation-guide/) | Full setup for Claude Code and the shared surface, with recovery | Beginner |
| [Installing for Codex CLI](./installing-codex.md) | Codex install + verification checklist | Beginner |
| [Installing for Cursor](./installing-cursor.md) | Cursor hook wiring + verification checklist | Beginner |
| [Installing for Devin CLI](./installing-devin.md) | Skills-only Devin integration | Beginner |
| [Installing for OMP](./installing-omp.md) | OMP agents, skills, commands and extension | Beginner |
| [Offline install](./offline-install.md) | Install without network access to the package index | Intermediate |
| [Team rollout](./team-rollout.md) | Roll nWave out to a team | Intermediate |
| [Activate nWave in a project](./activating-nwave-per-project.md) | Turn nWave on or off per repository and check status | Beginner |
| [Assign models to roles](./assigning-models-to-roles.md) | Run one role on a different model, per host | Beginner |
| [Configure documentation density](./configuring-doc-density.md) | Set how much documentation nWave produces | Beginner |

## Upgrade and recover

| Guide | Description | Level |
|-------|-------------|-------|
| [Migrate from nWave 3.x](./migrating-from-3x.md) | Upgrade a 3.x installation to v4, with backup and restore | Intermediate |
| [Update an existing project](./classic-spine-migration.md) | `nwave-ai update` and the project compatibility boundary | Intermediate |
| [Migrate to the SSOT model](./migrating-to-ssot-model/) | 3.x-era document-model migration, kept for existing 3.x projects | Intermediate |
| [Plugin migration guide](./plugin-migration-guide/) | Move from a custom installer to plugin installation | Intermediate |
| [Troubleshooting guide](./troubleshooting-guide/) | Quick fixes for common nWave issues | Intermediate |

## Extend

| Guide | Description | Level |
|-------|-------------|-------|
| [Develop and install tool plugins](./nwave-tool-plugins.md) | Build and install standalone CLIs (e.g. nwave-dedup) that extend nWave | Intermediate |
| [Plugin use cases](./plugin-use-cases/) | Four practical use cases with prompts and expected output | Beginner |

Per-host support depth (what is installed where, and what verifies it) is the
[vendor support matrix](./vendor-support.md). Concepts behind these tasks are
in [Explanation](./EXPLANATION.md).
