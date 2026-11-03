# nWave Tutorial Index

Tutorials teach by doing: a guided, hands-on lesson with a visible result.
Pick by the job you want to learn.

The `nwdes` steps these lessons walk are your assistant's to run in real
work; tutorial 1 is the one you type by hand — see
[For your assistant](./README.md#for-your-assistant).

> **Currency note (v4).** The tutorials under "The wave tutorials" and
> "Standalone lessons" were written for the 3.x workflow. The `/nw-*`
> commands they teach still exist, but 3.x delivery internals (per-wave
> directories, `roadmap.json`, `execution-log.json`) were removed in v4 and
> replaced by the nwdes handoff ([What's new in v4](./whats-new-v4/)). They
> are kept because the wave concepts and command behavior they teach still
> apply; expect artifact paths to differ.

---

## Start here

| # | Tutorial | Description | JTBD | Level | Status |
|---|----------|-------------|------|-------|--------|
| 1 | [First feature with nwdes](./tutorial-nwdes-first-feature/) | A safe walk through the command flow in a throwaway repository: create a handoff, declare one slice, observe RED, implement, reach GREEN, render examination material | "See the delivery flow once, safely" | Beginner | Current (v4) |
| 2 | [Deliver a feature](./nwdes/deliver-feature.md) (how-to) | The practical first run on the v4 route: handoff, product facts, design, oracle, craft, review, examination, integration | "Ship a feature fast with quality" | Beginner | Current (v4) |
| 3 | [Fix a bug](./nwdes/fix-bug.md) (how-to) | The lean v4 route on one understood defect | "Fix this defect properly, not just patch it" | Beginner | Current (v4) |

Tutorial 1 uses fixed role-output fixtures, so it needs no model calls —
read its disclaimer before treating anything in it as delivery evidence.

---

## The wave tutorials (3.x workflow)

Sequenced lessons following the wave sequence DISCOVER → DIVERGE → DISCUSS →
DESIGN → DEVOPS → DISTILL → DELIVER. Read the currency note above before
starting.

| # | Tutorial | Description | JTBD | Level |
|---|----------|-------------|------|-------|
| 4 | [From Idea to Validated Problem](./tutorial-discovery/) (`/nw-discover`) | Product discovery: validate a problem exists before writing code | "Make sure I'm building the right thing" | Intermediate |
| 5 | [Exploring Design Directions](./diverge-wave-guide/) (`/nw-diverge`) | Evaluate multiple solution approaches and recommend one | "Choose between competing design approaches" | Intermediate |
| 6 | [Requirements and UX Journey](./tutorial-discuss/) (`/nw-discuss`) | Turn a validated problem into user stories with acceptance criteria | "Get clear, testable requirements without a PM" | Intermediate |
| 7 | [Architecture Design](./tutorial-design/) (`/nw-design` + `/nw-diagram`) | Design system architecture and generate diagrams from requirements | "Make the right architecture decisions early" | Intermediate |
| 8 | [Generating Acceptance Tests](./tutorial-distill/) (`/nw-distill`) | Turn user stories and architecture into executable BDD acceptance tests | "Turn requirements into executable specs" | Intermediate |
| 9 | [Delivering the Feature](./tutorial-deliver-feature/) (`/nw-deliver`) | Whole delivery on a multi-component feature (teaches the 3.x roadmap flow; for v4 use [Deliver a feature](./nwdes/deliver-feature.md)) | "Ship a non-trivial feature end-to-end" | Intermediate |
| 10 | [Production Readiness](./tutorial-devops/) (`/nw-devops`) | CI/CD, infrastructure design, and deployment strategy | "Get to production with confidence" | Intermediate |

## Standalone lessons (3.x workflow)

| # | Tutorial | Description | JTBD | Level |
|---|----------|-------------|------|-------|
| 11 | [Understanding the Delivery Pipeline](./tutorial-delivery-pipeline/) | What happened inside a 3.x `/nw-deliver` run, and how to read its artifacts | "Know what the tool is doing so I can trust it" | Beginner |
| 12 | [Writing Acceptance Tests That Guide Delivery](./tutorial-writing-tests/) | Write your own tests from scratch and deliver against them | "Define what 'done' means, then let AI build it" | Beginner |
| 13 | [Safe Refactoring with Mikado](./tutorial-refactoring/) (`/nw-refactor` + `/nw-mikado`) | Untangle a messy codebase with progressive levels and the Mikado Method | "Safely improve legacy code without breaking things" | Intermediate |
| 14 | [Debugging with 5 Whys](./tutorial-debugging/) (`/nw-root-why`) | Investigate a production bug with systematic root cause analysis | "Find the real cause, not just the symptom" | Intermediate |
| 15 | [Evidence-Based Research](./tutorial-research/) (`/nw-research`) | Research a technology choice with verified sources | "Make informed decisions backed by evidence" | Beginner |
| 16 | [Validating Your Test Suite](./tutorial-mutation-testing/) (`/nw-mutation-test`) | Mutation testing to find gaps in test coverage | "Know if my tests actually catch bugs" | Intermediate |
| 17 | [Creating Quality Documentation](./tutorial-documentation/) (`/nw-document`) | Generate DIVIO-compliant docs from existing code | "Keep documentation accurate and useful" | Beginner |
| 18 | [Your First Outcome](./outcomes-first-outcome/) | Register and check an outcome with the `nwave-ai outcomes` CLI | "Measure what my work changed" | Beginner |

The 3.x-era first-run tutorials ([Your First Delivery](./tutorial-first-delivery/),
[Hello nWave](./tutorial-hello-nwave/), [Your First Feature](./tutorial-first-feature/))
are superseded by the v4 route above and kept as history.

---

## Recommended reading order

**If you have 15 minutes**: [What's new in v4](./whats-new-v4/), then start
[Deliver a feature](./nwdes/deliver-feature.md) on a toy request.

**If you have an hour**: finish the delivery end to end, then
[Fix a bug](./nwdes/fix-bug.md) and [Understanding nwdes](./understanding-nwdes/).

**Product lifecycle**: tutorials 4–10 in order, reading them as wave-concept
lessons while running the v4 route for the artifacts.

**Pick-and-choose**: tutorials 11–18 are standalone — jump to the job you
need done today.

---

> **Tip**: at any point, type `/nw-buddy` followed by your question to get
contextual help about nWave methodology, commands, project state, or
migration.
