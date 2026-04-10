---
name: nw-design
description: "Designs system architecture with C4 diagrams and technology selection. Routes to the right architect based on design scope (system, domain, application, or full stack). Two interaction modes: guide (collaborative Q&A) or propose (architect presents options with trade-offs)."
user-invocable: true
argument-hint: '[component-name] - Optional: --residuality --paradigm=[auto|oop|fp]'
---

# NW-DESIGN: Architecture Design

**Wave**: DESIGN (wave 3 of 6) | **Agents**: Morgan (nw-solution-architect), nw-system-designer, nw-ddd-architect | **Command**: `*design-architecture`

## Overview

Execute DESIGN wave through discovery-driven architecture design. The command starts with two interactive decisions:

1. **Design Scope** — routes to the right architect: system-level (@nw-system-designer), domain-level (@nw-ddd-architect), application-level (@nw-solution-architect), or full stack (all three in sequence).
2. **Interaction Mode** — guide (architect asks questions, you decide together) or propose (architect reads requirements, presents 2-3 options with trade-offs).

All architects write to `docs/product/architecture/brief.md` (SSOT), each in its own section. Analyzes existing codebase, evaluates open-source alternatives, produces C4 diagrams (Mermaid) as mandatory output.

## Prior Wave Consultation

Before beginning DESIGN work, read SSOT and prior wave artifacts in this order:

1. **Read SSOT architecture** (if `docs/product/` exists) — read `docs/product/architecture/brief.md` (extend, not recreate), `docs/product/architecture/adr-*.md` (existing decisions), `docs/product/journeys/{name}.yaml` (journey schema for port identification). Gate: all existing files read or confirmed missing.
2. **Read DISCUSS artifacts** (primary input) — read from `docs/feature/{feature-id}/discuss/`: `wave-decisions.md` (decision summary), `user-stories.md` (scope, requirements, acceptance criteria), `story-map.md` (walking skeleton and release slicing), `outcome-kpis.md` (quality attributes). Gate: all four files read or confirmed missing.
3. **Read SPIKE findings** (if spike was run) — read from `docs/feature/{feature-id}/spike/`: `findings.md` (validated assumptions, performance measurements, what didn't work). This informs your architecture constraints. Gate: file read if present, marked as not found if absent.
4. **Output confirmation checklist** — after reading, output `✓ {file}` for each read, `⊘ {file} (not found)` for each missing. Gate: checklist produced before any architecture work begins.
5. **Check for contradictions** — identify any DESIGN decisions that would contradict DISCUSS requirements or SPIKE findings. Flag contradictions and resolve with user before proceeding. Example: DISCUSS requires "real-time updates" but DESIGN chooses batch processing; or SPIKE found performance budget can't be met. Gate: zero unresolved contradictions.
6. **Migration gate check** — if `docs/product/` does not exist but `docs/feature/` has existing features, STOP. Guide the user to `docs/guides/migrating-to-ssot-model/README.md`. If greenfield, proceed — DESIGN will bootstrap `docs/product/architecture/`. Gate: migration status confirmed.

Note: DISCOVER evidence is already synthesized into DISCUSS — read DISCOVER only if wave-decisions.md flags something architecturally significant.

## Document Update (Back-Propagation)

When DESIGN decisions change assumptions from prior waves:

1. **Document the change** — add a `## Changed Assumptions` section at the end of the affected DESIGN artifact. Gate: section present in artifact.
2. **Reference the original** — quote the original assumption from the prior-wave document, with file path. Gate: original quoted verbatim with source.
3. **State the new assumption** — write the replacement assumption and its rationale. Gate: new assumption and rationale present.
4. **Propagate upstream if needed** — if architecture constraints require changes to user stories or acceptance criteria, write them to `docs/feature/{feature-id}/design/upstream-changes.md` for the product owner to review. Gate: upstream-changes.md created if any story/criteria changes needed.

## Discovery Flow

Architecture decisions are driven by quality attributes, not pattern shopping. Execute these steps in order:

1. **Understand the Problem** — review JTBD artifacts from DISCUSS. Ask: What are we building? For whom? Which quality attributes matter most? (scalability|maintainability|testability|time-to-market|fault tolerance|auditability). Gate: quality attribute priorities ranked.
2. **Understand Constraints** — ask: Team size/experience? Timeline? Existing systems to integrate? Regulatory requirements? Operational maturity (CI/CD, monitoring)? Gate: constraints list documented.
3. **Map Team Structure (Conway's Law)** — ask: How many teams? Communication patterns? Does proposed architecture match org chart? Gate: team-architecture alignment confirmed.
4. **Select Development Paradigm** — identify primary language(s) from constraints, then: FP-native (Haskell|F#|Scala|Clojure|Elixir) → recommend Functional; OOP-native (Java|C#|Go) → recommend OOP; Multi-paradigm (TypeScript|Kotlin|Python|Rust|Swift) → present both, let user choose. After confirmation, ask user permission to write paradigm to project CLAUDE.md: FP: `This project follows the **functional programming** paradigm. Use @nw-functional-software-crafter for implementation.` OOP: `This project follows the **object-oriented** paradigm. Use @nw-software-crafter for implementation.` Default if user declines/unsure: OOP. Gate: paradigm selected and optionally written to CLAUDE.md.
5. **Recommend Architecture Based on Drivers** — recommend based on quality attribute priorities|constraints|paradigm from steps 1-4. Default: modular monolith with dependency inversion (ports-and-adapters). Overrides require evidence. If functional paradigm: apply types-first design, composition pipelines, pure core / effect shell, effect boundaries as ports, immutable state — in architecture document only, no code snippets. Gate: architecture pattern selected with written rationale.
6. **Stress Analysis** (HIDDEN — `--residuality` flag only) — when activated: apply complexity-science-based stress analysis (stressors|attractors|residues|incidence matrix|resilience modifications) using the `stress-analysis` skill. When not activated: skip entirely, do not mention. Gate: activated only when flag present.
7. **Produce Deliverables** — write architecture document with component boundaries|tech stack|integration patterns. Produce C4 System Context diagram (Mermaid) — mandatory. Produce C4 Container diagram (Mermaid) — mandatory. Produce C4 Component diagrams (Mermaid) — only for complex subsystems. Write ADRs for significant decisions. Gate: mandatory C4 diagrams present, ADRs written.

## Rigor Profile Integration

Before dispatching the architect agent, read rigor config from `.nwave/des-config.json` (key: `rigor`). If absent, use standard defaults.

- **`agent_model`**: Pass as `model` parameter to Task tool. If `"inherit"`, omit `model` (inherits from session).
- **`reviewer_model`**: If design review is performed, use this model for the reviewer agent. If `"skip"`, skip design review.
- **`review_enabled`**: If `false`, skip post-design review step.

## Interactive Decision Points

### Decision 0: Design Scope (MANDATORY — do NOT skip)

**Question**: What are you designing?

You MUST ask this question before invoking any architect. Do NOT default to application scope. The answer determines WHICH agent to invoke.

**Options**:
1. **System / infrastructure** → invokes @nw-system-designer
2. **Domain / bounded contexts** → invokes @nw-ddd-architect
3. **Application / components** → invokes @nw-solution-architect
4. **Full stack** → invokes all three agents sequentially

### Decision 1: Interaction Mode

**Question**: How do you want to work?

**Options**:
1. **Guide me** — the architect asks questions, you make decisions together
2. **Propose** — the architect reads your requirements and proposes 2-3 options with trade-offs

## Agent Invocation

### Architect Routing (based on Decision 0)

| Decision 0 | Agent | Focus |
|-------------|-------|-------|
| System / infrastructure | @nw-system-designer | Distributed architecture, scalability, caching, load balancing, message queues |
| Domain / bounded contexts | @nw-ddd-architect | DDD, aggregates, Event Modeling, event sourcing, context mapping |
| Application / components | @nw-solution-architect | Component boundaries, hexagonal architecture, tech stack, ADRs |
| Full stack | @nw-system-designer then @nw-ddd-architect then @nw-solution-architect | All three in sequence |

Pass Decision 1 (guide/propose) to the invoked agent as the interaction mode.

All agents write to `docs/product/architecture/` (SSOT). Each architect owns its section:
- @nw-system-designer writes `## System Architecture` in `brief.md`
- @nw-ddd-architect writes `## Domain Model` in `brief.md`
- @nw-solution-architect writes `## Application Architecture` in `brief.md`

For **Full stack** mode, each agent reads the prior architect's output before starting its own work.

### Agent Dispatch (after Decision 0 — no default)

Based on Decision 0 answer, invoke the corresponding agent. Do NOT default to application scope without asking.

**System scope** → @nw-system-designer
**Domain scope** → @nw-ddd-architect
**Application scope** → @nw-solution-architect
**Full stack** → @nw-system-designer then @nw-ddd-architect then @nw-solution-architect

Execute \*design-architecture for {feature-id}.

Context files: see Prior Wave Consultation above.

**Configuration:**
- model: rigor.agent_model (omit if "inherit")
- interaction_mode: {Decision 1: "guide" or "propose"}
- interactive: moderate
- output_format: markdown
- diagram_format: mermaid (C4)
- stress_analysis: {true if --residuality flag, false otherwise}

**SKILL_LOADING**: Read your skill files at `~/.claude/skills/nw-{skill-name}/SKILL.md`. At Phase 4, always load: `nw-architecture-patterns`, `nw-architectural-styles-tradeoffs`. Do NOT load `nw-roadmap-design` during DESIGN wave -- roadmap creation belongs to the DELIVER wave (`/nw-roadmap` or `/nw-deliver`). Then follow your Skill Loading Strategy table for phase-specific skills.

## Success Criteria

- [ ] Business drivers and constraints gathered before architecture selection
- [ ] Existing system analyzed before design (codebase search performed)
- [ ] Integration points with existing components documented
- [ ] Reuse vs. new component decisions justified
- [ ] Architecture supports all business requirements
- [ ] Technology stack selected with clear rationale
- [ ] Development paradigm selected and (optionally) written to project CLAUDE.md
- [ ] Component boundaries defined with dependency-inversion compliance
- [ ] C4 System Context + Container diagrams produced (Mermaid)
- [ ] ADRs written with alternatives considered
- [ ] Handoff accepted by nw-platform-architect (DEVOPS wave)

## Next Wave

**Handoff To**: nw-platform-architect (DEVOPS wave)
**Deliverables**: See Morgan's handoff package specification in agent file

## Wave Decisions Summary

Before completing DESIGN, produce `docs/feature/{feature-id}/design/wave-decisions.md`:

```markdown
# DESIGN Decisions — {feature-id}

## Key Decisions
- [D1] {decision}: {rationale} (see: {source-file})

## Architecture Summary
- Pattern: {e.g., modular monolith with ports-and-adapters}
- Paradigm: {OOP|FP}
- Key components: {list top-level components}

## Technology Stack
- {language/framework}: {rationale}

## Constraints Established
- {architectural constraint}

## Upstream Changes
- {any DISCUSS assumptions changed, with rationale}
```

This summary enables DEVOPS and DISTILL to quickly assess architecture decisions without reading all DESIGN files.

## Expected Outputs

### Feature delta (in `docs/feature/{feature-id}/`)
```
  wave-decisions.md              (appends ## DESIGN Decisions section)
```

### SSOT updates (in `docs/product/architecture/`)
```
  brief.md                       (created or updated — each architect owns its section:
                                   ## System Architecture — nw-system-designer
                                   ## Domain Model — nw-ddd-architect
                                   ## Application Architecture — nw-solution-architect)
  adr-*.md                       (new ADRs for this feature's architectural decisions)
  c4-diagrams.md                 (current component topology, if separate from brief)
```

### Optional
```
CLAUDE.md (project root)         (optional: ## Development Paradigm section)
```
