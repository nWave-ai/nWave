# nWave Tutorial Index

A prioritized roadmap of tutorials, organized by learning paths. Each tutorial is mapped to a real job users are hiring nWave to do.

**Legend**: Published | Planned

---

## Learning Path 1: Getting Started

The minimum path from zero to productive. Start here.

| # | Tutorial | Description | JTBD | Time | Level | Prerequisites | Status |
|---|----------|-------------|------|------|-------|---------------|--------|
| 1 | [Your First Delivery](./tutorial-first-delivery/) | Clone a starter project, run `/nw-deliver`, watch tests go green | "Ship a feature fast with quality" | ~13 min | Beginner | Python 3.10+, Claude Code + nWave | Published |
| 2 | [Writing Acceptance Tests That Guide Delivery](./tutorial-writing-tests/) | Write your own tests from scratch (not a starter repo) and deliver against them | "Define what 'done' means, then let AI build it" | ~15 min | Beginner | Tutorial 1 | Published |
| 3 | [Understanding the Delivery Pipeline](./tutorial-delivery-pipeline/) | What happens inside `/nw-deliver` — roadmap, execute, review, mutation test, finalize — and how to read the output | "Know what the tool is doing so I can trust it" | ~16 min | Beginner | Tutorial 1 | Published |

---

## Learning Path 2: Full Product Workflow

The complete nWave lifecycle: from idea to production. These tutorials follow the 7-wave sequence (DISCOVER, DIVERGE, DISCUSS, DESIGN, DEVOPS, DISTILL, DELIVER) and can be done as a series on a single project.

| # | Tutorial | Description | JTBD | Time | Level | Prerequisites | Status |
|---|----------|-------------|------|------|-------|---------------|--------|
| 4 | [From Idea to Validated Problem](./tutorial-discovery/) | Run product discovery — identify assumptions, validate a problem exists before writing any code | "Make sure I'm building the right thing" | ~15 min | Intermediate | Tutorials 1-3 | Published |
| 5 | [Exploring Design Directions](./diverge-wave-guide/) | Run design exploration — evaluate multiple solution approaches and make an informed architecture recommendation | "Choose between competing design approaches" | ~15 min | Intermediate | Tutorial 4 | Planned |
| 6 | [Requirements and UX Journey](./tutorial-discuss/) | Turn a validated problem into user stories with acceptance criteria using the AI product owner | "Get clear, testable requirements without a PM" | ~15 min | Intermediate | Tutorial 5 | Published |
| 7 | [Architecture Design](./tutorial-design/) (`/nw-design` + `/nw-diagram`) | Design system architecture and generate visual diagrams from requirements | "Make the right architecture decisions early" | ~15 min | Intermediate | Tutorial 6 | Published |
| 8 | [Generating Acceptance Tests](./tutorial-distill/) (`/nw-distill`) | Auto-generate BDD acceptance tests from user stories and architecture docs | "Turn requirements into executable specs" | ~12 min | Intermediate | Tutorial 7 | Published |
| 9 | [Delivering the Feature](./tutorial-deliver-feature/) (`/nw-deliver`) | Full delivery with architecture-guided roadmap on a real multi-component feature | "Ship a non-trivial feature end-to-end" | ~20 min | Intermediate | Tutorial 8 | Published |
| 10 | [Production Readiness](./tutorial-devops/) (`/nw-devops`) | Set up CI/CD, infrastructure design, and deployment strategy for the delivered feature | "Get to production with confidence" | ~15 min | Intermediate | Tutorial 9 | Published |

---

## Learning Path 3: Everyday Tasks

Standalone tutorials for common jobs. No specific order required.

| # | Tutorial | Description | JTBD | Time | Level | Prerequisites | Status |
|---|----------|-------------|------|------|-------|---------------|--------|
| 11 | [Safe Refactoring with Mikado](./tutorial-refactoring/) (`/nw-refactor` + `/nw-mikado`) | Untangle a messy codebase using progressive refactoring levels and the Mikado Method for dependency graphs | "Safely improve legacy code without breaking things" | ~20 min | Intermediate | Tutorial 1 | Published |
| 12 | [Debugging with 5 Whys](./tutorial-debugging/) (`/nw-root-why`) | Investigate a production bug using systematic root cause analysis | "Find the real cause, not just the symptom" | ~12 min | Intermediate | Tutorial 1 | Published |
| 13 | [Evidence-Based Research](./tutorial-research/) (`/nw-research`) | Research a technology choice with verified sources and structured output | "Make informed decisions backed by evidence" | ~10 min | Beginner | Claude Code + nWave | Published |
| 14 | [Validating Your Test Suite](./tutorial-mutation-testing/) (`/nw-mutation-test`) | Run mutation testing to find gaps in your test coverage | "Know if my tests actually catch bugs" | ~12 min | Intermediate | Tutorial 1 | Published |
| 15 | [Creating Quality Documentation](./tutorial-documentation/) (`/nw-document`) | Generate DIVIO-compliant docs (tutorial, how-to, reference, explanation) from existing code | "Keep documentation accurate and useful" | ~12 min | Beginner | Claude Code + nWave | Published |

---

## Learning Path 4: Power User

For users who want to extend nWave itself.

| # | Tutorial | Description | JTBD | Time | Level | Prerequisites | Status |
|---|----------|-------------|------|------|-------|---------------|--------|
| 16 | Building Custom Agents (`/nw-forge`) | Create a domain-specific agent with skills, reviewer, and test harness | "Extend nWave with agents for my domain" | ~25 min | Advanced | Tutorials 1-3, familiarity with agent architecture | Planned |
| 17 | Functional TDD Workflow | Use the functional software crafter for FP-first projects (F#, Haskell, Scala, Elixir) | "Use nWave with my functional codebase" | ~15 min | Advanced | Tutorial 1, experience with FP language | Planned |

---

## Legacy Tutorials

Earlier tutorials superseded by the current learning paths. Preserved for reference.

| # | Tutorial | Description | Status |
|---|----------|-------------|--------|
| L1 | [Quick Start: Hello nWave](./tutorial-hello-nwave/) | Build a feature in 5 minutes with three commands | Legacy |
| L2 | [Your First Feature](./tutorial-first-feature/) | End-to-end feature using the four-command workflow | Legacy |

---

## Recommended Reading Order

**If you have 15 minutes**: Tutorial 1 only. You will ship a feature and understand the core value.

**If you have 1 hour**: Tutorials 1, 2, 3. You will be self-sufficient for day-to-day delivery.

**If you have a day**: Tutorials 1-10 in order. You will know the complete product lifecycle.

**Pick-and-choose**: Tutorials 11-15 are standalone — jump to whichever job you need done today.

---

## JTBD Summary

| Job | Primary Persona | nWave Command | Tutorial |
|-----|----------------|---------------|----------|
| Ship a feature fast with quality | Solo Dev | `/nw-deliver` | 1, 9 |
| Define "done" and let AI build it | Solo Dev, Tech Lead | Tests + `/nw-deliver` | 2 |
| Understand what the tool is doing | New Team Member | — | 3 |
| Validate a product idea | Product-Minded Dev | `/nw-discover` | 4 |
| Explore design directions | Tech Lead | `/nw-diverge` | 5 |
| Get clear requirements without a PM | Solo Dev, Tech Lead | `/nw-discuss` | 6 |
| Make architecture decisions early | Tech Lead | `/nw-design` | 7 |
| Turn requirements into test specs | Tech Lead | `/nw-distill` | 8 |
| Get to production | Solo Dev, Tech Lead | `/nw-devops` | 10 |
| Safely improve legacy code | Legacy Maintainer | `/nw-refactor`, `/nw-mikado` | 11 |
| Debug hard production issues | Solo Dev | `/nw-root-why` | 12 |
| Make evidence-based tech decisions | Tech Lead | `/nw-research` | 13 |
| Verify test suite catches real bugs | Tech Lead | `/nw-mutation-test` | 14 |
| Keep docs accurate and useful | Tech Lead | `/nw-document` | 15 |
| Extend nWave for my domain | Power User | `/nw-forge` | 16 |
| Get help with methodology or commands | Any | `/nw-buddy` | -- |

---

> **Tip**: At any point, type `/nw-buddy` followed by your question to get contextual help about nWave methodology, commands, project state, or migration.

---

**Last Updated**: 2026-04-06
