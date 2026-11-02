---
description: "nWave concierge — ask any question about methodology, project state, commands, migration, or troubleshooting. Read-only, contextual answers."
argument-hint: "[question] - Example: \"What should I do next for rate-limiting?\""
---

# NW-BUDDY: nWave Concierge

**Wave**: CROSS_WAVE | **Agent**: Guide (nw-nwave-buddy) | **Command**: `/nw-buddy`

## Overview

Ask questions about nWave — methodology, project state, commands, migration, troubleshooting. Guide reads your project and gives contextual answers.

## Agent Invocation

@nw-nwave-buddy

Execute *help to show capabilities, or ask any nWave question directly.

**Configuration:**
- model: sonnet (optimized for frequent, low-cost interactions)
- mode: read-only (never creates or modifies files)


## Success Criteria

- [ ] Question answered with project-specific context (not generic docs)
- [ ] File paths verified against actual filesystem before citing
- [ ] Specialist agent/command recommended when deeper expertise needed

## Expected Outputs

- Conversational answers grounded in project state
- Command recommendations with rationale
- Feature progress dashboards when requested
