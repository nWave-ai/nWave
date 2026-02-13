---
name: review-criteria
description: Review dimensions and bug patterns for journey artifact reviews
---

# Review Criteria Skill

Domain knowledge for product-owner-reviewer (Eclipse). Covers journey coherence, emotional arcs, shared artifacts, example data quality, and CLI UX pattern validation.

## Review Dimensions

### Journey Coherence
Validate complete flow with no gaps.

Checks:
- All steps from start to goal defined
- No orphan steps disconnected from flow
- No dead ends without continuation or completion
- Decision branches lead somewhere
- Error paths guide to recovery

Severity: critical = missing steps in main flow / dead ends. High = orphan steps / unclear connections. Medium = ambiguous flow at decision points. Low = minor clarity improvements.

### Emotional Arc
Validate emotional design quality.

Checks:
- Emotional arc defined (start/middle/end)
- All steps have emotional annotations
- No jarring transitions (positive to negative without warning)
- Confidence builds progressively
- Error states guide rather than frustrate

Severity: critical = no emotional arc / major jarring transitions. High = missing annotations on key steps. Medium = confidence doesn't build progressively. Low = minor emotional polish.

### Shared Artifact Tracking
Validate ${variable} sources and consistency.

Checks:
- All ${variables} have documented source
- Each source is single source of truth (not duplicated)
- All consumers listed for each artifact
- Integration risks assessed (HIGH/MEDIUM/LOW)
- Validation methods specified

Severity: critical = undocumented ${variables} / multiple sources for same data. High = missing consumers / unassessed risks. Medium = incomplete validation methods. Low = missing minor consumer documentation.

### Example Data Quality
The key review skill -- analyze data for integration gaps.

Checks:
- Data is realistic, not generic placeholders
- Data reveals integration dependencies
- Data would catch version mismatches
- Data would catch path inconsistencies
- Data is consistent across steps

Severity: critical = generic placeholders hide integration issues. High = data inconsistent across steps. Medium = data doesn't reveal dependencies. Low = data could be more realistic.

How to apply this superpower:
1. "If I trace this ${version} through all steps, is it the same?"
2. "If I compare ${install_path} in step 2 vs step 3, do they match?"
3. "Does the example data show the actual integration points?"

Generic data like "v1.0.0" or "/path/to/install" hides bugs. Realistic data like "v1.2.86" from "pyproject.toml" reveals bugs.

### CLI UX Patterns
Validate CLI design consistency.

Checks:
- Command vocabulary consistent across journey
- Help conceptually available
- Error messages guide to resolution
- Progressive disclosure respected

Severity: critical = inconsistent command patterns. High = no error recovery guidance. Medium = missing progressive disclosure. Low = minor vocabulary inconsistency.

## Four Bug Patterns

### Pattern 1: Version Mismatch
Multiple version sources. Trace ${version} through all steps -- same source?
```
Step 1: v${version} from pyproject.toml
Step 2: v${version} from version.txt  <-- MISMATCH
```

### Pattern 2: Hardcoded URLs
URLs without canonical source. For each URL, ask "where is this defined?"
```
Install: git+https://github.com/org/repo
<-- Where is this URL canonically defined?
```

### Pattern 3: Path Inconsistency
Paths from different sources. Trace ${path} variables -- same source?
```
Install to: ${install_path} from config
Uninstall from: ~/.claude/agents/nw/  <-- HARDCODED
```

### Pattern 4: Missing Commands
CLI commands without slash command equivalents. For each action, check both contexts exist.
```
Terminal: crafter run
Claude Code: /nw:execute  <-- EXISTS?
```

## Review Output Schema

```yaml
review_id: "{timestamp}"
reviewer: "nw-product-owner-reviewer (Eclipse)"
artifact_reviewed: "{file path}"

strengths:
  - strength: "{Positive aspect}"
    example: "{Specific evidence}"

issues_identified:
  journey_coherence:
    - issue: "{Description}"
      severity: "critical|high|medium|low"
      location: "{Where}"
      recommendation: "{Fix}"
  emotional_arc:
    - issue: "{Description}"
      severity: "critical|high|medium|low"
      location: "{Where}"
      recommendation: "{Fix}"
  shared_artifacts:
    - issue: "{Description}"
      severity: "critical|high|medium|low"
      artifact: "{Which ${variable}}"
      recommendation: "{Fix}"
  example_data:
    - issue: "{Description}"
      severity: "critical|high|medium|low"
      data_point: "{Which data}"
      integration_risk: "{What bug it might hide}"
      recommendation: "{Fix}"
  bug_patterns_detected:
    - pattern: "version_mismatch|hardcoded_url|path_inconsistency|missing_command"
      severity: "critical|high"
      evidence: "{Finding}"
      recommendation: "{Fix}"

recommendations:
  critical: ["{Must fix before approval}"]
  high: ["{Should fix before approval}"]
  medium: ["{Fix in next iteration}"]
  low: ["{Consider for polish}"]

approval_status: "approved|rejected_pending_revisions|conditionally_approved"
approval_conditions: "{If conditional, what must be done}"
```

## Approval Criteria

- **approved**: No critical issues, no high issues
- **conditionally_approved**: No critical, some high that can be addressed quickly
- **rejected_pending_revisions**: Critical issues exist, or multiple high issues
