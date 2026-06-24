# SPIKE Decisions — pi-kata-tdd-flow

## Assumption Tested
Given a synthesized CC-protocol transcript (4 DES markers) + real cwd on a real git repo, does the UNCHANGED subagent-stop adapter ALLOW a complete step and BLOCK an incomplete one — with zero src/des change?

## Probe Verdict
WORKS. Complete → SUBAGENT_STOP_PASSED / allow; incomplete → SUBAGENT_STOP_FAILED / stdout {"decision":"block"}. src/des CLEAN. KD4 synthesized-transcript route activates the gate; confirms the prior "always-allows" gap was the missing transcript+cwd context.

## Promotion Decision
DISCARD (user 2026-06-24). Findings sufficient; KD4 route proven with zero engine change; no new src/ walking-skeleton needed (pi-harness skeleton stands). Hand to DISTILL to author bootstrap / self-driven-cycle / full-kata scenarios; the 4 design constraints from findings are binding inputs.

## Design Implications
- Block delivered via stdout JSON at exit 0 (Stop-class hook), already handled by the pi extension (pi-harness 01-03).
- Exact marker fidelity required (malformed <\!-- degrades to non-DES passthrough/allow).
- Second-attempt-allow: never reuse a step id across cycles.
- Kata manifest (KD2) must set project-id/step-id/cwd so execution-log resolution + commit verification align.

## Constraints Discovered
- Commit verification fail-closed; needs a real git repo at the resolved cwd.
