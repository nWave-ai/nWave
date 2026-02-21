# Acceptance Criteria: Wizard Commands (/nw:new, /nw:continue, /nw:ff)

**Epic**: wizard-commands
**Date**: 2026-02-21
**Derived from**: User Stories US-001, US-002, US-003, US-004

## US-001: /nw:new -- Start a New Feature

- [ ] AC-001: User types `/nw:new` and receives an open-ended question about what they want to build
- [ ] AC-002: Wizard asks 2-3 clarifying questions after the feature description (new/existing, requirements readiness)
- [ ] AC-003: Wizard auto-detects greenfield (no `docs/feature/` artifacts) vs. brownfield
- [ ] AC-004: Wizard classifies feature type as one of: user-facing, backend, infrastructure, cross-cutting
- [ ] AC-005: Wizard recommends a starting wave with a human-readable rationale displayed to the user
- [ ] AC-006: Wizard derives a kebab-case project ID from the description (max 5 segments)
- [ ] AC-007: Wizard detects name conflicts with existing `docs/feature/{id}/` directories and offers resolution options
- [ ] AC-008: After user confirmation, wizard launches the recommended `/nw:{wave}` command with correct configuration
- [ ] AC-009: Vague descriptions (under 10 meaningful characters or unclassifiable) trigger follow-up questions instead of a launch

## US-002: /nw:continue -- Resume Feature Progress

- [ ] AC-010: User types `/nw:continue` and the wizard scans `docs/feature/` for project directories
- [ ] AC-011: Wizard determines wave completion status by checking required artifact files (per wave detection rules)
- [ ] AC-012: For a single project, wizard displays per-wave progress (complete / in progress / not started) and recommends the next wave
- [ ] AC-013: For multiple projects, wizard lists them ordered by last file modification timestamp and prompts selection
- [ ] AC-014: For DELIVER in progress, wizard shows step-level detail from `execution-log.yaml` (completed steps, next step)
- [ ] AC-015: When no projects exist under `docs/feature/`, wizard displays a message and suggests `/nw:new`
- [ ] AC-016: When wave artifacts are non-adjacent (e.g., DISCUSS + DELIVER but no DESIGN), wizard warns and offers options
- [ ] AC-017: When a required artifact file exists but is empty (0 bytes), wizard flags it and recommends re-running that wave

## US-003: Project ID Derivation

- [ ] AC-018: Wizard strips prefixes "implement", "add", "create", "build" from description before deriving ID
- [ ] AC-019: Wizard removes English stop words ("a", "the", "to", "for", "with", "and") from description
- [ ] AC-020: Wizard converts result to kebab-case
- [ ] AC-021: Wizard limits project ID to 5 hyphenated segments maximum
- [ ] AC-022: Wizard shows derived ID to user for confirmation before any wave launch
- [ ] AC-023: User can override the derived ID with a custom value

## US-004: /nw:ff -- Fast-Forward Through Remaining Waves

- [ ] AC-024: User types `/nw:ff` with optional description and the wizard shows the planned wave sequence
- [ ] AC-025: Wizard reuses `/nw:continue` detection logic to determine current progress
- [ ] AC-026: Wizard asks for one-time confirmation before executing the wave chain
- [ ] AC-027: Each wave executes in sequence, passing artifacts to the next wave automatically
- [ ] AC-028: Optional `--from={wave}` flag starts from a specific wave after validating prerequisites exist
- [ ] AC-029: If a wave fails mid-pipeline, execution stops with a clear error and suggests `/nw:continue`
- [ ] AC-030: DISCOVER wave is skipped by default (opt-in with `--from=discover`)

## Traceability

| AC | UAT Scenario |
|----|-------------|
| AC-001 through AC-005 | US-001 Scenario 1 (Sofia, greenfield backend) |
| AC-002, AC-009 | US-001 Scenario 3 (Priya, vague description) |
| AC-005, AC-008 | US-001 Scenario 2 (Kenji, needs discovery) |
| AC-006, AC-007 | US-001 Scenario 4 (Tomoko, name conflict) |
| AC-008 | US-001 Scenario 5 (Marcus, existing requirements) |
| AC-010 through AC-012 | US-002 Scenario 1 (Elena, single project) |
| AC-013 | US-002 Scenario 3 (Wei, multiple projects) |
| AC-014 | US-002 Scenario 2 (Rajesh, DELIVER resume) |
| AC-015 | US-002 Scenario 4 (Fatima, no projects) |
| AC-016 | US-002 Scenario 5 (Carlos, skipped waves) |
| AC-017 | US-002 Scenario 6 (Li Wei, corrupted artifact) |
| AC-018 through AC-021 | US-003 Scenarios 1-3 |
| AC-022, AC-023 | US-003 Scenario 4 (user override) |
| AC-024, AC-026, AC-027 | US-004 Scenario 1 (Marcus, full fast-forward) |
| AC-025, AC-027 | US-004 Scenario 2 (Elena, mid-pipeline fast-forward) |
| AC-028 | US-004 Scenario 3 (Rajesh, --from flag) |
| AC-029 | US-004 Scenario 4 (Sofia, wave failure) |
