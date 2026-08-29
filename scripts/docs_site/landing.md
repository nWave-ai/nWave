<!-- Landing-page getting-started prose. Rendered once and shown on every
     version's home page. Links use the {{V}} placeholder for the version
     segment; the generator stamps it per version. Keep it short. -->

## New to nWave?

nWave is an AI-powered workflow framework that runs **inside Claude Code**. It
orchestrates specialised agents through disciplined development *waves* —
enforcing test-driven development, phase tracking, and deterministic validation
at every step. The result: AI that ships features the way a senior team would,
not ad-hoc vibe-coding.

**The wave model**, end to end:

> DISCOVER → DISCUSS → DESIGN → DEVOPS → DISTILL → DELIVER

Each wave has a command (`/nw-discover`, `/nw-design`, `/nw-deliver`, …) and a
specialist agent behind it. You don't need all of them on day one.

Install nWave into Claude Code:

```bash
sh -c "$(curl -fsSL https://raw.githubusercontent.com/nWave-ai/nWave/main/scripts/install/install.sh)"
```

nWave installs globally but is **opt-in per project**: your first `/nw-` command activates the repo you're in (or run `nwave-ai project enable`). Check any repo with `nwave-ai status` — see [Activating nWave in a Project →](/{{V}}/guides/activating-nwave-per-project/).

Then get productive in three steps:

1. **Try your first delivery** — open a project in Claude Code and run `/nw-deliver`. Watch it write tests, make them pass, and commit.
2. **Follow the path** — [Your First Delivery →](/{{V}}/guides/tutorial-first-delivery/) walks you through it in about 13 minutes.
3. **Go wider** — the [Tutorials](/{{V}}/guides/TUTORIALS/) are ordered from zero to the full lifecycle.

## Already using nWave?

- **What changed** — see [What's New](/{{V}}/guides/whats-new-v319/) for per-project activation (the opt-in gate) and the documented `nwave-ai` CLI.
- **Turn nWave on or off per repo** — [Activating nWave in a Project](/{{V}}/guides/activating-nwave-per-project/) explains the opt-in gate and the `nwave-ai project` / `mode` / `status` commands.
- **Look something up** — the [Reference](/{{V}}/reference/) has every agent, command, skill, and template.
- **Upgrade a project** — [Migrating to the SSOT Model](/{{V}}/guides/migrating-to-ssot-model/) covers moving an existing project to the current document model.
- **Switch versions** — use the selector in the top-right to read the docs for the exact release you're running.

> **Tip:** stuck on anything? Type `/nw-buddy` followed by your question in Claude Code for contextual help on methodology, commands, or project state.
