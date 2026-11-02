---
name: nw-rigor
description: Configure explicit Codex or Claude model facts for nWave defaults or published roles, consumed by the native host where supported. Never derives a model from a competence label.
user-invocable: true
argument-hint: '[desired competence, provider, model, scope, optional role]'
---

# NW-RIGOR

Public provider/model configuration guidance.

Use the public `nwave-ai model` command to record explicit provider/model facts
for native-host role invocation where supported. nwdes does not execute models.
The command neither maps competence to a model, checks availability, nor falls back.

## Read known selections first

Before asking questions, read the current repository's `.nwave/config.json`
and the global `.nwave/config.json` under the configured agents-home location.
Respect a valid absolute `NWAVE_AGENTS_HOME` when it is set; otherwise
the global file is under the current home directory. Read only: there is no
public `nwave-ai model show` command.

Also reuse a provider, model, scope, or role that the user already selected in
this conversation. Do not ask the user to repeat a valid known value or type a
model identifier that is already available from one of those sources.

For the requested role, present the effective complete provider/model pair, if
one is declared, as a suggestion. A project role override wins over a global
default. If the user asks for a different competence level, explain that the
CLI has no competence profile or automatic mapping; keep the current pair as a
candidate until the user selects a different pair.

## Resolve only missing decisions

Ask only for missing material choices:

1. What work and competence level is needed, including any quality, cost, or
   latency preference?
2. Which scope and target should change: global or current project, and default
   or one published role?
3. Which `codex` or `claude` provider/model pair should be used, when no
   selected pair is already known?

The competence answer helps choose a pair; it is not an input the CLI can map
to a provider or model. A current effective pair, or an identifier from
trustworthy verified provider information, may be offered as a **suggestion**.
Name its source and let the user accept or change it. Once accepted, that known
identifier supplies the CLI input; it need not have been typed by the user.
Never invent an identifier, an automatic competence mapping, or a fallback.

If a role is requested, use its exact published name. `nwave-ai` refuses an
unreadable or unpublished role before it writes configuration.

## Apply the selected setting

After the needed decisions are known or accepted, run exactly one matching
command:

| Scope and target | Command |
|---|---|
| Global default | `nwave-ai model set --provider PROVIDER --model MODEL` |
| Current-project default | `nwave-ai model set --provider PROVIDER --model MODEL --project` |
| Global published-role override | `nwave-ai model set --provider PROVIDER --model MODEL --role ROLE` |
| Current-project published-role override | `nwave-ai model set --provider PROVIDER --model MODEL --role ROLE --project` |

Replace `PROVIDER` with the selected `codex` or `claude`, `MODEL` with the
accepted exact model string, and `ROLE` only with the selected published role.
State the command before executing it and report its result. Do not substitute
the other provider, a default model, or a different scope after a refusal.

Global settings are written to the nWave global configuration. `--project`
writes the current repository's `.nwave/config.json`; a project role override
takes precedence over a global default at runtime.
