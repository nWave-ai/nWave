---
name: nw-review
description: Dispatches an independent reviewer for a durable authority, immutable oracle, candidate diff, charter set, or operational artifact.
user-invocable: true
argument-hint: '[owner] [repository-relative artifact or diff identity]'
---

# NW-REVIEW

Before diagnosing or assigning corrections, load `nw-cross-cutting-invariants`
and apply `delivery:trustworthy-baseline-and-repair-scope`. A blocking observation
requires attention; it does not alone authorize an independent repair.

Load `nw-cross-cutting-invariants` and apply `flow:findings-go-to-the-owner-directly` when exchanging findings or questions between roles.


Select the reviewer that owns the artifact class. Give it the actual
repository-relative artifact or actual diff, not copied prose.

Use the exact installed reviewer/examiner with the permitted evidence.
The examiner works from the user's point of view and supplied public contract
and observations; implementation source is not needed for that judgment.

Reviews leave the assessed artifact unchanged and remain adversarial. Every finding cites a file/line,
terminal command or exhibited counterexample. `APPROVE` requires the artifact
to survive every applicable check; missing or stale evidence is
`INDETERMINATE`, not approval.

The final reviewer owns selection and sufficiency of the touched-file selected tests.
It reuses a complete applicable native result (host, CI or the normal commit hook)
whose source, test, argv and runtime inputs are unchanged, citing its original operator
and run; it executes only missing or affected checks, once. Reuse never waives a check.

Review durable product/design authority at its owner, acceptance oracles with
the acceptance-designer reviewer, implementation diffs with the crafter
reviewer, charters with the PO reviewer, and platform artifacts with the
platform reviewer. A reviewer may veto but never silently repair the artifact.

Supply each finding's location, obligation, observation, remediation and correction
owner (oracle, design, implementation or product). Keep the assessed artifact/diff
identity and capability limits explicit. Missing evidence remains INDETERMINATE;
it never becomes an accepted review. Make the immutable evidence the review cites
available with the artifact before assessment. Send each completed finding directly
to its artifact owner through native messaging when available; relay through the host
route only when direct messaging is genuinely absent.

## Convergence

A review converges only against a CLOSED criterion set. Four rules, all binding.

- **Declared before, not chosen during.** The dispatcher states the original agreed
  value and the closed criteria in the dispatch. The reviewer first checks that the
  criteria preserve that value, then judges the declared set. Where an executable
  reference model exists, the set is "the surface agrees with the model" plus the
  named suites; anything outside it is not review material. A criterion the reviewer
  invents mid-review is out of scope, however true it is.
- **Classify against the request.** Judge agreed behavior, required quality and
  delivery obligations, and regressions caused by the request's work. Apply the
  shared repair-scope clause to safety-net failures and uncertain relevance.
  Independent improvements are notes, not automatic same-slice corrections.
- **Preserve the safety net.** A required failure cannot be waived. Its owner
  diagnoses and restores the required verification within the existing authority;
  independent redesign requires a scope decision, not an implicit repair chain.
  For public behavior corrections, compare existing coverage with the counterexample;
  invoke ATD only for uncovered behavior. After an owner's correction, the reviewer
  reassesses only the affected delta; notes alone do not require a review round.
- **Precise instruction repair is allowed.** Change the smallest instruction bytes
  that remove a proven contradiction. State measurable claims in executable checks
  where one exists; prose may state role boundaries, ownership, or remediation.

## Design-review question set

Structure (algebra) and time (protocol) questions that make a design review
adversarial instead of confirmatory. Finds structural incoherence, never
temporal holes -- a temporal gap needs the model checker (T5), not this list.

**Structure (algebra):**

- **S1** [INSPECTIVE] -- for every finite sum type, list the cases and pair
  each with its domain meaning; flag any case with no meaning and any
  meaning split across cases.
- **S2** [MECHANICAL] -- for every pair of invariants mentioning the same
  field, construct a state satisfying the first and check the second,
  delegated to a property test; "I couldn't find one" is not evidence.
- **S3** [MECHANICAL] -- for every invariant proven under an added
  hypothesis, remove the hypothesis and verify a counterexample still
  exists; if none exists the hypothesis was decorative, and the
  conditional theorem was the signal a type was needed.
- **S4** [INSPECTIVE] -- every unreachable arm of a total function must be
  made unreachable by the type, never by a comment.

**Time (protocol):**

- **T5** [MECHANICAL] -- declared progress/liveness: show do-nothing;
  model-check liveness excludes it; safety-only: `NOT_APPLICABLE`.
- **T6** [INSPECTIVE] -- name every fairness assumption's real guarantor,
  monitor, and violation consequence.
- **T7** [JUDGEMENT] -- list every model step and name the real code
  mechanism guaranteeing its atomicity; the answer must be a code
  reference, never prose. If it cannot be named, the review returns the
  QUESTION to the human, not a verdict.

**Marking rule (three values, load-bearing):** MECHANICAL = a tool answers,
the outcome is a fact -- if the tool was not executed, the review is
INCOMPLETE BY CONSTRUCTION, never approvable. INSPECTIVE = no tool, but the
answer is a fact readable on the artifact. JUDGEMENT = the answer is a
question returned to the human, never a verdict.
