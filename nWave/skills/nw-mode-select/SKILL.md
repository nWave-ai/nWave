---
name: nw-mode-select
description: Choose or change how to collaborate with the human for the current scope; reuses human-collaboration guidance without runtime gates.
user-invocable: true
argument-hint: '[interactive | final human review | full delegation] [scope]'
---

# Collaboration mode

Load `nw-human-collaboration` before answering, from the host skill catalog or
the source `nWave/skills/nw-human-collaboration/SKILL.md`. That skill owns the
collaboration choices and their meaning; this command is their public entry point.

Use the current request and conversation to identify the scope and any explicit
collaboration preference. Preserve that preference without asking again. A user
can change it for the current scope without restarting the session.

If no preference is established, offer the choices from `nw-human-collaboration`,
favoring interactive collaboration. Explain the consequence of each briefly and
ask one question using context, recommendation, options, and a direct question.
Silence does not select full delegation.

State the selected collaboration mode and its scope in ordinary language. Return
to the current conversation or authorized work; invoking this command alone does
not start implementation or delegate work. If the user only asks about modes,
explain them without requiring a selection.

Collaboration preference and task size are distinct. The LLM still evaluates
S/M/L and applicable waves from evidence; this command supplies no size-to-route
mapping. For delivery orchestration guidance, use `nw-auto` when applicable.

Do not emit machine markers, inspect transcripts to establish permission, create
mode state/configuration files, invoke a tool to set a mode, or add tool gates.
This command is optional: it is not an activation prerequisite. Existing scope,
quality obligations, independent review, and applicable EXAMINE remain in force.
