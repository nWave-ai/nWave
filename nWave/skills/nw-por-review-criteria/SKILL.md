---
name: nw-por-review-criteria
description: "Review dimensions and bug patterns for journey artifact reviews. Load when reviewing user journey coherence, emotional arcs, shared artifacts, or CLI UX patterns."
user-invocable: false
disable-model-invocation: true
---

# Review Criteria Skill

Domain knowledge for product-owner-reviewer (Eclipse). Covers journey coherence, emotional arcs, shared artifacts, example data quality, CLI UX patterns.

## Review Dimensions

### Journey Coherence
Validate complete flow with no gaps.

Checks: all steps start-to-goal defined | no orphan steps | no dead ends | decision branches lead somewhere | error paths guide to recovery

Severity: critical = missing main flow steps / dead ends | high = orphan steps | medium = ambiguous decisions | low = minor clarity

### Emotional Arc
Validate emotional design quality.

Checks: arc defined (start/middle/end) | all steps annotated | no jarring transitions | confidence builds progressively | error states guide not frustrate

Severity: critical = no arc / major jarring transitions | high = missing key annotations | medium = confidence doesn't build | low = minor polish

### Shared Artifact Tracking
Validate ${variable} sources and consistency.

Checks: all ${variables} have documented source | single source of truth | all consumers listed | integration risks assessed | validation methods specified

Severity: critical = undocumented ${variables} / multiple sources | high = missing consumers / unassessed risks | medium = incomplete validation | low = minor consumer docs

### Example Data Quality
Key review skill -- analyze data for integration gaps.

Checks: realistic not generic | reveals integration dependencies | catches version mismatches | catches path inconsistencies | consistent across steps

Severity: critical = generic placeholders hide issues | high = inconsistent across steps | medium = doesn't reveal deps | low = could be more realistic

Apply: 1) trace ${version} through all steps -- same? 2) compare ${install_path} step 2 vs 3 -- match? 3) does data show actual integration points?

Generic "v1.0.0" or "/path/to/install" hides bugs. Realistic "v1.2.86" from "pyproject.toml" reveals bugs.

### CLI UX Patterns
Checks: command vocabulary consistent | help available | error messages guide to resolution | progressive disclosure respected

Severity: critical = inconsistent commands | high = no error recovery guidance | medium = missing progressive disclosure | low = minor vocabulary

## Four Bug Patterns

### Pattern 1: Version Mismatch
Multiple version sources. Trace ${version} through all steps -- same source?
```
Step 1: v${version} from pyproject.toml
Step 2: v${version} from version.txt  <-- MISMATCH
```

### Pattern 2: Hardcoded URLs
URLs without canonical source. For each URL: "where is this defined?"
```
Install: git+https://github.com/org/repo
<-- Where is this URL canonically defined?
```

### Pattern 3: Path Inconsistency
Paths from different sources. Trace ${path} -- same source?
```
Install to: ${install_path} from config
Uninstall from: ~/.claude/agents/nw/  <-- HARDCODED
```

### Pattern 4: Missing Commands
CLI commands without slash equivalents. Check both contexts exist.
```
Terminal: crafter run
Claude Code: /nw-execute  <-- EXISTS?
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

- **approved**: No critical, no high issues
- **conditionally_approved**: No critical, some high addressable quickly
- **rejected_pending_revisions**: Critical issues exist, or multiple high
