# Regression — F-2 (RC-B): `des-verify-integrity --roadmap-only` flag silently
# dropped by hand-rolled `args[0]` arg parsing.
# RCA: docs/feature/fix-roadmap-json-drift/discuss/rca.md (Branch B).
#
# Pre-fix drift:
#   src/des/cli/verify_deliver_integrity.py:55-87 hand-rolled `args[0]` loop
#   treats `--roadmap-only` as the positional `project_dir`, then fails with
#   "roadmap.json not found at --roadmap-only/roadmap.json". The intended
#   behaviour (referenced in nw-deliver SKILL.md:153 as a HARD GATE before
#   crafter dispatch) is to run schema validation only, skipping the
#   execution-log cross-reference — but the flag never wires through.
#
# Post-fix (F-2):
#   The CLI uses `argparse.ArgumentParser` with positional `project_dir` and
#   boolean `--roadmap-only` flag. When set: instantiate RoadmapValidator
#   against `roadmap.json`, print errors/warnings, exit on validator verdict
#   (0=valid, 2=invalid). DO NOT read execution-log.json. When unset:
#   existing path (load both, cross-reference, integrity verify).
#
# Driving port: `des-verify-integrity` CLI invoked via subprocess.
# Driven adapter: real `roadmap.json` on tmp_path (no mocking — port-to-port).
#
# State-delta universes per Mandate Paradigm 2026-05-05:
#   A (--roadmap-only on valid roadmap, no execution-log present):
#       universe = {cli.exit_code, cli.skipped_execution_log,
#                   cli.touched_validator}
#       expected post-fix: 0 / True / True
#   B (--roadmap-only on invalid roadmap, no execution-log present):
#       universe = {cli.exit_code, cli.skipped_execution_log,
#                   cli.stdout_reports_errors}
#       expected post-fix: 2 / True / True
#   C (no flag — backward compat with both files present):
#       universe = {cli.exit_code, cli.stdout_ok}
#       expected: 0 / True (no regression, both pre- and post-fix)
#   D (unknown flag --bogus-flag):
#       universe = {cli.exit_code, cli.stderr_contains_usage}
#       expected post-fix: non-zero / True (argparse usage banner)

Feature: --roadmap-only flag validates roadmap schema without execution-log

  As a deliver orchestrator
  I need `des-verify-integrity --roadmap-only` to run RoadmapValidator only
  And to skip execution-log cross-reference
  So that the Phase 1 hard gate can verify roadmap format before any
  execution-log entries exist (because crafter dispatch has not started yet)

  @bug-roadmap-schema-drift @driving_port @rca-root-cause-B
  Scenario: Roadmap-only flag validates a well-formed roadmap with no execution-log present
    Given a feature dir with a well-formed roadmap and no execution-log file
    When the des-verify-integrity CLI runs with --roadmap-only against the feature dir
    Then the verifier exits with status 0
    And the verifier skipped reading the execution-log

  @bug-roadmap-schema-drift @driving_port @rca-root-cause-B
  Scenario: Roadmap-only flag reports schema errors and exits non-zero
    Given a feature dir with a malformed roadmap and no execution-log file
    When the des-verify-integrity CLI runs with --roadmap-only against the feature dir
    Then the verifier exits with non-zero status
    And the verifier stdout reports schema errors

  @bug-roadmap-schema-drift @driving_port @rca-root-cause-B
  Scenario: Backward compat — no flag still runs full integrity verification
    Given a feature dir with a well-formed roadmap and a complete execution-log
    When the des-verify-integrity CLI runs without --roadmap-only against the feature dir
    Then the verifier exits with status 0
    And the verifier output reports complete DES traces

  @bug-roadmap-schema-drift @driving_port @rca-root-cause-B
  Scenario: Unknown flag surfaces argparse usage banner
    Given a feature dir with a well-formed roadmap and a complete execution-log
    When the des-verify-integrity CLI runs with an unknown flag against the feature dir
    Then the verifier exits with non-zero status
    And the verifier stderr contains the argparse usage banner
