# E7 — install registration walking skeleton (ADR-CA-006 D6/D7/O-4).
#
# The rewrite engine (E1-E6) is built and green. This slice is what makes it
# FIRE in production: install must register a Bash commit-attribution hook in
# ~/.claude/settings.json, gated by attribution.enabled, COEXISTING with the
# existing DES Bash execution-log guard (append, never replace).
#
# Driving port: the install plugin lifecycle over a sandboxed ~/.claude. The
# observable is the settings.json hooks.PreToolUse array CONTENT — whether
# Claude Code then fires the registered hook is the manual release smoke
# (O-2/O-3), out of CI scope.

@walking_skeleton @driving_port @real-io @contract-shape:bounded-change
Feature: Installing nWave registers the commit-attribution hook alongside the guard

  Background:
    Given a sandboxed nWave home where the commit guard is already registered

  Scenario: A fresh install with attribution enabled registers the commit-attribution hook
    Given the operator has chosen to enable attribution
    When nWave is installed
    Then the commit-attribution hook is registered for Bash commands
    And the existing commit guard is still registered
