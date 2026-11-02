---
name: nw-doc-as-artifact
description: Use briefs and HTML as shared reading surfaces for human understanding and collaborative review.
user-invocable: false
disable-model-invocation: true
---

# Human document projection

The feature's current authority is the source; Markdown briefs and HTML
are generated reading surfaces. Never write a second competing narrative, edit
the generated output by hand, or use an external URL as the only authority.
Publication is optional and separate; never upload automatically.

## Render the current authority

Render full briefs and HTML from the feature's current authority with the
available renderer; use its supported options rather than reconstructing
an obsolete invocation.
Keep source identity and the resulting local paths with the review evidence.
Inspect the rendered page and diagnostics before reporting success; an
unavailable renderer is a concrete gap, not a new workflow gate.

There is no wave-entry preference or density setting to read. Rendering does
not establish wave completion, verification, publication or human approval.
Do not invent a separate wave document, a completion event or an HTML success
when rendering failed. Preserve the source and report the actual failure.

## Facilitate with the view

Use the view during product refinement when it helps the conversation or the
human asks. Honor an explicitly chosen alternative reading surface. Do not
generate an extra view whose only consumer is software.

The Product Owner's semantic values should make intent, actors, journeys,
relevant states, examples, decisions and open questions understandable before
formal detail. Resolve product meaning before rendering the shared view.
Keep summaries brief, unresolved questions visibly open and each fact in its appropriate record.

Document language follows `nw-human-collaboration`. Include stable references
to prototypes and mechanically rendered scenarios and make clear which were
reviewed. Explain unfamiliar terms on first use. If the human cannot explain
or challenge a consequence, return the semantic correction to the PO before
rendering again; styling cannot repair ambiguous requirements.

Share the local HTML path and discuss one meaningful topic at a time.
Regenerate the same projection after authority changes. Do not claim a view
is current without rendering the current authority. No custom LLM-authored
renderer, new ledger or progression gate is needed.
