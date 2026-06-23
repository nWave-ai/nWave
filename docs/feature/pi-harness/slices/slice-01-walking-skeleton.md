# Slice 01 — Walking skeleton: bare-`pi` crafter + live DES extension

**Goal (one sentence):** After installing nWave-for-pi, a bare `$ pi` session can load `/skill:software-crafter` and the DES extension fires on tool calls into the existing audit log.

## IN scope
- nWave installer pi plugin set (mirrors `codex_*`/`opencode_*`): installs the pi extension + the software-crafter skill files; manifest-tracked.
- pi extension contributes the crafter skill path via `resources_discover`.
- pi extension subscribes to `tool_call`/`tool_result` and bridges to the Python DES adapter (promoted from SPIKE-0) — logging only, no gates yet.
- Clean uninstall.

## OUT scope
- Any blocking decision (slices 02–03).
- `Step-Id` commit provenance (slice 03).

## Learning hypothesis
**Disproves** "pi can host the crafter + DES adapter" if the skill won't load in bare `pi`, command completion doesn't surface it, or the extension can't stay attached across a real session. **Confirms** the end-to-end plumbing if a tool call in a `/skill:software-crafter` session produces an audit-log entry.

## Acceptance criteria
- `$ pi` (no options) → `/skill:software-crafter` appears in completion and loads.
- A tool call in that session produces a DES audit-log entry (existing JSONL surface).
- `nwave install`/`uninstall` for pi adds/removes all artifacts per manifest.

## Production-data requirement
Demo against a real local repo + the real adapter — not a synthetic harness.

## Effort / reference class
≈ 2–3 days. Reference: existing OpenCode shim slice (`opencode_des_plugin.py` + TS shim).

## Dependencies
SPIKE-0 GREEN.
