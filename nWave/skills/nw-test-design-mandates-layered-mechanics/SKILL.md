---
name: nw-test-design-mandates-layered-mechanics
description: "Layered acceptance-test mechanics: public state preservation, native generative laws, real-boundary journeys and explicit failure observations."
user-invocable: false
disable-model-invocation: true
---

# Test-Design Mandates — Layered Mechanics

**Kind**: KNOWLEDGE. Consult when choosing observation mechanics for a known
boundary and driven-adapter realness. Numbering is internal to
`nw-test-design-mandates`; its language convention frame owns native discovery.

## Mandate 8 — Universe-bound public-state observation

For state-mutating tests, name the public state promised to change or remain
unchanged, observe before/after, and reject undeclared changes in that observation
universe. Use native assertions or existing project helpers; no required
`assert_state_delta` signature, copied predicate library or `tests/common` path.
Private struct fields and mock call counts are not consumer outcomes. A pure
output assertion needs no invented mutable universe.

## Mandate 9 — Law-bearing generative testing

Choose treatment from the contract and actual composition, not file suffix,
decorator density or an assumed language adapter. In-memory compositions make
broad exploration inexpensive; a real driven dependency requires real-boundary
observations. Neither fact alone decides whether a broad law exists.

- Broad input/state/failure laws receive native generative properties, ordinarily
  one per independent law. Combine only when one generated observation honestly
  falsifies every combined law. Closed finite domains use native examples or
  exhaustive finite checks without mandatory generation.
- Follow `nw-property-based-testing` for constructive branch reachability,
  independent oracles, meaningful distributions/transitions, shrinking and replay.
  A missing shipped `nw-pbt-*` family is not an adoption barrier: use repository
  evidence to select its native generator/shrinker. Never bridge to Python.
- Keep properties deterministic and bounded. When real I/O is slow, choose the
  nearest law-bearing seam with an explicit preservation map to the promised
  real-port observation; a model without that map is a proxy. Properties never
  replace the representative real journey or persistent storage laws.
- No honest seam or unavailable native capability is `EVIDENCE_GAP` to DESIGN,
  with a concrete cause. Do not silently downgrade a broad obligation to examples
  or remove the promise to fit available tools.

## Mandate 10 — Journey and state-space observations

Keep an identifiable end-to-end business journey per feature through production
composition. Reuse the project's business helpers and installed/build lineage.
Gherkin, `.feature`, `steps_*.py`, a particular state-machine filename and a
three-scenario threshold are not requirements.

Add state-machine properties when the promised transitions/sequences have a broad
space. Share useful business vocabulary and incumbent helpers without forcing a
new DSL, composition class or helper library. Sequential model exploration does
not establish crash, race or protocol timing: those need targeted synchronized
real observations when promised. One journey does not mean one test total.

## Mandate 11 — Distinguishable failure observations

Observe each promised distinguishable failure/recovery mode with a concrete
native example at the relevant real boundary, and retain broad failure laws as
budgeted native properties where applicable. Error types/business outcomes and
state preservation matter; arbitrary failure-name stems, imports and separate
file requirements do not. Failure coverage follows selected authority, not a
hardcoded environment path or invented default environment matrix.

## Layered Test Discipline

| Surface | Evidence |
|---|---|
| Domain / in-memory port | Native properties for broad laws; examples for finite observations; public-state preservation |
| Real adapter / storage | Real dependency and persistent/translation laws; targeted failure observations |
| Protocol / crash / race | Authentic capture and synchronized promised checkpoints; model evidence is supplementary |
| Feature E2E | Business-readable journey through production composition, built/installed artifact where consumed |

Use the nearest honest boundary preserving the observation. Load matching
`nw-pbt-*` native guidance only when needed and available; these skill families
are examples, not a closed allowlist or compulsory nWave adapters. Native tool
absence is explicit, never a Python fallback. Architectural and contract checks
follow the applicability and executable selections in the generated DESIGN
grammar (`nw-design`), and remain required through primary-oracle realignment.
