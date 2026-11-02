---
name: nw-po-scenario-exploration
description: Assess product values for Quint relevance and explore them through actual traces and mechanically rendered scenarios for human review.
user-invocable: false
disable-model-invocation: true
---

# Product Scenario Exploration

**Kind**: PROCEDURE | **Job**: explore product behavior through actual Quint scenarios.
**Trigger**: assess each DISCUSS value's relevance before constructing the brief/handoff.

## Per-value relevance (single owner of this rule)

Does any value have a sad path: refusal, conflict, concurrency/race, stale or
invalid input, or a missing operand? Then it is Quint-relevant by definition:
prepare its product questions and actor observations for bounded exploration,
even when the expected sad-path behavior is settled. Also explore unclear order,
timing or state interactions, and human-requested model-generated alternatives.
Only settled happy-path-only behavior may skip exploration without an availability
or human-refusal reason. Supply each value's explicit relevance judgment and reason;
one feature-level unavailability statement is not a per-value judgment.

For relevant values, run Quint inside the PO-human collaboration sequence,
before settling product facts, not as an afterthought or separate offer.
This introduces no wave, solver-owned route or formal-method gate.

## Collaboration sequence (single owner of this policy)

| Mode | Sequence |
|---|---|
| Interactive | initial concrete examples -> model actual assumptions -> actual Quint traces -> deterministic domain rendering -> human judgment -> revise/regenerate changed choices/model -> settled product facts and brief |
| Auto (delegated) | same steps without waiting; supply actual generated scenarios and assumptions or unresolved doubts for human reading and product authority. Silence or no human reply is never approval; keep it Open |

Question and value authority stay with the human unless explicitly delegated. The
LLM orchestrates. Default documents are English; the human
conversation uses the human's language (`nw-human-collaboration`). The modeler
writes readable Quint; the PO never needs to read code.

## Human authority

The human owns the intended behavior. The PO proposes contrasting scenarios and
records the judgment, actor and conditions. A repeated choice supports those
cases only; it does not prove general translation fidelity. Disagreement may
expose an incorrect translation, ambiguity, changed intent or unclear rendering.

The LLM orchestrates tool use within the active roles' capabilities and requests
model-capable help when needed. Product reasoning starts from the user's point
of view; implementation code is unnecessary. The solver controls no delivery
route. Installation still requires authorization.

## Availability and installation

The execution owner probes `quint --version`, including a configured local binary
when applicable. If unavailable, explain its purpose and offer a host-appropriate
installation once, as for Agda. Install only with authorization; preserve an
earlier acceptance or refusal. Check the host's Node/npm availability and the
official Quint installation instructions before suggesting commands.
On refusal or unsupported tooling, continue ordinary scenario discussion and
mark formal exploration unavailable. Never present invented traces as tool output.

## Model to human review

- Select a concrete operation pair and observation; where M2 is in use, identify
  its candidate relation. One example pair does not establish a general law.
- Separate recorded human choices from modeler assumptions. Timing needs an
  explicit clock/unit; simulation steps alone are not seconds. Name delivery,
  fairness and failure-detection assumptions rather than hiding them.
- Generate traces from the actual model. Retain model identity, tool version,
  command, seed/bounds and raw trace. Simulation is not exhaustive verification;
  Quint exploration does not establish FRET realizability or conflict diagnosis.
- Use a verified deterministic renderer with explicit domain action templates.
  Show actors, order, actual versus observed state, time and relevant conditions.
  Preserve trace indices and model identity; disclose any prefix or projection.
  Unsupported actions are reported, never filled in with invented narration.
  If no suitable renderer is available, report that integration gap.
- Let the human review the readable scenarios without reading Quint or formulas:
  correct, incorrect, depends, unclear, or a proposed correction. Show assumptions
  and allow challenging the wording itself; do not preselect acceptance.
- Record the judgment against the exact model/scenario. An open question remains
  open; silence is not approval. Revise the model after an actual decision, then
  generate fresh scenarios for review. Keep automated review distinct from the
  human's semantic judgment and respect explicitly delegated collaboration mode.

Tool reference: https://quint.sh/docs/quint

## DISCUSS integration and HTML

For each relevant value, the PO returns product questions and actor observations
to the host as an execution request rather than declaring exploration unrun.
The host selects a model-capable helper for bounded Quint work within authorized
tooling. The helper owns the model and raw trace evidence, not product intent.
Return model assumptions and deterministically rendered scenarios to the PO
before settling product authority.

Render trace events through domain templates, then share the readable scenario
in the local nWave HTML view using `nw-doc-as-artifact`. This has two distinct
transformations: trace-to-domain-scenario (must preserve events mechanically)
and document-to-branded-HTML (the existing shared renderer). The HTML renderer
alone does not implement the trace transformation. If that first component is
absent, report it instead of writing an LLM paraphrase and calling it mechanical.

After actual feedback, supply revised scenarios with title, Given, When and Then.
Preserve the human decision or automatic mode's unreviewed status, conditions,
assumptions and open doubts. Distinguish Proposed, Confirmed and Open judgments;
name an owner for every Open decision. Cite model identity, actual command/version,
seed/bounds and raw trace; preserve mechanically rendered event order.
Without real tool output, never claim generated exploration. A relevant value
may remain unrun only after host-reported Quint unavailability or human refusal;
otherwise return the execution/rendering gap to the host for resolution.

Replace superseded scenarios deliberately, then render the updated shared view.
Re-explore a changed model before reusing old feedback.
No automatic installation, model approval, wave transition or runtime proof.
