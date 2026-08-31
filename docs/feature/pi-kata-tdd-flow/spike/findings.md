# SPIKE Findings — pi-kata-tdd-flow: activate the commit gate via synthesized transcript (KD4)

**Date:** 2026-06-24 · **Agent:** Attila (nw-software-crafter) · **Method:** mechanism probe — real temp git repo + real `des-init-log`/`des-log-phase` + a synthesized CC-protocol transcript fed to the UNCHANGED `subagent-stop` adapter. (Hard gate before DISTILL per ADR-pkt-001 KD4.)

## Assumption tested (single)
Given a synthesized Claude-Code-protocol transcript (the four DES markers in the first user message) + a real `cwd`, does the UNCHANGED `subagent-stop` adapter return ALLOW for a complete step and BLOCK for an incomplete one — with zero `src/des/**` change?

## Verdict: **WORKS**

### Evidence
- **Complete step 01-01** (RED+GREEN+COMMIT phases via `des-log-phase` + a real `Step-Id`/`Task-Id`-trailered commit): adapter → audit `SUBAGENT_STOP_PASSED`, empty stdout = **ALLOW** (genuine verified allow, not the non-DES passthrough).
- **Incomplete step 02-01** (only RED, no matching commit): adapter → audit `SUBAGENT_STOP_FAILED`, stdout `{"decision":"block","reason":"STOP HOOK VALIDATION FAILED… Step: kata-fizzbuzz/02-01…"}` = **BLOCK**.
- `git diff --name-only src/des/` empty → **zero engine change** (K2 / KD4 honored).
- Confirms the pi-harness "gate always-allows" gap was precisely the missing transcript+cwd context; supplying it (KD4) activates the gate.

### Critical design notes (for DISTILL/DELIVER)
1. **Block is delivered via stdout JSON `{"decision":"block"}` at EXIT 0** — `subagent-stop` is a Stop-class hook; exit 2 would make the harness discard the JSON. The pi extension's commit branch must read the stdout decision (it already does — pi-harness step 01-03).
2. **Marker fidelity is essential** — the transcript's first user message must carry literal `<\!-- DES-VALIDATION : required -->`, `DES-PROJECT-ID`, `DES-STEP-ID`, `DES-PROJECT-ROOT`; a malformed `<\!--` silently degrades to non-DES passthrough (allow). The extension's transcript assembler must emit exact markers.
3. **Second-attempt-allow** — the service allows-despite-failure on a repeated validation of the same step (anti-infinite-loop). Fresh per-step ids (one tiny test = one step) avoid an accidental allow; DELIVER must not reuse a step id across cycles.
4. **Context resolution** — `DES-PROJECT-ROOT` marker (or `cwd` fallback) drives the execution-log resolution (`docs/feature/<project_id>/deliver/execution-log.json`) + git-trailer commit verification. The kata manifest (KD2) must set project-id/step-id/cwd consistently.

## Constraints discovered
- Commit verification is fail-closed and needs a real git repo at the resolved cwd.
- Stop-class decision channel (stdout) differs from PreToolUse (exit 2) — already handled by the shipped extension.

## Promotion decision
PIVOT/PROMOTE/DISCARD — pending gate (recommend DISCARD: findings sufficient, route proven, no new src needed; hand to DISTILL). No throwaway src/ code (temp probe under $TMPDIR).
