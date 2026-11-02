# work

`work set` updates size and value. Uses the [common write options](index.md#common-write-options).

| Option | Meaning |
|---|---|
| `--slice` | Slice ID; omission selects feature-level work |
| `--size` | S, M, or L |
| `--value` | Intended delivered value |

Returns written or unchanged output paths. Refusals: MissingFact, PartInvalid, ConfigurationMalformed, HandoffInvalid, DanglingReference. Size does not select a route.
