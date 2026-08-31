# Slice 01 — Self-bootstrap a DES-tracked kata session

**Goal:** Invoking the crafter with a kata in an activated pi project auto-initializes a DES execution log + first step (no manual setup).

## IN scope
- On crafter invocation with a kata, run `des-init-log` (project-dir + feature-id) and establish a first `step-id` + project-id + a session marker.
- Ensure `des-*` CLIs are reachable from pi's bash in an installed setup (G4).
- The bootstrap mechanism per DESIGN (K3): pi command vs skill-only.

## OUT scope
- Driving the TDD cycle / recording phases (Slice 02).
- Multi-step kata (Slice 03).

## Learning hypothesis
**Disproves** "a single pi agent can self-bootstrap a DES session" if the CLIs aren't reachable from pi bash, or the agent can't reliably run the bootstrap from the skill/command. **Confirms** the session-setup half of the driving layer.

## Acceptance criteria
- Invoke crafter + kata → `execution-log.json` created under the kata's deliver dir; step `01-01` announced; session marker written.
- No manual `des-init-log` required.
- Activated project only (reuses `enabled_for_repo:true`).

## Dependencies
pi-harness (extension + plugin shipped). DESIGN picks the bootstrap surface (K3).

## Effort / reference
≈ 1–2 days. Reference: `des-init-log` CLI + the `/nw-deliver` Phase-1 setup it replaces.
