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

## Output Tiers (per D2)

Provenance: feature `lean-wave-documentation` — D2 (schema-typed sections), D10 (one-line expansion descriptions). Tier-1 [REF] sections (always emitted) + Tier-2 EXPANSION CATALOG items (lazy, on-demand) are the two output bands. Full contract: `nWave/skills/nw-density-resolution-contract/SKILL.md`.

### Tier-1 [REF] — always emitted

Under `## Wave: DESIGN / [REF] <Section>` headings:

- DDD list — D-numbered design decisions with verdicts and one-line rationale
- Component decomposition — table of components with paths and change types
- Driving ports — inbound surfaces (CLI, skill, HTTP) named per the C4 contract
- Driven ports + adapters — outbound side-effects with adapter mapping
- Technology choices — pinned languages/frameworks/runtime versions
- Decisions table — DDD-N row per locked decision (no rationale prose)
- Reuse Analysis table — every overlapping component classified EXTEND or CREATE NEW
- Open questions — items deliberately deferred to DISTILL/DELIVER

### Tier-2 EXPANSION CATALOG — lazy, on-demand (per D10)

Rendered under `## Wave: DESIGN / [WHY|HOW] <Section>` only when requested via `--expand <id>` (DDD-2), the wave-end menu (`expansion_prompt = "ask"`), `mode = "full"` auto-expansion, or an ad-hoc user request mid-session.

| Expansion ID | Tier label | One-line description |
|---|---|---|
| `trade-off-analysis` | [WHY] | Quality-attribute trade-off matrix with prioritization rationale |
| `rejected-alternatives` | [WHY] | Architectures weighed and rejected with one-paragraph reason per option |
| `c4-narrative` | [HOW] | Long-form C4 walkthrough: System Context → Container → Component prose |
| `evolution-scenarios` | [WHY] | Hypothetical future stress vectors and how the design absorbs them |
| `paradigm-rationale` | [WHY] | Why FP/OOP was selected; comparison vs the alternative for this domain |
| `reuse-analysis-deep-dive` | [WHY] | Per-row justification for every EXTEND vs CREATE NEW decision in the Reuse table |
| `c4-component-diagrams` | [HOW] | Component-level C4 diagrams for complex subsystems (Mermaid) |
| `expansion-catalog-rationale` | [WHY] | Why this set of expansions, why these defaults, why D10 enforces one-line descriptions |

## Density resolution (per D12)

Call `resolve_density(global_config)` from `scripts/shared/density_config.py` after reading `~/.nwave/global-config.json` (missing/malformed = empty dict). Returns `mode` (`"lean"` | `"full"`) + `expansion_prompt` (`"ask"` | `"always-skip"` | `"always-expand"` | `"smart"`) per the D12 cascade (resolver-internal, DDD-5 — do NOT replicate locally). Branch on `density.mode` for what to emit; branch on `density.expansion_prompt` at wave end for menu behaviour. Full cascade detail, branch semantics, ad-hoc override workflow: `nWave/skills/nw-density-resolution-contract/SKILL.md`.

## Telemetry (per D4 + DDD-6)

Every expansion choice emits a `DocumentationDensityEvent` (dataclass at `src/des/domain/telemetry/documentation_density_event.py`) via `event.to_audit_event()` → `JsonlAuditLogWriter().log_event(...)`. Schema fields per D4: `feature_id`, `wave`, `expansion_id`, `choice`, `timestamp`. For this wave the schema declares `"wave": "DESIGN"`. Use helper `scripts/shared/telemetry.py:write_density_event(...)` — do NOT write JSONL directly.

Wave-specific signal: DEVOPS/DISTILL consuming a lean DESIGN feature-delta — downstream `--expand` requests for trade-off or evolution scenarios indicate the `[REF]` baseline was insufficient. Full emission rules: `nWave/skills/nw-density-resolution-contract/SKILL.md`.

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
5. **Reuse Analysis (MANDATORY — RCA F-1 fix)** — before designing ANY new component, search the existing codebase for components with overlapping responsibilities. For each overlap, decide "extend existing" or "justify new". Output a table:

   ```
   | Existing Component | File | Overlap | Decision | Justification |
   |-------------------|------|---------|----------|---------------|
   | WorkflowExecutor | src/des/application/zero_trust/workflow_executor.py | Phase iteration, gate eval | EXTEND | Adding dispatch branch is ~15 LOC vs 200 LOC new class |
   ```

   Rules:
   - If the design creates a new class that does something an existing class already does (iterate phases, evaluate gates, dispatch agents, handle retry), the default is EXTEND, not CREATE NEW.
   - CREATE NEW requires evidence that extending is impossible or creates unacceptable coupling (not just "it's complex").
   - "The existing class has too many dependencies" is NOT a valid justification — simplify the existing class instead (see F-4: strategy pattern extraction).
   - The reviewer MUST verify this table exists and challenge every "CREATE NEW" decision.
   - Gate: Reuse Analysis table present with zero unjustified CREATE NEW decisions.

6. **Recommend Architecture Based on Drivers** — recommend based on quality attribute priorities|constraints|paradigm from steps 1-5. Default: modular monolith with dependency inversion (ports-and-adapters). Overrides require evidence. If functional paradigm: apply types-first design, composition pipelines, pure core / effect shell, effect boundaries as ports, immutable state — in architecture document only, no code snippets. Gate: architecture pattern selected with written rationale.
6. **Stress Analysis** (HIDDEN — `--residuality` flag only) — when activated: apply complexity-science-based stress analysis (stressors|attractors|residues|incidence matrix|resilience modifications) using the `stress-analysis` skill. When not activated: skip entirely, do not mention. Gate: activated only when flag present.
7. **Produce Deliverables** — write architecture document with component boundaries|tech stack|integration patterns. Produce C4 System Context diagram (Mermaid) — mandatory. Produce C4 Container diagram (Mermaid) — mandatory. Produce C4 Component diagrams (Mermaid) — only for complex subsystems. Write ADRs for significant decisions. Gate: mandatory C4 diagrams present, ADRs written.

## Outcome Collision Check (per DISCUSS#D-5 grain)

Provenance: feature `outcomes-registry` — DISCUSS#D-2 (lean Tier-1 + Tier-2 default), D-5 (per-typed-contract grain), D-6 (gate-scoping: code-feature pipelines only).

**Trigger**: a new feature-delta has been emitted in DESIGN with a Reuse Analysis table. Run this check AFTER step 5 (Reuse Analysis) in the Discovery Flow and BEFORE producing the final architecture deliverables in step 7.

**Skip when**: the feature is methodology-only (skill propagation, prose changes, no new typed contract surface). Per D-6 gate-scoping, the outcomes registry tracks code-feature pipelines only.

**Procedure**:

1. **Run** the collision-check CLI against the freshly-emitted feature-delta:
   ```
   nwave-ai outcomes check-delta docs/feature/{feature-id}/feature-delta.md
   ```
2. **Handle exit codes**:
   - **Exit `0`** — no collisions detected. Proceed to step 7 (Produce Deliverables).
   - **Exit `1`** — one or more candidate outcomes overlap with existing OUT-N rows in `docs/product/outcomes/registry.yaml`. Review the reported OUT-ids. For each:
     - **Genuine duplication**: link the new candidate to the existing OUT-N via `related: [OUT-N]` in the registry, OR mark the existing OUT-N `superseded_by: OUT-M` if the new contract replaces it. Re-run `check-delta` to confirm.
     - **False positive** (Tier-1 keyword/shape match fired but Tier-2 disambiguation reveals the contracts are distinct): annotate the candidate's keywords in the registry to be more distinctive, then re-run.

The registry at `docs/product/outcomes/registry.yaml` is the SSOT for "what we promise the system does." Reuse Analysis (step 5) deduplicates within the codebase; the Outcome Collision Check deduplicates across the contract registry — they are complementary gates.

Gate: `check-delta` exits `0`, OR every reported collision has been resolved (linked, superseded, or disambiguated) and the re-run exits `0`, OR the feature is documented as methodology-only and the check is correctly skipped.

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
- [ ] **Reuse Analysis table present** with every overlapping component listed (HARD GATE — reviewer blocks without this)
- [ ] Architecture supports all business requirements
- [ ] Technology stack selected with clear rationale
- [ ] Development paradigm selected and (optionally) written to project CLAUDE.md
- [ ] Component boundaries defined with dependency-inversion compliance
- [ ] C4 System Context + Container diagrams produced (Mermaid)
- [ ] ADRs written with alternatives considered
- [ ] Per-wave peer review (OPTIONAL — invoke `/nw-review nw-solution-architect-reviewer` only on trigger: contested ADR, novel pattern, performance-budget unverified by spike, security boundary change. Default: skip. Mandatory consolidated review fires at end of DISTILL covering all 4 waves in parallel.)
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

## Reuse Analysis
| Existing Component | File | Overlap | Decision | Justification |
|-------------------|------|---------|----------|---------------|
| {component} | {path} | {what overlaps} | EXTEND/CREATE NEW | {evidence} |

## Technology Stack
- {language/framework}: {rationale}

## Constraints Established
- {architectural constraint}

## Upstream Changes
- {any DISCUSS assumptions changed, with rationale}
```

This summary enables DEVOPS and DISTILL to quickly assess architecture decisions without reading all DESIGN files.

## Outputs

**Single narrative file**: `docs/feature/{feature-id}/feature-delta.md` — DDD list, component decomposition, driving/driven ports, technology choices, decisions table, reuse analysis, open questions all become `## Wave: DESIGN / [REF|WHY|HOW] <Section>` headings.

**Machine artifacts**: none unique to feature dir (the `feature-delta.md` IS the artifact; SSOT writes carry the architectural payload).

**SSOT updates** (per Recommendation 3 / back-propagation contract — DESIGN is the primary SSOT integrator):
- `docs/product/architecture/brief.md` — created or updated. Each architect owns its section: `## System Architecture` (nw-system-designer), `## Domain Model` (nw-ddd-architect), `## Application Architecture` (nw-solution-architect)
- `docs/product/architecture/adr-*.md` — one ADR per significant architectural decision
- `docs/product/architecture/c4-diagrams.md` — current component topology if separate from brief

**Optional** (project-root, not feature-dir): `CLAUDE.md` `## Development Paradigm` section.

Legacy multi-file outputs (per-wave `wave-decisions.md`, `architecture-design.md`, etc. inside `docs/feature/{id}/design/`) are NOT produced — that content lives in `feature-delta.md` plus the SSOT integration above. Validator: `scripts/validation/validate_feature_layout.py`.
