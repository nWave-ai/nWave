# Technology Stack: Wizard Commands

**Feature**: wizard-commands
**Date**: 2026-02-21

## Stack Summary

No new technologies introduced. This feature uses the existing nWave task file infrastructure exclusively.

## Technology Decisions

| Component | Technology | License | Rationale |
|-----------|-----------|---------|-----------|
| Command files | Markdown with YAML frontmatter | N/A (plain text) | Matches all 18 existing nWave commands |
| User interaction | Claude Code conversational interface | N/A (existing platform) | NFR-01 requires conversational text, not menus |
| Filesystem scanning | Claude Code Read/Glob/Grep tools | N/A (existing platform) | Wave detection requires listing directories and checking file existence |
| Wave dispatch | Claude Code command invocation (/nw:{wave}) | N/A (existing platform) | Existing dispatch mechanism used by all wave commands |

## What Is NOT Used

| Rejected Technology | Reason |
|--------------------|--------|
| Python scripts for wave detection | Constraint: no new Python code; detection logic is simple enough to express as markdown instructions |
| JSON/YAML configuration for recommendation rules | Over-engineering; decision tree is < 15 rules, readable as prose |
| Separate shared-logic file | No include/import mechanism for markdown task files; inline duplication is acceptable for < 30 lines |
| New agent definitions | Constraint: wizard runs as main Claude instance |

## File Format Conventions

### Frontmatter Schema

```yaml
---
description: "One-line description for command listing"
argument-hint: "[usage pattern] - Optional flags and examples"
disable-model-invocation: true  # Wizard runs as main instance, not via Task tool
---
```

### Body Structure

Follows the pattern observed across all existing task files:
- H1 title: `# NW-{NAME}: {Description}`
- Metadata: Wave, Agent (or "Main Instance"), Command
- Overview section
- Behavior flow (numbered steps with clear conditionals)
- Error handling section
- Success criteria (checkbox format)
- Examples section
