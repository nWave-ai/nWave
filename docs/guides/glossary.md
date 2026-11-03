# nWave glossary

Short definitions for the terms nWave uses, in v4 wording. Each term is
defined once; longer explanations live on the linked pages.

| Term | Meaning |
|---|---|
| **brief** | A human-readable rendering of the handoff (`brief.md`, `architecture.md`, `acceptance.md`, plus HTML), produced by nwdes on `feature new`, `slice set` and `document`; the shared surface for reading and discussing a feature. |
| **charter** | Optional record, one per feature, written by the product owner: intent, exploration, at least one positive and one negative observation. See [Understanding delivery artifacts](./understanding-delivery-artifacts/). |
| **DES runtime** | The predecessor delivery runtime that v4 retires; the name is historical and nWave documents no expansion of it. The v4 installer writes no runtime copy and removes the predecessor's footprint on upgrade. Delivery now runs through nwdes. |
| **EXAMINE** | The source-blind examination of the whole feature: an examiner judges every fixed expectation from the user's point of view, using only its own observations gathered in a public-only workspace. |
| **expectations** | The fixed, E-numbered rows stating what every public promise must look like to a user; fixed once per feature by the examiner before oracle authoring. |
| **GREEN** | The observed pass of the declared verification command on the implemented candidate. See **RED**. |
| **handoff** | The one canonical JSON record of a feature, `docs/feature/ID/handoff.json` in your repository; also the resume point after an interruption. |
| **host** | The coding application that runs the models and invokes the roles (Claude Code, Codex, OpenCode, OMP, Cursor, Copilot, Devin). |
| **installer self-validation** | The installer's own prerequisite checks and final validation report — the verification you get on hosts without a dedicated end-to-end install test. |
| **Jev** | The remote TypeSafe System One service consulted for bounded, typed semantic judgments; it is authorized by default, can be refused per call or per configuration, and works only when the `TYPESAFE_API_KEY` environment variable is set (a technical prerequisite, not the authorization). See [Understanding Jev](./understanding-jev.md). |
| **lane** | An optional isolated Git worktree per feature (`nwdes lane open`) for parallel work; integrate merges it back without rewriting trunk. |
| **oracle** | An executable check of a promised behavior through the public surface; authored by the acceptance designer and independently approved before craft begins. |
| **paradigm** | The implementation style a slice declares — functional, object-oriented or procedural; the route dispatches the functional crafter when it is functional. |
| **prefactoring** | A behavior-preserving production move declared by DESIGN before new behavior, verified before the move and after it, before the new behavior exists. See [Understanding design rigor](./understanding-design-rigor.md). |
| **promise** | A public outcome a feature commits to ("the search result is returned"), recorded as a P-numbered row. |
| **RED** | The observed failure of the missing behavior on the declared verification command, before implementation. |
| **review** | An independent examination of an artifact by the matching reviewer role; one fresh whole-candidate review is required per delivery, and embedded slice reviews are optional early feedback. |
| **role** | A specialist agent with its own skills: product owner, architect, acceptance designer, crafter, reviewer, examiner, and others. |
| **root assistant** | The session you talk to: it orchestrates, passes role prompts verbatim, reads real results, and decides the next step. |
| **route** | How a Request travels: spine waves, host-led nwdes steps, or working directly. Chosen by what must survive the session and the cost of a late refusal. |
| **S / M / L** | The working size assessment a Request opens with, with its reason; an explanation of a judgment that never decides the route. |
| **slice** | One observable behavior of a feature, tied to the promises it serves; the first slice is the walking skeleton — one thin public path end to end — and later slices extend it with explicit dependencies. |
| **spine waves** | The `/nw-*` commands (discover, discuss, design, distill, deliver, ...) that carry delivery gates and independent review for a whole feature. |
| **throughput** | Running several features in parallel on one machine, admitted by real capacity (memory, then CPU), not by an agent count. See [Throughput and swarm](./nwdes/throughput-and-swarm.md). |
| **verification command** | The command a slice declares; the host runs it to observe RED and GREEN. nwdes never runs it. |

See also [Understanding nwdes](./understanding-nwdes/) for how the pieces
fit together, and [For your assistant](./README.md#for-your-assistant) for
who runs what.
