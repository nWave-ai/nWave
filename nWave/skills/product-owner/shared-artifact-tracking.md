---
name: shared-artifact-tracking
description: Shared artifact registry, common artifact patterns, and integration validation. Load when tracking data that flows across journey steps or validating horizontal coherence.
---

# Shared Artifact Tracking

## Purpose

Shared artifacts are data values that appear in multiple places across a journey. Every ${variable} must have a single source of truth and documented consumers. Untracked artifacts are the primary cause of horizontal integration failures.

## Artifact Registry Schema

```yaml
shared_artifacts:
  {artifact_name}:
    source_of_truth: "{canonical file path}"
    consumers: ["{list of places this value appears}"]
    owner: "{responsible feature/component}"
    integration_risk: "HIGH|MEDIUM|LOW - {explanation}"
    validation: "{How to verify consistency}"
```

## Common Artifact Patterns

### Version
- Typical source: `pyproject.toml`
- Common consumers: CLI --version, about command, README, install output
- Risk: HIGH -- version mismatch breaks user trust

### Install Path
- Typical source: `config/paths.yaml` or `constants.py`
- Common consumers: install script, uninstall script, documentation
- Risk: HIGH -- path mismatch breaks installation

### Repository URL
- Typical source: `pyproject.toml` or config
- Common consumers: README, error messages, install docs
- Risk: MEDIUM -- URL mismatch breaks external links

### Configuration Values
- Typical source: config file or environment variable
- Common consumers: runtime behavior, documentation, defaults display
- Risk: MEDIUM -- inconsistency causes confusion

### Command Names
- Typical source: CLI argument parser definition
- Common consumers: help text, documentation, error messages, tutorials
- Risk: HIGH -- name mismatch makes features undiscoverable

## Integration Validation

### Consistency Check Process
1. List all shared artifacts from the journey schema
2. For each artifact, verify the source of truth exists
3. For each consumer, verify it references the correct source
4. Flag any artifact without a documented source
5. Flag any consumer that hardcodes a value instead of referencing source

### Validation Questions
- "Does every ${variable} in the TUI mockups have a documented source?"
- "If the version changes, would all consumers automatically update?"
- "Are there any hardcoded values that should reference a shared artifact?"
- "Do any two steps display the same data from different sources?"

### Quality Gates

Journey completeness:
- All steps have clear goals
- All steps have CLI commands or actions
- All steps have emotional annotations
- All shared artifacts tracked
- All integration checkpoints defined

Emotional coherence:
- Emotional arc defined (start/middle/end)
- No jarring transitions between steps
- Confidence builds progressively
- Error states guide to resolution

Horizontal integration:
- All shared artifacts have single source of truth
- All consumers documented for each artifact
- Integration checkpoints validate consistency
- CLI vocabulary consistent across journey

CLI UX compliance:
- Command structure follows chosen pattern
- Help available on all commands
- Progressive disclosure implemented
- Error messages are actionable

## Handoff Specifications

### To Requirements Crafting (internal handoff within Luna)
Luna uses these journey artifacts as input to Phase 4 (Requirements Crafting):
- `docs/ux/{epic}/journey-{name}.yaml` -- Complete journey with emotional arc
- `docs/ux/{epic}/shared-artifacts-registry.md` -- Tracked artifacts with sources

Validation checklist:
- Journey complete with all steps
- Emotional arc defined
- Shared artifacts documented
- CLI vocabulary consistent

### To Acceptance Designer (Quinn)
Deliverables:
- `docs/ux/{epic}/journey-{name}.yaml` -- Journey schema
- `docs/ux/{epic}/journey-{name}.feature` -- Gherkin scenarios
- `docs/ux/{epic}/shared-artifacts-registry.md` -- Integration validation points

Validation checklist:
- All product-owner checks passed
- Gherkin scenarios generated
- Integration checkpoints testable
- Peer review approved
