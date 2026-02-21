# Shared Artifacts Registry: Wizard Commands

**Epic**: wizard-commands
**Date**: 2026-02-21

## Artifact Registry

| Artifact | Type | Single Source | Producers | Consumers | Validation |
|----------|------|---------------|-----------|-----------|------------|
| `feature_description` | string | User input in /nw:new Step 2 | User | Classify step, project ID derivation, wave command argument | Non-empty, min 10 characters |
| `project_id` | string (kebab-case) | Derived from `feature_description` | /nw:new wizard logic | `docs/feature/{project_id}/` path, all wave commands | Unique in docs/feature/, kebab-case, max 5 words |
| `feature_type` | enum | Wizard classification in /nw:new Step 3 | /nw:new wizard | DISCUSS wave `feature_type` config | One of: user-facing, backend, infrastructure, cross-cutting |
| `project_state` | enum | Auto-detected from filesystem | /nw:new artifact scan | Recommendation logic | One of: greenfield, brownfield |
| `readiness_level` | enum | User answers in /nw:new Step 2 | User + wizard inference | Wave recommendation, research_depth config | One of: needs-discovery, needs-requirements, ready-for-design |
| `wave_progress_map` | object | Artifact scanning in /nw:continue | /nw:continue scan logic | Status display, wave recommendation | Maps wave names to completion status |
| `recommended_wave` | enum | Wizard recommendation logic | /nw:new or /nw:continue | Command dispatch | One of: discover, discuss, design, devops, distill, deliver |
| `wave_configuration` | object | Assembled from classification + detection | /nw:new wizard | Target wave command configuration block | Matches target wave's expected config schema |
| `last_modified_timestamps` | map | File system metadata | /nw:continue scan | Multi-project ordering | Valid ISO timestamps, one per project |
| `resume_context` | object | .develop-progress.json + execution-log.yaml | DELIVER wave state files | /nw:continue DELIVER resume | Contains last_step, failure_point |

## Integration Checkpoints

1. **project_id uniqueness**: Before launching a wave, verify `docs/feature/{project_id}/` does not already exist (or handle the conflict).
2. **wave_configuration schema**: The configuration object assembled by the wizard must match what the target wave command expects (feature_type, walking_skeleton, research_depth for DISCUSS; no extra keys for DESIGN).
3. **resume_context validity**: When resuming DELIVER, verify that execution-log.yaml and .develop-progress.json are consistent (last completed step in log matches progress file).
4. **artifact completeness**: The /nw:continue scanner must check that "complete" waves have all required artifacts (not just the directory existence).
