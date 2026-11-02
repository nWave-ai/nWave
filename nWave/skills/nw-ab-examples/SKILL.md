---
name: nw-ab-examples
description: "KNOWLEDGE — canonical worked examples for agent creation, migration, and command optimization. Reference for the relevant procedures; no sequence."
user-invocable: false
---

# nw-ab-examples (KNOWLEDGE)

**Kind**: KNOWLEDGE (reference). Loaded on demand by the procedure whose example it carries. No forced sequence.

### Example 1: Good V2 Agent (Specialist)
User requests agent for database migration planning.

```yaml
---
name: nw-db-migrator
description: Use for database migration planning. Designs migration strategies with rollback safety.
model: inherit
tools: Read, Glob, Grep, Bash
maxTurns: 40
skills:
  - nw-deployment-strategies
---
```

Core definition: ~150 lines (role, 5 divergent principles, 4-phase workflow, 4 critical rules, 3 examples). Domain knowledge extracted to the `nw-deployment-strategies` skill (rollback planning, ~200 lines). Total always-loaded: ~150 lines. With skill: ~350 lines.

### Example 2: Bad Monolithic Agent
2,400-line spec with embedded YAML config, 17 commands, 7-layer enterprise security framework, aggressive language.

Action: Apply migration path:
1. Extract YAML config -> frontmatter (5 lines)
2. Remove 5 "production frameworks" duplicating platform features (~400 lines saved)
3. Remove default behavior specifications (~500 lines saved)
4. Extract domain knowledge to 2-3 Skills (~800 lines moved)
5. Replace aggressive language with direct statements
6. Result: ~250 line core + 3 Skills

### Example 3: Skill Extraction Decision
Agent at 380 lines — within 400-line target. Extract Skills?

Decision tree:
- Functional and passing validation? Yes -> Ship as-is
- Clearly separable knowledge domains (>100 lines each)? Yes -> Extract for reusability
- Will grow as domain knowledge expands? Yes -> Extract now to prevent bloat
- Knowledge useful to other agents? Yes -> Extract as shared skill
Default: under 400 lines and passing validation -> do not over-engineer with premature extraction.

### Example 4: Command Optimization (Dispatcher)
User asks to optimize execute.md (1,051 lines). It's a dispatcher command.

Analysis: ~35% reducible (300 lines JSON state examples contradicting v2.0 format|200 lines duplicated parameter parsing|100 lines agent registry|deprecated references).

Action:
1. Remove JSON state examples (v2.0 uses pipe-delimited, not JSON) -- 300 lines saved
2. Extract parameter parsing to shared preamble -- 200 lines saved
3. Remove agent registry duplication -- 100 lines saved
4. Move TDD phase details to nw-software-crafter agent -- 200 lines saved
5. Restructure as declarative dispatcher using forge.md pattern
6. Result: ~120 lines (agent invocation + context extraction pattern + success criteria)

### Example 5: Command Optimization (Orchestrator)
develop.md at 2,394 lines embeds 6 sub-command workflows inline.

Action: Replace embedded workflows with phase references. Keep orchestration logic (phase sequencing, resume handling). Remove all embedded agent prompt templates. Target: 200-300 lines of pure orchestration.
