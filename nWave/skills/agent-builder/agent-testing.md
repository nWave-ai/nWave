---
name: agent-testing
description: 5-layer testing approach for agent validation including adversarial testing, security validation, and prompt injection resistance
---

# Agent Testing Framework

## 5-Layer Testing Approach

### Layer 1: Output Quality (Unit-Level)

Validate that the agent produces correct, well-structured outputs for typical inputs.

**What to test**:
- Agent follows its specified workflow phases
- Outputs match expected format and content structure
- Domain-specific rules are correctly applied
- Token efficiency within acceptable bounds

**How to test**: Manual invocation with representative inputs. Check output against acceptance criteria defined in the agent's description.

### Layer 2: Integration / Handoff Validation

Validate that the agent correctly receives inputs from and passes outputs to other agents in workflows.

**What to test**:
- Input parsing handles the format provided by upstream agents
- Output format matches what downstream agents expect
- Error signals propagate correctly through the chain
- Subagent mode activation works (skip greet, execute autonomously)

**How to test**: End-to-end workflow execution through the full agent chain (e.g., DISCUSS -> DESIGN -> DELIVER).

### Layer 3: Adversarial Output Validation

Challenge the validity of agent outputs rather than accepting them at face value.

**What to test**:
- Source verification: are cited sources real and accurate?
- Bias detection: does the output favor one approach without evidence?
- Edge case coverage: does the agent handle boundary inputs?
- Completeness: are required sections present?

**How to test**: Peer review by a `-reviewer` agent using structured critique dimensions.

### Layer 4: Adversarial Verification (Peer Review)

Independent review to catch biases and blind spots in the agent's design.

**What to test**:
- Does the agent definition follow the validation checklist?
- Are there redundant instructions that duplicate Claude defaults?
- Is the agent over-specified or under-specified?
- Could a simpler agent achieve the same results?

**How to test**: `@nw-agent-builder` validates using the 11-point checklist. Or: `@agent-builder-reviewer` runs structured review.

### Layer 5: Security Validation

Test the agent's resilience against misuse and prompt injection.

**What to test**:
- Tool restriction enforcement (agent only uses declared tools)
- maxTurns limit respected
- Permission mode correctly scoped
- Agent stays within its declared scope boundaries

**How to test**: Frontmatter fields enforce these at the platform level. Verify frontmatter is correctly configured.

## Prompt Injection Resistance

Claude Code's platform provides injection resistance through:
- Subagent isolation (own context window, cannot spawn sub-subagents)
- Tool restriction via frontmatter `tools` field
- Permission modes via `permissionMode` field
- Hook-based validation (PreToolUse, PostToolUse)

Agent definitions should NOT add prose-based injection defense. Instead, configure platform features:

```yaml
---
tools: Read, Glob, Grep           # Only tools this agent needs
maxTurns: 30                       # Prevents runaway execution
permissionMode: default            # User approves dangerous actions
---
```

## Security Validation Checklist

Before deploying any agent:

- [ ] `tools` field restricts to minimum necessary (least privilege)
- [ ] `maxTurns` set to prevent runaway execution
- [ ] `permissionMode` appropriate for the agent's risk level
- [ ] No `Bash` tool unless agent requires command execution
- [ ] No `Write` tool unless agent creates/modifies files
- [ ] Agent description accurately describes its scope
- [ ] Subagent mode correctly handles autonomous execution
- [ ] No sensitive data hardcoded in the agent definition

## Testing Workflow for New Agents

1. **Create** the agent with minimal definition
2. **Test Layer 1**: Invoke with 2-3 representative inputs, check outputs
3. **Test Layer 2**: Run in a workflow chain if applicable
4. **Fix** any failures observed in testing
5. **Validate**: Run 11-point validation checklist
6. **Iterate**: Add instructions only for observed failure modes
