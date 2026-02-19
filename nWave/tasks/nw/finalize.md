---
description: "Archives a completed feature to docs/evolution/ and cleans up workflow files. Use after all implementation steps pass and mutation testing completes."
disable-model-invocation: true
argument-hint: '[agent] [project-id] - Example: @platform-architect "auth-upgrade"'
---

# NW-FINALIZE: Feature Completion and Archive

**Wave**: CROSS_WAVE
**Agent**: @nw-platform-architect (default) or specified agent

## Overview

Finalize a completed feature: verify all steps done, create evolution document in docs/evolution/, clean up workflow files in docs/feature/{project-id}/, and optionally generate reference documentation. The agent knows how to gather project data, analyze execution history, write summaries, archive, and clean up.

## Usage

```
/nw:finalize @{agent} "{project-id}"
```

## Context Files Required

- docs/feature/{project-id}/roadmap.yaml - Original project plan
- docs/feature/{project-id}/execution-log.yaml - Step execution history (Schema v2.0)

## Pre-Dispatch Gate: All Steps Complete

Before dispatching to agent, verify all steps are done. This prevents archiving incomplete features.

Parse execution-log.yaml and verify every step has status DONE. If any step is not DONE, block finalization and list the incomplete steps with their current status. Do not dispatch to the agent until all steps are complete.

## Agent Invocation

@{agent}

Finalize: {project-id}

**Key constraints to reinforce:**
- Create evolution document in docs/evolution/YYYY-MM-DD-{project-id}.md
- Archive workflow files, do not delete before user approval
- Verify all steps DONE before proceeding
- Update architecture doc statuses from "FUTURE DESIGN" to "IMPLEMENTED"
- Optionally invoke /nw:document for reference documentation (skip with --skip-docs)
- Commit and push evolution document after approval

## Phases

Agent handles: gather project data, analyze completion stats, write evolution document, archive to docs/evolution/, clean up workflow files (after user approval), update architecture docs, and commit.

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
| Missing project ID | "Usage: /nw:finalize @agent 'project-id'" |
| Project directory not found | "Project not found: docs/feature/{project-id}/" |
| Incomplete steps | Block finalization, list incomplete steps |

## Examples

### Example 1: Standard finalization
```
/nw:finalize @nw-platform-architect "auth-upgrade"
```
Dispatcher verifies all steps done, invokes nw-platform-architect with "Finalize: auth-upgrade". Agent reads project files, creates docs/evolution/2026-02-08-auth-upgrade.md, requests cleanup approval, commits.

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
**Deliverables**: docs/evolution/YYYY-MM-DD-{project-id}.md, cleaned docs/feature/{project-id}/

## Expected Outputs

```
docs/evolution/YYYY-MM-DD-{project-id}.md
Updated architecture docs (status -> IMPLEMENTED)
Cleaned docs/feature/{project-id}/ directory
```
