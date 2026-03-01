---
name: shared-artifact-tracking
description: Shared artifact registry, common artifact patterns, and integration validation. Load when tracking data that flows across journey steps or validating horizontal coherence.
---

# Shared Artifact Tracking

## Purpose

Shared artifacts are data values appearing in multiple places across a journey. Every ${variable} must have a single source of truth and documented consumers. Untracked artifacts are the primary cause of horizontal integration failures.

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
Source: `pyproject.toml` | Consumers: CLI --version, about command, README, install output
Risk: HIGH -- version mismatch breaks user trust

### Install Path
Source: `config/paths.yaml` or `constants.py` | Consumers: install script, uninstall script, documentation
Risk: HIGH -- path mismatch breaks installation

### Repository URL
Source: `pyproject.toml` or config | Consumers: README, error messages, install docs
Risk: MEDIUM -- URL mismatch breaks external links

### Configuration Values
Source: config file or environment variable | Consumers: runtime behavior, documentation, defaults display
Risk: MEDIUM -- inconsistency causes confusion

### Command Names
Source: CLI argument parser definition | Consumers: help text, documentation, error messages, tutorials
Risk: HIGH -- name mismatch makes features undiscoverable

## Integration Validation

### Consistency Check Process
1. List all shared artifacts from journey schema
2. For each artifact, verify source of truth exists
3. For each consumer, verify it references correct source
4. Flag any artifact without documented source
5. Flag any consumer that hardcodes instead of referencing source

### Validation Questions
- "Does every ${variable} in TUI mockups have a documented source?"
- "If the version changes, would all consumers automatically update?"
- "Are there hardcoded values that should reference a shared artifact?"
- "Do any two steps display the same data from different sources?"

### Quality Gates

Journey completeness: all steps have clear goals | CLI commands/actions | emotional annotations | shared artifacts tracked | integration checkpoints defined

Emotional coherence: emotional arc defined (start/middle/end) | no jarring transitions | confidence builds progressively | error states guide to resolution

Horizontal integration: all shared artifacts have single source of truth | all consumers documented | integration checkpoints validate consistency | CLI vocabulary consistent

CLI UX compliance: command structure follows chosen pattern | help available on all commands | progressive disclosure implemented | error messages actionable

## Handoff Specifications

### To Requirements Crafting (internal handoff within Luna)
Artifacts: `docs/feature/{feature-id}/discuss/journey-{name}.yaml` (complete journey with emotional arc) | `docs/feature/{feature-id}/discuss/shared-artifacts-registry.md` (tracked artifacts with sources)

Validation: journey complete with all steps | emotional arc defined | shared artifacts documented | CLI vocabulary consistent

### To Acceptance Designer (Quinn)
Deliverables: `docs/feature/{feature-id}/discuss/journey-{name}.yaml` (journey schema) | `docs/feature/{feature-id}/discuss/journey-{name}.feature` (Gherkin scenarios) | `docs/feature/{feature-id}/discuss/shared-artifacts-registry.md` (integration validation points)

Validation: all product-owner checks passed | Gherkin scenarios generated | integration checkpoints testable | peer review approved
