---
name: nw-agent-testing
description: "Tests agents across 5 layers: output quality, integration, adversarial, security, and prompt injection resistance. Use when validating agent behavior or hardening agents against misuse."
user-invocable: false
disable-model-invocation: true
---

# Agent Testing Framework

## 5-Layer Testing Approach

### Layer 1: Output Quality (Unit-Level)

Validate agent produces correct, well-structured outputs for typical inputs.

**Test**: Agent follows workflow phases | Outputs match expected format/structure | Domain-specific rules correctly applied | Token efficiency within bounds

**How**: Manual invocation with representative inputs. Check against acceptance criteria in agent description.

### Layer 2: Integration / Handoff Validation

Validate correct input/output between agents in workflows.

**Test**: Input parsing handles upstream format | Output format matches downstream expectations | Error signals propagate correctly | Subagent mode activation works (skip greet, execute autonomously)

**How**: End-to-end workflow execution through full agent chain (e.g., DISCUSS -> DESIGN -> DELIVER).

### Layer 3: Adversarial Output Validation

Challenge validity of agent outputs rather than accepting at face value.

**Test**: Source verification (cited sources real and accurate?) | Bias detection (favors one approach without evidence?) | Edge case coverage | Completeness (required sections present?)

**How**: Peer review by `-reviewer` agent using structured critique dimensions.

### Layer 4: Adversarial Verification (Peer Review)

Independent review to catch biases and blind spots in agent design.

**Test**: Definition follows validation checklist? | Redundant Claude default instructions? | Over/under-specified? | Could simpler agent achieve same results?

**How**: `@nw-agent-builder` validates via 11-point checklist or `@agent-builder-reviewer` runs structured review.

### Layer 5: Security Validation

Test resilience against misuse and prompt injection.

**Test**: Tool restriction enforcement | maxTurns respected | Permission mode correctly scoped | Agent stays within declared scope

**How**: Frontmatter fields enforce at platform level. Verify configuration.

## Prompt Injection Resistance

Claude Code platform provides injection resistance through: subagent isolation (own context, no sub-subagents) | Tool restriction via frontmatter `tools` | Permission modes via `permissionMode` | Hook-based validation (PreToolUse, PostToolUse)

Do NOT add prose-based injection defense. Configure platform features:

```yaml
---
tools: Read, Glob, Grep           # Only tools this agent needs
maxTurns: 30                       # Prevents runaway execution
permissionMode: default            # User approves dangerous actions
---
```

## Security Validation Checklist

- [ ] `tools` restricted to minimum necessary (least privilege)
- [ ] `maxTurns` set to prevent runaway execution
- [ ] `permissionMode` appropriate for risk level
- [ ] No `Bash` unless agent requires command execution
- [ ] No `Write` unless agent creates/modifies files
- [ ] Description accurately describes scope
- [ ] Subagent mode handles autonomous execution correctly
- [ ] No sensitive data hardcoded in definition

## Testing Workflow for New Agents

1. **Create** with minimal definition
2. **Layer 1**: Invoke with 2-3 representative inputs, check outputs
3. **Layer 2**: Run in workflow chain if applicable
4. **Fix** failures observed
5. **Validate**: Run 11-point checklist
6. **Iterate**: Add instructions only for observed failure modes
