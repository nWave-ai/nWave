---
name: nw-discuss
description: PO-led product conversation, visible feedback increments and human-readable briefs.
user-invocable: true
argument-hint: '<product question or outcome>'
---
# NW-DISCUSS

Read `nw-human-collaboration` for interactive refinement. Honor an already
selected final-review or full-delegation mode; the host manages dialogue and
progression. Apply `flow:findings-go-to-the-owner-directly` from
`nw-cross-cutting-invariants` when exchanging findings.

## Product ownership

Read `nw-role-invocation` before delegating. The exact installed
`nw-product-owner` owns semantic product facts and decomposition, using its
collaboration, JTBD, BDD and value-slicing knowledge. The host relays human
questions and executes requested tools within authorization. Offer proportionate
visual exploration for changed experiences; select UX help or a bounded spike
only when useful. Capturing product facts does not complete the conversation.

Supply promises, included/excluded scope, decisions, journeys and independently
observable slices. Keep corrections with the Product Owner and unresolved
prerequisites with their owner; do not silently substitute product meaning.

## Explore relevant scenarios

Before settling product authority, read `nw-po-scenario-exploration` and
apply its per-value relevance rule with the Product Owner. Do any values need
bounded Quint exploration, or is an unexamined deferral hiding the uncertainty?

1. Obtain the PO's product questions and actor observations for relevant values.
2. Probe `quint --version`, including a configured local binary. If unavailable,
   follow that skill's one-time installation offer and authorization rules.
3. The host obtains a model-capable helper and bounded real `quint run` evidence:
   literal command, explicit seed/bounds, tool version, model identity and raw
   trace. Mechanically render events through deterministic domain templates;
   an LLM paraphrase is not deterministic rendering. The PO owns product meaning,
   not model implementation.
4. Return rendered scenarios and assumptions to the PO. In automatic mode keep
   them unreviewed/open, never human-approved; in interactive mode obtain the
   human's judgment through the exploration skill's collaboration sequence.
5. Have the PO record real scenarios as Scenario promises and assumptions or
   unresolved judgments as decisions. Tool unavailability or human refusal stays explicit. A missing model,
   broken renderer or other host-owned prerequisite returns to that owner, not
   to a silent skip or repeated unchanged PO invocation.

The LLM owns semantic values, their supplied order and dependencies.
A simulation is not implementation verification.
No solver is required for ordinary scenario discussion when the relevance rule
finds no applicable value. Frontend/backend contracts and implementation planning
remain design and delivery responsibilities.

## Shared human view

Read `nw-doc-as-artifact` and use current briefs or HTML during meaningful
refinement when the view helps the human. Inspect
the result; if rendering is unavailable, expose the gap and keep the host
conversation readable. Rendering is not publication, approval or a progression gate.

Keep intent, actor/value outcomes, confirmed decisions, proposals, assumptions
and open questions distinct. Start from known facts; deepen only what affects a
decision or the human asks to explore. Human emotion belongs to the human:
record it only from the human's account, or explicitly mark it not supplied.
Explain unfamiliar terms and preserve original scope.
Document language follows `nw-human-collaboration`.

Forward human corrections to the Product Owner for revision.
Regenerate the same local view after a meaningful authority change; never edit
generated Markdown or HTML. No wave-entry setting, density gate, automatic
expansion offer or separate completion ledger is needed.
