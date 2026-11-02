---
name: nw-abr-critique-dimensions
agent: nw-agent-builder-reviewer
description: Review dimensions for validating agent quality - template compliance, safety, testing, and priority validation
user-invocable: false
disable-model-invocation: true
---

# Agent Quality Critique Dimensions

Use these dimensions when reviewing or validating agent definitions.

## Dimension 1: Template Compliance

Does the agent follow official Claude Code format?

**Check**: YAML frontmatter with name and description (required) | Markdown body as system prompt | No embedded YAML config blocks | No activation-instructions or IDE-FILE-RESOLUTION sections | Skills referenced in frontmatter, not inline

**Severity**: High -- non-compliant agents may not load correctly.

## Dimension 2: Size and Focus

**Check**: Core definition under 400 lines | Domain knowledge in Skills | Single clear responsibility | No monolithic sections (>50 lines without structure) | No redundant Claude default behaviors

**Measurement**: `wc -l {agent-file}`. Target: 200-400 lines.

**Severity**: High -- oversized agents suffer context rot.

## Dimension 3: Divergence Quality

Does the agent specify only what diverges from Claude defaults?

**Check**: No file operation instructions | No generic quality principles ("be thorough") | No tool usage guidelines | Core principles are domain-specific and non-obvious | Each instruction justifies why Claude wouldn't do this naturally

**Severity**: Medium -- redundant instructions waste tokens, cause overtriggering.

## Dimension 4: Safety Implementation by Construction (GDP-0)

Which producer could make the unsafe action unrepresentable — did the spec construct it away, or reach for a check?

**Check**: Tools restricted via frontmatter `tools` field | maxTurns set | permissionMode set for risky actions | provider-enforced structured outcome used only for ephemeral semantic IPC | terminal prose never parsed as control input | durable handovers/documents produced by existing CLI/software from authority and observable effects | any hook present only as last resort with a recorded reason | No embedded enterprise safety frameworks

**Severity**: High -- prose safety is ineffective and token-wasteful.

## Dimension 5: Language and Tone

**Check**: No "CRITICAL:", "MANDATORY:", "ABSOLUTE" language | Direct statements ("Do X" not "You MUST X") | Affirmative phrasing ("Do Y" not "Don't do X") | Consistent terminology | No repetitive emphasis

**Severity**: Medium -- aggressive language causes overtriggering on Opus 4.6.

## Dimension 6: Examples Quality

**Check**: 3-5 canonical examples present | Cover critical/subtle decisions (not obvious cases) | Good/bad paired where useful | Concise (not full implementations)

**Severity**: Medium -- missing examples cause edge case failures.

## Dimension 7: Skill Loading Effectiveness

Does each skill reach the role exactly once, at the right time?

**Check**: Apply the source-aware Skill addressing procedure in `nw-agent-creation-workflow` to the actual candidate surface | Every frontmatter skill exists, is always needed and is not reloaded by the body | Each conditional skill has a precise reachable trigger in the single generated index | No handwritten loading section or duplicate directive.

**Severity**: High — a missing declared asset, intended conditional knowledge with no reachable trigger, a repeated preload, or a duplicate index. An installed project's missing build-time registry is a source-capability limit, not an orphan finding. The absence of a duplicate body Load directive for a frontmatter skill is correct.

## Dimension 8: Token Efficiency

Is the agent definition compressed without losing semantic content?

**Check**: No verbose prose where pipe-delimited lists suffice | Imperative voice throughout | No filler words ("in order to", "it is important to") | `### Example N:` headers preserved verbatim (not inlined) | AskUserQuestion options preserved with numbered descriptions | Code blocks preserved verbatim | No duplicate content already in skills

**Severity**: Medium — bloated definitions waste context window and degrade performance via context rot.

**Compression safe**: prose descriptions, bullet lists, related items -> pipe-delimited
**Compression unsafe**: example headers, code blocks, decision tree options, YAML frontmatter

## Dimension 9: Priority Validation

**Questions**: 1. Is this the largest bottleneck? (Evidence required) | 2. Simpler alternatives considered? | 3. Constraint prioritization correct? | 4. Architecture data-justified?

**Severity**: High if agent addresses secondary concern while larger problem exists.

## Review Result Boundary

Evaluate every dimension and cite concrete findings in diagnostic prose. In a
managed invocation, the caller may request a provider-enforced ephemeral
semantic outcome; it must not ask the model to print YAML, JSON, headings or a
verdict grammar. Findings remain semantic review evidence. Any durable review
projection is materialized by existing CLI/software, never by the reviewer.

## Failure Conditions

Review is not acceptable if: any high-severity dimension fails | 3+ medium-severity fail | Agent exceeds 400 lines without Skills extraction | Zero examples provided
