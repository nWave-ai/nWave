---
name: nw-expectation-charter
description: Supplies or reviews user-view qualitative charter facts when EXAMINE applies.
user-invocable: false
---

# Expectation Charter

The charter gives the examiner an independent human oracle. Derive it from
public product intent and the observed user surface. Work from the user's
point of view; design, tests, implementation and diffs are not needed to define
the expected public experience. Dispatch `nw-product-owner` for the charter task.

## Charter content

The Product Owner supplies intent, exploration, positive observations and a
negative observation from public product facts. Explain unresolved prerequisites,
their owner and remedy; uncertainty is not acceptance.

## Value conservation

State intent, public starting conditions, what to explore and concrete
positive and negative observations. A public
start recipe uses a real product surface: exact CLI argv, a consumer's public
library setup/call, an HTTP/RPC request, or ordered UI actions. Preparing
internal state or invoking a private application/domain seam is not that recipe.

Every precondition and observation must preserve the public product intent:
clarify wording without adding or removing an input class, surface, failure
mode, quality or promise. A negative observation negates the same promised
outcome on admitted input; it does not invent a new scenario. Missing intent
or an exact usable public recipe returns to the product owner/human for
clarification, rather than inferring user intent from architecture, source or tests.

Do not include internal implementation names, test selectors, diffs or a
precomputed verdict. CLI, API and infrastructure capabilities can be user
surfaces when a real operator observes them. A charter is an expectation,
not proof that the candidate behaved correctly.

## Host-owned evidence and reuse

Keep adequate unchanged product authority and prior charter evidence when still
applicable; changed facts require the owning role's current result, not a
hand-edited generated document. EXAMINE receives the public contract, charter
and actual observations for its independent user-view assessment.
The host captures observations and retains candidate/currentness evidence.
No separate charter directory grammar, session-log writer or progress ledger
is introduced by this skill.
