---
name: critique-dimensions
description: Review dimensions for validating agent quality - template compliance, safety, testing, and priority validation
---

# Agent Quality Critique Dimensions

Use these dimensions when reviewing or validating agent definitions.

## Dimension 1: Template Compliance

Does the agent follow the official Claude Code format?

**Check**:
- YAML frontmatter with name and description (required)
- Markdown body as system prompt
- No embedded YAML configuration blocks
- No activation-instructions or IDE-FILE-RESOLUTION sections
- Skills referenced in frontmatter, not embedded inline

**Severity**: High — non-compliant agents may not load correctly.

## Dimension 2: Size and Focus

Is the agent appropriately sized and focused?

**Check**:
- Core definition under 400 lines
- Domain knowledge extracted to Skills
- Single clear responsibility (not a multi-purpose agent)
- No monolithic sections (>50 lines without structure)
- No redundant specification of Claude default behaviors

**Measurement**: `wc -l {agent-file}`. Target: 200-400 lines.

**Severity**: High — oversized agents suffer context rot.

## Dimension 3: Divergence Quality

Does the agent specify only what diverges from Claude defaults?

**Check**:
- No file operation instructions (Claude knows Read/Write/Edit)
- No generic quality principles ("be thorough", "be accurate")
- No tool usage guidelines (Claude knows tool conventions)
- Core principles are domain-specific and non-obvious
- Each instruction justifies why Claude wouldn't do this naturally

**Severity**: Medium — redundant instructions waste tokens and can cause overtriggering.

## Dimension 4: Safety Implementation

Is safety implemented through platform features?

**Check**:
- Tools restricted via frontmatter `tools` field
- maxTurns set in frontmatter
- No prose-based security layers (use hooks instead)
- No embedded enterprise safety frameworks
- permissionMode set if agent performs risky actions

**Severity**: High — prose safety is both ineffective and token-wasteful.

## Dimension 5: Language and Tone

Is the language appropriate for Opus 4.6?

**Check**:
- No "CRITICAL:", "MANDATORY:", "ABSOLUTE" language
- Instructions phrased as direct statements ("Do X" not "You MUST X")
- Affirmative phrasing ("Do Y" not "Don't do X")
- Consistent terminology (one term per concept)
- No repetitive emphasis on the same point

**Severity**: Medium — aggressive language causes overtriggering on Opus 4.6.

## Dimension 6: Examples Quality

Are examples effective and well-chosen?

**Check**:
- 3-5 canonical examples present
- Examples cover critical/subtle decisions (not obvious cases)
- Good and bad examples paired where useful
- Examples are concise (not full implementations)

**Severity**: Medium — missing examples cause failures on edge cases.

## Dimension 7: Priority Validation

Is the agent solving the right problem?

**Questions**:
1. Is this the largest bottleneck? (Evidence required)
2. Were simpler alternatives considered?
3. Is constraint prioritization correct?
4. Is the architecture data-justified?

**Severity**: High if the agent addresses a secondary concern while a larger problem exists.

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
    priority_validation: {pass|fail}
  issues:
    - dimension: "{dimension}"
      severity: "{high|medium|low}"
      finding: "{description}"
      recommendation: "{fix}"
  verdict: "{approved|revisions_needed}"
```

## Failure Conditions

An agent review is blocked (verdict: revisions_needed) if:
- Any high-severity dimension fails
- 3+ medium-severity dimensions fail
- Agent exceeds 400 lines without Skills extraction
- Zero examples provided
