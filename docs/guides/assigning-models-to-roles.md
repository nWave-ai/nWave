# Assigning models to roles

Give one nWave role a different model without changing its competence. The
principle: **the role defines the work; the model is your choice per role.**
nWave never hard-couples a role to a vendor's model line — where the host has
its own model configuration, nWave defers to it.

How you set the model depends on the host. Paths below are the installed
nWave asset directories each host uses.

## Claude Code

Installed role agents live in `~/.claude/agents/nw/` as Markdown files with
YAML frontmatter. Each carries a `model` field:

```yaml
---
name: nw-acceptance-designer
description: Authors the public executable oracle when required.
model: claude-opus-5
---
```

Allowed values include a concrete model (`claude-opus-5`, `sonnet`,
`haiku`) and `inherit`, which follows your session model. To change a role's
model, edit its `model` line.

## OMP (oh-my-pi)

The installer writes role agents to `~/.omp/agent/agents/` and **omits the
model field on purpose**: every nWave model declaration is a Claude alias,
and an alias there would route the role away from your configured OMP model.
Omission means the role inherits your active model. To pin a different model
for one role, use OMP's own agent model configuration; how to do that is
documented by OMP, not by nWave.

## Codex CLI

Role agents are installed as TOML files, and any Claude model selector in a
role is dropped at install time — the installer reports what it dropped, and
Codex answers with the model from its active configuration
(`~/.codex/config.toml`). The TOML agent schema accepts an optional
`model = "..."` field. If you set it on an installed agent, name a model
your Codex configuration recognizes (see Codex's own model documentation);
Claude model names are not valid here:

```toml
model = "<a-model-name-from-your-codex-configuration>"
```

## OpenCode

Installed agent files carry no `model` field — the projection removes it
together with `name` and `skills`. Model selection follows OpenCode's own
configuration; that mechanism is documented by OpenCode, not by nWave.

## Cursor, Copilot, Devin

These hosts install no role agents (Cursor and Copilot are wired through
hooks; Devin through skills only), so per-role model choice does not apply
there. See [Vendor support](vendor-support.md) for what each host
receives.

## Recording a model preference nWave can keep

Besides editing host files, you can record an explicit provider/model pair
in nWave's configuration with the CLI:

```bash
nwave-ai model set --provider {codex,claude} --model MODEL [--role ROLE [--competence COMPETENCE]] [--project]
```

It writes `model_runtime.default`, or `model_runtime.roles.<role>` with
`--role`, into the global file (or the project's `.nwave/config.json` with
`--project`). The supported providers are `codex` and `claude`; whether your
host reads `model_runtime` is that host's own model-configuration support —
the per-host sections above remain the authoritative mechanism per host. See
the [global configuration reference](../reference/global-config.md) for the
keys.

## Set models for a group, then one role

`nwave-ai rigor` sets models for this project in one run: put a group first, then override the roles that differ. It writes the pairs into the project file `.nwave/config.json` in the current directory, so run it from the repository root. The global file is not changed.

1. See what is in effect. Each role line ends with its source: `project`, `global` or `built-in default`.

```bash
nwave-ai rigor --show
```

2. Set a group, then override one role. Scripted, every answer is an option, so nothing is asked:

```bash
nwave-ai rigor --yes --model-set reviewers=claude/opus-4-6 --model-set nw-documentarist=codex/gpt-5 --review-rounds current --documents keep --hosts none
```

A later `--model-set` for the same role replaces an earlier one, so the single-role override goes after the group. `--review-rounds current` and `--documents keep` leave those settings unchanged, and `--hosts none` changes no host file.

Interactively, run `nwave-ai rigor` in a terminal. It asks six questions one at a time: the models, review rounds, examine level, documents, the document language (only when documents is `yes`), and hosts. It shows the final summary, and writes after you type `yes`. The models question takes one `target=provider/model` pair, so use the scripted form when you set a group and an override together.

3. Check the result:

```bash
nwave-ai rigor --show
```

**Done:** `--show` lists the overridden role with your model and source `project`.

The `--hosts` answer decides whether any host file changes. Which hosts write, which refuse, and which formats are unverified is in the [rigor entry](../reference/cli.md#nwave-ai-rigor). Dynamic mode (`/nw-dynamic`) reads only the examine level among these settings; see [Which routes read these settings](../reference/cli.md#which-routes-read-these-settings).

## Keep your edits across upgrades

`nwave-ai install` manages its asset directories and rewrites them on
reinstall. Keep a copy of your model edits outside the managed directories
and re-apply them after upgrading, the same way you would keep any other
local change to installed assets ([Migrate from nWave
3.x](migrating-from-3x.md)).

**Done:** the role you retargeted answers on the model you chose, and other
roles are unchanged.
