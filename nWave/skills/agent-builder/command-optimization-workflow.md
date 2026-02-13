---
name: command-optimization-workflow
description: Step-by-step workflow for converting bloated command files to lean declarative definitions
---

# Command Optimization Workflow

## Overview

Convert oversized command files (500-2400 lines) to lean declarative definitions (40-300 lines) by removing duplication, extracting domain knowledge to agents, and adopting the forge.md pattern.

## Phase 1: Analyze

1. **Classify the command**: dispatcher, orchestrator, or simple
2. **Measure current size**: `wc -l` the file
3. **Identify content categories** (approximate percentages):
   - Parameter parsing/validation
   - Workflow/orchestration logic
   - Agent prompt templates
   - Examples/documentation
   - Error handling
   - Boilerplate (orchestrator briefing, agent registry, etc.)
4. **Flag reducible content**:
   - Content duplicated from other commands (check for orchestrator briefing block, agent registry, parameter parsing rules)
   - Domain knowledge that belongs in agent definitions (TDD phases, review criteria, methodology details)
   - Dead code (deprecated formats, aspirational features, old signatures)
   - Verbose examples (JSON state blocks that exceed 3 examples)
   - Aggressive language markers (count CRITICAL/MANDATORY/MUST occurrences)

## Phase 2: Extract

Work through these extraction targets in order:

### 2a: Remove shared boilerplate

These blocks appear in 5-12 commands and should be extracted to a shared orchestrator preamble skill:
- "Sub-agents have NO ACCESS to Skill tool" briefing (~20-30 lines per file)
- Agent registry with capabilities (~15-20 lines per file)
- Parameter parsing rules (~10-15 lines per file)
- Pre-invocation validation checklist (~10-15 lines per file)
- "What NOT to include" blocks (~8-12 lines per file)

After extraction, the command references the preamble rather than embedding it.

### 2b: Move domain knowledge to agents

If a command contains HOW the agent should do its work, move that content to the agent definition or an agent skill:
- TDD phase details -> nw-software-crafter agent/skill
- DIVIO templates -> nw-documentarist agent/skill
- Refactoring hierarchies -> nw-software-crafter agent/skill
- BDD/Gherkin syntax -> nw-acceptance-designer agent/skill
- Review criteria -> reviewer agent/skill
- Mutation testing config -> nw-software-crafter agent/skill

The command retains WHAT to do and success criteria. The agent owns HOW.

### 2c: Delete dead content

Remove without replacement:
- Deprecated format references (old step file paths, v1.0 schemas)
- Aspirational features not yet implemented (execution metrics, queue management)
- Verbose JSON examples that contradict the current format
- BUILD:INJECT placeholders
- Mixed-language comments

### 2d: Reduce aggressive language

Replace emphasis markers with direct statements:
- "CRITICAL: You MUST extract..." -> "Extract..."
- "MANDATORY: Use the Task tool" -> "Use the Task tool"
- "NON-NEGOTIABLE requirement" -> Remove the adjective entirely

### 2e: Condense examples

Keep 2-3 canonical examples maximum. Each example should demonstrate a distinct pattern (correct usage, edge case, common mistake to avoid).

## Phase 3: Restructure

Apply the declarative command template (load `command-design-patterns` skill):
1. Header: wave, agent, overview
2. Context files required
3. Agent invocation with configuration
4. Success criteria
5. Next wave handoff
6. Expected outputs

For orchestrators, add a Phases section between overview and agent invocation, describing the coordination flow.

## Phase 4: Validate

Checklist for optimized commands:

- [ ] File is under size target (dispatchers: 40-150, orchestrators: 100-300)
- [ ] No duplicated boilerplate (orchestrator briefing, agent registry, etc.)
- [ ] No domain knowledge that belongs in agents
- [ ] No aggressive language (CRITICAL/MANDATORY/MUST count = 0)
- [ ] 2-3 examples maximum
- [ ] No dead code or deprecated references
- [ ] Declarative structure (WHAT not HOW)
- [ ] Success criteria are measurable
- [ ] Agent invocation pattern is clear

## Phase 5: Measure and Report

Report before/after:
- Line count (target: 60-80% reduction for large files)
- Content categories removed/moved
- Aggressive language instances removed
- Dependencies created (shared preamble, agent skill additions)

## Special Case: develop.md (Mega-Orchestrator)

develop.md at 2,394 lines is the largest command. It requires special handling:

1. It embeds 6+ sub-command workflows inline (mutation-test, refactor, execute, etc.)
2. It should reference sub-commands rather than embed them
3. The orchestration logic (phase sequencing, resume handling) is legitimate orchestrator content -- keep it
4. The agent prompt templates embedded for each sub-command should be replaced with references to the actual command files
5. Target: 200-300 lines of pure orchestration logic

Approach: extract the orchestration phases as a lean sequence (which agent, which command, what context to pass, what gate to check), and remove all embedded sub-command content.

## Shared Orchestrator Preamble

Extract common orchestrator knowledge to a single shared skill that commands can reference. This skill contains:
- The architectural constraint about sub-agent tool access
- Valid agent list with brief capability descriptions
- Standard parameter parsing rules
- Pre-invocation validation pattern
- Correct/wrong invocation examples (2 each)

Estimated size: ~60-80 lines. Replaces ~620 lines of duplicated content across all commands.
