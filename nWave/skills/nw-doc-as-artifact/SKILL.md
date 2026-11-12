---
name: nw-doc-as-artifact
description: Use briefs and HTML as shared reading surfaces for human understanding, including the readable-brief round between the documentarist and the owning roles.
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

## Readable brief: diagrams, decisions and one round of questions

Applies when `documents.readable_brief` is enabled: the role bundle or the host says so.
The diagrams and decisions below are part of the readable result, not extras.

**Diagrams.** Read `nw-diagram` before you draw or change a diagram. Before you
report a render as successful, check R1 (title in the block) and R2 (description
above the block) for every diagram of the authority. Source shown as code is not
a description. Styling cannot repair a diagram that fails these rules.

**Decisions at the source.** The role that owns a choice records it in its own
record, with its own CLI verb. Write the text as a title of at most 8 words, a
colon, then the reason: `Use one config file: two files drifted in the past`.
Product owner: product decisions. Architect: design decisions and constraints.
Platform architect: operational decisions, in the architect's design authority.
A choice with no recorded reason is not yet a decision.

**One round.** At the end of analysis the documentarist reads the current
authority and sends ONE message to each owning role. Each message has numbered
questions; each question cites a decision id or a diagram and names the gap:
missing title, missing reason, a choice the reader cannot follow, or a failed rule.
The owner answers once: it corrects or adds the decision at the source, and
replies with the id. Without direct messaging, the questions go to the caller
as `CLARIFICATION_NEEDED`. The round is not repeated. An unanswered question
is shown as open in the document.

**The documentarist presents, never decides.** It writes each decision into
the readable document citing its id, with the title and reason as recorded.
It writes no decision, changes no authority and does not fill a missing reason
from its own reading.
