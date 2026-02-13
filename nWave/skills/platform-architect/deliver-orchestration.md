---
name: deliver-orchestration
description: DELIVER wave orchestration workflow -- 9 phases from baseline to finalization. Load when user invokes *deliver command. Covers state tracking, smart skip logic, retry, resume, and quality gate enforcement.
---

# DELIVER Wave Orchestration

When invoked via `*deliver "{feature-description}"`, Apex orchestrates the complete DELIVER wave lifecycle.

## Orchestration Role

Parse feature description, derive project ID, and execute 9 phases in order. Track state for resume capability.

**Invocation**: `*deliver "Implement user authentication with JWT tokens"`

## 9 Phases

### Phase 1-2: Baseline Creation + Review
- Create: `docs/feature/{project-id}/baseline.yaml`
- Reviewer: @nw-software-crafter-reviewer
- Smart skip: yes (if file exists AND `validation.status == "approved"`)

### Phase 3-4: Roadmap Creation + Dual Review
- Create: `docs/feature/{project-id}/roadmap.yaml`
- Reviewer 1: @nw-product-owner-reviewer (business validation)
- Reviewer 2: @nw-software-crafter-reviewer (technical validation)
- Sequential reviews
- Smart skip: yes (if approved)

### Phase 5-6: Split + Review Each Step
- Define steps in: `docs/feature/{project-id}/roadmap.yaml`
- Reviewer: @nw-software-crafter-reviewer (per roadmap step)
- Smart skip: yes (if all approved)

### Phase 7: Execute All Steps
- For each step: invoke `@nw-software-crafter` with step ID
- Automatic dependency ordering (topological sort via Kahn's algorithm)
- 11-phase TDD per step (PREPARE through COMMIT)
- Local commit after each step (no push)
- Stop immediately if any step fails

### Phase 8: Finalize
- Archive to: `docs/evolution/{timestamp}_{project-id}.md`
- Clean up workflow files

### Phase 9: Report Completion
- Display comprehensive statistics
- List all quality gates passed
- Show next steps (review evolution doc, push commits, proceed to DEVOP wave validation)

## Smart Skip Logic

- File exists AND `validation.status == "approved"` --> skip creation, load for context
- File exists but not approved --> skip creation, proceed directly to review
- File missing --> create new artifact

## Quality Gates

| Gate | Reviews | Reviewer |
|------|---------|----------|
| Baseline | 1 | nw-software-crafter-reviewer |
| Roadmap | 2 | nw-product-owner-reviewer + nw-software-crafter-reviewer |
| Step files | N (per step) | nw-software-crafter-reviewer |
| TDD phases | 2N (per step) | REVIEW + POST-REFACTOR REVIEW |

**Total reviews per feature**: 3 + 3N (where N = number of steps)

## Retry Logic

- Max 2 attempts per review
- Rejected: regenerate artifact with feedback, retry review
- Rejected after 2 attempts: stop workflow, require manual intervention

## Stop-on-Failure Policy

- Any review fails after 2 attempts --> stop entire workflow
- Any step execution fails --> stop entire workflow
- User fixes issue manually, re-runs `*deliver` (resumes from failure point)

## State Tracking

Progress tracked in `docs/feature/{project-id}/.deliver-progress.json`:

```json
{
  "project_id": "user-authentication",
  "started_at": "2025-01-13T10:30:00",
  "last_updated": "2025-01-13T12:45:00",
  "completed_phases": ["Phase 1", "Phase 2"],
  "current_phase": "Phase 3",
  "failed_phase": null,
  "failure_reason": null,
  "completed_steps": ["01-01", "01-02"],
  "failed_step": null,
  "skip_flags": {
    "baseline": true,
    "roadmap": false,
    "split": false
  },
  "orchestration_complete": false
}
```

## Resume Capability

On re-invocation:
1. Load `.deliver-progress.json`
2. Skip completed phases
3. Resume from failure point or current phase

## Post-Completion

After DELIVER wave completes:
1. All code committed locally (one commit per step)
2. Evolution document created in `docs/evolution/`
3. User reviews commits and evolution document
4. User pushes commits: `git push`
5. Validate production readiness: `*validate-completion`
