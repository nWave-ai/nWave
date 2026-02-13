---
name: review-workflow
description: Detailed review process, v2 validation checklist, and scoring methodology for agent definition reviews
---

# Agent Review Workflow

## V2 Validation Checklist (11 Points)

Run this checklist against every agent under review. Each item is pass/fail.

1. **Frontmatter format**: Uses `---` delimited YAML with `name` and `description` fields
2. **Size compliance**: Total definition under 400 lines; domain knowledge in Skills
3. **Divergence-only**: Specifies only behaviors that diverge from Claude defaults
4. **Calm language**: No "CRITICAL", "MANDATORY", or "ABSOLUTE" signaling
5. **Examples present**: 3-5 canonical examples for critical/subtle behaviors
6. **Least privilege tools**: Tools restricted to minimum needed in frontmatter
7. **maxTurns set**: `maxTurns` present in frontmatter
8. **Platform safety**: Safety via frontmatter fields and hooks, not prose paragraphs
9. **Affirmative phrasing**: "Do X" not "Don't do Y"
10. **Consistent terminology**: One term per concept throughout
11. **Clear delegation**: Description field states when to delegate to this agent

## Scoring Methodology

### Per-Dimension Scoring

For each of the 7 critique dimensions (from critique-dimensions skill):
- **Pass**: All checks within the dimension are satisfied
- **Fail**: One or more checks are not satisfied

### Verdict Logic

```
IF any high-severity dimension fails:
  verdict = "revisions_needed"
ELIF count(medium-severity failures) >= 3:
  verdict = "revisions_needed"
ELSE:
  verdict = "approved"
```

High-severity dimensions: template_compliance, size_and_focus, safety_implementation, priority_validation
Medium-severity dimensions: divergence_quality, language_and_tone, examples_quality

### Evidence Requirements

Every finding must include:
- **Dimension**: Which of the 7 dimensions
- **Severity**: high, medium, or low
- **Finding**: What was observed (with line numbers or counts)
- **Recommendation**: Specific action to fix it

## Common V1 to V2 Migration Issues

When reviewing agents that were recently migrated from v1:

| Residual Pattern | What to Flag |
|-----------------|-------------|
| Embedded YAML config blocks | Should be frontmatter or removed |
| `activation-instructions` section | Remove — Claude Code handles activation |
| `IDE-FILE-RESOLUTION` section | Remove — not needed in v2 |
| `commands` with 10+ entries | Reduce to 3-5 focused commands |
| Inline `embed_knowledge` | Extract to Skills |
| 5+ "production frameworks" | Remove — platform handles safety |
| `CRITICAL:` prefixed instructions | Rephrase as calm direct statements |
| Python/YAML code examples for safety | Remove — these are aspirational, not executable |

## Peer Review Protocol

When invoked as a peer reviewer for nw-agent-builder:

1. Receive the agent file path from the builder
2. Execute full dimension review
3. Return structured YAML verdict
4. If verdict is `revisions_needed`, include prioritized fix list
5. Builder revises and resubmits (max 2 iterations)
6. On second rejection, escalate to user

## Command Template Review

When reviewing nWave command files (tasks), apply these additional checks:

- Size: 50-60 lines target; flag >60 as warning, >150 as major, >500 as blocker
- Structure: must have agent activation metadata, context files section, success criteria
- Delegation: business logic belongs in agent, not command file
- No embedded procedural steps (STEP 1, STEP 2, etc.)
