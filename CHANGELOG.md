# Changelog

All notable changes to this project will be documented in this file.

## [1.1.13] - 2026-02-17

### Fixed
- **Deliver Phase 3 not using /nw:refactor**: The Complete Refactoring phase
  was described as a generic dispatch to @nw-software-crafter. Now explicitly
  invokes `/nw:refactor` to ensure the systematic Mikado Method flow with
  L1-L4 refactoring levels is used.

## [1.1.12] - 2026-02-16

### Fixed
- **SubagentStop hook crash: `classifyHandoffIfNeeded is not defined`**:
  Removed unsupported `systemMessage` field from hook protocol response.
  The field is not part of the Claude Code hook protocol and caused a JS
  runtime error when DES blocked an incomplete step.

## [1.1.9] - 2026-02-15

### Fixed
- **DES hooks fail with missing PyYAML on pipx/pip installs** ([#1](https://github.com/nWave-ai/nWave/issues/1)):
  Hook commands now use the installer's Python (with `$HOME` substitution for
  portability) instead of bare `python3`. This ensures dependencies like PyYAML
  and pydantic are available at hook runtime regardless of install method.
- **Installation blocked by missing pipenv**: Removed `PipenvCheck` from
  preflight — pipenv is a dev-only tool, not required for end users.
- **Post-install verification tested wrong Python**: `verify()` now also checks
  `import yaml` to catch missing dependencies at install time instead of runtime.
- Fixed broken Claude Code link in README ([#2](https://github.com/nWave-ai/nWave/pull/2) — thanks @sagatowski)

### Changed
- Hook portability test updated: accepts any non-project-venv Python path
  (system, pipx, pip venv) instead of requiring only `python3` or `$HOME`-based

## [1.1.0] - 2026-02-03

### Added
- Plugin architecture for modular installation system
- DES (Deterministic Execution System) integration
- DES utility scripts: `check_stale_phases.py`, `scope_boundary_check.py`
- Pre-commit hook templates for nWave projects (`.pre-commit-config-nwave.yaml`)
- DES audit trail documentation (`.des-audit-README.md`)
- Plugin development guide for contributors

### Changed
- Installer refactored to use PluginRegistry for dependency resolution (backward compatible)
- Installation orchestration via topological sort (Kahn's algorithm)

### Migration
- No breaking changes - existing installations work unchanged
- Fresh installs include DES automatically
- All file locations preserved from v1.0.x
- Backward compatibility guaranteed: plugins call existing installer methods

## [1.0.0] - Previous

See git history for earlier versions.
