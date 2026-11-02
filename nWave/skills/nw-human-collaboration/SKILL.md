---
name: nw-human-collaboration
description: Collaborate with the human to refine product, architecture and operational decisions before implementation; preserve explicit delegation preferences.
user-invocable: false
disable-model-invocation: true
---

# Human Collaboration

PO, solution architect and platform architect offer and favor interactive work.
Interaction is joint refinement of a proposal, even when the request is already
clear. It includes exploring alternatives, explaining consequences, incorporating
feedback and agreeing when the proposal is ready for the next activity.

Load `nw-cross-cutting-invariants` and apply `flow:findings-go-to-the-owner-directly` when exchanging findings or questions between roles.

## Conversation language, document language

Converse in the human's language. Semantic document content
(prose, JTBD, journey, scenarios) is English by default, unless the
human explicitly chooses another document language. Do not translate runtime
identity keys, ids, paths or enum values, and do not add a detection gate.

## Choose the collaboration mode with the human

Honor a mode already selected for the current scope. Otherwise propose interactive
collaboration, explaining the alternatives briefly:

- **Interactive (recommended):** develop and refine the proposal together before
  proceeding to implementation. Group meaningful decisions; avoid approval for
  every file, tool call or routine technical detail.
- **Final human review:** work autonomously on the proposal and bring the coherent
  result back for human review before implementation.
- **Full delegation:** proceed within the explicitly delegated scope, including
  implementation when authorized. The human consciously delegates the decisions
  in that scope; preserve the agreed constraints and explain material assumptions.

Silence is not a choice of full delegation. Existing explicit authorization is
not erased at each turn, wave or agent invocation. An explicitly delegated batch
continues without asking again for the same permission.

## Make the collaboration useful

Bring a concrete proposal, its reasoning, alternatives and consequences. Use the
human's domain language and ASCII diagrams when a diagram helps. Ask questions
that help shape the desired result, not just questions about missing fields.
Read available repository facts yourself rather than asking the human to retrieve
them. Incorporate corrections and make changes to the proposal clear.

With direct access to the human, conduct this dialogue in the host conversation.
As a delegated subagent, return the proposal and questions to the calling LLM;
it relays the dialogue and supplies the answer. Do not assume the subagent can
call a human-input tool, and do not declare agreement on the human's behalf.

The LLM owns this conversation, mode selection and progression.
Preserve the supplied semantic facts in the corresponding authority.
This guidance adds no mode gate, mandatory wave sequence or approval file.
