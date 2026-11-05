---
name: nw-design
description: "Establishes durable architecture, reuse, boundaries, cross-layer algebra, residual stress behavior, paradigm, and prefactoring decisions for deterministic minimal handover construction."
user-invocable: true
argument-hint: '[bounded design question] --paradigm=[auto|oop|fp|procedural] [--residuality]'
---

> **Code facts** — resolve structural facts through `code-fact`; degrade
> LOUD when its provider-neutral adapters cannot answer.

# NW-DESIGN

Use `nw-human-collaboration` for interactive refinement with the human.
Honor an already selected final-review or full-delegation mode; the LLM
manages the dialogue and progression.

Load `nw-cross-cutting-invariants` and apply `flow:findings-go-to-the-owner-directly` when exchanging findings or questions between roles.


## Authority

DESIGN updates durable architecture brief/ADRs, never a per-delivery narrative,
plan or duplicate contract. Product value is decomposed once into an ordered
graph; no downstream competence reslices it. DISTILL asks the existing
CLI/software producer to derive one minimum executable whole-Request handover
from Git and the existing durable product/design/oracle authorities. Every
independently observable and shippable value slice represented in that graph
gets one oracle and an independent acceptance-test review before craft and
RED/GREEN. The Request gets one fresh independent whole-candidate final review
after all slices are GREEN, plus embedded per-slice refinement reviews for early
feedback. Source-blind EXAMINE where applicable and integration close the Request
once; internal technical shards, packages, layers and steps get no mini-cycle.

**Requested scope, designed scope and unresolved shared decisions are distinct.**
For a feature with several values, first establish or confirm existing common contracts,
dependencies and observation of the whole requested result, then design
per-slice deltas; a slice is not ready until the shared decisions it depends on
are resolved. Inherit epic/project decisions when present; never invent them. A
one-value or local change reuses adequate existing architecture: no full upfront
local implementation design, repeated boilerplate or universal gate. Resolve a
shared contract the slice needs first; an independent slice proceeds when
inherited architecture suffices, and that does not make the feature design
complete. Honor an explicit human instruction to design shared decisions first.
A single-value Request needs no shared section. A value oracle covers the slice
delta and references inherited common constraints and feature walking-skeleton
obligations by stable ids, without copying definitions; it does not attest feature completeness. This paragraph is the sole owner
of this rule; other roles and skills reference it.

Resolve cited `Proposed` decisions by confirming or changing them with a reason.
For each `Open` item assigned to DESIGN, supply its decision or the reason it
remains open and its owner. Preserve the product's original actors and scope.

When an uncertain boundary needs exercise, orient the existing delegation toward
one concrete producer-to-consumer connection: semantic design facts
to an executable oracle on the real public port. Let that consumer's
specific missing semantic question and counterexample return to its decision
owner before expanding the affected design or solution. This tests one
uncertainty in an existing value-level connection; it neither shrinks the
requested architecture scope nor attests that feature DESIGN is complete, and it
creates no technical-fragment cycle or additional delivery phase.

The coordinating architect owns the Required Design Pass, self-falsification
and complete design values. Consulted specialists supply plain owned advice;
integrate platform advice into the same coherent design authority.

Route application/component to `nw-solution-architect`, domain boundaries to
`nw-ddd-architect`, scale/distribution to `nw-system-designer`, deployment to
`nw-platform-architect`. Invoke only risk-required lenses. Algebra, certainty
and formal verification are owner-scoped lenses, never replacement routes.
Code-level structure stays downstream unless a public contract needs a boundary.

For an independent operational review of a selected platform lens, the outer native caller follows `nw-role-invocation` and consumes `nw-platform-architect-reviewer`'s actual recorded findings and outcome. Keep the evidence; builder success is not reviewer approval.

**Consultation policy (short).** The application/component architect owns
coherent design decisions by default — no fanout for routine work. Involve the
system designer only for a genuinely consequential distribution, capacity,
scaling, or availability trade-off. Involve the DDD architect only when
language, bounded context, aggregate, or invariant boundaries are actually
contested. Pattern/style selection (e.g. hexagonal, CQRS, event-driven)
applies only when system structure is actually in scope for the change at
hand — not by default on every design pass. The LLM chooses which consult(s)
to make and integrates their input into one coherent decision.

## Required Design Pass

Performed by the coordinating architect, not the outer host or a consulted lens.
Apply `design:simplest-design-that-delivers` in `nw-cross-cutting-invariants` throughout this pass.

1. **Intent and constraints** — bind product identities/observations; name
   uncertainty, never invent a requirement. Carry every cited input bound,
   range and explicit absence of a bound into `constraints`; explain each
   narrower or wider design as a deviation, never silently adapt the authority
   to a storage representation or generator.
2. **Code facts and reuse** — map responsibilities/callers/ports/dependencies;
   choose evidence-backed `REUSE`, `EXTEND`, `REPLACE` or `CREATE_NEW` for each.
   Check specifically for a SEMANTIC duplicate authority or a parallel
   implementation independently deciding the same business rule/fact under a
   different name or shape — not only a textual/symbol match (see
   `nw-code-craftsmanship`). Gate: `CREATE_NEW` explains why no candidate
   safely owns it. Record every candidate and the reason for it in
   `reuse_analysis`, so a reviewer sees the reuse/`CREATE_NEW` rationale.
   Close the responsibility's impact before freezing targets: implementation,
   public interfaces, exports, every known consumer, tests/helpers/fixtures,
   discovery/build/package metadata, manifest/lock and runtime. Record the
   closure in `impact_closure`: one item per target path and per agreement
   consumer locator with a language-neutral kind, a `CHANGED`, `MIGRATED` or
   `UNCHANGED_COMPATIBLE` decision and a reason. Classify by this repository's
   actual interface, build, manifest and lock artifacts, never by a fixed file
   name. Give every affected locator a disposition and reason before craft;
   an unresolved consumer is a design gap, not proof of compatible cutover.
   Compiler, LSP and native build facts are evidence; unsupported/noisy
   code-fact output is unknown, never zero consumers or proof of closure.
   Retain each code-fact query, subject, answering provider, confidence and
   scan-scope/degradation in the semantic evidence. A failed or unsupported
   query remains unknown; label any Glob/Grep/manual fallback and its limits.
3. **Prefactoring** — decide applicability in the current design payload.
   For a minimal preserving move, select a GREEN existing oracle and
   verification recipe; observe it before the move and after it, before
   behavior, with unchanged oracle, support and runtime identities
   (`nw-code-craftsmanship`). A declaration, missing selector or runs after
   feature implementation is not evidence. Assign a shared move to the
   selected value's `prefactoring` declaration; shared authority records no
   run and waives no distinct move. A code-target slice states this decision,
   or `nwdes design not-applicable add --in SLICE --analysis prefactoring
   --reason TEXT` (or `--shared`), never both. Any level L1 to L6 may be
   requested; `--move` names the follow-up change it makes easier. Use
   code-fact signals when the provider answers; else say it is unavailable
   and name platform install commands. The host relays the offer; never ask
   the human or install. Read smells for the declared paradigm:
   `nw-code-design-fp`, `nw-code-design-oo`; procedural has none.
4. **Ports and boundaries** — define driving/driven ports, dependency direction,
   ownership and failure translation. Name the native type/record and owning
   module for decisions, effects, errors and per-process state.
   Gate: change requires durable amendment.
5. **Paradigm** — preserve settled repository authority. Select
   `functional`, `object_oriented` or `procedural` from repository and problem
   evidence only when the application decision is genuinely open, not from
   taste; all consume the same laws/boundaries. Preserve an evidenced imperative
   transaction script as `procedural`, not FP merely because it exposes
   functions. Do not introduce classes or new files merely to fit a label.
   Follow `construction:design-paradigm-projection` for absent or contested
   authority, or settled authority outside these three values: that is a bounded
   representation gap, not permission to coerce its design or submit an
   unsupported field. Read OO/FP design guidance only for its matching
   paradigm; procedural does not force either specialized skill.
   For `object_oriented` and `functional`, design for the rules the crafter
   applies: the same `nw-code-design-oo` or `nw-code-design-fp` you read. Give
   each domain decision a cohesive owner that holds its data, justified in the
   reuse analysis, and target it `EXTEND` when it exists or `CREATE_NEW` when it
   does not (value object, first-class collection, choice type). A policy that
   spans several aggregates may live in a domain service. Never place a decision
   about one object's data in an application service or script: the crafter
   refuses a design that forces an anemic entity, an application transaction
   script or domain decisions in effectful code.
6. **Cross-layer algebra** — for every affected layer name states, operations,
   observations, equality and falsifiable laws:
   - domain: legal states and transitions;
   - application/ports: explicit success, refusal and retry outcomes;
   - adapter/integration: protocol, decoding, concurrency and dependency failures;
   - infrastructure/recovery: timeout, partial failure, replay, recovery and loss.
   Use `nw-algebraic-design-protocol` for observation limits and
   representation-preservation checks; native types/patterns, not forced FP syntax.
   Default in every design: algebraic modeling with formal verification.
   Read `nw-solution-architect-formal-verification` in every design. Map each
   claim to its checker and reason in `decisions`: Quint for state models,
   TLA+/TLC when Quint is insufficient (including required temporal/fairness
   support), Agda for proofs, and both/all when one checker cannot cover it.
   Probe needed tools with exact argv and output before relying on them.
7. **Residuality** — derive stressors by negating declared assumptions and name
   the assumption in each row. Record the preserved observation, allowed
   degradation, forbidden outcome and surviving residue. Name single points
   of failure and construction bypasses, with the remaining obligation and
   owner or the evidence that makes them unreachable. Keep admitted, excluded
   and unknown states with their risk owner.
   Walk a second stressor set not used to derive the design against the finished
   design; record what each shows and distinguish a walkthrough from execution.
   Use `nw-stress-analysis` for its triggered analysis. A removed-hypothesis
   counterexample is triage evidence, not automatically a missing type.
   A new residue amends architecture, never refactoring.
8. **Test substrate** — name real driving port, helper/import, fixture,
   executor/lifecycle, dependency owner, resolved version and manifest/lock,
   declared/runtime state and literal argv.  If a required dependency is absent,
   include its architecture-grounded target delta; hand off only when it is both
   declared and present in the verification runtime.
   Choose native runner, test layout and PBT from repository evidence under
   `nw-test-design-mandates`' language convention frame, including actual
   manifest/build/test stanzas; no closed language allowlist or nWave adapter
   prerequisite. Keep a minimal falsifier per obligation, native properties for
   broad laws and native examples for finite/singular observations. Real storage,
   synchronized crash/race/protocol integration and an identifiable feature E2E
   remain when promised; a cheap model is not their replacement.
   For each broad law, declare public generator domain and size bounds,
   shrinking/replay approach, and independent observation or falsifier under
   `nw-property-based-testing`; reuse applicable formal-model invariants.
   Without a native PBT library, design seeded generators and explicit shrinking
   in the repository's language, retaining any unexecuted shrinking limitation.
   The architect supplies these semantic obligations; ATD authors the executable
   public properties, not the architect's design probes.
   For warm verification, decide whether native commands invalidate actual
   dependency/toolchain/flag/generated-input changes and freshly execute checks.
   The host owns workspace and generated-directory retention; see `nw-throughput`.
   No automatic toolchain duplication, language detection or universal cache key.
   Unsupported recipes use cold isolation. Run the declared verification command
   for a new observation rather than relabeling an old receipt.
   Gate: DISTILL cannot invent an ambient interpreter or boundary.
   Test time (`test:feedback-loop-budget` in `nw-cross-cutting-invariants`): declare the per-test and property
   budgets and the feature's share of the default CI suite (300 s unless a
   repository ADR sets another); give every formal law a fast executable
   projection on the pure core. When the feature has critical infrastructure
   paths, propose its derogation request to the human: the infrastructure tests
   with one risk/value record each, the suite's trigger and the extra budget. Once
   granted, cite the feature's derogation ADR in the design. Only a human grants
   it.
9. **Human projection** — explain current observations/equality, alternatives,
   laws, consequences/trade-offs, failures and guarantee ceilings in ordinary
   language. Keep one authority. Ask only when
   an answer changes equality, carrier, law or an irreducible trade-off.
   Human-readable views project the same current model, never a second authority.
10. **Agreement analysis** — reuse asks "does something already own this?";
    agreement analysis asks the question reuse cannot: "who else must agree
    with the contract I am changing?" For every shared contract the change
    touches (a schema, a wire format, a config shape read by more than one
    producer/consumer), record every producer and every consumer with
    `nwdes design agreement add --in SLICE` (or `--shared`): its locator, its
    party (`Producer` or `Consumer`), a closed decision (`Migrated`,
    `UnchangedCompatible`, or `Incompatible`) and a reason. Gate: a change
    touching no shared contract records a reasoned
    `nwdes design not-applicable add --in SLICE --analysis agreement --reason TEXT`;
    it is never inferred from silence.
11. **Architectural and contract test applicability** — record applicable checks
    with `architectural-test add` or `contract-test add`; record concrete
    non-applicability reasons with `nwdes design not-applicable add --in SLICE
    --analysis architectural_tests` (or `contract_tests`) and a written reason. An
    architectural check applies when authority evidences a deliberate
    dependency/boundary/owner law the change can reach; it falsifies that law
    over the whole scope the law governs, including members added later and
    transitive paths the law covers, not incidental AST
    or style. A contract check applies when the parties can change apart —
    another owner, deployable or release schedule, or persisted/wire data
    outliving the producer's version. It runs the real producer output
    through the real consumer and observes the promised outcomes, errors or
    version compatibility, never mock echoes or hand-written producer records.
    Callers inside one deployable that change in the same commit are covered
    by the primary oracle, not a contract test.
    Reuse sufficient native checks; do not mandate Pact/ArchUnit/import-linter.
    Bind their test locators to declared verification selections and preserve
    those obligations when DISTILL realigns its primary oracle.

Resolve uncertain constructibility with a concrete consumer case and
counterexample to the decision owner, batching related findings. Consult ATD
for timing/public construction where needed, not a mandatory extra review
at every layer. New ATD supports available before craft and future production
targets have different timing. If implementation changes a prospective name
or owner, reconcile this same authority and regenerate its projections; never
create a competing decision document or rewrite chronology.

Before craft, close the host/crafter agreement on committed versus uncommitted
work, measured before/after revisions, staging ownership and install/hooks.
Use scoped currentness to reuse unchanged adequate decisions; native remeasurement
does not itself require semantic reauthoring. Contract/prerequisite changes may
invalidate evidence with unchanged production. The host decides compatibility,
continuation and authorized repair.

## Design content and evidence

Supply the established paradigm (functional, object-oriented or procedural),
decisions, constraints, reuse rationale, full responsibility impact and boundaries.
Describe failure algebra, observations, equality and constructors; laws,
refutations, construction claims and state exclusions; model/proof sources,
refinement, properties, atoms and mutants; closure axes, stressors and residual
guarantees. Preserve native architectural and contract obligations.

Each slice needs its oracle, supports, ordered verification commands, production
targets, public stimulus, expected result and falsifier. Describe preservation
work before behavior changes and ADR reasoning.

Keep shared architecture and slice deltas distinct; inherit common facts without
copying them. Preserve retained ADR identity and unchanged accepted reasoning;
make replacements and supersession explicit.
Models/proofs remain complete external source files. Retain native run receipts
beside them: checker/version, literal argv, exit, stdout, stderr and model hash.
Cite source and receipt locators; a locator is not proof of execution.


The Request's ordered value graph is decomposed once. Every independently
observable, shippable value slice retains its value-level oracle and
independent acceptance-test review before craft and RED/GREEN. Implementation
candidate review, conditional source-blind EXAMINE and integration happen once
per Request after all slices are GREEN. Internal technical shards receive no
separate contract, review, EXAMINE, or finalization.

## Constructive closure and refinement

For every public value, distinguish **safety** excludes an invalid state;
**inhabitation** proves an intended valid value can be constructed from admitted
input; **public reachability** proves its producer-to-consumer path reaches a
public driving/observation port; **liveness** proves eventual progress under
explicit temporal/fairness assumptions. Record each in the brief/ADR on separate
axes: DESIGN `PASS|BLOCKED`, runtime
`OBSERVED|DESIGNED_NOT_BUILT|INDETERMINATE`, and the proof/check result with its
actual evidence or `INDETERMINATE`. An unchecked DESIGN claim is `BLOCKED`;
an unexecuted checker establishes no proof. Irrelevant liveness carries a
concrete non-applicability reason, not a third DESIGN-axis value.
Bounded/synchronous execution justifies that only for liveness, never
safety/refinement/reachability. Omission is `BLOCKED`.

Record `input -> constructor/producer -> consumer -> public port`, with exact
owner/invocation/existing symbol or concrete repo-relative DNB site/symbol.
Generic “planned site” is not buildable DESIGN evidence. `PASS +
DESIGNED_NOT_BUILT` is acyclic/buildable/unobserved. Reject an unseeded cycle or
name its bootstrap.

A formal model closes only its claim: map atoms to runtime symbols, exclusions
and refinement. For `RED_TO_GREEN`, unimplemented runtime is allowed only with
mapping/refinement obligation and declared limits. A verified mapped model may
close DESIGN, never runtime; without mapping it is unrefined **model-only**.

## Counterexample discipline

A refuted invariant, a failing property, a model-check violation, or a
scenario the design cannot classify is first a ROOT-CAUSE question about the
representation, never a patch site:

1. Ask which type made the violating state representable. Route the
   diagnosis through `nw-algebraic-design-protocol` (follow the contradiction
   to the type or observation that causes it) and the cure through
   `nw-certainty-by-construction` (encode the missing distinction so the
   state is unrepresentable). Never add a law, guard, or ceremony on top of
   the unchanged representation as the first move.
2. A theorem that only holds conditionally is the same signal: triage its
   hypothesis as missing type/carrier distinction, law scope or external boundary.
3. An added law over an unchanged representation is a symptom patch. It may
   ship only with an explicit recorded justification of why the representation
   cannot change, in the amended durable authority.
   Retain each attempted concrete counterexample and its actual result; for a
   refuted law, name the carrier distinction, law-scope or boundary diagnosis.

## Independent statement review — retired

Proof/model/exhaustive artifacts verify the PROOFS, not the STATEMENTS; two
lanes may agree on the same misreading — that is a coherence check, never
corroboration. This limitation remains a DESIGN self-falsification duty, not an
independent delivery review. Before closing with `--outcome accepted`, DESIGN attacks its own
observations, constructive public-oracle chain, reuse/prefactoring choices,
boundary/failure algebra, residual guarantees and test substrate with concrete
counterexamples. The delivery flow's independent quality points are the
acceptance-oracle review, one whole-diff implementation review, and conditional
source-blind EXAMINE.

Default in every design: algebraic modeling with formal verification.
Missing required checkers are an installation-or-waiver decision for the human,
relayed by the host. State an indeterminate judgment naming missing tools,
affected claims and platform-specific install commands; install only with authorization.
Only a recorded human waiver permits continuation without that proof.
A waived claim remains INDETERMINATE with the waiver reason, never PASS;
native property tests or finite checks do not silently replace it.

For each unknown load-bearing system fact, use a bounded empirical probe and
record the unknown, executed fact and result. A probe resolves a discriminator,
never prototypes a desired answer or becomes a wave. Repeating an inconclusive
probe needs a changed hypothesis or useful new evidence under
`delivery:trustworthy-baseline-and-repair-scope`.

Use `nw-solution-architect-formal-verification` for checker selection, bounded
execution, complete model/proof delivery and property-specific falsification.
Self-falsification may also use native property tests or finite checks, but they
do not replace a required formal checker. Preserve useful existing models and
actual host limits. Missing tooling stops the affected proof; state an
indeterminate judgment and relay the human's installation or explicit waiver choice.
Unrelated analysis may continue, but missing tools alone do not authorize an
accepted design without the required proof. Record any human waiver
with `decision add`, naming the affected claims and reason; the proof stays `INDETERMINATE`
and its unchecked DESIGN claim stays `BLOCKED`, never PASS.

Use applicable `nw-review` questions as DESIGN self-checks only (S1-S4
structure; selected T5-T7 time; three values). They never replace the
acceptance-oracle review. Do not dispatch a separate independent DESIGN review
unless the nwdes delta shows a changed shared decision or ADR; otherwise the
whole-candidate review suffices. They find "structural incoherence", never
temporal holes; a
temporal gap needs a temporal/state-exploration check with the checker covering
that claim, TLA+/TLC when Quint is insufficient. Missing tooling follows the
host-relayed installation-or-waiver rule above, never a silent native-test downgrade.

## Handoff

After self-falsification, supply the truthful judgment and diagnostic.
Unresolved findings name their decision owner and remedy. Changed design
preserves unaffected decisions and deliberately replaces superseded facts.

The semantic input records only current decisions and executable obligations.
Define purpose, common architecture and each value's delta once as catalog facts
so a reader unfamiliar with the Request can understand parts,
responsibilities and binding rules. Carry the driving port, public observations,
native substrate and runner argv, architectural/contract obligations, typed
carriers and invariants required by the downstream oracle owner. Inherit common
constraints without copying a second authority. Downstream roles need the
complete current design facts, not an unsupported completion claim.

Keep complete formal model/proof bytes in external source files, cited by
their model path; retain native execution receipts beside them. Keep actual
argv, exits, output, traces and identities distinct from modeler-declared
coverage, backend, seed, bounds and interpretation. An asserted receipt or
hash alone proves no run; missing evidence stays explicit.
When a needed assurance fact cannot be expressed truthfully, name that gap and
its owner as indeterminate. Preserve reachable semantic work without inventing
facts, future commands or side authority.

## Human-readable design

Use current full briefs and HTML with `nw-doc-as-artifact` for human review. Rendering
does not establish completion or proof; there is no wave-entry density
preference or expansion-offer mechanism to resolve.
