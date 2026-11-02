# Explanation

Understanding-oriented material. These pages explain *why* nWave works the
way it does — the concepts, models, and decisions behind the methodology. Read
them when you want background and context, not a step-by-step task.

> In the [Divio documentation system](https://docs.divio.com/documentation-system/),
> explanation is distinct from tutorials (learning), how-to guides (tasks), and
> reference (information). It is the discursive quadrant: it clarifies and
> illuminates a topic rather than instructing or specifying.

## v4 and the delivery tool

| Topic | What it explains | Level |
|-------|------------------|-------|
| [What's new in v4](./whats-new-v4/) | Why delivery moved to nwdes, what was removed, and what that means for daily use | All |
| [Understanding nwdes](./understanding-nwdes/) | What the delivery tool is, what it never does, how records stay honest, and how the three routes are chosen | Beginner |
| [Understanding delivery artifacts](./understanding-delivery-artifacts/) | The handoff, oracle, expectations, charter, review and EXAMINE — who produces each, in what order, with the delivery flow diagram | Beginner |
| [Understanding design rigor](./understanding-design-rigor.md) | Algebraic design, prefactoring, and the optional formal checkers (Quint, TLA+, Agda) per role | Intermediate |
| [Understanding Jev](./understanding-jev.md) | The remote judgment service: what it answers, its default authorization and technical prerequisite, and how to refuse | All |

## Concepts and models

| Topic | What it explains | Level |
|-------|------------------|-------|
| [Wave Routing and Entry Points](./wave-routing-and-entry-points/) | The mental model for choosing which wave to start in, and how waves hand off to each other | Intermediate |
| [Understanding the SSOT Model](./understanding-ssot-model/) | Why nWave's documentation structure changed and how the single-source-of-truth document model works | Intermediate |
| [Wave Directory Structure](./wave-directory-structure/) | How nWave organizes artifacts across the seven-wave pipeline, and why | Intermediate |
| [Jobs To Be Done](./jobs-to-be-done-guide/) | The ODI/JTBD framing that maps real jobs to nWave workflows | Intermediate |

## Release history

| Topic | What it explains | Level |
|-------|------------------|-------|
| [What's New in v3.19](./whats-new-v319/) | Per-project activation (the opt-in gate) and the documented `nwave-ai` CLI | All |
| [What's New in v3.14](./whats-new-v314/) | Changes and additions in the v3.14 release | All |
| [What's New in v3.5](./whats-new-v35/) | The DIVERGE wave, the SSOT model, the three DESIGN architects, and `/nw-buddy` | All |

---

## Where explanation sits in the docs

- **[Tutorials](./TUTORIALS.md)** — learning-oriented. Start here if you are new.
- **[How-To Guides](./HOW-TO.md)** — task-oriented. Use these to get a specific job done.
- **[Reference](./REFERENCE.md)** — information-oriented. Look up precise specs for agents, commands, skills, and config.
- **Explanation** (this page) — understanding-oriented. Read these for the *why*.
