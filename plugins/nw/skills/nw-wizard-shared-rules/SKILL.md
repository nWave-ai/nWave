---
name: nw-wizard-shared-rules
description: Shared rules for feature ID derivation and wave detection used by /nw-new, /nw-continue, and /nw-fast-forward wizards
user-invocable: false
disable-model-invocation: true
---

# Wizard Shared Rules

Shared rules referenced by `/nw-new`, `/nw-continue`, and `/nw-fast-forward` wizards.

## Feature ID Derivation

Derive a kebab-case feature ID from the feature description:

1. Strip common prefixes: "implement", "add", "create", "build"
2. Remove English stop words: "a", "the", "to", "for", "with", "and", "in", "on", "of"
3. Convert to kebab-case (lowercase, hyphens between words)
4. Limit to 5 hyphenated segments maximum

**Examples:**
- "Add rate limiting to the API gateway" → `rate-limiting-api-gateway`
- "OAuth2 upgrade" → `oauth2-upgrade`
- "Implement a real-time notification system with WebSocket support for mobile and desktop clients" → `real-time-notification-system-websocket`

## Wave Detection Rules

Check SSOT first, then feature delta:

| Wave | Complete When | In Progress When |
|------|--------------|-----------------|
| DISCOVER | `docs/product/jobs.yaml` has a validated job for this feature | `docs/feature/{id}/discover/` exists but no validated job in SSOT |
| DISCUSS | `docs/feature/{id}/discuss/user-stories.md` exists and is non-empty | `docs/feature/{id}/discuss/` exists but user-stories.md missing or empty |
| DESIGN | `docs/product/architecture/brief.md` has a section for this feature | `docs/feature/{id}/design/` exists but brief.md not updated |
| DEVOPS | `docs/product/kpi-contracts.yaml` has contracts for this feature | `docs/feature/{id}/devops/` exists but no KPI contracts in SSOT |
| DISTILL | `tests/acceptance/{id}/` has feature files | `docs/feature/{id}/distill/` exists but test files incomplete |
| DELIVER | `docs/feature/{id}/deliver/execution-log.json` with all roadmap steps at COMMIT/PASS | `docs/feature/{id}/deliver/execution-log.json` exists with some steps incomplete |

"Not started" = neither SSOT entry nor feature delta directory exist for that wave.
