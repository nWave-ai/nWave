---
name: nw-typesafe-system-one
description: "Use Jev System One for every supported, authorized semantic judgment when available: relevance selection, handoff preflight, evidence mapping, finding clustering, and confidence-gated escalation."
user-invocable: false
disable-model-invocation: true
---

# TypeSafe System One for Delivery

**Kind**: KNOWLEDGE. For every supported task-level semantic question, MUST use Jev when authorized and available. Resolve mechanical facts with local code. Loading this skill alone is not service use. This policy applies in every user project where nWave is active, not only the framework repository.

## Boundary

Jev is a remote System One service. It receives `state` and typed questions and returns a structured `Choice`, `Score`, or `Noul` with probabilities. It does not write code, reason through a delivery, prove a property, execute a command, or replace a human or independent reviewer.

A supported question has permitted evidence, explicit criteria and a typed answer
that the decision owner will actually use. Confidence, simplicity and predicted
savings are not reasons to skip it. Decompose larger reasoning tasks into their
supported subquestions; do not disguise synthesis or proof as a forced choice.

Jev is authorized by default: do not ask the user for authorization again. The
only authorization gate is an explicit refusal, `--jev unauthorized` on the call
or `"jev": "unauthorized"` in the repository or global configuration. When
refused, do not transmit and retain that limitation. `TYPESAFE_API_KEY` is only
a technical prerequisite for the service to work; it is never authorization or
consent. Jev is remote, not telemetry.

Check service capability at the first eligible question. If the key, permitted
invocation path or service is unavailable, record `typesafe: unavailable` and
continue locally. Never fabricate a call, widen role permissions, retry blindly
or block delivery on service failure. A malformed request is a caller defect,
not an unavailable-service exemption. Repair a known defect before a new attempt;
an unresolved defect remains explicit and local work can continue.

Do not call Jev for arithmetic, hashes, dates, parsing, schema checks, command
execution or symbol resolution. Use their deterministic tools.

Minimize transmitted state. Exclude credentials, secrets, personal data, private findings, source-blind material, confidential account/host/resource identifiers and secret-bearing logs. Source/test/consumer fragments may be sent only within explicit authorized review scope; do not send repository dumps, historical grader/baseline material or producer evidence to an independent assessment. If redaction removes needed relationships, classify insufficient and work locally. Record returned model, input/output tokens, duration and cost when actually available; unknown cost is not zero.

The LLM owns orchestration. nwdes constructs handoffs and documents without choosing steps. Jev supplies bounded judgments; code owns identities, arithmetic, schema checks, policy, and actions.

## Mandatory invocation routine

1. Identify the task-level semantic question, its owner and permitted evidence.
   Do not recursively classify whether a classification needs classification.
2. Reuse an applicable result only within the same decision-owner and independence
   boundary. Otherwise batch independent questions over the same compact state
   and invoke the existing client. A question counts once per relevant revision,
   not once per sentence or reformulation.
3. Inspect the distribution and raw answer, check relevant original evidence,
   and record the resulting local action with the request/result. A low-confidence
   or `insufficient` answer calls for reasoning or a discriminator, not blind trust.

```bash
python <this-skill>/scripts/jev_decide.py --request request.json --output result.json
```

A role that may not write files (for example a reviewer) passes `-` for both
`--request` and `--output`, supplying the request JSON on stdin (a heredoc);
the raw response is printed on stdout, so no file is created and every write
prohibition of the role still holds.

Run the client from a shell command, with the heredoc in that same command. A
tool kernel, for example a Python eval kernel, may not inherit the session
environment that holds the key, and then the client reports exit 3.

Request fields are exactly `state`, `model`, and non-empty `questions`. Use the
configured supported model; retained calls currently use `jev-1.13.0`. Include
`insufficient` where legitimate. Service responses are judgments, not proof.

Keep owner and revision receipts in the local record. If permitted ownership context is needed in the transmitted evidence, place it inside `state`; `owner`, `role`, and `revision` are not extra root request keys. A validation failure returns unchanged to the requesting owner, who corrects its own request. The caller never strips keys or rewrites an independent question to make it pass.

For a choice, `type` is lowercase `"choice"`. The keys of `criteria` are the
answer labels, and each value describes when that answer applies. They are not
scoring dimensions. This complete request illustrates the wire format:

For `"score"`, `criteria` is a nonempty ordered array of rubric levels, not
an object of dimensions. Ask one Score per relevant item/dimension with anchored
levels. For `"noul"`, criteria may be omitted/null or an object of `true`/`false`
descriptions. Choice criteria is a label object. Preserve role-authored request
and raw response; the existing client validates the actual wire contract.

```json
{
  "model": "jev-1.13.0",
  "state": {"need": "Notify state changes", "candidates": {"A": "Event subscription", "B": "String formatter"}},
  "questions": {
    "relevance": {
      "type": "choice",
      "instructions": "Which candidate directly supports the stated need?",
      "criteria": {
        "A": "Event subscription directly supports notification.",
        "B": "String formatting directly supports notification.",
        "insufficient": "The supplied descriptions do not support a choice."
      }
    }
  }
}
```

HTTP 400 is a caller defect. Check this request shape and repair a known mismatch;
do not relabel it as service unavailability.

| Exit | Meaning | Caller action |
|---|---|---|
| 0 | Response recorded | Inspect the answer; do not equate recording with acceptance |
| 2 | Caller/schema defect, including HTTP 400/422 | Repair the named request defect; never call it service absence |
| 3 | Missing key, network timeout/failure, HTTP 408/429/5xx | Record unavailability and continue locally; no blind retry |
| 5 | HTTP 401/403 access or configuration failure | Record access limitation; fix known configuration without exposing credentials |
| 4 | Invalid service response or otherwise unclassified HTTP failure | Preserve the distinction; do not invent a judgment or caller-defect diagnosis |

### Independent review and valid reuse

Reviewers and examiners form their own questions from permitted evidence. They
MUST NOT consume or reuse producer-owned Jev judgments, even if apparent inputs
match. Reuse within the same independent assessment requires the same owner,
evidence boundary, complete input, rubric, model/policy and evidence revision.
Retain these identities in existing request/result records; no cache service is
required. Never convert broader-context results into source-blind evidence.

### Complete, role-owned quality assessment

Enumerate the candidate's relevant items deterministically using local evidence:
test/family and logical implementation unit for code/oracle review; design
decision, boundary and producer/consumer agreement for architecture; applicable
pipeline, infrastructure, environment, rollout/recovery and KPI→telemetry plan
for platform. Link each item to its obligation and sufficient consumer context.
Assess every relevant item on each applicable dimension below; batch independent
questions over compact state. Not every line or YAML entry is a separate unit.
Applicability, out-of-scope and insufficient evidence are separate Choice/Noul
decisions, not the lowest quality score. Preserve explicit local limitations
for unavailable calls rather than fabricate a verdict or silently skip items.

| Item | Distinct assessment dimensions |
|---|---|
| Test / family | Obligation fidelity; observation/falsifier strength; incidental coupling; business readability; property adequacy |
| Implementation unit | Cohesion/invariant ownership; semantic reuse/duplication; dependency direction; type precision; effect separation |
| Architecture decision / agreement / boundary | Requested outcome/constraint fidelity; reuse/CREATE_NEW rationale; ownership/SSOT; simplest adequate alternative; state/failure/guarantee ceiling; substrate/test/prefactoring adequacy |
| Platform plan | Requirement-to-plan fidelity; infrastructure reuse; rollout/rollback conditions; failure/recovery and persistent data; KPI/SLO→signal→alert/runbook traceability; security/permission/config risk; truthful readiness evidence |

Reconcile applicability with current authority before scoring. No deployment
promise means no invented IaC/rollout requirement; `DESIGNED_NOT_BUILT` is not
`OBSERVED`. Native tools and real probes, not scores, establish callers,
temporal properties, recovery, compatibility and preservation.

Keep Score's score/confidence/legend/probabilities as service output. It provides
no free-form rationale. The owner verifies locators, observations and concrete
counterexamples locally and labels those reasons `reviewer_reason` (or explicit
architect self-check reason), never `jev_reason`. A label may classify a supplied
hypothesis; it is not autonomous diagnosis. Scores order attention, never
compensate blockers by averaging, prove correctness/completeness, authorize
deployment, replace human choices or add a universal DESIGN review phase.

Architect self-check is producer-owned, not independent review. A reviewer
forms its own minimized questions under its own ceiling. Run known-defect and
positive-control pilots before claiming calibrated thresholds or efficiency;
retain false flags, missed defects, item coverage and whole-path cost/time.

### Roles without a callable client

Use the role's existing permitted tool when it can invoke the client. If the
native host supports a caller exchange, the role may send its own typed question
and permitted state to the caller; the caller executes it unchanged and returns
the raw bound response to that same role. The caller must not choose, amend or
substitute an independent reviewer's question or judgment. Use the host's normal
continuation; do not add a delivery route, special verdict or orchestration protocol.
If that exchange is not available, record the capability limitation and continue
locally. A reference to this skill is not proof of callable tool access.

Source-blind EXAMINE currently has no demonstrated isolated Jev capability.
Do not call Jev there or inject producer/caller classifications into its packet.
Enabling it requires a separately verified path using only the examiner-owned
questions and its authorized public packet, preserving its independent verdict.
This explicit capability limit is not a general exemption for other roles.

A finite option set alone does not establish task suitability. The LLM still
forms alternatives and criteria, owns orchestration, synthesis, authoring and
independent verdicts. Every supported subquestion must nevertheless use Jev.

## Good Judgment Shapes

| Need | Primitive | State | Code decides |
| --- | --- | --- | --- |
| Select one candidate from a closed set | Choice | Request plus candidate descriptions | threshold and selected next read |
| Test one grounded condition | Noul | Claim and cited evidence | pass, investigate, or escalate |
| Rank a defined quality dimension | Score | Artifact plus concrete rubric | ordering and cut-off |
| Evaluate independent concerns | Parallel questions | Same narrow state | which answers apply |

Ask one direct semantic question. Put the exact condition in `instructions`; put contrasts and boundary cases in `criteria`. For batched cases, each question explicitly names the exact case/claim in `state`; do not rely on matching question IDs or an unqualified "the recommendation" to bind different subjects. Include `none`, `insufficient`, or `not-applicable` when it is a legitimate answer. Do calculations, counts, hashes, date ordering, schema validation, and path resolution in code before or after the request.

## Delivery Use Cases

These are mandatory triggers when their supported question and authorized invocation are available. Load conditional knowledge as needed; never suppress mandatory role skills.

### 1. Specialist-task preflight

For actual questions about task scope, ownership, missing facts or evidence relevance, classify them before dispatch. Reuse an applicable same-owner result rather than buying a duplicate classification.

Ask in parallel whether the task has:

| Question | Negative result means |
| --- | --- |
| One concrete deliverable | split the task or name the artifact |
| Authoritative inputs | attach the authority or state the unknown |
| Usable acceptance evidence | name the observation, command result, or document the consumer needs |
| A pending human trade-off | stop and ask the human |
| An orchestration leak | remove route selection or other roles' responsibility from the task |

The preflight is advice. It cannot reject a delivery or replace the role's own review.

### 2. Requirement-to-evidence map

Generate candidate links mechanically: requirement paragraphs, test names, public observations, and recorded outcomes. Ask Jev separately whether each candidate evidence item directly proves the stated requirement, supports it indirectly, contradicts it, or is unrelated.

Use the result to produce a compact evidence packet for a reviewer. Verify every accepted direct link by reading the original artifact. A test count, a green command, and a confidence score do not prove a requirement by themselves.

### 3. Connected-finding batch

Give Jev short, redacted finding summaries and ask whether each pair concerns the same producer/consumer mismatch, the same missing input, or different causes. Form one correction batch only after code and authority inspection confirms the relationship.

This reduces serial patching. Similar wording is never enough to merge defects.

### 4. Change-surface reading queue

First use repository tools to enumerate changed files, callers, skills, commands, help, fixtures, and document sections. Then ask Jev which candidates are semantically affected by the stated behavior change. Read the high-probability candidates and sample rejected ones.

Jev does not replace structural analysis. It prioritizes human or LLM attention where symbol names and imports cannot express the relationship.

### 5. Public-oracle critique

For a supplied public scenario and its declared value, ask narrow questions:

- Does the scenario observe user-visible behavior through the public port?
- Does it require a fact absent from the closed design?
- Does it distinguish the promised behavior from a plausible wrong behavior?
- Is a range, ordering, round-trip, or state trace present that needs a property observation?

The acceptance designer still authors the oracle. Jev never determines that a test is accepted, complete, or non-tautological.

### 6. Cheap-first escalation

Use a cheaper model or deterministic producer for a bounded draft or extraction. Route supported grouping and classification questions through Jev. Ask Jev one failure-oriented question per field or claim. Escalate to a stronger reasoning model or person only when a verifier signal crosses a threshold or the case is inherently ambiguous.

```text
cheap bounded result -> Jev grounded checks -> code checks -> strong model or human for flagged cases
```

Measure the whole path: input tokens, wall-clock, false flags, missed errors, specialist turns avoided, and accepted delivery outcome. A low Jev price is not a saving if verification work grows.

### 7. Conditional skill and context selection

Give Jev a compact index of candidate skills, their triggers, and the current task. Ask which single additional skill is relevant and whether no additional skill applies. Re-read the best few candidates with fuller descriptions before suggesting one.

Mandatory role skills remain mandatory. Jev may select only optional, conditional knowledge; it never suppresses a required competence or replaces the LLM's judgment.

## Confidence Policy

Use the returned distribution, not only the chosen label. Thresholds are local to the question and consequence; do not reuse a number across different questions or a Noul and a Choice.

| Result | Action |
| --- | --- |
| High confidence, low consequence | prioritize the suggested read or bounded check |
| Medium confidence | retain competing candidates and collect a discriminator |
| Low confidence or `insufficient` | ask for context, use a stronger model, or ask the human |
| High confidence, high consequence | independently verify against original evidence before acting |

Calibrate thresholds on held-out completed deliveries. Compare recommendations with later accepted outcomes and record false positives, false negatives, cost, and elapsed time.

## Known Limits

Do not use Jev for arithmetic, counts, hashes, dates, source parsing, path rules, invariants, or multi-hop reasoning. Do not feed it a repository dump. It degrades with irrelevant state and can interpret adversarial text as instructions. Use code to enumerate and filter candidates; send only named, relevant fields.

Never infer these claims from a Jev result:

- an implementation is correct;
- a contract is complete;
- a test is non-tautological;
- a candidate is admissible;
- a source-blind reviewer may be skipped;
- a user or human authority has made a decision.

## Request Record

Retain this local record outside source-blind packets:

```yaml
typesafe_judgment:
  purpose: task-preflight|evidence-map|finding-batch|change-surface|oracle-critique|cascade|skill-selection
  state_summary: redacted description of transmitted fields
  questions: [stable question ids]
  model: version returned by service
  input_tokens: integer
  policy: threshold and resulting local action
  later_outcome: accepted|rejected|indeterminate|not-yet-known
```

Record call, applicable same-owner reuse or explicit limitation for each identified question, alongside the resulting local action. Counts show use, not usefulness or savings. The record makes economic claims testable. Keep raw payloads only where their retention and privacy are explicitly authorized.

## Role decision points

| Role | Supported questions that require Jev |
|---|---|
| Principal orchestrator | Finding scope, related correction groups, evidence owner, optional context relevance, comparison of ready actions |
| PO / UX | Actor-outcome links, scenario contrasts, ambiguities, duplicate questions, ranking under human criteria |
| Architect / platform / DDD | Reuse-candidate relevance, described alternatives, requirement-boundary links, risk and assumption classification |
| ATD | Criterion-stimulus-observation links, uncovered expectations, overlapping tests, implementation coupling, evidence-packet adequacy |
| OO / FP crafter | Relevance of mechanically found implementations, related failures, bounded options and in-scope refactoring opportunities |
| Independent reviewer | Own finding classification, evidence relevance, connected causes, selected violation versus uncertainty or new expectation |
| Research / other specialists | Permitted-source relevance, contradictions, classification and ranking against the assigned rubric |

Use these at existing decision points. No mandatory extra phase, hook, acceptance
gate or fixed service-call quota is introduced. Measure downstream rework and
cost without using an unmeasured saving estimate as permission to skip.
