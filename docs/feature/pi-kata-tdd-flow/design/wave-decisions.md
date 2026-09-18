# DESIGN wave decisions — pi-kata-tdd-flow

> nw-solution-architect (Morgan), PROPOSE mode, 2026-06-24. Builds on the shipped
> pi-harness (`docs/product/architecture/brief.md` `## Application Architecture`,
> ADR-PI-001/002/003) and the DISCUSS spec
> (`docs/feature/pi-kata-tdd-flow/feature-delta.md`, K1–K4 LOCKED).
> Headline ADR: `docs/product/architecture/adr-pkt-001-kata-driving-and-commit-context.md`.

## Prior-wave reading checklist

| Source | Read | Note |
|--------|:----:|------|
| `docs/feature/pi-kata-tdd-flow/feature-delta.md` (DISCUSS, K1–K4) | ✓ | 3 stories, 3 slices; K1 commit-boundary strictness, K2 zero engine change, K3 deferred to DESIGN, K4 DELIVER-cycle-only scope |
| `docs/product/architecture/brief.md` (pi-harness `## Application Architecture`) | ✓ | thin TS translator + commit gate model; D6 Hybrid; contract-shape table |
| `adr-pi-001-step-completion-model.md` | ✓ | `SubagentStopService.validate()` is pure over `(elog, project, step, cwd)`; commit boundary is the trigger |
| `adr-pi-002-extension-and-installer-reuse.md` | ⊘ | not present at path; superseded content captured in brief `## Application Architecture` + DELIVER sections (read) |
| `adr-pi-003-crafter-skill-wiring.md` | ✓ | crafter = pi skill via `resources_discover` `skillPaths`; no `pi_skills_plugin` for thin slice |
| `docs/feature/pi-harness/feature-delta.md` (DELIVER sections) | ✓ | what shipped: extension full gate set, plugin, 21/22 green, commit gate wired |
| `docs/feature/pi-harness/spike/findings.md` (SPIKE-0) | ✓ | `tool_call` blocks; adapter reachable via subprocess; `DES_AUDIT_LOG_DIR` pin; activation gate |
| `findings-spike-1-driving-ports.md` (SPIKE-1) | ✓ | bash `tool_call` blockable + `input.command` inspectable; `tool_result.details.exitCode` |
| `docs/evolution/pi-harness-evolution.md` | ⊘ | not located at the given path; evolution captured across the two feature-delta files (read) |
| `nWave/templates/pi-des-extension.ts.template` (shipped) | ✓ | the EXTEND target; current `subagent-stop` spawn lacks DES context |
| `scripts/install/plugins/pi_des_plugin.py` (shipped) | ✓ | the EXTEND target; renders extension, manifest, `install_paths` resolvers |
| `src/des/cli/init_log.py` (`des-init-log`) | ✓ | `--project-dir --feature-id`; classic-mode default; reuse unchanged |
| `src/des/cli/log_phase.py` (`des-log-phase`) | ✓ | `--project-dir --step-id --phase --status --data`; reuse unchanged |
| `src/des/adapters/drivers/hooks/subagent_stop_handler.py` | ✓ | two protocols; direct → `cwd=""`; CC → reads `cwd`; marker-driven |
| `src/des/application/subagent_stop_service.py` | ✓ | commit verify only `if context.cwd`; `project_id`==`Task-Id` |
| `src/des/adapters/driven/git/git_commit_verifier.py` | ✓ | `Step-Id`+`Task-Id` `--all-match`, runs `git log` in `cwd` |
| `src/des/domain/des_marker_parser.py` (markers) | ✓ | `DES-VALIDATION/PROJECT-ID/STEP-ID/PROJECT-ROOT` regexes |
| `nWave/skills/nw-execute/SKILL.md` (OUTCOME_RECORDING + markers) | ✓ | `des-log-phase` per phase; `DES-PROJECT-ID/STEP-ID` markers; the Claude Code driving model being adapted |
| `nWave/agents/nw-software-crafter.md` + `nw-tdd-methodology/SKILL.md` | ✓ | 3-phase canon; self-decompose discipline; `Step-Id` trailer |
| `scripts/shared/install_paths.py` (spawn resolvers) | ✓ | `resolve_python_command_for_spawn` / `resolve_des_lib_path_for_spawn` |

## The four headline decisions (K3)

See ADR-PKT-001 for full alternatives + matrices. Verdicts:

| # | Decision | Verdict | One-line rationale |
|---|----------|---------|--------------------|
| D-PKT-1 | Bootstrap/driving mechanism | **Hybrid**: registered `pi.registerCommand` bootstraps (init-log + manifest + session marker), then hands to the reused crafter skill which drives + records | A single agent can't be trusted to run multi-step bootstrap from prose; a command makes it deterministic, the skill owns the open-ended loop |
| D-PKT-2 | Self-decomposition + step-id origin | **Convention + kata manifest**: `project-id` = kata id; `step-id` = `NN-NN` (`01-01`, `01-02`…) incremented per tiny test; no `roadmap.json` | Reuses the existing step-id convention without an architect; manifest is the single source of `(project-id, step-id, deliver-dir)` |
| D-PKT-3 | CLI reachability post-install | **Install-time-resolved python + PYTHONPATH** `python -m des.cli.init_log/log_phase`, via `install_paths` resolvers | Mirrors the proven adapter-spawn path; portable; avoids unconfirmed console-script-on-PATH and dev-only `PYTHONPATH=src .venv` form |
| D-PKT-4 | Commit-boundary context | **Synthesized transcript via the Claude Code protocol** (markers + `cwd`); direct protocol rejected (skips commit verify → would need engine change) | ONLY zero-engine-change route to full commit verification at the pi boundary (K2) |

## Key discovery (decisive for K2)

The shipped pi `subagent-stop` spawn passes `{cwd, tool_name, tool_input}` —
which matches **neither** engine protocol — so the commit gate currently
**always allows** (`_resolve_des_context` → `des_context is None` →
`{"decision":"allow"}`). pi-kata-tdd-flow is exactly the layer that activates it.
The activation MUST use the Claude Code protocol (synthesized transcript) because
the direct protocol returns `effective_cwd=""` and the service guards commit
verification behind `if context.cwd` — enabling it on the direct path is an
`src/des/**` change (K2 violation). The transcript route reuses the engine's own
marker parser + cwd handling verbatim.

## SPIKE recommendation

**A timeboxed SPIKE is WARRANTED** before DELIVER, on D-PKT-4 only. It is
model-free and cheap (python subprocess vs the unchanged adapter, SPIKE-0 Half-1
pattern). One probe question: *given a synthesized one-line transcript carrying
the four DES markers + a `cwd` on a real temp git repo, does the unchanged
`subagent-stop` adapter return allow/block with COMMIT_VERIFIED / COMMIT_NOT_VERIFIED
for complete vs incomplete execution-logs — with zero `src/des/**` change?* If
the probe fails, escalate to the user as a K2 upstream-issue (the direct protocol
needs `cwd`) — do NOT design the engine change.

## K2 risk flag

D-PKT-4 is the only place K2 is at risk. The chosen transcript route keeps the
engine untouched. The fallback (engine reads `cwd` in the direct protocol) is an
upstream issue to be escalated, never silently designed. All other components are
EXTEND (extension, plugin) or REUSE-UNCHANGED (DES CLIs, gate, verifier,
resolvers, crafter skill).

## Open questions for DISTILL / DELIVER

1. Confirm pi's `registerCommand` API surface in 0.79.9 (name, handler signature,
   how the command receives the kata problem text) — DELIVER source-inspection,
   same method as SPIKE-1.
2. Confirm the synthesized-transcript route end-to-end model-free (the SPIKE).
3. Manifest location + schema: a `kata-manifest.json` under the kata's deliver
   dir (`docs/feature/{kata}/deliver/`) holding `{project_id, current_step_id, cwd}`.
4. Whether `des-log-phase`'s 3-phase canon (`RED`/`GREEN`/`COMMIT`) phase names
   validate against the installed TDD schema in a standalone (non-repo) install
   (the schema loader path) — verify during DELIVER.
5. Live-model full-kata demo remains `@requires_external` (DoD item 9), as in
   pi-harness.
