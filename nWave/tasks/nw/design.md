---
description: "Designs system architecture with C4 diagrams and technology selection. Use when defining component boundaries, choosing tech stacks, or creating architecture documents."
argument-hint: "[component-name] - Optional: --residuality --paradigm=[auto|oop|fp]"
---

# NW-DESIGN: Architecture Design

**Wave**: DESIGN (wave 3 of 6) | **Agents**: Morgan (nw-solution-architect) | **Command**: `*design-architecture`

## Overview

Execute DESIGN wave through discovery-driven architecture design. Morgan asks about business drivers and constraints first, then recommends architecture that fits. Analyzes existing codebase, evaluates open-source alternatives, produces C4 diagrams (Mermaid) as mandatory output.

## Context Files Required

- docs/feature/{feature-id}/discuss/jtbd-job-stories.md — Job stories from DISCUSS
- docs/feature/{feature-id}/discuss/jtbd-four-forces.md — Four Forces analysis from DISCUSS
- docs/feature/{feature-id}/discuss/jtbd-opportunity-scores.md — Opportunity scores (if multiple jobs)
- docs/feature/{feature-id}/discuss/journey-{name}-visual.md — UX journey map from DISCUSS
- docs/feature/{feature-id}/discuss/user-stories.md — User stories from DISCUSS
- docs/feature/{feature-id}/discuss/requirements.md — Requirements from DISCUSS

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

## Agent Invocation

@nw-solution-architect

Execute \*design-architecture for {feature-id}.

Context files: see Context Files Required above.

**Configuration:**
- model: rigor.agent_model (omit if "inherit")
- interactive: moderate
- output_format: markdown
- diagram_format: mermaid (C4)
- stress_analysis: {true if --residuality flag, false otherwise}

**SKILL_LOADING**: Read your skill files at `~/.claude/skills/nw/solution-architect/`. At Phase 4, always load: `architecture-patterns.md`, `architectural-styles-tradeoffs.md`, `roadmap-design.md`. Then follow your Skill Loading Strategy table for phase-specific skills.

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

## Expected Outputs

```
docs/feature/{feature-id}/design/
  architecture-design.md       (includes C4 diagrams in Mermaid)
  technology-stack.md
  component-boundaries.md
  data-models.md
docs/adrs/
  ADR-NNN-*.md
CLAUDE.md (project root)   (optional: ## Development Paradigm section)
```
