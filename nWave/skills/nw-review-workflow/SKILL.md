---
name: nw-review-workflow
description: Detailed review process, v2 validation checklist, and scoring methodology for agent definition reviews
disable-model-invocation: true
---

# Agent Review Workflow

## V2 Validation Checklist (11 Points)

Run against every agent under review. Each item pass/fail.

1. **Frontmatter format**: `---` delimited YAML with `name` and `description`
2. **Size compliance**: Under 400 lines; domain knowledge in Skills
3. **Divergence-only**: Only behaviors diverging from Claude defaults
4. **Calm language**: No "CRITICAL", "MANDATORY", "ABSOLUTE"
5. **Examples present**: 3-5 canonical for critical/subtle behaviors
6. **Least privilege tools**: Minimum needed in frontmatter
7. **maxTurns set**: Present in frontmatter
8. **Platform safety**: Via frontmatter/hooks, not prose
9. **Affirmative phrasing**: "Do X" not "Don't do Y"
10. **Consistent terminology**: One term per concept
11. **Clear delegation**: Description states when to delegate

## Scoring Methodology

### Per-Dimension Scoring

For each of 7 critique dimensions (from critique-dimensions skill):
- **Pass**: All checks satisfied
- **Fail**: One or more checks not satisfied

### Verdict Logic

```
IF any high-severity dimension fails:
  verdict = "revisions_needed"
ELIF count(medium-severity failures) >= 3:
  verdict = "revisions_needed"
ELSE:
  verdict = "approved"
```

High-severity: template_compliance, size_and_focus, safety_implementation, priority_validation
Medium-severity: divergence_quality, language_and_tone, examples_quality

### Evidence Requirements

Every finding includes: **Dimension** (which of 7) | **Severity** (high/medium/low) | **Finding** (observed, with line numbers/counts) | **Recommendation** (specific fix action)

## Common V1 to V2 Migration Issues

| Residual Pattern | What to Flag |
|-----------------|-------------|
| Embedded YAML config blocks | Should be frontmatter or removed |
| `activation-instructions` section | Remove -- Claude Code handles activation |
| `IDE-FILE-RESOLUTION` section | Remove -- not needed in v2 |
| `commands` with 10+ entries | Reduce to 3-5 focused |
| Inline `embed_knowledge` | Extract to Skills |
| 5+ "production frameworks" | Remove -- platform handles safety |
| `CRITICAL:` prefixed instructions | Rephrase as calm direct statements |
| Python/YAML safety code examples | Remove -- aspirational, not executable |

## Peer Review Protocol

1. Receive agent file path from builder
2. Execute full dimension review
3. Return structured YAML verdict
4. If `revisions_needed`, include prioritized fix list
5. Builder revises and resubmits (max 2 iterations)
6. On second rejection, escalate to user

## Command Template Review

Additional checks for nWave command files (tasks):
- Size: 50-60 lines target; >60 warning, >150 major, >500 blocker
- Structure: agent activation metadata, context files section, success criteria
- Delegation: business logic belongs in agent, not command
- No embedded procedural steps (STEP 1, STEP 2)
