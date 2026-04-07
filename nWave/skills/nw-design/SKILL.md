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

Before beginning DESIGN work, read SSOT and prior wave artifacts:

1. **SSOT** (if `docs/product/` exists):
   - `docs/product/architecture/brief.md` — existing architecture to extend (if exists)
   - `docs/product/architecture/adr-*.md` — existing architectural decisions
   - `docs/product/journeys/{name}.yaml` — journey schema for port identification
2. **DISCUSS** (primary input): Read from `docs/feature/{feature-id}/discuss/`:
   - `wave-decisions.md` — decision summary
   - `user-stories.md` — scope, requirements, and embedded acceptance criteria
   - `story-map.md` — walking skeleton and release slicing
   - `outcome-kpis.md` — quality attributes informing architecture

**Migration gate**: If `docs/product/` does not exist but `docs/feature/` has existing features, STOP. Guide the user to `docs/guides/migrating-to-ssot-model/README.md` and complete the migration first. If greenfield, DESIGN will bootstrap `docs/product/architecture/`.

DESIGN reads SSOT architecture first (to extend, not recreate), then feature-level DISCUSS artifacts for the delta. DISCOVER evidence is already synthesized into DISCUSS — read DISCOVER only if wave-decisions.md flags something architecturally significant.

**READING ENFORCEMENT**: You MUST read every file listed in Prior Wave Consultation above using the Read tool before proceeding. After reading, output a confirmation checklist (`✓ {file}` for each read, `⊘ {file} (not found)` for missing). Do NOT skip files that exist — skipping causes architectural decisions disconnected from requirements.

After reading, check whether any DESIGN decisions would contradict DISCUSS requirements. Flag contradictions and resolve with user before proceeding. Example: DISCUSS requires "real-time updates" but DESIGN chooses batch processing — this must be resolved.

## Document Update (Back-Propagation)

When DESIGN decisions change assumptions from prior waves:
1. Document the change in a `## Changed Assumptions` section at the end of the affected DESIGN artifact
2. Reference the original prior-wave document and quote the original assumption
3. State the new assumption and the rationale for the change
4. If architecture constraints require changes to user stories or acceptance criteria, note them in `docs/feature/{feature-id}/design/upstream-changes.md` for the product owner to review

## Discovery Flow

Architecture decisions driven by quality attributes, not pattern shopping:

### Step 1: Understand the Problem
Review JTBD artifacts from DISCUSS to understand which jobs the architecture must serve. Morgan asks: What are we building? For whom? Which quality attributes matter most? (scalability|maintainability|testability|time-to-market|fault tolerance|auditability)

### Step 2: Understand Constraints
Morgan asks: Team size/experience? Timeline? Existing systems to integrate? Regulatory requirements? Operational maturity (CI/CD, monitoring)?

### Step 3: Team Structure (Conway's Law)
Morgan asks: How many teams? Communication patterns? Does proposed architecture match org chart?

### Step 3.5: Development Paradigm Selection

Morgan identifies primary language(s) from constraints, then applies:

- **FP-native** (Haskell|F#|Scala|Clojure|Elixir): recommend Functional
- **OOP-native** (Java|C#|Go): recommend OOP
- **Multi-paradigm** (TypeScript|Kotlin|Python|Rust|Swift): present both, let user choose based on team experience and domain fit

After confirmation, ask user permission to write paradigm to project CLAUDE.md:
- FP: `This project follows the **functional programming** paradigm. Use @nw-functional-software-crafter for implementation.`
- OOP: `This project follows the **object-oriented** paradigm. Use @nw-software-crafter for implementation.`

Default if user declines/unsure: OOP. User can override later.

### Step 4: Recommend Architecture Based on Drivers
Recommend based on quality attribute priorities|constraints|paradigm from Steps 1-3.5. Default: modular monolith with dependency inversion (ports-and-adapters). Overrides require evidence.

If functional paradigm selected, Morgan adapts architectural strategy:
- Types-first design: define algebraic data types and domain models before components
- Composition pipelines: data flows through transformation chains, not method dispatch
- Pure core / effect shell: domain logic is pure, IO lives at boundaries (adapters are functions)
- Effect boundaries replace port interfaces: function signatures serve as ports
- Immutable state: state changes produce new values, no mutation in the domain
These are strategic guidance items for the architecture document — no code snippets.

### Step 5: Advanced Architecture Stress Analysis (HIDDEN -- `--residuality` flag only)
When activated: apply complexity-science-based stress analysis — stressors|attractors|residues|incidence matrix|resilience modifications. See `stress-analysis` skill.
When not activated: skip entirely, do not mention.

### Step 6: Produce Deliverables
- Architecture document with component boundaries|tech stack|integration patterns
- C4 System Context diagram (Mermaid) -- MANDATORY
- C4 Container diagram (Mermaid) -- MANDATORY
- C4 Component diagrams (Mermaid) -- only for complex subsystems
- ADRs for significant decisions

## Rigor Profile Integration

Before dispatching the architect agent, read rigor config from `.nwave/des-config.json` (key: `rigor`). If absent, use standard defaults.

- **`agent_model`**: Pass as `model` parameter to Task tool. If `"inherit"`, omit `model` (inherits from session).
- **`reviewer_model`**: If design review is performed, use this model for the reviewer agent. If `"skip"`, skip design review.
- **`review_enabled`**: If `false`, skip post-design review step.

## Interactive Decision Points

### Decision 0: Design Scope

**Question**: What are you designing?

**Options**:
1. **System / infrastructure** — distributed architecture, scalability, caching, load balancing, message queues
2. **Domain / bounded contexts** — DDD, aggregates, Event Modeling, event sourcing, context mapping
3. **Application / components** — component boundaries, hexagonal architecture, tech stack, ADRs
4. **Full stack** — all three in sequence: system -> domain -> application

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

### Default Invocation (Application scope)

@nw-solution-architect

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
