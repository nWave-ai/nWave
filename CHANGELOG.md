# Changelog

All notable changes to this project will be documented in this file.

## [1.7.0] - 2026-02-03

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
- All file locations preserved from v1.5.x
- Backward compatibility guaranteed: plugins call existing installer methods

## [1.5.15] - Previous

See git history for earlier versions.
