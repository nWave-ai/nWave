---
name: nw-distill-port-treatment-policy
description: "Port-to-port acceptance criteria + the Architecture of Reference (port-class → test treatment) + the Project Infrastructure Policy (concrete mechanism per port) + the walking-skeleton canonical definition and not-applicable exemptions. Consult while classifying a port's test treatment and the concrete mechanism for this codebase."
user-invocable: false
disable-model-invocation: true
---

# DISTILL Port Treatment + Infrastructure Policy (KNOWLEDGE)

**Kind**: KNOWLEDGE (reference). No forced sequence — consulted on its trigger.

**Trigger**: you are classifying a port → test treatment (real vs fake) and choosing the concrete mechanism for THIS codebase (Testcontainers vs dedicated env vs in-memory; which fake class), or determining walking-skeleton applicability. Composed by `nw-distill`.

## Reasoning Mandate (Caveman)

Verdict-first, tables over prose, evidence-dense, zero narrative. Depth comes from rigor, not padding. State the conclusion, then the supporting evidence; never bury the verdict under exposition.

## Acceptance Criteria: Port-to-Port Principle

Every AC MUST name the driving port (entry point) exercising the behavior → port-to-port ATs → TBU (Tested But Unwired) defects structurally impossible.

Each AC:
1. **Observable outcome**: what user/system sees
2. **Driving port**: entry point triggering the behavior (service, handler, endpoint, CLI command)

No driving port → crafter can write correct code never wired into the system.

**Features**: "When user {action} via {driving_port}, {observable_outcome}"
**Bug fixes**: "When {trigger}, {modified_code_path} produces {correct_outcome} instead of {current_broken_behavior}"

## Architecture of Reference (ports & adapters — project-level defaults)

Three port classes, each with default test treatment. Table = PROJECT-LEVEL: decided once per project (DESIGN of first feature, or framework adoption). NOT renegotiated per feature. Agent applies defaults; per-feature decision = MECHANISM (Project Infrastructure Policy below), not treatment.

| Port type | Examples | Default in test |
|---|---|---|
| **Driving** (entry point) | HTTP API, CLI, in-process call, hook | **In-process via the `OutputPort`** — drive the real entry (`cli main(argv)` / application-service method) IN-PROCESS with a fake output port, no interpreter fork. The ONE selected `@walking_skeleton` proves installed wiring; additional real-boundary observations require a separately declared integration need. |
| **Driven internal** (shared state) | Repository, read model, application cache | **In-memory fake for focused acceptance scenarios.** The feature's one explicitly selected walking skeleton uses the real adapter; separately declared adapter-integration tests also exercise real I/O under `nw-tdd-methodology-walking-skeleton`. A project config selects the concrete real mechanism for those observations, not a real-I/O alternative for every focused scenario. |
| **Driven external / non-deterministic** | Clock, email, SMS, push, payment, LLM, third-party API | Fake/stub with output capture (so a `Then` can observe the side effect) |

Replaces the earlier per-feature Walking Skeleton Strategy A/B/C/D choice. Decision is structural — port CLASS implies port TREATMENT; per-project Infrastructure Policy specializes the mechanism per treatment.

Port unclassifiable by agent → ask the user with a soft prompt. Do NOT improvise the classification.

### The inverted Driving default — in-process, not subprocess (the speed default)

The Driving default INVERTS the old "CLI = subprocess runner" assumption. A new acceptance test drives the entry point **in-process** by default: it calls the real `cli main(argv)` (or an application-service method) directly, threading a fake `OutputPort` that captures the terminal output a `Then` asserts on. No `subprocess.run([sys.executable, ...])` fork — the same Mandate-13 driving-port semantics, 10–100× faster. (Language-agnostic: the rule is "call the shipped entry in-process with a captured output sink"; the `cli main(argv)` form is the Python illustration.)

**The feature has ONE `@walking_skeleton` subprocess-E2E, reused and extended by its slices** (canonical policy: `nw-tdd-methodology-walking-skeleton`). That scenario proves the installed artifact is wired end-to-end. Additional E2E scenarios require distinct observable integration needs; they are not additional walking skeletons. Every other AT defaults to in-process/in-memory. Wiring coverage beyond it comes from the independent Examiner exercising charter observables through the real surface and the final whole-slice verification; never multiply E2E scenarios to imitate confidence.

### The "CLI = e2e by construction" caveat is DISSOLVED

The old caveat held that a CLI command can only be tested end-to-end (subprocess) because the terminal is intrinsic to the command. That conflation dissolves under the hexagonal cure: **the terminal is an external system behind the `OutputPort`.** The CLI surface SPLITS into two:

| Facet | What it proves | Default treatment |
|---|---|---|
| **output-content / behaviour** | the command computes + emits the right output | **in-process** via the `OutputPort` (captured, asserted on the fake's buffer) |
| **terminal-wiring** | the installed binary actually reaches a real terminal | **exactly one `@walking_skeleton`** per FEATURE (subprocess-e2e) |

The content facet (the bulk of the ATs) drives in-process; the wiring facet is the single WS. Do not multiply subprocess ATs per scenario, slice or command. A separately declared adapter-integration observation may require another real process when the skeleton cannot observe the promised boundary property; it is not another walking skeleton.

### Config-switch — in-memory local default / testcontainers prod-like

Driven-internal ports use an **in-memory fake** in focused acceptance scenarios. Within feature acceptance scenarios, real driven-internal I/O is reserved for the one explicitly selected walking skeleton. Separately declared adapter-integration observations exercise their real adapter boundary. A config parameter selects the concrete prod-like mechanism (Testcontainers / dedicated env) for these real-I/O observations; it does not switch focused acceptance scenarios away from their in-memory treatment. Resolve the mechanism from the project Infrastructure Policy (`docs/architecture/atdd-infrastructure-policy.md`) per port:

The speed default never weakens a promised concurrency, atomicity, durability or recovery observation. If an in-memory fake cannot expose the declared failure, retain an explicitly declared real adapter-integration observation with the required process/resource boundary; do not relabel it as focused coverage, replace it with a fake, or omit it to meet a one-skeleton count.

- **`@in-memory`** (default) — the in-memory double; runs everywhere, no container runtime needed.
- **`@real-io` / prod-like** — the selected walking skeleton or a separately declared adapter-integration observation uses Testcontainers, a dedicated environment, or the declared local real adapter. Config selects its mechanism, not its applicability. When required external infrastructure is absent, report that observation INDETERMINATE (`@requires_external`, skip-if-absent), never a silent pass or an in-memory substitute for the real-I/O observation. Focused in-memory scenarios still run.

This keeps the local loop fast (in-memory) while guaranteeing the prod-like path is reachable and exercised where the infrastructure exists.

### Shared-provisioning default for `@real-io` — provision ONCE, isolate PER TEST

**THE RULE: the real adapter's provisioning + teardown (container start/stop, real subprocess/repo/filesystem setup) happens ONCE per test session (or module, if the project's runner cannot share across modules) — never once per test, never once per test class.** Test independence is a SEPARATE, cheap concern layered on top of that one shared instance: a unique namespace/schema/branch/directory per test, or a transaction-and-rollback boundary, or an explicit reset-between-tests step — never re-provisioning the whole real resource per test.

Motivating evidence (this codebase, measured 2026-07-19/20): subprocess-spawning `@real-io` tests that provisioned their own real repo or process per test accounted for **519s = 35% of total CPU in 19% of tests**. Another delivery check leaked orphaned real-postgres clusters because teardown was repeated per test. Both failures share one cause: per-test provisioning of a real resource.

Applying the rule:
- **Author the fixture at session/module scope**, not function scope: the real container/repo/process comes up once, is handed to every test that needs it, and comes down once at the end (or is explicitly reaped on every exit path, including a killed run — never assume the happy-path teardown always runs).
- **Isolate with the CHEAPEST mechanism that keeps tests independent** for that adapter: a fresh schema/table-prefix per test on one shared database, a fresh branch/worktree-relative-path per test on one shared repo clone, a fresh temp-subdirectory per test on one shared filesystem root. The Project Infrastructure Policy's `Note` column records which isolation mechanism was chosen, alongside the shared-provisioning mechanism — e.g. `Testcontainers.MongoDb, ONE instance per session, per-test db name` replaces the older per-test-class-fresh-instance framing.
- **Never let one test's isolation leak into another's** — the isolation mechanism is the thing under scrutiny in review, not the provisioning (provisioning is deliberately NOT re-verified per test, since it is identical for all of them by construction).
- **Degrade-LOUD on shared-instance failure**: if the ONE shared instance becomes unusable mid-session (killed, corrupted), every dependent test must fail informatively (what broke, which test broke it if determinable) — never silently skip or silently re-provision without saying so.

This generalizes the git-pollution-guard fix (`tests/conftest.py:_common_git_dir_is_shared`, 2026-07-20): the failure mode there was the INVERSE of this rule violated on the CONSUMING side — a guard fixture assumed it was the sole writer of a real `.git`, when in fact many linked worktrees legitimately shared it, and its per-test "restore" clobbered siblings' real work. The lesson is symmetric: whichever side owns a SHARED real resource must know it is shared, and neither side may treat per-test churn on it as safe to no-questions-asked reset.

## Project Infrastructure Policy

Architecture of Reference fixes **port class → test treatment** defaults. Project Infrastructure Policy specializes them with the **concrete mechanism** for THIS codebase. **Once per project, not per feature**.

### File location and structure

Lives at `docs/architecture/atdd-infrastructure-policy.md` (project-local). Three tables, one per port class, columns: `Port | Mechanism | Note`.

```markdown
# ATDD Infrastructure Policy

## Driving
| Port | Mechanism | Note |
|---|---|---|
| HTTP API | WebApplicationFactory<Program> | |
| CLI | in-process main with captured output; installed subprocess for the selected walking skeleton or a separately declared process-boundary integration observation | Focused scenarios remain in-process. |

## Driven internal (in-memory default + prod-like leg)
| Port | Mechanism | Note |
|---|---|---|
| IUserRepository (MongoDB) | In-memory fake for focused scenarios; Testcontainers.MongoDb, ONE instance per session, per-test db name for selected real-I/O observations | Real adapter only in the selected walking skeleton or separately declared adapter-integration tests. |

## Driven external / non-deterministic (fake)
| Port | Fake | Note |
|---|---|---|
| IClock | FakeClock | manual advance |
| IEmailSender | FakeEmailSender | in-memory capture |
```

`Note` column optional — one-line clarification only.

### Apply-if-exists / write-if-absent

| Case | Action |
|---|---|
| File exists (default `--policy=inherit`) | read policy, apply recorded decisions; no renegotiation for ports already in table |
| In-scope port missing from policy | Use a mechanism already established by the supplied design or project defaults; if a necessary mechanism is still unspecified, record the missing design fact in the acceptance close diagnostic below. Append a decided row only when policy writing is an authorized support. |
| File absent | Only when the policy path is a declared support, create the three-section skeleton (`policy-bootstrap-template`); otherwise write no policy file. Treat in-scope ports as missing (row above). |

Edited in place. No per-row versioning — git history = audit trail.

Writing the policy file is a declared support write: the acceptance designer creates or appends it only when the dispatch names the policy path among its supports. Otherwise apply the Architecture of Reference defaults and write no policy file. The acceptance designer records values through its `nwdes acceptance` verbs and closes with `--outcome accepted|rejected|indeterminate` and `--diagnostic T`; nwdes constructs the record, not a model-authored envelope. Carry any missing-mechanism reason and concrete question for the DESIGN owner in that diagnostic. If the missing fact prevents a constructible public oracle, close with `--outcome rejected` before changing oracle bytes and explain the port, missing mechanism, and required DESIGN clarification in the diagnostic. If the supplied design and defaults suffice, author the oracle and close with `--outcome accepted`; a nonblocking policy-mechanism gap may be noted in the diagnostic, never turned into a new gate. The native caller relays the finding to the DESIGN owner; diagnostic prose does not select a software route.

### `--policy=fresh` flag

`--policy=fresh`: ignore existing decisions this run; resolve every in-scope port as a missing row under the same design/default and diagnostic rules above. Rewrite only a declared policy support path with the resolved decisions. `fresh` = major refactors (stack swap, test-strategy overhaul). Otherwise `inherit`.

### Relationship to the Architecture of Reference

Architecture of Reference: "what kind of treatment for this port class?" (real vs fake). Project Policy: "which concrete implementation for that treatment?" (Testcontainers vs dedicated env, which fake class).

Policy CANNOT override port-class treatment: focused scenarios keep driven-internal ports in memory, the explicitly selected walking skeleton and separately declared adapter-integration observations use their real driven-internal adapter, and driven-external ports stay fake. Policy records the concrete mechanism for the applicable treatment; it cannot opt every focused scenario into real I/O.

### Expansion `policy-bootstrap-template`

Emitted on first DISTILL in a project (file absent):

```markdown
# ATDD Infrastructure Policy

Per `nw-distill-port-treatment-policy`. One file per project. Apply-if-exists; write-if-absent; rewrite with `--policy=fresh`. Git history is the audit trail.

## Driving
| Port | Mechanism | Note |
|---|---|---|

## Driven internal (in-memory default + prod-like leg)
| Port | Mechanism | Note |
|---|---|---|

## Driven external / non-deterministic (fake)
| Port | Fake | Note |
|---|---|---|
```

## Walking Skeleton Strategy + canonical definition

The 4-way per-feature choice (Strategy A/B/C/D) is REPLACED by two structural decisions: the Architecture of Reference (port-class treatment, once per project) + the Project Infrastructure Policy (concrete mechanism, once per project). Per-feature, DISTILL reads policy (`--policy=inherit` default); appending rows or rewriting (`--policy=fresh`) requires the policy path to be a declared support.

### Canonical definition (Cockburn / GOOS)

A walking skeleton is the **thinnest slice of real functionality that runs end-to-end** — from the real entry point through the real architectural components to a terminal on real data — and which can be **automatically built, deployed, and tested** (Cockburn, *Crystal Clear*, paraphrase). In GOOS (Freeman & Pryce) the consequence is operative: **the first acceptance test IS the walking skeleton**, written outside-in before any production code. Because the test drives the real entry point and asserts a real terminal effect, fixture-theater is impossible **by construction** (cross-ref the protocol-driver contract in `nw-test-design-mandates-composition-contract`, the SSOT for the tautological-test anti-pattern).

Default: **every feature is applicable** — it has a real entry point and a real terminal. Only three honest cases exempt a feature, and the declared exemption is **verified by inspecting the feature's changeset** (filesystem inspection of changed files, NOT a mechanical git invocation — gates depend only on Python + filesystem):

| # | "Not applicable" case | Condition | Delta check |
|---|---|---|---|
| 1 | Pure library, no entry point | adds only importable functions/types; no CLI/HTTP/hook/composition entry | no new driving adapter or `__main__`/subcommand in delta |
| 2 | Internal refactor, no new public interface | behavior-preserving restructure; existing ATs cover the surface | no net-new public symbol reachable from an entry point |
| 3 | Config-or-docs-only | change is markdown/yaml/config; no executable behavior path | delta touches only `*.md` / `*.yaml` / config, zero `src/` behavior |

Declaring not-applicable requires naming the case (1/2/3); a delta that contradicts the declaration (e.g. a new subcommand under case 1) is a BLOCKER. Reference: `docs/research/walking-skeleton-atdd-best-practices-2026-06-12.md` (findings A1–A6).

Survives from the old section:

- **Walking-skeleton SCENARIO**: still required (unless a case 1/2/3 exemption is declared and delta-verified). One per feature, tagged `@walking_skeleton @driving_port`, closing the end-to-end loop through the production composition root. Litmus: a non-technical stakeholder confirms "yes, that is what users need."
- **Tagging convention** (unchanged):
  - `@real-io` — scenario uses real adapters (driving + driven-internal per Architecture of Reference)
  - `@in-memory` — scenario uses in-memory doubles (Tier B state-machine PBT, or in-memory acceptance per Mandate 10)
  - `@requires_external` — scenario needs an external system not in the project policy; skip if absent
  - Walking-skeleton scenarios MUST carry `@walking_skeleton @driving_port` and use the production composition root.
