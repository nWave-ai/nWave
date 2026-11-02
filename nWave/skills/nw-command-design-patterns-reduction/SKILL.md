---
name: nw-command-design-patterns-reduction
description: What is reducible in a bloated command - the duplication triangle, the anti-pattern catalog, and the compress/never-compress rules
user-invocable: false
disable-model-invocation: true
---

# Command Reduction: Duplication, Anti-Patterns, Compression (KNOWLEDGE)

**Kind**: KNOWLEDGE (reference). Composed by `nw-command-design-patterns` core. Fires when: a command is bloated and the question is "what here is reducible / what should be removed / how far can I compress" (the duplication triangle + anti-pattern + compression rules). No forced sequence.

## The Duplication Triangle

Commands duplicate content in three directions, all waste tokens:

1. **Command-to-Command**: Orchestrator briefings, agent registries, parameter parsing repeated in 5-12 files (~620 lines waste)
2. **Command-to-Agent**: Domain knowledge belonging in agents (~1,300 lines waste). Examples: TDD phases in execute.md, DIVIO templates in document.md, refactoring hierarchies in refactor.md
3. **Command-to-Self**: develop.md embeds other commands inline (~1,000 lines)

Fix: Extract shared content to preamble skill. Move domain knowledge to agents. Have orchestrators reference sub-commands.

## Anti-Patterns

| Anti-pattern | Impact | Fix |
|---|---|---|
| Procedural overload | Step-by-step for capable agents wastes tokens, "lost in the middle" | Declare goal + constraints, let agent apply methodology |
| Duplicated briefings | Same orchestrator constraints in every command (30-80 lines each) | Extract to shared preamble, reference once |
| Embedded domain knowledge | Refactoring hierarchies, review criteria, TDD cycles in commands | Move to agent definitions or skills |
| Aggressive language | "CRITICAL/MANDATORY/MUST" causes overtriggering in Opus 4.6 | Direct statements without emphasis markers |
| Example overload | 50+ lines of JSON examples | 2-3 canonical examples suffice |
| Inline validation logic | Prompt template validation in command text | Platform/hook responsibility |
| Dead code | Deprecated formats, aspirational metrics, old signatures | Remove; version control preserves history |
| Verbose JSON state examples | 200+ lines of unused JSON | Show actual format (pipe-delimited), 3 examples max |

## Compression Guidelines

When optimizing command files for token efficiency:

**Safe to compress**:

1. Prose descriptions → pipe-delimited
2. Verbose explanations → imperative voice
3. Filler words ("in order to", "it is important to") → remove
4. Related bullet items → single line with `|` separators

**Never compress**:

1. `### Example N:` section headers — keep verbatim (eval tools and agents depend on these)
2. AskUserQuestion decision tree options — these are runtime menu items, not documentation
3. `**Question**:` lines in decision points — runtime behavior
4. Code blocks and YAML — preserve verbatim
5. YAML frontmatter — preserve exactly

**Compression evidence**: Pipe-delimited compression achieves 15-30% token reduction on prose-heavy files. Code-heavy files (PBT skills, code examples) yield <5%. Average across framework: ~7.4% overall.

**Orchestrator skill loading section**: Commands dispatching sub-agents must include `SKILL_LOADING` in the Task prompt reminding the agent to read its skills at `~/.claude/skills/nw-{skill-name}/SKILL.md`. Sub-agents can invoke the Skill tool (but not slash commands), though a skill carrying `disable-model-invocation: true` stays unreachable through it and must be READ at the path above; the `skills:` frontmatter field eagerly preloads full skill content into custom subagents, so this reminder targets skills meant to load at point-of-use instead. Without it, sub-agents operate without domain knowledge.
