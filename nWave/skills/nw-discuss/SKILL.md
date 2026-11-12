---
name: nw-discuss
description: Use when a product question or request must become agreed promises, sad paths, journey and slices before design or tests.
user-invocable: true
argument-hint: '<product question or outcome>'
---

# Discuss: from request to agreed product facts

The Product Owner (PO) owns product facts. The host relays human questions and runs tools. A missing human answer goes back to its owner as an open question; never fill it with your own product meaning.

## 1. Keep scope to the request

1. Copy the request unchanged at the top of the brief. Promises, actor, outcome and titles follow nw-jtbd-core.
2. Name each value's included and excluded behaviour. Anything beyond the request is a Suggestion, outside the in-scope list and the ordered values until the human selects it.
3. Reuse existing product authority only where relevant; leave delivered behaviour alone.
4. Add no gate, check or approval step unless a named consumer needs its effect.
5. Add no receipt, log, status field or marker unless something other than its producer reads it.
6. Report an independent pre-existing defect you find to its owner as an Open question. Fix it only when the human authorised it or the request's own change caused it.

## 2. Find the sad paths

Per value, list the sad paths the request states (refusal, conflict, race, stale or invalid input, missing operand). Each is its own promise with its own observable outcome, even when the expected behaviour seems settled; tests need one test per promised sad path.

Sad paths you find by exploration are proposals. Write each as a Suggestion or Open question; it becomes a promise only when the request states it or the human accepts it. List unclear order, timing or state interactions as Open questions.

Explore with bounded Quint when available:
1. Probe `quint --version`. If missing, write "exploration unavailable" for the value.
2. Run bounded `quint run` with an explicit seed and bounds; keep the command, version and raw trace.
3. Render trace events through fixed domain templates, not LLM paraphrase. Return scenarios and assumptions to the PO.
4. Record assumptions and unresolved judgments as decisions with status Open. In automatic mode they stay Open; silence is never approval.

A value with only a settled happy path may skip exploration; write that judgment and its reason per value.

## 3. Journey (when you write one)

1. The journey runs from start to goal. Every step is reachable and leads on; no orphan step, no dead end; every error step leads to a recovery step.
2. Write a step's emotion only from the human's account; else "emotion: not supplied".

## 4. Slices

1. Each slice is one behaviour a user observes alone through the real driving port. A technical layer ("the API contract", "the database table") or a mocked interaction is not a slice; fold groundwork into the thinnest slice that delivers observable value.
2. Slice 1 is the walking skeleton: the thinnest end-to-end path, through the real port and real I/O. Order the rest by dependency; each extends that path and none adds a second skeleton.
3. Per slice, state the observable result, dependencies and size.

## 5. Decisions and shared view

1. Mark every decision Confirmed, Proposed or Open, with an owner per open question. An Open question is never an agreed requirement.
2. On a human correction, replace the superseded facts, keep the unaffected facts and identities, and say what changed.
3. Brief or HTML views keep intent, actor outcomes, confirmed decisions, proposals, assumptions and open questions in separate sections. Regenerate after a change; never hand-edit generated files. Documents in English; talk to the human in theirs.

## 6. Self-check

1. The request is quoted unchanged; nothing in scope that the request does not state.
2. Each stated sad path is a promise; each explored one is a Suggestion or Open question; per-value exploration judgment is written.
3. No gate, receipt or marker without a reader; no pre-existing defect fixed unasked.
4. Journey (if any): no orphan, no dead end, errors lead to recovery, emotion only if supplied.
5. Each slice is one user-observable behaviour; one walking skeleton, extended.
6. Every decision has a status; no open assumption presented as agreed.
