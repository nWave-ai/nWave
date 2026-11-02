# rework

Uses the [common write options](index.md#common-write-options).

| Action | Options | Result |
|---|---|---|
| `rework set` | `--delta` delta identity; `--reason` reason text; optional `--slice` | Records rework |
| `rework clear` | Optional `--slice` | Clears rework |

Before setting slice-level rework, set that slice's work through `work set` with `--slice`, `--size`, and `--value`. Feature-level work does not supply those slice-level values.

Omitting `--slice` selects feature-level work. Supplying it selects an existing slice. Returns written or unchanged output paths. Both actions can refuse MissingFact, PartInvalid, ConfigurationMalformed, HandoffInvalid, or DanglingReference. Neither action decides which checks to run.

Rework is an annotation, not an evidence-withdrawal operation or a prerequisite for upstream replacement. Setting or clearing it neither retires identities nor removes dependent entries. Valid upstream replacement computes withdrawals independently and reports them after successful writes; it does not set, clear, or complete rework. The root chooses any subsequent roles or checks; neither rework nor withdrawal notices dispatch them automatically.
