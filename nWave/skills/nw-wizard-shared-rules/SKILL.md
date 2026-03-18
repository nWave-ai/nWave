---
name: nw-wizard-shared-rules
description: Shared rules for feature ID derivation and wave detection used by /nw:new, /nw:continue, and /nw:fast-forward wizards
disable-model-invocation: true
---

# Wizard Shared Rules

Shared rules referenced by `/nw:new`, `/nw:continue`, and `/nw:fast-forward` wizards.

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

For a given project (`docs/feature/{id}/`), check each wave's artifacts:

| Wave | Complete When | In Progress When |
|------|--------------|-----------------|
| DISCOVER | `docs/feature/{id}/discover/problem-validation.md` AND `docs/feature/{id}/discover/lean-canvas.md` exist and are non-empty | `docs/feature/{id}/discover/` exists but required files missing or empty |
| DISCUSS | `docs/feature/{id}/discuss/requirements.md` AND `docs/feature/{id}/discuss/user-stories.md` exist and are non-empty | `docs/feature/{id}/discuss/` exists but required files missing or empty |
| DESIGN | `docs/feature/{id}/design/architecture-design.md` exists and is non-empty | `docs/feature/{id}/design/` exists but required file missing or empty |
| DEVOPS | `docs/feature/{id}/devops/platform-architecture.md` exists and is non-empty | `docs/feature/{id}/devops/` exists but platform-architecture.md missing or empty |
| DISTILL | `docs/feature/{id}/distill/test-scenarios.md` exists and is non-empty | `docs/feature/{id}/distill/` exists but required file missing or empty |
| DELIVER | `docs/feature/{id}/deliver/execution-log.json` with all roadmap steps at COMMIT/PASS | `docs/feature/{id}/deliver/execution-log.json` exists with some steps incomplete |

"Not started" = neither directory nor required artifacts exist for that wave.
