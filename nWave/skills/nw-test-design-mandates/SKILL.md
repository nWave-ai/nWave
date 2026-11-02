---
name: nw-test-design-mandates
description: Design mandates for acceptance tests - hexagonal boundary, business language abstraction, user journey completeness, pure function extraction, 3 Pillars (domain language / chained narrative / production composition), and the layered ATD discipline (Universe-bound assertion, layer-dependent PBT mode, two-tier acceptance, example-based sad paths). Lean recomposing core - routes to three narrow mandate modules.
user-invocable: false
---

# Acceptance Test Design Mandates (recomposing core)

This skill is the Single Source of Truth (SSOT) for every acceptance-test-design mandate. All mandates are enforced during peer review and must pass before handoff to software-crafter.

This core holds the cross-cutting concerns (numbering, registry, language-convention frame, compliance-verification handoff) and COMPOSES three narrow mandate modules. The canonical mandate definitions live in the modules — this core does not re-inline them.

Load `nw-cross-cutting-invariants` and apply `flow:findings-go-to-the-owner-directly` when exchanging findings or questions between roles.

## Assertion failure messages state WHAT / WHY / HOW (STANDING)

Every AT assertion's failure message MUST state **WHAT** observable failed (the specific
expected-vs-actual), **WHY** it matters (the contract it breaks), and **HOW** to fix (what
the implementation must make true / the concrete remediation). A bare `assert x == y` with
no message — or a message that only restates the code — is itself a defect: a RED must TEACH
the crafter exactly what to make true, not force them to reverse-engineer the intent. Same
what/why/how rule the product's own error surfaces obey.

Then/Assert steps own these business-named assertions and carry WHAT/WHY/HOW internally;
scenario bodies call clean domain steps, not wordy assertion-message builders.

## Test time (STANDING)

Test time is a critical responsibility of the acceptance designer and its
reviewer (`test:feedback-loop-budget` in `nw-cross-cutting-invariants`). Keep every
test within the design's per-test and property budgets, and the default CI suite
within its ceiling (300 s unless a repository ADR sets another). Give each formal
law a fast executable projection on the pure core in the default suite. Put real
adapter fault injection (storage down, interrupted or double write, crash,
concurrent writers) only in the infrastructure suite of a feature whose derogation
the human granted. Measure per-test time over at least nine sequential runs and report n, median,
maximum and load; a test meets its budget on the median with at most one run over it. Never write a test above the
budgets: propose the feature's derogation request, with one risk/value record per
test, and ask for the human's decision instead.

Three cost laws complete this budget (Ale 2026-10-30): (1) RED default — a test
covering a declared-not-yet-deployed obligation is RED by default in its natural
committed state; pass/xfail bridging is not a substitute and synthetic RED by
removing markers is not an observed FAIL. (2) Mutation is nightly — text-flip and
similar belong to the nightly delta on implemented code, never to review gating.
(3) End-to-end installer cycles are an integration concern — rare, and always
reusing an existing prepared setup, never reinstalling per case; an oracle case
never executes a full lifecycle subprocess.

## Durable outcome naming (STANDING)

Every acceptance-test identifier must name the durable observable value it
protects. Delivery bookkeeping is not value: never put `slice_NN` or
`slice-NN` in a test file/function name. Do not create a ledger, delivery
narrative or execution plan to preserve that bookkeeping; Git owns change
provenance. Before RED, derive
the identifier from the charter's value statement; a reader must understand
what is protected without opening delivery bookkeeping. Scenario titles and
parametrization IDs follow the same naming rule. The acceptance designer and
reviewer validate the observable meaning at authoring time; no language-specific
post-hoc naming gate is part of the delivery spine.

## Closure obligations — COUNT / PARTITION / SILENCE (STANDING)

Three generative obligations. They fire at AUTHORING time, on the shape of what an AT (or the
artifact it certifies) asserts — not as a gate that fires after the error. They are
domain-agnostic: a validator checks the obligation is DISCHARGED without understanding the
subject. Whenever a scenario, a charter oracle, or a design artifact emits one of these
shapes, the matching cell is filled inline while writing:

- **Emit a COUNT → name the POPULATION.** A number ("3 consumers wired", "0 findings", "5
  slices") is meaningless without its denominator: 3 of WHAT total, 0 out of a set that was
  actually enumerated. An AT asserting a count MUST also pin the population it was drawn from,
  and assert the count against that population — never a bare integer.
- **Emit a PARTITION → assert CONSERVATION.** When a whole is split into parts (buckets,
  statuses, refused/accepted halves, per-category verdicts), the parts MUST sum back to the
  whole. Assert the conservation law, not just the individual buckets — a partition whose
  pieces silently drop members is the exact defect this catches.
- **Declare SILENCE/ABSENCE → name the DISCRIMINATOR.** A "clean / nothing found / no-op /
  not-applicable" result MUST carry what distinguishes **looked-and-genuinely-absent** from
  **never-actually-looked** (no capable tier, unparseable input, swallowed error). The AT
  proves the discriminator by constructing the empty case AND a broken/incapable case and
  asserting their outputs DIFFER — the negative test no positive test can replace (Vera's
  absence ≠ incapacity, `nw-user-examiner` §8). A silence indistinguishable from a swallowed
  error is a false negative wearing a degraded alibi, never a PASS.

Why here, why inline: the obligation is SEEDED mechanically from what the design already
states — a Reuse Analysis `EXTEND` row that names a field ("binding_name plus template_parts")
already implies the population; the charter's negative oracle already implies the
discriminator. Filling the cell while authoring costs the system, not a gate firing after a
wrong path is taken (GDP-2 inline-at-authoring + GDP-5 cost-on-system). The denominator is not
documentation — it is the falsifier made mechanical.

## Composition (load by trigger)

| Module | Kind | Trigger — load when... | Covers |
|---|---|---|---|
| `nw-test-design-mandates-scenario-design` | KNOWLEDGE | shaping/judging a scenario's SHAPE — boundary, language, journey, fixtures, style | Mandates 1-4, the 3 Pillars, Walking Skeleton Strategy |
| `nw-test-design-mandates-layered-mechanics` | KNOWLEDGE | choosing test MECHANICS for a layer + adapter-realness — assertion style, PBT mode, tier, sad-path treatment | Mandates 8-11, Layered Test Discipline table, Polyglot Adapter Matrix |
| `nw-test-design-mandates-composition-contract` | KNOWLEDGE | composing the AT's DRIVING SURFACE + code contract — SSOT-via-types, driving-port-only, contract-shape tag, dormant-seam | Mandates 12-15 |

Load path: `~/.claude/skills/nw-test-design-mandates-{module}/SKILL.md`. Load the module whose trigger matches your current moment; load more than one when a task spans moments. The three triggers partition the mandate-space — every mandate lives in exactly one module.

## Numbering Convention (read before citing any mandate)

Mandate numbers are an **SSOT-internal index**, defined in exactly one place — this registry. They may be re-indexed at will when the registry is reorganized.

- **Inside the modules**: each mandate carries a number for ordering and cross-reference.
- **Everywhere else** (agents, other skills, tasks, docstrings, ADRs, tests): refer to a mandate by its **stable descriptive name** plus a pointer to this SSOT — e.g. "the Driving-Port-Only Boundary mandate (SSOT: `nw-test-design-mandates`)". Do NOT hard-code the number in external references; the number is not a contract and external code must not lock onto it.
- Existing numeric labels in test docstrings (`Mandate-12`, `Mandate-13`, ...) are legacy shorthand for the named rules; treat them as references to this SSOT, not as independent definitions.

## Mandate Registry (canonical names → module)

| # | Name | Module |
|---|------|---|
| 1 | Hexagonal Boundary Enforcement | scenario-design |
| 2 | Business Language Abstraction | scenario-design |
| 3 | User Journey Completeness | scenario-design |
| 4 | Pure Function Extraction Before Fixtures | scenario-design |
| — | The 3 Pillars (style backbone) | scenario-design |
| — | Walking Skeleton Strategy | scenario-design |
| 8 | Universe-bound assertion at layers 1-3 | layered-mechanics |
| 9 | PBT input mode is layer-dependent (+ v2 mock-status driver) | layered-mechanics |
| 10 | Two-tier acceptance for rich journeys | layered-mechanics |
| 11 | Integration sad paths stay example-based | layered-mechanics |
| — | Layered Test Discipline table + Polyglot Adapter Matrix | layered-mechanics |
| 12 | SSOT + Zero Duplication via Types + Services + DSL | composition-contract |
| 13 | Driving-Port-Only Boundary | composition-contract |
| 14 | Contract Shape Classification | composition-contract |
| 15 | Dormant-Seam Reconciliation | composition-contract |
| 16 | Algebraic Analysis Before the Scenario | scenario-design |

## LANGUAGE CONVENTION FRAME (read FIRST — overrides all examples in the modules)

**Code examples in the modules use Python syntax for illustration only.** They are NOT prescriptive about target language. nWave is language-agnostic per the "genericity and agnosticism" mandate (2026-05-24).

Discover the project's native test/build contract from actual manifests, lockfiles,
build files, test stanzas/targets and incumbent source/test conventions. This is
an open evidence set, not a language allowlist: include `dune-project`, `dune`
library/executable/test stanzas and `.opam` when present, as well as whatever
the repository actually uses. Follow native interfaces, export/discovery metadata,
build aliases, runner argv, cwd and declared dependencies.

Project conventions win over every illustrative import, suffix and directory.
Use native generators, shrinking/replay and assertions when a broad law needs
PBT; native examples suffice for closed finite or singular observations. A
matching `nw-pbt-*` skill is optional on need, not a required adapter enrollment.
For an unlisted stack, investigate its incumbent/native tool rather than reject
it or introduce Python, pytest, Hypothesis, Gherkin or `tests/common`.
Missing toolchain or needed native capability is an explicit evidence gap,
never permission to switch the project's stack.

## Mandate Compliance Verification

Handoff to software-crafter includes proof all mandates pass (definitions per the cited module):

- **CM-A** (Mandate 1 — scenario-design): All test files import entry points (driving ports), zero internal component imports
- **CM-B** (Business Language Abstraction — scenario-design): Scenario bodies visibly compose typed business-language Given/When/Then steps for journeys or Arrange/Act/Assert steps for focused contract/property tests, with exactly one When/Act. Gherkin files are optional; the native test framework is valid. Technical protocol details live behind reusable domain steps in project-native helpers.
- **CM-C** (Mandate 3 — scenario-design): Journey scenarios validate complete user journeys with business value; focused contract/property scenarios validate a named observable contract at its declared boundary.
- **CM-D** (Mandate 4 — scenario-design): Business logic extracted to pure functions. Impure code isolated behind adapters. Fixture parametrization applies only to adapter layer.
- **CM-E** (Universe-bound assertion — layered-mechanics): State-mutating observations declare changed and preserved public state using native assertions or sufficient incumbent helpers; no compulsory matcher API.
- **CM-F** (Mandate 9 — layered-mechanics): the representative layer 3+ wiring/sad-path test is example-only; for every declared broad-input/state/failure law (e.g. `BROAD_INPUT_DOMAIN`), the smallest sufficient set of separate, budgeted semantic-PBT tests exists instead — normally one property per distinct law, combined only when one generated observation honestly falsifies all combined laws — each sited at a deterministic, replayable, law-bearing surface (real I/O not required, but the generated observation carries an explicit preservation map to the promised real-port observation), proving the SAME promised observation as the representative example — never a proxy, never a replacement for it. When no such surface exists, the result is `EVIDENCE_GAP` back to DESIGN before authoring — DESIGN names the surface and preservation map or corrects the law; the obligation is never silently downgraded to example-only
- **CM-G** (Two-tier acceptance — layered-mechanics): An identifiable feature journey through production composition exists in native layout; broad state/sequence laws have sufficient native replayable properties with a preservation map. No suffix, Gherkin file or scenario-count threshold is required.
- **CM-H** (Mandate 11 — layered-mechanics): Layer 3+ sad paths are named example-based tests; no PBT machinery imported into that sad-path set — the CM-F carve-out's semantic-PBT test(s) live in their own file(s), never merged into these examples

Evidence is the obligation → business stimulus → public response/state → falsifier relation and actual native execution. Names, import scans, decorator counts, file presence and technical-word greps are not substitutes for semantic review or observed properties.
