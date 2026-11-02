---
name: nw-test-design-mandates-composition-contract
description: "Composition-root authoring-contract mandates for acceptance tests — SSOT + Zero Duplication via Types + Services + DSL, Driving-Port-Only Boundary (Farley four-layer protocol-driver contract, fixture-theater/tautological-test anti-pattern), Contract Shape Classification (@in-memory/@real-io tag-vs-composition), and Dormant-Seam Reconciliation (AT drives the DESIGN-declared seam, not the new component). Consult while composing the AT's driving surface, structuring step/type/service code, and tagging the contract shape. Canonical definitions; SSOT for these mandates."
user-invocable: false
disable-model-invocation: true
---

# Test-Design Mandates — Composition Contract

**Kind**: KNOWLEDGE (reference). No forced sequence — consulted on its trigger.

**Trigger**: you are composing the AT's DRIVING SURFACE and its code contract — how the step/type/service code is structured (SSOT-via-types), which driving port the AT reaches the SUT through (and which surfaces are forbidden), which contract-shape tag the scenario carries, and whether the AT drives the DESIGN-declared seam. Mandates 12-15. These are HARD invariants enforced at review + the hook spine.

Numbering is an SSOT-internal index defined in the recomposing core `nw-test-design-mandates`; refer to mandates by descriptive name externally. Language-convention frame (non-Python target adaptation) lives in the core.

## Mandate 12 — SSOT + Zero Duplication via Types + Services + DSL

Domain concepts are expressed once via the type system; logic lives in composition-root services as the single source of truth; a business-language Given/When/Then (GWT) or Arrange/Act/Assert (AAA) step DSL invokes those services and never inlines business logic. Given/When (or Arrange/Act) steps drive the public driving port; Then/Assert steps own business-named assertions and their WHAT/WHY/HOW failure messages internally. State lives in a typed scenario-scoped context created fresh per test, never static or global step objects.

- Domain concepts live once in a test-side domain-vocabulary module in the project's native language and layout, as native typed constructs (enums / variants / records / newtypes / value objects). Python binding (illustrative only): `tests/{path}/acceptance/steps/domain_types.py` with enums / dataclasses / NewTypes.
- Business logic lives in composition-root services, not in step bodies.
- The DSL emerges from typed domain concepts and composable, reusable domain steps, NOT hundreds of unique one-off step definitions. Parameterization is allowed only for data variants of the SAME scenario with the same expected outcome shape, never to merge scenarios with distinct outcomes.

Compliance is mechanical via four language-neutral criteria (checked with the project's own syntax tooling or by review; absent tooling is a declared EVIDENCE_GAP with cause, never a stack change; see `nw-tdd-cross-language` and the language-convention frame in `nw-test-design-mandates`):
1. **(criterion 1)** A domain-type declaration exists, in the language's own constructs, for every domain noun used in the scenarios.
2. **(criterion 2)** Composition methods consume those domain types; no raw primitive (string/int) parameter where a domain type exists.
3. **(criterion 3)** Each scenario body visibly composes typed Given steps, exactly one When, then Then steps for user journeys, or Arrange steps, exactly one Act, then Assert steps for focused contract/property tests. No business logic, branching or looping in scenario bodies; steps contain no business logic. No helper owns a whole scenario or branches on scenario kind; composition-root services sit behind the steps.
4. **(criterion 4)** Step-reuse-ratio (`total_step_invocations / unique_step_definitions`) measured and documented as INFORMATIONAL natural ceiling per feature — NOT a gate; below 4× is acceptable when criteria 1-3 are met (forcing ≥4× would sacrifice Pillar 1 readability).

Anti-pattern: copying the same hard-coded literals across scenarios, hiding a whole scenario inside a helper, branching a helper on scenario kind, OR collapsing distinct outcomes into ratio-maximizing parameterized templates that degrade domain coherence. Visible inline GWT/AAA step composition is required, not duplication; keep each identical stimulus/assertion pair once. Reference: ADR-026; `[[feedback_atdd_ssot_via_types_services_dsl_2026_05_18]]`, `[[feedback_mandate12_refinement_2026_05_18]]`.

**DISTILL-before-DELIVER timing (atdd_pure)**: under `atdd_pure`, DISTILL authors `domain_types.{py,ts,...}` BEFORE DELIVER has created any production domain module — at authoring time there is nothing to import. <!-- mode-ref-ok --> This is expected and NOT a violation of "expressed once": the DISTILL-authored module is a PLACEHOLDER for the slice(s) still to ship, not a permanent second definition. Two rules follow:
- The placeholder's doc comment MUST say it is a DISTILL-time placeholder pending DELIVER (e.g. "placeholder until DELIVER lands `src/domain/...` — at implementation, this declaration MOVES into production source and this module IMPORTS it from there, it does not keep its own copy"). A comment stating the split as a PERMANENT design choice ("these are NOT imported from production code" with no reconciliation obligation) is the anti-pattern this note exists to close — it re-introduces exactly the "test passes against the old behavior — silent drift" failure Mandate 12 forbids, because production and test-side types WILL diverge in shape the moment either evolves independently.
- Once DELIVER lands the production domain module for a given concept, ITS SAME SLICE's GREEN phase (or a dedicated reconciliation step, never deferred past that slice) MUST move that type's declaration into the production source and change `domain_types.{py,ts,...}` to IMPORT it directly from there — a bare `import { X } from "src/domain/..."` (or language equivalent), never a re-export wrapper, never a structurally-independent redeclaration, however similarly shaped. A domain type that still exists standalone (declared, not imported) in the test-side module AFTER its production counterpart has shipped is a Mandate-12 violation, mechanically detectable as: for each type name declared in both places, the test-side declaration is not a direct import of the production one (e.g. a test-side bare string-literal union next to a production discriminated union for the same concept name is the signature of this exact drift).

## Mandate 13 — Driving-Port-Only Boundary

ATs drive the SUT **exclusively** through a composition-root driving port at one of three layers — never via direct-domain / function-level / CLI-internal testing. HARD invariant.

**The three permitted driving surfaces**:
- **Layer 3 subprocess** — real public CLI invocation (preferred for CLI/script behaviors).
- **Layer 3 composition** — real service via composition root (e.g. `PreToolUseService(...).evaluate(...)`, for hook/intercept behaviors).
- **Layer 4 wiring_e2e** — full stack, real hook subprocess invocation (for end-to-end gate behaviors).

**ATs MUST NOT**:
1. Import private production modules directly in step composition (`Y().method(...)` on a private domain/application/adapter implementation is not a driving surface).
2. Test pure-function behavior at the function boundary (function-level unit testing is an anti-pattern for ATs).
3. Place new behavioral acceptance coverage among private unit tests rather than the repository's existing public-port acceptance/CLI test directories.

**Rejection rule**: if a dispatch prompt requires private unit-level composition for acceptance behavior, return the boundary conflict to its owner and name a public-driving-port alternative. A reviewer recommendation that introduces direct-domain acceptance testing is itself the same anti-pattern.

### Protocol-driver contract (Farley four-layer ATDD)

Two conditions, BOTH mandatory — the boundary is not satisfied by traversal alone:

1. **Real protocol only.** The AT reaches the SUT exclusively via its real public CLI or production composition root. The protocol driver owns the actual protocol; only genuinely external systems may be stubbed (Farley Test → DSL → Protocol Driver → SUT).
2. **Assert a shipped artifact or an observed effect.** Every assertion reads an **artifact the SUT actually shipped** (a file on disk written by the SUT, an emitted event, a captured stdout, a process exit code) or an **observable effect the SUT produced** — NEVER a string/structure rendered by the test itself.

**Anti-pattern — *tautological test / self-fulfilling fixture***: a green test whose oracle is data the test fabricated (the fixture supplies the expected output, the assertion re-reads the fixture). Zero validation power: passes with the production code deleted. (Phenomenon naming per `docs/research/walking-skeleton-atdd-best-practices-2026-06-12.md`; the term "The Mockery" is Bugayenko-specific and NOT used here.) nWave term: **fixture-theater** (Critical Rule 7).

**Prose-surface case** — observe the real shipped/rendered/installed asset through its consumer. Validate reachable references, parseable deliberate machine contracts and actual user behavior; do not test source phrases, headings, hash snapshots or incidental wording. Exact public text may be asserted only for a **machine contract** of a shipped surface: a schema, a table grammar, a CLI output format or a parse rule. A design record's declared observation never authorises it, and a regex or shape predicate over prose, including the presence or absence of a phrase, is a wording pin. Prose targets are verified by review and EXAMINE, never pinned by a test. A fixture string or content-pin assertion cannot establish that loaded guidance was applied.

### Artifact Lineage Closure — assembled surfaces

When the paying user consumes a derived or assembled artifact — wheel, package,
archive, image, generated tree, installed plugin set, executable bundle,
deployment manifest, or synchronized configuration — reaching the producer's
real entry point is necessary but insufficient. The AT MUST close the full
consumer lineage:

```
production input
  -> real production pipeline
  -> one immutable candidate
  -> clean consumer environment
  -> public user journey
  -> user-observable capability
```

All six links are mandatory:

1. **Real production pipeline** — build through the same public producer used
   for release. A test-authored copy, reconstructed fixture, or hand-assembled
   directory is not the release artifact.
2. **One immutable candidate** — identify the candidate by exact path plus
   digest (or equivalent immutable identity). Build once; downstream probes
   consume that same candidate. A rebuild is a different subject.
3. **Clean consumer environment** — install/load where the candidate cannot
   borrow from the source checkout, developer HOME, editable install, or global
   installation.
4. **Public user journey** — exercise the command/API/loader/runtime a customer
   uses. Archive inspection alone is insufficient when the product claim is
   installation or execution.
5. **User-observable capability** — assert what the user can actually do, not
   merely a packaging declaration, manifest entry, configured source path, or
   producer success message.
6. **Loud failure** — an incomplete candidate returns explicit non-success
   naming WHAT capability/artifact is unavailable, WHY the journey cannot
   complete, and HOW to produce a valid candidate.

**Decide on the produced PROPERTY, never its DESIGNATION.** A declaration is
evidence only when the declaration itself is the public contract. When it is
meant to produce another artifact/effect, assert the produced property: a
manifest naming `nWave/templates` is weaker than the immutable wheel containing
those templates and a clean installation loading them. Never require the
Acceptance Designer to resolve this rule through another skill that its phase
does not load.

This obligation does NOT multiply E2E tests. The feature's single
`@walking_skeleton` closes the lineage when the feature is assembly-sensitive;
focused behavioral scenarios remain at L2. If one feature truly exposes
multiple independent assembled consumer journeys, justify the additional E2E
or split the feature along those value boundaries.

Rationale: hexagonal boundary discipline and public-port acceptance observations. A test of private implementation details is not evidence that the assembled consumer works; a reviewer must recommend a driving-port alternative, not another private parity guard.

### The 6-level composition — the induction target for a new AT

A new acceptance test is INDUCED onto exactly one of six composition levels. The default level is **L2 in-process acceptance** — drive the real entry `cli main(argv)` IN-PROCESS with a fake output port, config-switchable in-memory ↔ prod-like (per `nw-distill-port-treatment-policy`). subprocess-e2e (L1) is reserved for the one `@walking_skeleton` per command. The other levels are induced only when the contract calls for them; sad-paths / ZOMBIES are enumerated at EVERY level (language-agnostic — the level names are the rule, the Python entry forms are illustration):

| Level | Proves | DEFAULT for a new AT? | Induced when... |
|---|---|---|---|
| **L1 walking-skeleton** | the installed artifact is wired end-to-end (real fork, real terminal) | no — **ONLY** the one `@walking_skeleton` per command | always exactly one per command (terminal-wiring facet) |
| **L2 in-process acceptance** | the command computes + emits the right output, driven in-process | **YES — the default** | every non-WS behavioural AT; the in-memory ↔ prod-like config-switch is owned by `nw-distill-port-treatment-policy` |
| **L3 integration (adapter ↔ real)** | a driven adapter works against its real I/O | no | a driven adapter ships → ≥1 `@real-io @adapter-integration` AT names it (Mandate 6) |
| **L4 contract** | a port's method contract holds for all implementations; or independently changing producer and consumer still agree | no | a port/Protocol ships → ≥1 contract test exercises its contract; DESIGN declares an applicable `contract_tests` obligation → real producer output drives the real consumer at its declared locator |
| **L5 architecture** | a declared dependency/boundary/owner law holds | no | DESIGN declares an applicable `architectural_tests` obligation → one check falsifies that law over its whole governed scope at its declared locator |
| **L6 law-bearing seam / PBT** | a declared broad input/state/failure law holds at the nearest honest law-bearing seam; unit checks pin otherwise unreachable behavior | no | a broad law needs native generative exploration, or an AT cannot reach GREEN without a unit-level pin; preserve its public-port observation explicitly; PBT is not restricted to pure functions and never bypasses the acceptance driving-port boundary |

- **Default = L2.** Absent a specific contract reason to descend, a new AT is L2 in-process acceptance — it is the speed default. Reaching for L1 subprocess on a non-WS scenario is the regression the subprocess-overuse gate flags.
- **L1 is singular.** One walking-skeleton per command, never per scenario (the terminal-wiring facet of the CLI split; see `nw-distill-port-treatment-policy`).
- **L3/L4 are induced by declared contract obligations, not quotas.** Add a real-I/O or port-contract observation only when the architecture exposes that boundary and the observation is not already preserved by another honest test.
- **Failure paths are obligation-driven.** Every declared failure or recovery law needs a distinguishable observation; no fixed error-test percentage is evidence of completeness.

The active-RED authoring pattern (P1-P4) lives in `nw-distill-red-scaffolding`. Drive the project's stable public entry through its real output boundary; do not copy an nWave-internal command as a universal exemplar.

## Mandate 14 — Contract Shape Classification

Each scenario declares its contract shape so the reviewer can verify the tag matches the composition root it actually drives. OR-reduction classifies adapter realness only; it does not select example-based versus generative treatment:

- `@in-memory` — ALL driven adapters in the composition root are in-memory / mock / stub fakes.
- `@real-io` — AT LEAST ONE driven adapter is a real I/O adapter (real filesystem, subprocess, network, HMAC keys). Observe the actual public-port output/effect; for mutable state, observe the promised before/after universe with native assertions or incumbent helpers.
- `@mixed` — disallowed; OR-reduction collapses the mixed case to `@real-io`.

Select law treatment under Mandate 9 in `nw-test-design-mandates-layered-mechanics` and `nw-property-based-testing`: broad laws receive native generative properties with independent oracles, shrinking and replay; closed finite domains receive native examples or exhaustive finite checks. Real I/O does not categorically preclude PBT. If it is slow, use the cheapest honest law-bearing seam with an explicit preservation map to the promised real-port observation, retaining representative real journeys and persistent-storage laws. Tag each resulting scenario by its actual composition, never label a fake seam `@real-io` to borrow integration evidence. No honest seam or unavailable native capability is `EVIDENCE_GAP` to DESIGN with its concrete cause, not permission to downgrade a broad law to examples.

A scenario tagged `@real-io` whose composition is observably all-mock is a TAG-COMPOSITION MISMATCH (reviewer flags NEEDS_REVISION). Enforced by `nw-acceptance-designer-reviewer` Critique Vector S3 (mock-tag consistency) and the `@contract-shape:` machine-parseable tag. Spike source: `docs/analysis/adapter-integration-slice-design-2026-05-27.md` §3/§6.

## Mandate 15 — Dormant-Seam Reconciliation

The AT-oracle target is the DESIGN-declared **seam**, not the new component. HARD invariant (D11).

For every net-new seam declared load-bearing in the DESIGN driving-surface for the slice — a net-new effectful entry-point parameter (e.g. `clock=`), a net-new effectful call reached from the entry point (e.g. `absorb_ready_refs()`), or a net-new param threaded into an existing seam — the slice AT MUST:
1. Name THAT exact seam as the port it drives.
2. Drive it through the **real entry point**.
3. Assert an **observable effect** (state delta / emitted event / captured side effect).

Re-deriving the AT target from "what's new in the slice" silently substitutes the COMPONENT for the SEAM — the intra-commit contradiction that ships a seam DORMANT (no production call-site, never reached from the real entry point) despite all per-slice gates passing.

**Witness indirect wiring.** Registry, entry-point discovery and dependency injection can reach a seam without a direct call-site. Drive the actual entry point and observe its effect, rather than treating a name match or per-component GREEN as proof of wiring. A declared seam with no observation returns to its design/oracle owner; no dormant-seam gate or exception marker substitutes for that observation.
