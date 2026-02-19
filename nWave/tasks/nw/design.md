---
description: "Designs system architecture with C4 diagrams and technology selection. Use when defining component boundaries, choosing tech stacks, or creating architecture documents."
argument-hint: "[component-name] - Optional: --residuality (enable residuality analysis for complex/critical systems)"
---

# NW-DESIGN: Architecture Design

**Wave**: DESIGN (wave 3 of 6)
**Agents**: Morgan (nw-solution-architect)
**Command**: `*design-architecture`

## Overview

Execute DESIGN wave through discovery-driven architecture design. Morgan asks about business drivers and constraints first, then recommends architecture that fits -- no pattern menus, no upfront style selection.

Morgan analyzes the existing codebase, evaluates open-source alternatives, and produces C4 diagrams (Mermaid) as mandatory output.

## Context Files Required

- docs/feature/{feature-name}/discuss/requirements.md - From DISCUSS wave
- docs/feature/{feature-name}/discuss/user-stories.md - From DISCUSS wave
- docs/feature/{feature-name}/discuss/domain-model.md - From DISCUSS wave
- docs/feature/{feature-name}/discuss/ux-journey.md - From DISCUSS wave
- docs/feature/{feature-name}/design/constraints.md - Technical and business constraints

## Discovery Flow

Architecture decisions are driven by quality attributes, not pattern shopping:

### Step 1: Understand the Problem
Morgan asks: What are we building? For whom? What quality attributes matter most? (scalability, maintainability, testability, time-to-market, fault tolerance, auditability)

### Step 2: Understand Constraints
Morgan asks: Team size and experience? Timeline? Existing systems to integrate with? Regulatory requirements? Operational maturity (CI/CD, monitoring)?

### Step 3: Team Structure (Conway's Law)
Morgan asks: How many teams? How do they communicate? Does the proposed architecture match the org chart?

### Step 4: Recommend Architecture Based on Drivers
Morgan recommends architecture based on the quality attribute priorities and constraints gathered in Steps 1-3. Default is modular monolith with dependency inversion (ports-and-adapters). Overrides require evidence. User can request a different approach.

### Step 5: Residuality Analysis (OPTIONAL)
Offered only when: `--residuality` flag provided, OR system has regulatory constraints, complex failure modes, or volatile business environment. Skipped for simple projects.

### Step 6: Produce Deliverables
- Architecture document with component boundaries, tech stack, integration patterns
- C4 System Context diagram (Mermaid) -- MANDATORY
- C4 Container diagram (Mermaid) -- MANDATORY
- C4 Component diagrams (Mermaid) -- only for complex subsystems
- ADRs for significant decisions

## Agent Invocation

@nw-solution-architect

Execute \*design-architecture for {feature-name}.

Context files: see Context Files Required above.

**Configuration:**

- interactive: moderate
- output_format: markdown
- diagram_format: mermaid (C4)
- residuality: {true if --residuality flag, false otherwise}

## Success Criteria

- [ ] Business drivers and constraints gathered before architecture selection
- [ ] Existing system analyzed before design (codebase search performed)
- [ ] Integration points with existing components documented
- [ ] Reuse vs. new component decisions justified
- [ ] Architecture supports all business requirements
- [ ] Technology stack selected with clear rationale
- [ ] Component boundaries defined with dependency-inversion compliance
- [ ] C4 System Context diagram produced (Mermaid)
- [ ] C4 Container diagram produced (Mermaid)
- [ ] ADRs written with alternatives considered
- [ ] Handoff accepted by nw-platform-architect (DEVOP wave)

## Next Wave

**Handoff To**: nw-platform-architect (DEVOP wave)
**Deliverables**: See Morgan's handoff package specification in agent file

## Expected Outputs

```
docs/feature/{feature-name}/design/
  architecture-design.md       (includes C4 diagrams in Mermaid)
  technology-stack.md
  component-boundaries.md
  data-models.md
docs/adrs/
  ADR-NNN-*.md
```
