---
name: nw-agent-evals
description: Lightweight eval method for testing nWave AGENTS and SKILLS (LLM behavior) as a lean alternative to heavy BDD/ATD. An eval = one prompt -> one captured run (trace + artifacts) -> a small set of checks -> a comparable score over time. Load when validating agent behavior, building a regression net for an agent/skill, or reducing agent-test bloat.
user-invocable: false
disable-model-invocation: true
---

# Agent Evals

## Why this exists

Agents are LLMs — non-deterministic. Traditional BDD/unit testing tests them *badly* and breeds bloat (measured: 294K test LOC, 5.5:1 test:src, step reuse 1.10x vs >=4x target). Evals are the lean way to verify agent behavior: a few targeted signals instead of a monolithic spec.

This skill is the **antithesis of ATD over-specification**. Keep it small. The anti-pattern is up-front exhaustive specification — that IS the bloat.

| | `nw-agent-testing` (sibling skill) | `nw-agent-evals` (this skill) |
|---|---|---|
| Form | static 5-layer manual checklist | executable dataset + grader + score over time |
| Use | one-shot design review of a spec | repeatable regression net for behavior |
| Output | pass/fail judgement | comparable score, trend across runs |

Use both: `nw-agent-testing` to vet the spec, `nw-agent-evals` to watch behavior over time.

## What an eval is

One eval = **prompt -> run -> checks -> score**.

- **prompt** — a single input that should (or should NOT) trigger the agent/skill.
- **run** — one provider turn through the selected nWave adapter, with its
  available native evidence and artifacts captured.
- **checks** — a small set of targeted assertions (not one monolithic check).
- **score** — a comparable number you can track across runs to catch regressions.

Replaces "vibes" with measurable signals: *did it invoke the right skill, run
the expected tools, respect the conventions and produce the required observable
effect?* Never grade a terminal-text grammar as a behavioral outcome.

## Definition of Done — before you write the eval

Write the success criteria FIRST, before implementing the agent/skill or its eval. Four check categories:

| Category | Question | Graded by |
|---|---|---|
| OUTCOME | Did the task complete through its required public effect and evidenced semantic result? | deterministic |
| PROCESS | Was required skill delivery or use evidenced, with only behavior-relevant tool observations? | deterministic |
| STYLE | Does the output respect nWave conventions (sections, format)? | model-graded |
| EFFICIENCY | No useless commands / no token blowup? | deterministic |

If you cannot state DoD before writing the skill, the skill's job is not yet defined — stop and define it.

## Workflow

Run these steps in order:

1. **Define success first** — write a small set of falsifiable checks in the
   four categories above.
2. **Use one representative probe when needed** — capture the provider-native
   evidence that the selected adapter actually exposes.
3. **Add only the cases needed** — include a positive case and a relevant
   negative control; grow the set from observed failures.
4. **Grade deterministic evidence** — check public effects, admitted tool
   evidence, and structured artifacts. Do not derive a verdict from terminal
   prose.
5. **Grade semantic quality separately** — use the existing rubric facility;
   retain narrative feedback as diagnostic evidence, not terminal control input.

## Capturing provider evidence

The selected adapter owns the provider projection. Claude roles run through
the Claude adapter; Codex roles run through the Codex adapter's `codex exec`
projection. Do not substitute one provider's trace shape, tool names, or
launcher for the other's.

Distinguish these three facts when evaluating a skill:

| Fact | Evidence | What it establishes |
|---|---|---|
| **Preloaded knowledge** | The role declares the skill in frontmatter and `load_role_instructions` materializes it in the provider instruction. | The role received the skill before the turn. It creates no native `Read` event. |
| **Native read** | A provider-native tool event reads a conditional `SKILL.md` path. Claude's existing transcript tracker records this form. | The turn fetched that file on demand. It does not prove that the knowledge affected the result. |
| **Actual use** | A predicted, observable effect or a capability-specific tool/result is present, with no simpler explanation. | The role applied the skill sufficiently for this eval. A catalog entry, preload, or `Read` alone is insufficient. |

Evaluate semantic results and public effects separately from their presentation.
Terminal prose, stdout, stderr, recorder entries and native tool traces carry
diagnostic/provenance evidence, not interchangeable proof of a durable effect.
Use the selected host's native transcript/tool receipts rather than another parser.
Inspect only events and recorder evidence
that its adapter preserves. If the required observation is absent on the
selected provider, report that check as **INDETERMINATE**; do not infer it from
another projection.

Check an artifact on disk as well as its reported tool event. Only ask for a
tool when the behavior requires it. Tool order and an exact command sequence
are not general quality signals.

## Deterministic graders (nWave-native signals)

Parse the trace, assert mechanically. nWave-specific, high-value signals:

| Signal | Assertion | Why it matters |
|---|---|---|
| Declared preload | resolved role instruction contains the declared skill once | verifies delivery of resident knowledge, not its use |
| Conditional read | native `Read` event for the resolved skill path, where the provider exposes one | verifies on-demand fetch, not semantic use |
| Capability-specific behavior | required public effect or justified tool/result is present | tests actual application of the skill |
| Semantic outcome observed | the semantic result and required public effect are evidenced | separates judgment from presentation |
| Artifact content | the required document contains the accepted facts | checks durable outcome rather than a completion claim |
| Efficiency | compare only a measured, relevant excess such as duplicate calls | avoids arbitrary ceilings |
| Negative control | the unsupported behavior or unnecessary skill effect is absent | guards against over-eager invocation |

Bind to the code-fact CLI where useful: e.g. assert the agent invoked `code-fact query.callers-of` rather than relying on a catalog entry (catalogued != wired). Note that feature-level change-scope analysis has no stable CLI today — an eval must not demand a capability the production CLI does not expose, or it grades the tooling rather than the agent.

## Qualitative grader (model-graded rubric)

For STYLE / design-quality / review-quality, use the existing rubric facility.
Keep each check single-purpose: identity, pass/fail judgement and evidence-located
notes; retain the overall judgement and comparable score in the harness-owned
result. Models supply judgements, not serialized rubric templates or terminal
grammars. The harness owns result structure and recording; unavailable recording
capability is **INDETERMINATE**, not permission to ask a role to print a data object.

When behavior under eval supplies a DESIGN decision, evaluate two linked
observations: the values satisfy the Request, and the resulting authority
contains them. Preserve one current authority rather than a competing ADR or
brief. Revisions preserve unaffected facts; unsuccessful changes must not
silently replace accepted authority.

For an EXAMINE eval, preserve the source-blind boundary. Give the examiner the
available observation packet, not source access; an absent observation remains
**INDETERMINATE** rather than becoming an inferred pass or failure.

## Dataset

Use the smallest CSV dataset that covers the observed positive behavior and a
relevant negative control. Minimum columns:

```csv
id,prompt,should_trigger,expected_skill,expected_observation,notes
ev-01,"Describe design facts for X",true,nw-design-patterns,"decision satisfies Request; resulting authority contains its facts",explicit
ev-07,"Just fix this typo",false,,,"negative control - no design facts"
```

- Mix: explicit-invocation, implicit-from-description (does `description` alone trigger it?), contextual, and NEGATIVE-CONTROLS (`should_trigger=false`).
- `name` + `description` are the PRIMARY invocation signal — implicit rows test exactly that.
- Coverage grows from real failures, never speculatively.

## Where evals live

```
tests/evals/<agent-or-skill-name>/
  dataset.csv          # the prompt set
  rubric.json          # model-graded rubric (JSON-Schema)
  README.md            # DoD + how to run
  runs/                # captured transcripts + scores per run (gitignored or pruned)
```

Reuse the existing `tests/evals/` facility; do not create a new general
harness. Keep raw provider records out of committed bloat unless a test needs a
small, scrubbed fixture.

## Principles

1. **Define success before you write the skill** — no DoD, no skill.
2. **Small targeted checks beat monolithic ones** — many cheap signals catch regressions early; one giant assertion hides them.
3. **Every manual fix is a future eval** — coverage is earned from observed failures.
4. **Negative controls are mandatory** — an agent that fires when it shouldn't is as broken as one that doesn't fire.
5. **name + description are the invocation contract** — test them, don't bypass them with explicit invocation only.
6. **Least privilege** — eval graders are read-only over traces + artifacts.
7. **Stay lean** — over-specifying up front recreates the ATD bloat this method exists to avoid.

## Example: eval for `nw-solution-architect`

DoD — the architect supplies valid semantic design facts and their resulting
authority. When structural code facts are necessary and obtainable, they are
provider-labelled and support the decision. A completion claim alone establishes
neither valid content nor the durable effect.

Dataset rows (excerpt):

```csv
id,prompt,should_trigger,expected_skill,expected_observation,notes
sa-01,"Describe design facts for the handoff-state-algebra feature",true,nw-design-patterns,"decision satisfies Request; resulting ADR contains its facts",design
sa-02,"What ADRs exist for the gate layer?",true,,"provider-labelled code facts support the answer when code facts are needed",lookup
sa-03,"Rename this variable to camelCase",false,,,negative control - not an architecture task
```

Deterministic grader (over the captured trace + artifact):

- DELIVERY: the role's resolved instruction contains the declared preload once;
  a conditional native read is checked only when this case requires it.
- OUTCOME: the design facts satisfy the requested decision.
- OUTCOME: the declared ADR contains accepted facts, observed through the
  actual consumer surface.
- EVIDENCE: when structural analysis is necessary, its provider and confidence
  labels support the decision; do not demand a fixed shell spelling or order.
- NEGATIVE (sa-03): no architecture facts or durable-design production occurs.

Model-graded rubric (STYLE/quality):

| Check | Example judgement | Evidence note |
|---|---|---|
| Context states the problem | Pass | Clear problem framing in the generated ADR |
| Decision is singular | Pass | One owned decision addresses the supplied gap |
| Consequences quantify trade-offs | Fail | Trade-offs remain qualitative |

These are rubric judgements, not a role-output template. The harness constructs
the stored result; terminal notes alone establish no recorded outcome.

Score = deterministic checks (binary, weighted) + rubric `score`, tracked per
comparable run. A missing required fact, generated document, or relevant supporting
observation flags a regression; unavailable evidence is reported as
**INDETERMINATE**.
