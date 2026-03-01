---
description: "Archives a completed feature to docs/evolution/ and cleans up workflow files. Use after all implementation steps pass and mutation testing completes."
disable-model-invocation: true
argument-hint: '[agent] [feature-id] - Example: @platform-architect "auth-upgrade"'
---

# NW-FINALIZE: Feature Completion and Archive

**Wave**: CROSS_WAVE
**Agent**: @nw-platform-architect (default) or specified agent

## Overview

Finalize a completed feature: verify all steps done|create evolution document in docs/evolution/|clean up workflow files in docs/feature/{feature-id}/|optionally generate reference docs. Agent gathers project data|analyzes execution history|writes summaries|archives|cleans up.

## Usage

```
/nw:finalize @{agent} "{feature-id}"
```

## Context Files Required

- docs/feature/{feature-id}/deliver/roadmap.json - Original project plan
- docs/feature/{feature-id}/deliver/execution-log.json - Step execution history (Schema v2.0)

## Pre-Dispatch Gate: All Steps Complete

Before dispatching, verify all steps are done — prevents archiving incomplete features.

Parse execution-log.json, verify every step has status DONE. If any step is not DONE, block finalization and list incomplete steps with current status. Do not dispatch until all steps complete.

## Agent Invocation

@{agent}

Finalize: {feature-id}

**Key constraints:**
- Create evolution document in docs/evolution/YYYY-MM-DD-{feature-id}.md
- Archive workflow files, do not delete before user approval
- Verify all steps DONE before proceeding
- Update architecture doc statuses from "FUTURE DESIGN" to "IMPLEMENTED"
- Optionally invoke /nw:document for reference docs (skip with --skip-docs)
- Commit and push evolution document after approval

## Phases

Agent handles: gather project data|analyze completion stats|write evolution document|archive to docs/evolution/|clean up workflow files (after user approval)|update architecture docs|commit.

## Success Criteria

- [ ] All steps verified DONE before dispatch
- [ ] Evolution document created in docs/evolution/
- [ ] User approved summary before cleanup
- [ ] Workflow directory cleaned up
- [ ] Architecture docs updated to "IMPLEMENTED" status
- [ ] Evolution document committed and pushed

## Error Handling

| Error | Response |
|-------|----------|
| Invalid agent name | "Invalid agent. Available: nw-researcher, nw-software-crafter, nw-solution-architect, nw-product-owner, nw-acceptance-designer, nw-platform-architect" |
| Missing feature ID | "Usage: /nw:finalize @agent 'feature-id'" |
| Project directory not found | "Project not found: docs/feature/{feature-id}/" |
| Incomplete steps | Block finalization, list incomplete steps |

## Examples

### Example 1: Standard finalization
```
/nw:finalize @nw-platform-architect "auth-upgrade"
```
Verifies all steps done, invokes nw-platform-architect with "Finalize: auth-upgrade". Agent reads project files, creates docs/evolution/2026-02-08-auth-upgrade.md, requests cleanup approval, commits.

### Example 2: Architect summary
```
/nw:finalize @nw-solution-architect "microservices-migration"
```
Same flow but nw-solution-architect provides architecture-focused evolution summary.

### Example 3: Blocked by incomplete steps
```
/nw:finalize @nw-platform-architect "data-pipeline"
```
Pre-dispatch gate finds step 02-03 status IN_PROGRESS. Returns: "BLOCKED: 1 incomplete step - 02-03: IN_PROGRESS. Complete all steps before finalizing."

## Next Wave

**Handoff To**: Feature complete - no next wave
**Deliverables**: docs/evolution/YYYY-MM-DD-{feature-id}.md, cleaned docs/feature/{feature-id}/

## Expected Outputs

```
docs/evolution/YYYY-MM-DD-{feature-id}.md
Updated architecture docs (status -> IMPLEMENTED)
Cleaned docs/feature/{feature-id}/ directory
```
