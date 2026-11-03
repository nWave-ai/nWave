# nWave

nWave supplies specialist roles and a host-led delivery workflow for software teams. Its `nwdes` command builds one canonical handoff per feature — the single JSON record of the feature's facts — and renders briefs, role prompts, output schemas, and review packets from it. Your coding host (Claude Code, Codex, OpenCode, OMP, Cursor, Copilot, or Devin) invokes the roles and runs the models; the root assistant — the session you talk to — runs verification and decides what happens next. You decide scope and trade-offs.

> Coming from 3.x? nWave 4 is a major release and a breaking change from 3.x. The old delivery runtime is removed, the 3.x delivery commands are replaced by the nwdes verbs, and Python 3.11 or newer is required. There is no converter for 3.x roadmaps or execution logs. Read the migration guide before you upgrade: https://github.com/nWave-ai/nWave/blob/main/docs/guides/migrating-from-3x.md.

New to the vocabulary? Each term below is defined at first use; the [glossary](https://github.com/nWave-ai/nWave/tree/main/docs/guides/glossary.md) collects them in one place.

## What is new in v4

- **`nwdes` is the delivery tool.** One canonical handoff per feature; briefs, prompts, schemas and packets are rendered from it. The host invokes the roles.
- **The previous delivery runtime was removed** from the source tree. `nwave-ai install`, `nwdes` and `code-fact` keep working.
- **Python 3.11 or newer is required.** pip and uv refuse the install on Python 3.10.
- **Commit attribution is on by default** (a `Co-Authored-By: nWave <nwave@nwave.ai>` trailer). An explicit off still wins.
- **Jev questions are on by default.** Jev, the remote judgment service for bounded questions, is authorized by default in `nwdes`; an explicit refusal always wins (`--jev unauthorized` on the call, or `"jev": "unauthorized"` in `~/.nwave/config.json`). The `TYPESAFE_API_KEY` environment variable is only a technical prerequisite — nwdes never reads it.

Full notes and upgrade steps: [release notes](https://github.com/nWave-ai/nWave/releases), [What's new in v4](https://github.com/nWave-ai/nWave/tree/main/docs/guides/whats-new-v4/), [Migrate from 3.x](https://github.com/nWave-ai/nWave/tree/main/docs/guides/migrating-from-3x.md).

## Install

Requires:

- Python 3.11 or newer;
- a supported coding host (see the table below);
- Git for commits — 2.38 or newer for the lane actions.
- Linux or macOS; on Windows, use WSL ([installation guide](https://github.com/nWave-ai/nWave/tree/main/docs/guides/installation-guide/README.md)).

Preview any install with `--dry-run` before it writes host files.

```bash
uv tool install nwave-ai            # or: pipx install nwave-ai
nwave-ai install --platform claude-code --dry-run   # preview first
nwave-ai install --platform claude-code             # then install
```

`--platform` accepts exactly: `auto`, `claude-code`, `opencode`, `codex`, `cursor`, `copilot`, `omp`, `devin`, `all`. Auto-detect never guesses: with no detected host, the installer refuses before writing anything.

| Platform | The installer deploys | Verified by | Guide |
|---|---|---|---|
| `claude-code` | Templates, utilities, agents, `/nw-*` commands, skills | Container end-to-end install tests | [Installation guide](https://github.com/nWave-ai/nWave/tree/main/docs/guides/installation-guide/README.md) |
| `opencode` | Skills, agents, commands, plugin | Container end-to-end install tests | [Installation guide](https://github.com/nWave-ai/nWave/tree/main/docs/guides/installation-guide/README.md) |
| `codex` | Skills, TOML agents, hook integration | Container end-to-end install tests | [Installing for Codex](https://github.com/nWave-ai/nWave/tree/main/docs/guides/installing-codex.md) |
| `omp` | Skills, agents, `/nw-*` commands, extension | Installer self-validation | [Installing for OMP](https://github.com/nWave-ai/nWave/tree/main/docs/guides/installing-omp.md) |
| `cursor` | Global user hooks only | Installer self-validation | [Installing for Cursor](https://github.com/nWave-ai/nWave/tree/main/docs/guides/installing-cursor.md) |
| `copilot` | Hook integration only | Installer self-validation | [Vendor support](https://github.com/nWave-ai/nWave/tree/main/docs/guides/vendor-support.md) (no guide yet) |
| `devin` | Public skills under `~/.config/devin/skills/` plus a manifest | Installer self-validation | [Installing for Devin](https://github.com/nWave-ai/nWave/tree/main/docs/guides/installing-devin.md) |

Verification depth differs per host, as the table states: container end-to-end install tests exercise a full install in a container, while installer self-validation means the installer's own prerequisite checks and final validation report — no dedicated end-to-end test covers those hosts yet. Cursor and Copilot are hook-only (no agents or native skills); Devin is skills-only; OMP receives skills, agents, commands and an extension. Restart the host after installation, then confirm `nwdes --help` works — the one `nwdes` command you run at setup.

Installation is host-wide; project activation is separate and opt-in:

```bash
cd /path/to/your/project
nwave-ai project enable
nwave-ai status        # expect: This project is active.
```

`project enable` writes `.nwave/config.json` with `"enabled": true` and makes it trackable. Commit that file if your team should inherit the activation. Then, inside the host, ask `/nw-buddy What should I do next?` (Claude Code), `$nw-buddy` (Codex, OpenCode) or `/nw-buddy` (OMP installs the same `/nw-*` commands). Cursor, Copilot and Devin have no host command: restart the host, then point your assistant at [Deliver a feature](https://github.com/nWave-ai/nWave/tree/main/docs/guides/nwdes/deliver-feature.md) — on Devin by asking about the installed `nw-` skills; on Cursor and Copilot the assistant has no nWave skills, so paste it the sentence from [For your assistant](https://github.com/nWave-ai/nWave/tree/main/docs/guides/README.md#for-your-assistant) (the `nwdes` terminal route stays as a fallback there).

Before an upgrade you can create a recovery point with `nwave-ai install --backup-only`. `nwave-ai install --restore` rolls back a Claude Code installation; on Codex a restore is currently a no-op, and the other hosts differ — read the [installation guide](https://github.com/nWave-ai/nWave/tree/main/docs/guides/installation-guide/README.md) for your host's recovery surface. On Claude Code, `nwave-ai doctor` checks the installation; on the other hosts, read the installer's own final validation (doctor checks Claude Code assets, so a host-only install can fail it without being broken).

## First steps

The `nwdes` steps in these guides are your assistant's to run; the
[For your assistant](https://github.com/nWave-ai/nWave/tree/main/docs/guides/README.md#for-your-assistant) block gives you
the exact sentence to paste. The first lesson below is the one you type
yourself, once, to learn the command flow.

- [First feature with nwdes](https://github.com/nWave-ai/nWave/tree/main/docs/guides/tutorial-nwdes-first-feature/) — a safe walk through the command flow in a throwaway repository.
- [Deliver a feature](https://github.com/nWave-ai/nWave/tree/main/docs/guides/nwdes/deliver-feature.md) — the real route, end to end.
- [Fix a bug](https://github.com/nWave-ai/nWave/tree/main/docs/guides/nwdes/fix-bug.md) — the single-defect route.

Per-wave lessons (discovery, discuss, design, distill, deliver, devops and more) live under `docs/guides/tutorial-*`.

## How a delivery runs

Three routes are open to a request. **Spine waves** run the `/nw-*` commands with their gates, independent review and source-blind examination for a whole feature. **Host-led nwdes steps** let the root invoke roles with generated prompts; roles record their own values and close their drafts; a public oracle is approved before code. **Working directly** keeps no gate and no delivery authority. Choose by what must survive the session and what a late refusal would cost; the choice is stated openly. Working directly remains a valid answer when little must survive.

Every request starts with a working **S/M/L assessment** — small, medium, or large — with its reason: outcome, number and coupling of values, correction radius, cost of a late refusal. It is a judgment to revise as evidence changes; it never selects the route, and no command routes by it.

Only two waves are required for development: **DISTILL**, which authors the executable public oracle, and **DELIVER**, which implements against it. DISCOVER, DIVERGE, DISCUSS, DESIGN and DEVOPS are optional; each answers a question you may not have.

A delivery produces its artifacts in this order (all in your repository):

1. The root records product facts: promises and slices. A **slice** is one observable behavior.
2. The architect records design facts, when the request needs them.
3. The examiner fixes **expectations**: the statements it will later judge.
4. The acceptance designer writes the **oracle** — an executable check of the promised public behavior — and the oracle is independently approved before any production code.
5. The host observes the oracle fail (**RED**), the crafter implements, the host observes it pass (**GREEN**).
6. A fresh independent **review** judges the whole candidate, including the oracle.
7. **EXAMINE**: a source-blind examiner judges every expectation from the user's point of view, without seeing the source, reviews or producer claims.
8. The candidate integrates.
One optional **charter** records the feature's intent with at least one positive and one negative observation; it is written once for the whole feature, never per slice.

The **handoff** — `docs/feature/<id>/handoff.json` in your repository — holds every recorded fact of the feature. nwdes keeps no workflow state: after an interruption, you resume by reading the handoff and the briefs rendered from it, not by replaying a pipeline. [Understanding delivery artifacts](https://github.com/nWave-ai/nWave/tree/main/docs/guides/understanding-delivery-artifacts/) explains each artifact, its producer and the flow diagram.

## nwdes is a tool, not a runner

nwdes builds prompts and packets, records the typed values that roles supply, and refuses what does not add up. It makes no model calls, stores no verdicts of its own, and has no gates: the root assistant chooses the next step; humans decide scope. Roles record through typed verbs — the first `add` opens a draft, `close` publishes it, and a refusal preserves the draft unchanged. Wrong states are made hard to write: you cannot close an incomplete record, submit another role's draft, or hand-edit the handoff instead of recording facts.

Every refusal names WHAT is wrong, WHY it was refused, and HOW to correct it. For example, `nwdes review close` without a recorded observation refuses `ReviewUnobserved`, naming the missing fact and how to record one — an unobserved review cannot be published. [Understanding nwdes](https://github.com/nWave-ai/nWave/tree/main/docs/guides/understanding-nwdes/) expands the tool's contract and its limits.

## Parallel work on one machine

A **lane** is an isolated Git worktree and branch for one feature: `nwdes lane open`, then `nwdes lane compose` (merge trunk in; it prints the EXPECTED and CANDIDATE identities), then `nwdes lane integrate` (fast-forward trunk and remove the lane, refusing every problem in one pass). Independent features run in parallel lanes. Open lanes are a work-in-progress count, not a cap: what admits a local test run is machine capacity — check available memory before each run, never starve the box, and send broad runs to CI. CI gates the push, never the local integration. [Throughput and swarm](https://github.com/nWave-ai/nWave/tree/main/docs/guides/nwdes/throughput-and-swarm.md), [use lanes](https://github.com/nWave-ai/nWave/tree/main/docs/guides/nwdes/use-lanes.md).

## Choosing a model per role

The role defines the work; the model is your choice, per role. The mechanism is the host's agent file: on Claude Code each agent's frontmatter carries a `model:` field (values such as `claude-opus-5`, `sonnet`, `haiku`, or `inherit`) — edit the installed file to change one role. On OMP, installed roles inherit your configured model. On Codex, each agent TOML has an optional `model` field; Claude-named selectors are dropped at install (with a visible notice), so Codex roles answer on the host-configured model unless you set a Codex model there. [Assigning models to roles](https://github.com/nWave-ai/nWave/tree/main/docs/guides/assigning-models-to-roles.md) covers every host, including the ones without role agents.

## Configuration

nwdes reads nested JSON tiers; a later tier overrides the same key: global `~/.nwave/config.json`, then the repository's `.nwave/config.json`, then — for destination keys only — the feature's `.nwave/features/<id>/config.json`. Keys select output directories, the lane trunk branch (`lanes.trunk`, no built-in default) and the Jev choice. Project activation is separate and opt-in (`nwave-ai project enable` / `disable`; machine-wide `nwave-ai mode opt-in|all`). How much explanation you get after a completed wave is `documentation.expansion_prompt` in the global file (`ask-intelligent` by default). Details: [configuration reference](https://github.com/nWave-ai/nWave/tree/main/docs/guides/nwdes/reference/index.md#configuration), [activating nWave per project](https://github.com/nWave-ai/nWave/tree/main/docs/guides/activating-nwave-per-project.md), [documentation detail](https://github.com/nWave-ai/nWave/tree/main/docs/guides/configuring-doc-density.md).

## Jev and privacy

Jev (TypeSafe System One) answers bounded semantic questions — a choice between stated candidates, a score against a rubric — for supported task-level decisions. Jev is authorized by default in nWave. `nwdes` resolves the authorization from the `--jev` flag when given, else the repository's `.nwave/config.json`, else the global `~/.nwave/config.json`, else the default `authorized`; an explicit refusal always wins, and every role bundle prints the resolved value. What authorizes Jev is the default policy plus your refusal switch. The `TYPESAFE_API_KEY` environment variable only lets the service accept requests; without it nothing is sent and the caller records `typesafe: unavailable` — nwdes never reads the variable. Credentials, secrets, personal data, private findings and confidential identifiers are never sent. nWave collects no telemetry: workflow artifacts stay on your machine. [Understanding Jev](https://github.com/nWave-ai/nWave/tree/main/docs/guides/understanding-jev.md), [Privacy Policy](PRIVACY.md).

## Design depth, when you want it

For a design that keeps giving wrong answers, nWave's algebraic protocol names what a user can observe and what counts as equal before choosing any representation, then follows each contradiction back to the representation that caused it. **Prefactoring** is a behavior-preserving structural move made before new behavior: the design declares it, and the check runs before the move and again after the move, before any new behavior exists. Formal checkers are optional and per role: Quint explores product scenarios for the product owner; Agda, Quint and TLA+ check architect models. nWave ships none of them — the assistant offers the installation once, and never blocks on a proof. [Understanding design rigor](https://github.com/nWave-ai/nWave/tree/main/docs/guides/understanding-design-rigor.md).

## What nWave writes, and when not to use it

In your repository: `.nwave/config.json` (activation and project settings) and, per feature, `docs/feature/<id>/handoff.json` with `brief.md`, `architecture.md`, `acceptance.md` (plus HTML renderings) and the roles' run records beside it. The installer writes only host directories; preview it with `--dry-run`. Commits stay yours: one plain `git commit` per green slice, hooks on — nwdes never passes `--no-verify`. The attribution trailer is on by default; `nwave-ai attribution off` removes it.

Not every job needs nWave. Working directly stays open and honest: no gate, no retained authority, nothing that attests the result. A one-off script, a throwaway probe, or a change you will verify yourself may not need roles, oracles or review. If you want the result to survive the session — reviewed, examined, resumable — use a route that provides it.

## Reference

| Look up | Read |
|---|---|
| nwdes verbs and options | [nwdes reference](https://github.com/nWave-ai/nWave/tree/main/docs/guides/nwdes/reference/index.md) |
| The delivery workflow contract | [nw-nwdes reference](https://github.com/nWave-ai/nWave/tree/main/docs/reference/skills/nw-nwdes.md) |
| Routing and size assessment | [nw-auto reference](https://github.com/nWave-ai/nWave/tree/main/docs/reference/skills/nw-auto.md) |
| Models per role | [nw-rigor reference](https://github.com/nWave-ai/nWave/tree/main/docs/reference/skills/nw-rigor.md) |
| Terms | [Glossary](https://github.com/nWave-ai/nWave/tree/main/docs/guides/glossary.md) |
| Host support levels | [Vendor support](https://github.com/nWave-ai/nWave/tree/main/docs/guides/vendor-support.md) |
| Agents, skills, commands | [Agents index](https://github.com/nWave-ai/nWave/tree/main/docs/reference/agents/index.md), [Skills index](https://github.com/nWave-ai/nWave/tree/main/docs/reference/skills/index.md), [Commands index](https://github.com/nWave-ai/nWave/tree/main/docs/reference/commands/index.md) |
| Troubleshooting, offline, teams | [Troubleshooting](https://github.com/nWave-ai/nWave/tree/main/docs/guides/troubleshooting-guide/README.md), [Offline install](https://github.com/nWave-ai/nWave/tree/main/docs/guides/offline-install.md), [Team rollout](https://github.com/nWave-ai/nWave/tree/main/docs/guides/team-rollout.md) |
| Uninstall | `nwave-ai uninstall` (see the per-host guides) |
| What changed in v4 | [What's new in v4](https://github.com/nWave-ai/nWave/tree/main/docs/guides/whats-new-v4/) |

## Community and privacy

Report defects and feature requests on [GitHub Issues](https://github.com/nWave-ai/nWave/issues); discuss on [Discord](https://discord.gg/Cywj3uFdpd); develop with [Contributing](CONTRIBUTING.md). Workflow artifacts stay local; no telemetry. See the [Privacy Policy](PRIVACY.md).

MIT licensed. See [LICENSE](LICENSE).
