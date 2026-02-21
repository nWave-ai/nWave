# ADR-002: Inline Shared Logic Instead of Extraction

## Status

Accepted

## Context

Wave detection rules and project ID derivation logic are used by multiple wizard commands: detection by `/nw:continue` and `/nw:ff`, ID derivation by `/nw:new` and `/nw:ff` (and already by `/nw:deliver`). Options: (a) extract to a shared file that all commands reference, (b) inline the logic in each task file.

## Decision

Inline the shared logic in each task file that needs it. Each file contains its own copy of the wave detection table and/or project ID derivation instructions.

## Alternatives Considered

- **Shared markdown file referenced by all commands**: e.g., `nWave/tasks/nw/_shared/wave-detection.md`. Rejected because markdown task files have no include/import mechanism. The Claude instance would need explicit instructions to "read file X first" which adds cognitive overhead and a fragile dependency.
- **Python utility module for detection logic**: Would enable code sharing and unit testing. Rejected by the no-new-Python constraint.

## Consequences

- **Positive**: Each task file is fully self-contained; the Claude instance needs only one file to execute any command. No cross-file dependencies.
- **Negative**: Detection rules are duplicated in 2 files (continue.md, ff.md). ID derivation is duplicated in 3 files (new.md, ff.md, deliver.md). Updates require changing multiple files.
- **Mitigation**: The duplication is small (< 30 lines per instance). The requirements document is the canonical source. A future refactoring could add a "read shared context" preamble if the duplication becomes a maintenance burden.
