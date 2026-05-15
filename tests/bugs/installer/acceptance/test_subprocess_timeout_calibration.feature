# Regression — P1: pytest build-tier subprocess timeouts under contention.
# RCA: docs/feature/fix-pytest-build-tier-timeouts/discuss/rca.md
#   Root Cause A — pip-install timeout (test_install_smoke.py:51) at 120s = 1.82×
#                  the 66s serial baseline → fires SubprocessError on first
#                  parallel-contention spike (66s × 2.66× observed multiplier = 176s).
#   Root Cause B — assertion message on test_idempotent_second_run:103 includes
#                  only `stderr`, omitting `parent.name` + `stdout` → operators
#                  cannot diagnose which tutorial setup-script + which lifecycle
#                  phase produced the failure when CI cascades.
#   Root Cause C — surrounding build-tier timeouts (validate_installed_wheel.py
#                  lines 75/104/138 + test_build_dist.py lines 427/445/462/476/501
#                  + test_install_smoke.py lines 72/84) inherit the same systemic
#                  property: every subprocess invocation MUST have a timeout
#                  whose ratio over its serial baseline meets the headroom rule.
#
# Driving ports:
#   Scenario A — pytest-bdd scenario walking AST of the 3 target files via
#                `ast.parse(...).walk()`, pairing each `subprocess.run` Call's
#                `timeout=` literal with its (file:line) and the empirically
#                measured serial baseline. The property under test:
#                `forall (file, line, timeout, baseline) in targets:
#                   timeout >= baseline * HEADROOM_RATIO`
#                with HEADROOM_RATIO = 3.5 (observed parallel-contention
#                multiplier 2.66× + ~30% suite-growth/neighbour-drift safety).
#   Scenario B — pytest-bdd scenario walking the AST of
#                `tests/build/acceptance/test_tutorial_setup_scripts.py` looking
#                for the assertion at line 103 (the first-run-returncode check
#                inside `test_idempotent_second_run`). The property under test:
#                `assertion_message contains all of {"parent.name", "stdout",
#                "stderr"}` so operators have full lifecycle context.
#
# Pre-fix: scenario A finds ≥1 (file,line) pair violating the headroom rule
#          (currently the 120s pip-install at install_smoke.py:51, ratio 1.82×).
#          Scenario B finds the assertion message references only `stderr`.
#          Both raise AssertionError. Conftest auto-xfails them under @failing
#          (xfail strict=False) so the pre-fix RED signal stays loud but does
#          not block CI; the flip to XPASS the moment step 01-02 lands.
# Post-fix (step 01-02): scenario A — all timeout ratios ≥ 3.5×. Scenario B —
#          assertion message embeds `parent.name`, `stdout`, `stderr`. Both
#          XPASS; @failing markers stripped in a follow-up.

@bug-pytest-build-tier-timeouts @property-test @driving_port
Feature: Subprocess timeout headroom + tutorial diagnostic message
  Build-tier subprocess timeouts MUST survive parallel-contention spikes
  (observed multiplier 2.66× over serial baselines). Tutorial setup-script
  assertion messages MUST include enough lifecycle context to diagnose
  failures cited in the message text.

  Scenario: Property — every subprocess.run timeout has >= 3.5x headroom over its serial baseline
    Given the empirically measured serial baselines for build-tier subprocesses
    And the headroom ratio is 3.5
    When the AST of every targeted build-tier source file is walked
    Then every subprocess.run timeout literal satisfies the headroom rule

  Scenario: Property — tutorial setup-script idempotent-second-run assertion embeds lifecycle context
    Given the tutorial setup-script idempotency test at test_tutorial_setup_scripts.py
    When the AST of its first-run-returncode assertion is inspected
    Then the assertion message string references parent.name
    And the assertion message string references stdout
    And the assertion message string references stderr
