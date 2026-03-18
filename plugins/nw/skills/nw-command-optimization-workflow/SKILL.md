---
name: nw-command-optimization-workflow
description: Step-by-step workflow for converting bloated command files to lean declarative definitions
disable-model-invocation: true
---

# Command Optimization Workflow

## Overview

Convert oversized commands (500-2400 lines) to lean declarative definitions (40-300 lines) by removing duplication, extracting domain knowledge to agents, and adopting the forge.md pattern.

## Phase 1: Analyze

1. **Classify**: dispatcher, orchestrator, or simple
2. **Measure**: `wc -l` the file
3. **Identify content categories** (approximate %): parameter parsing/validation | Workflow/orchestration logic | Agent prompt templates | Examples/documentation | Error handling | Boilerplate (orchestrator briefing, agent registry)
4. **Flag reducible content**: Duplication from other commands (orchestrator briefing, agent registry, parameter parsing) | Domain knowledge belonging in agents (TDD phases, review criteria, methodology) | Dead code (deprecated formats, aspirational features, old signatures) | Verbose examples (JSON blocks exceeding 3 examples) | Aggressive language (count CRITICAL/MANDATORY/MUST)

## Phase 2: Extract

### 2a: Remove shared boilerplate
These blocks appear in 5-12 commands, extract to shared orchestrator preamble skill:
- "Sub-agents have NO ACCESS to Skill tool" briefing (~20-30 lines/file)
- Agent registry with capabilities (~15-20 lines/file)
- Parameter parsing rules (~10-15 lines/file)
- Pre-invocation validation checklist (~10-15 lines/file)
- "What NOT to include" blocks (~8-12 lines/file)

After extraction, command references preamble.

### 2b: Move domain knowledge to agents
If command contains HOW the agent works, move to agent definition or skill:
- TDD phase details -> nw-software-crafter | DIVIO templates -> nw-documentarist | Refactoring hierarchies -> nw-software-crafter | BDD/Gherkin -> nw-acceptance-designer | Review criteria -> reviewer agent | Mutation testing config -> nw-software-crafter

Command retains WHAT and success criteria. Agent owns HOW.

### 2c: Delete dead content
Remove: deprecated format references | Aspirational unimplemented features | Verbose JSON contradicting current format | BUILD:INJECT placeholders | Mixed-language comments

### 2d: Reduce aggressive language
- "CRITICAL: You MUST extract..." -> "Extract..."
- "MANDATORY: Use the Task tool" -> "Use the Task tool"
- "NON-NEGOTIABLE requirement" -> Remove adjective entirely

### 2e: Condense examples
Keep 2-3 canonical examples max. Each demonstrates distinct pattern (correct usage, edge case, common mistake).

## Phase 3: Restructure

Apply declarative command template (load `command-design-patterns` skill):
1. Header: wave, agent, overview
2. Context files required
3. Agent invocation with configuration
4. Success criteria
5. Next wave handoff
6. Expected outputs

For orchestrators, add Phases section between overview and agent invocation.

## Phase 4: Validate

- [ ] Under size target (dispatchers: 40-150, orchestrators: 100-300)
- [ ] No duplicated boilerplate
- [ ] No domain knowledge belonging in agents
- [ ] No aggressive language (CRITICAL/MANDATORY/MUST count = 0)
- [ ] 2-3 examples max
- [ ] No dead code or deprecated references
- [ ] Declarative structure (WHAT not HOW)
- [ ] Measurable success criteria
- [ ] Clear agent invocation pattern

## Phase 5: Measure and Report

Report before/after: Line count (target 60-80% reduction for large files) | Content categories removed/moved | Aggressive language removed | Dependencies created (shared preamble, agent skill additions)

## Special Case: develop.md (Mega-Orchestrator)

develop.md at 2,394 lines requires special handling:
1. Embeds 6+ sub-command workflows inline
2. Should reference sub-commands, not embed them
3. Orchestration logic (phase sequencing, resume) is legitimate -- keep it
4. Agent prompt templates for sub-commands -> replace with references
5. Target: 200-300 lines of pure orchestration

Approach: extract orchestration phases as lean sequence (which agent, which command, what context, what gate), remove all embedded sub-command content.

## Shared Orchestrator Preamble

Extract common orchestrator knowledge to single shared skill:
- Architectural constraint about sub-agent tool access
- Valid agent list with brief capabilities
- Standard parameter parsing rules
- Pre-invocation validation pattern
- Correct/wrong invocation examples (2 each)

Estimated: ~60-80 lines. Replaces ~620 lines duplicated across commands.
