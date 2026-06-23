# SPIKE Decisions — pi-harness

## Assumption Tested
- Can a pi extension intercept `tool_call`, block a production-code write, and invoke the existing Python DES adapter via subprocess (Claude Code JSON hook protocol), landing an entry in the DES JSONL audit log?

## Probe Verdict
- **WORKS**: adapter subprocess returns exit 2 + `{"decision":"block"}` + audit entry; the bridge was executed **inside the real pi runtime** (session_start self-probe → `{"bridge":"ok","exitCode":2,"blocked":true}`). pi's `tool_call`→block is a documented contract (not executed live here — no LLM backend available).

## Promotion Decision
- **PROMOTE** (2026-06-23): mechanism proven and a working extension exists to grow; build the thin walking skeleton now.

## Walking Skeleton (PROMOTED)
- Driving adapter: pi loading the nWave DES extension; `session_start` startup self-test + `tool_call` gate.
- Production artifact: `nWave/templates/pi-des-extension.ts.template` (protocol translator; zero adapter fork).
- Acceptance test: `tests/des/acceptance/pi_harness/walking-skeleton.feature` (+ steps) — model-free, drives real pi, asserts the `[nWave DES] enforcement active for pi` health line. **GREEN.**
- Demo command: `pi --no-extensions -e <rendered-ext> --offline --no-session --no-tools -p "noop"` in an activated project → prints the health line.
- Follow-up (not in skeleton): the installer plugin `pi_des_plugin.py` (render+install+manifest, mirroring `opencode_des_plugin.py`); the crafter skill wiring; the RED/GREEN/REFACTOR step-completion model (D6).

## Design Implications
- See findings.md §"Design implications" (1–7). Headlines: enforce on `tool_call`/`tool_result`; activation marker `.nwave/local-config.json:{enabled_for_repo:true}` required; pin `DES_AUDIT_LOG_DIR`; zero adapter fork holds; reuse installer interpreter/lib resolution; D6 (step-completion analog) still open; live e2e needs a model backend (CI caveat).

## Constraints Discovered
- No LLM backend in this env (no key; ollama empty). pi needs `~/.pi/agent/` write access. `$TMPDIR` differs sandboxed vs not.
