# Definition of Ready Checklist: Wizard Commands

**Epic**: wizard-commands
**Date**: 2026-02-21
**Status**: PASS (all 8 items)

## DoR Validation

### 1. Problem statement clear and in domain language
**Status**: PASS

US-001: "Developer with a feature idea must understand the wave pipeline to pick the right entry point. New users default to guessing when they might need a different wave."

US-002: "After stepping away for hours or days, developers lose context on which wave they completed last. They manually inspect artifact directories and sometimes re-run completed waves."

Both statements use developer-facing language (waves, commands, artifacts) without prescribing implementation.

### 2. User/persona identified with specific characteristics
**Status**: PASS

- Kenji Nakamura: backend developer, new to nWave, has a feature idea but no pipeline knowledge
- Sofia Reyes: developer with clear requirements, needs formalization
- Elena Voronova: full-stack developer returning after time away, lost context
- Rajesh Patel: developer with partially completed DELIVER wave
- Priya Sharma: developer with vague feature idea
- Wei Zhang: developer with multiple active projects

Each persona has a specific context of use and motivation.

### 3. At least 3 domain examples with real data
**Status**: PASS

- US-001: 4 examples (Sofia/rate-limiting, Kenji/feedback-portal, Priya/vague, Tomoko/name-conflict)
- US-002: 5 examples (Elena/notification-service, Rajesh/rate-limiting-deliver, Wei/multi-project, Fatima/no-projects, Carlos/skipped-waves)
- US-003: 3 examples (Sofia/standard, Kenji/short, Priya/long-truncated)

All use real names and realistic feature descriptions.

### 4. UAT scenarios in Given/When/Then (3-7 scenarios)
**Status**: PASS

- US-001: 5 scenarios (greenfield-discuss, needs-discovery, vague-description, name-conflict, existing-requirements)
- US-002: 6 scenarios (single-project, deliver-resume, multi-project, no-projects, skipped-waves, corrupted-artifact)
- US-003: 4 scenarios (standard, short, truncated, user-override)

All in Given/When/Then format with real persona names and data.

### 5. Acceptance criteria derived from UAT
**Status**: PASS

23 acceptance criteria (AC-001 through AC-023) with full traceability table mapping each AC to its source UAT scenario. See acceptance-criteria.md.

### 6. Story right-sized (1-3 days, 3-7 scenarios)
**Status**: PASS

- US-001: 5 scenarios, estimated 2-3 days (conversational wizard with classification logic)
- US-002: 6 scenarios, estimated 2 days (artifact scanning and progress display)
- US-003: 4 scenarios, estimated 1 day (string transformation logic, subset of US-001)

No story exceeds 7 scenarios or 3 days estimated effort.

### 7. Technical notes identify constraints and dependencies
**Status**: PASS

Each story includes Technical Notes section identifying:
- Output file path (nWave/tasks/nw/new.md, continue.md)
- Convention requirements (task file frontmatter format)
- Execution model (main Claude instance, no subagent)
- Shared logic references (project ID derivation matching deliver.md)
- Dependencies (filesystem access, existing wave commands, artifact conventions)

### 8. Dependencies resolved or tracked
**Status**: PASS

Dependency map in user-stories.md shows:
- US-003 feeds into US-001 (project ID derivation)
- US-001 and US-002 both depend on existing wave commands (stable)
- US-002 depends on DELIVER resume logic (stable: .develop-progress.json, execution-log.yaml)
- No blocking dependencies -- all upstream dependencies are stable existing features

All dependencies are on stable, shipped features. No blockers.

## Summary

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Problem statement clear | PASS |
| 2 | Persona identified | PASS |
| 3 | 3+ domain examples | PASS |
| 4 | UAT in Given/When/Then | PASS |
| 5 | AC derived from UAT | PASS |
| 6 | Right-sized stories | PASS |
| 7 | Technical notes | PASS |
| 8 | Dependencies tracked | PASS |

**Verdict**: Ready for DESIGN wave handoff.
