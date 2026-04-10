---
name: nw-buddy-wave-knowledge
description: Wave methodology knowledge for the buddy agent — what each wave does, its inputs and outputs, and how to route questions.
---

# Wave Methodology Knowledge

The nWave methodology organizes work into a canonical sequence of **waves**. Each wave has a purpose, a primary agent, inputs from earlier waves, and outputs consumed by later waves. The buddy agent uses this map to answer "where am I in the process" and "what should I do next" questions without stepping into execution territory.

## The canonical wave sequence

```
DISCOVER -> DISCUSS -> SPIKE(opt) -> DESIGN -> DEVOPS -> DISTILL -> DELIVER
```

Each wave has a slash command (`/nw-<wave>`) and a primary agent. Waves run top-to-bottom. Skipping waves is a smell; going back to revise an earlier wave is normal and expected. SPIKE is optional — include it when validating a new mechanism, performance requirement, or external integration.

## Wave-by-wave reference

### 1. DISCOVER

- **Purpose**: validate that an opportunity exists and is worth pursuing.
- **Primary agent**: product-discoverer.
- **Inputs**: a rough idea, a user complaint, a market signal, or a strategic prompt.
- **Outputs**: an evidence brief — problem statement, target users, pains, existing solutions, strength of signal, go/no-go recommendation.
- **Typical artifacts**: `docs/discover/<opportunity>-brief.md`, user interview notes, competitive scans.
- **Common questions**: "is this worth doing?", "who has this problem?", "what's the evidence?"

### 2. DISCUSS

- **Purpose**: turn a validated opportunity into user stories with acceptance criteria.
- **Primary agent**: product-owner.
- **Inputs**: DISCOVER output — validated problem and target users.
- **Outputs**: a set of user stories, each with a goal, acceptance criteria in Given-When-Then form, and a rough priority.
- **Typical artifacts**: `docs/discuss/<feature>-stories.md`, a backlog update.
- **Common questions**: "what does 'done' look like for this feature?", "what are the user stories?"

### 3. SPIKE (optional)

- **Purpose**: validate one core assumption through timeboxed throwaway code before investing in architecture design.
- **Primary agent**: software-crafter.
- **Inputs**: DISCUSS output — stories, acceptance criteria, and assumptions to test.
- **Outputs**: spike findings documenting what works, what assumptions were wrong, performance measurements. Code is discarded.
- **Typical artifacts**: `docs/feature/<name>/spike/findings.md`, throwaway code (not committed).
- **Common questions**: "will this mechanism work?", "can we hit the performance budget?", "does the third-party API behave as expected?"
- **When to run**: Include SPIKE when the feature involves a new mechanism never tried before, a performance requirement that can't be validated by reasoning alone, or an external integration with unknown behavior. Skip for pure refactoring, bug fixes, or features < 1 day.
- **Duration**: max 1 hour, timeboxed.

### 4. DESIGN

- **Purpose**: propose the solution architecture — component boundaries, key abstractions, major trade-offs.
- **Primary agent**: solution-architect.
- **Inputs**: DISCUSS output — stories and acceptance criteria. SPIKE findings (if spike was run) — validated assumptions and performance constraints.
- **Outputs**: an architecture proposal, usually updating the SSOT architecture doc, plus ADRs for significant decisions.
- **Typical artifacts**: `docs/architecture/architecture-design.md` updates, `docs/adrs/ADR-NNN-<title>.md`, diagrams.
- **Common questions**: "how will this be built?", "what are the components?", "what are the boundaries?"

### 5. DEVOPS

- **Purpose**: plan the infrastructure, CI/CD, and deployment needed to run what DESIGN proposed.
- **Primary agent**: platform-architect.
- **Inputs**: DESIGN output.
- **Outputs**: infrastructure plan, CI/CD changes, deployment checklist, rollback plan.
- **Typical artifacts**: updated CI workflow files, IaC changes, runbooks.
- **Common questions**: "how do we ship this?", "what does CI need?", "what's the rollback plan?"

### 6. DISTILL

- **Purpose**: translate stories and acceptance criteria into executable BDD test scenarios — the specification the crafter will implement against.
- **Primary agent**: acceptance-designer.
- **Inputs**: DISCUSS stories and DESIGN architecture.
- **Outputs**: `tests/acceptance/` files with Given-When-Then scenarios, tagged with `@skip` initially, plus a roadmap of delivery steps.
- **Typical artifacts**: feature files or test classes with BDD scenarios, a delivery roadmap in `docs/feature/<name>/roadmap.md`.
- **Common questions**: "what are the test scenarios?", "what's the delivery plan?"

### 7. DELIVER

- **Purpose**: implement the feature using Outside-In TDD, step by step, until all DISTILL scenarios pass.
- **Primary agent**: software-crafter.
- **Inputs**: DISTILL output — scenarios and roadmap.
- **Outputs**: working, tested, committed code.
- **Typical artifacts**: commits following the TDD 5-phase cycle (PREPARE -> RED_ACCEPTANCE -> RED_UNIT -> GREEN -> COMMIT), updated tests, updated source files.
- **Common questions**: "is this feature done?", "what step are we on?", "is the test suite green?"

## Cross-wave agents

Some agents operate across waves:

- **researcher** — gathers evidence for any wave that needs it.
- **troubleshooter** — diagnoses problems in existing code or processes.
- **documentarist** — produces user-facing documentation, typically after DELIVER.
- **visual-architect** — produces diagrams to support DESIGN.

Peer reviewers exist for each specialist (one per wave) and enforce quality gates.

## Routing questions to the right wave

When a user asks something, the buddy identifies which wave owns the question and answers from that wave's artifacts. Examples:

| Question | Wave | Where to read |
|---|---|---|
| "Is this idea any good?" | DISCOVER | discover briefs |
| "What are the user stories?" | DISCUSS | story docs / backlog |
| "How will the module be shaped?" | DESIGN | architecture doc, ADRs |
| "What's the CI plan?" | DEVOPS | CI workflows, runbooks |
| "What are the test scenarios?" | DISTILL | feature files, roadmap |
| "What step are we on?" | DELIVER | commits, test suite, roadmap |

If the user's question spans multiple waves (e.g., "what's this feature and how does it work?"), answer with contributions from each relevant wave, in order.

## Recognizing which wave the user is in

Signals:

- **DISCOVER**: user is asking about opportunity, not code. Words like "should we", "is there demand".
- **DISCUSS**: user is talking about stories, acceptance criteria, user needs.
- **SPIKE**: user is asking about validating assumptions, prototyping a mechanism, or performance testing. Words like "prove it works", "test this idea", "spike".
- **DESIGN**: user is asking about components, layers, boundaries, trade-offs.
- **DEVOPS**: user is talking about deployment, CI, environments, secrets, rollout.
- **DISTILL**: user is asking about test scenarios, Given-When-Then, the roadmap.
- **DELIVER**: user is asking about implementation status, failing tests, next step, commits.

If unsure, ask.

## What the buddy does NOT do

- **Does not run the crafter.** The buddy is read-only guidance. If the user wants code written, they should invoke `/nw-deliver` or the crafter agent directly.
- **Does not skip waves.** If a user asks to "just implement this" and DISTILL hasn't been run, the buddy points out the gap and suggests running DISTILL first.
- **Does not invent artifacts.** If a DESIGN doc doesn't exist, the buddy says so — it doesn't make one up.
- **Does not write acceptance tests on the fly.** That's DISTILL's job.
- **Does not change the wave order.** The sequence exists because each wave depends on the previous.

## Rule of thumb

The buddy's mental model is always: *"What wave is this question in, which files hold the answer, and what are the gaps?"* Answer from those files, cite them, and flag gaps as findings.
