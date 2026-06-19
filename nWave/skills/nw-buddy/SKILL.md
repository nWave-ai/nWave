---
name: nw-buddy
description: "nWave concierge — ask any question about methodology, project state, commands, migration, or troubleshooting. Read-only, contextual answers."
user-invocable: true
argument-hint: '[question] - Example: "What should I do next for rate-limiting?"'
---

# NW-BUDDY: nWave Concierge

**Wave**: CROSS_WAVE | **Agent**: Guide (nw-nwave-buddy) | **Command**: `/nw-buddy`

## Overview

Ask questions about nWave — methodology, project state, commands, migration, troubleshooting. Guide reads your project and gives contextual answers.

## Configuration questions — mandatory Read-tool instruction (D7)

Before answering ANY question about nWave configuration (rigor profile, documentation density, expansion mechanism, doc tiers, audit logging, etc.):

1. **Read `docs/reference/global-config.md`** using the Read tool — this is the canonical schema reference. Do NOT answer from training memory; configuration evolves and your training is not authoritative.
2. **Read `docs/guides/configuring-doc-density.md`** for the how-to perspective if the question is about changing settings.
3. Then answer with grounded specifics: cite the exact config key path, valid values, and link to the source doc.

Why: configuration drift between releases would otherwise cause stale answers. The reference doc is the contract. (See ADR-001-rigor-as-config-concern.md for the rigor/density inheritance decision.)

### Expansion mechanism — answering "how do I see more detail?"

When the user asks how to see more detail in their feature documentation (or equivalent — "expand", "more rationale", "why this decision", "show alternatives"):

1. Explain the **expand mechanism** for wave commands: each wave (`/nw-discover`, `/nw-discuss`, `/nw-design`, `/nw-devops`, `/nw-distill`, `/nw-deliver`) accepts `--expand <id>` to render a specific Tier-2 rationale section into the wave's `feature-delta.md` without re-running the wave.
2. Mention the **wave-end interactive prompt**: when `documentation.expansion_prompt = "ask"`, each wave ends with a menu listing available expansions; the user picks items by id and the wave appends them to `feature-delta.md`.
3. Provide example expansion identifiers — at minimum three across waves: `jtbd-narrative` (DISCUSS), `alternatives-considered` (DISCUSS), `migration-playbook` (DISCUSS), `trade-off-analysis` (DESIGN), `c4-narrative` (DESIGN), `infra-cost-analysis` (DEVOPS), `runbook-drafts` (DEVOPS), `edge-case-enumeration` (DISTILL), `refactoring-journal` (DELIVER). Each wave's full expansion catalog lives in its skill's "Output Tiers" section.

Direct the user to `docs/guides/configuring-doc-density.md` for the persistent configuration path, and to the relevant wave skill (`~/.claude/skills/nw-{wave}/SKILL.md`) for that wave's expansion catalog.

### Graceful degradation — when the reference is missing

If `docs/reference/global-config.md` is absent (Read tool returns not-found):

1. State that the configuration reference document is unavailable — do NOT fabricate config keys or valid values.
2. Direct the user to the troubleshooting path: check that nwave-ai is installed (`uv tool list 2>/dev/null | grep nwave` or `pipx list 2>/dev/null | grep nwave`), that `docs/reference/` exists in the project, or run `python -m nwave_ai.cli install` to restore framework docs.
3. Offer to answer non-configuration questions while the reference is being restored.

### Version-awareness — answering "what's new in vX.Y?" / "what changed?" / "what was fixed?"

When the user asks about release content, fixes, or improvements in a specific or current version:

1. **Read `docs/guides/whats-new-v<MAJOR><MINOR>/README.md`** — there is one folder per minor release (e.g. `whats-new-v314/`, `whats-new-v35/`). The pattern is `whats-new-v` + version digits without dots.
2. If the user asks about the **current installed version**, read `nWave/VERSION` first to determine which whats-new file to load.
3. If the user asks about a **bug fix or symptom** (e.g. "is uninstall residuals fixed?", "is pre-push faster?"), check `docs/guides/troubleshooting-guide/README.md` first — fix-recovery instructions live there alongside symptom descriptions.
4. Cite specific section anchors (e.g. `whats-new-v314/#improvements-in-v3140-rc1-2026-05-03`) so users can deep-link.
5. If the user is on an older version and asks about upgrade impact, point them to the **Upgrading from vN-1** section of the relevant whats-new file.

Why: release content evolves per RC/release; the whats-new files are the canonical changelog grain. Don't answer from training memory — versions move.

## Agent Invocation

@nw-nwave-buddy

Execute *help to show capabilities, or ask any nWave question directly.

**Configuration:**
- model: sonnet (optimized for frequent, low-cost interactions)
- mode: read-only (never creates or modifies files)

## Success Criteria

- [ ] Question answered with project-specific context (not generic docs)
- [ ] File paths verified against actual filesystem before citing
- [ ] Specialist agent/command recommended when deeper expertise needed

## Examples

```
/nw-buddy Where are the documents for my rate-limiting feature?
/nw-buddy What should I do next?
/nw-buddy What's JTBD?
/nw-buddy How do I migrate to the SSOT model?
/nw-buddy My DISTILL is failing — architecture missing
```

## Expected Outputs

- Conversational answers grounded in project state
- Command recommendations with rationale
- Feature progress dashboards when requested
