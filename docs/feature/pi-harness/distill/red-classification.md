# Pre-DELIVER fail-for-the-right-reason gate — pi-harness DISTILL

Run: `pytest tests/des/acceptance/pi_harness/` · 2026-06-23 · python `.venv` 3.14

**Result: 8 PASSED · 12 FAILED · 1 SKIPPED.** Every FAIL classified
`MISSING_FUNCTIONALITY` (correct RED). Zero `IMPORT_ERROR` / `FIXTURE_BROKEN` /
`SETUP_FAILURE` / `WRONG_ASSERTION`. The inherited `@walking_skeleton` scenario
remains GREEN and untouched.

## Classification per scenario

| Scenario | Feature | Status | Classification | Failure signal |
|----------|---------|--------|----------------|----------------|
| Starting pi in an activated project confirms DES enforcement is live | walking-skeleton | **GREEN** | n/a (inherited, untouched) | — |
| A production write is translated to the RED gate and the engine's block is relayed verbatim | extension-translation | GREEN | passes today (skeleton maps write→pre-write; engine blocks the sentinel) | — |
| An allowed write is relayed as allow | extension-translation | GREEN | passes today (engine allows non-guarded write) | — |
| A non-mutating read tool call is passed through untouched | extension-translation | GREEN | passes today (`mapTool` returns null for `read`) | — |
| A translator failure never blocks a legitimate tool call | extension-translation | GREEN | passes today (skeleton has fail-open `catch`) | — |
| The extension contains no allow or block decision of its own | extension-translation | GREEN | passes today (exactly 1 block relay gated on exit 2) | — |
| A commit tool call is translated to the step-completion validation | extension-translation | RED | `MISSING_FUNCTIONALITY` | `AssertionError: extension must map the git-commit tool call to the subagent-stop validation` — skeleton lacks the `subagent-stop` mapping (D10 gate-set growth) |
| A test-run result is translated to the suite-state recording action | extension-translation | RED | `MISSING_FUNCTIONALITY` | `AssertionError: extension must map the test-run tool_result to post-tool-use` — skeleton lacks `tool_result` subscription (D12) |
| Installing into a present pi config dir places the extension and manifest | installer-lifecycle | RED | `MISSING_FUNCTIONALITY` | `AssertionError: Not yet implemented -- RED scaffold` (pi_des_plugin.py:install) |
| Installing when pi is not present skips without failing | installer-lifecycle | RED | `MISSING_FUNCTIONALITY` | scaffold AssertionError |
| Installing before the DES library is present is refused with guidance | installer-lifecycle | RED | `MISSING_FUNCTIONALITY` | scaffold AssertionError (validate_prerequisites) |
| Verifying a completed install confirms the placed artifacts | installer-lifecycle | RED | `MISSING_FUNCTIONALITY` | scaffold AssertionError |
| Verifying before installing reports the missing extension | installer-lifecycle | RED | `MISSING_FUNCTIONALITY` | scaffold AssertionError (verify) |
| Reinstalling refreshes the extension without removing the operator's own pi files | installer-lifecycle | RED | `MISSING_FUNCTIONALITY` | scaffold AssertionError |
| Uninstalling removes every placed artifact and leaves the operator's files | installer-lifecycle | RED | `MISSING_FUNCTIONALITY` | scaffold AssertionError (uninstall) |
| Uninstalling when nothing was installed completes without error | installer-lifecycle | RED | `MISSING_FUNCTIONALITY` | scaffold AssertionError |
| Writing implementation before a failing test is blocked at the write boundary | tdd-enforcement-gates | RED | `MISSING_FUNCTIONALITY` | `AssertionError: RED gate ... must be blocked (exit 2), engine returned exit 0` — per-step RED gate wiring is DELIVER's job |
| Writing the test first is allowed | tdd-enforcement-gates | GREEN | passes today (engine allows test-file write) | — |
| Committing a step that did not complete its phases is blocked at the commit boundary | tdd-enforcement-gates | RED | `MISSING_FUNCTIONALITY` | `AssertionError: step-completion gate ... rejected (exit 2), got exit 0` — per-step commit-boundary wiring is DELIVER's job |
| Committing a step that completed its phases with a trailered commit is allowed | tdd-enforcement-gates | GREEN | passes today (subagent-stop allows by default w/o incomplete state) | — |
| A live pi model turn honors the block on a real production write | tdd-enforcement-gates | **SKIPPED** | `@requires_external` — no pi model backend in CI (SPIKE-0 R4) | `pytest.skip` |

## DELIVER reads this at RED-phase entry

The 12 RED scenarios are the one-at-a-time DELIVER backlog. Recommended order:
installer-lifecycle (scaffold → real plugin) → extension gate-set growth
(commit→subagent-stop, test-run→post-tool-use) → per-step RED/commit gate wiring.
The 8 GREEN scenarios pin already-wired contract surface (the committed skeleton +
the standing DES engine decisions) and must stay green throughout.

## Bad-RED fixes applied during authoring (now resolved)

- `NameError: re/os not defined` in `test_extension_translation_contract.py` —
  missing imports (ruff stripped them when intermediate edits left them unused).
  Fixed; re-run confirmed pure AssertionError classification.
- Thin-translator assertion initially counted `block: true` in comments
  (refactor-hostile). Rewritten to strip comments and count decision statements —
  now passes against the skeleton (correct: the skeleton IS a thin translator).
