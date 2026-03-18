---
name: nw-ab-critique-dimensions
description: Review dimensions for validating agent quality - template compliance, safety, testing, and priority validation
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

## Dimension 4: Safety Implementation

**Check**: Tools restricted via frontmatter `tools` field | maxTurns set | No prose-based security layers (use hooks) | No embedded enterprise safety frameworks | permissionMode set for risky actions

**Severity**: High -- prose safety is ineffective and token-wasteful.

## Dimension 5: Language and Tone

**Check**: No "CRITICAL:", "MANDATORY:", "ABSOLUTE" language | Direct statements ("Do X" not "You MUST X") | Affirmative phrasing ("Do Y" not "Don't do X") | Consistent terminology | No repetitive emphasis

**Severity**: Medium -- aggressive language causes overtriggering on Opus 4.6.

## Dimension 6: Examples Quality

**Check**: 3-5 canonical examples present | Cover critical/subtle decisions (not obvious cases) | Good/bad paired where useful | Concise (not full implementations)

**Severity**: Medium -- missing examples cause edge case failures.

## Dimension 7: Skill Loading Effectiveness

Does the agent ensure skills are actually loaded during execution?

**Check**: Skill Loading Strategy table present for agents with 3+ skills | Every frontmatter skill has matching `Load:` directive in workflow | Skills path documented (`~/.claude/skills/nw/{agent-name}/`) | Phase-gated loading (not "load everything at start")

**Severity**: High — orphan skills (declared but never loaded) mean sub-agents operate without domain knowledge. The `skills:` frontmatter field is declarative only; Claude Code does not auto-load skill files.

**Gold standard**: `nw-product-owner.md` — Skill Loading Strategy table mapping phases to skills with triggers + explicit `Load:` directives in each workflow phase.

## Dimension 8: Token Efficiency

Is the agent definition compressed without losing semantic content?

**Check**: No verbose prose where pipe-delimited lists suffice | Imperative voice throughout | No filler words ("in order to", "it is important to") | `### Example N:` headers preserved verbatim (not inlined) | AskUserQuestion options preserved with numbered descriptions | Code blocks preserved verbatim | No duplicate content already in skills

**Severity**: Medium — bloated definitions waste context window and degrade performance via context rot.

**Compression safe**: prose descriptions, bullet lists, related items → pipe-delimited
**Compression unsafe**: example headers, code blocks, decision tree options, YAML frontmatter

## Dimension 9: Priority Validation

**Questions**: 1. Is this the largest bottleneck? (Evidence required) | 2. Simpler alternatives considered? | 3. Constraint prioritization correct? | 4. Architecture data-justified?

**Severity**: High if agent addresses secondary concern while larger problem exists.

## Review Output Format

```yaml
review:
  agent: "{agent-name}"
  dimensions:
    template_compliance: {pass|fail}
    size_and_focus: {pass|fail}
    divergence_quality: {pass|fail}
    safety_implementation: {pass|fail}
    language_and_tone: {pass|fail}
    examples_quality: {pass|fail}
    skill_loading: {pass|fail|n/a}
    token_efficiency: {pass|fail}
    priority_validation: {pass|fail}
  issues:
    - dimension: "{dimension}"
      severity: "{high|medium|low}"
      finding: "{description}"
      recommendation: "{fix}"
  verdict: "{approved|revisions_needed}"
```

## Failure Conditions

Review blocked (verdict: revisions_needed) if: any high-severity dimension fails | 3+ medium-severity fail | Agent exceeds 400 lines without Skills extraction | Zero examples provided | Agent with 3+ skills missing Skill Loading Strategy table
