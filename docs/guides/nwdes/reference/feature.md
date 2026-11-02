# feature

`feature new` creates a handoff. It uses the [common write options](index.md#common-write-options).

| Option | Value |
|---|---|
| `--request` | Original request text |
| `--size` | S, M, or L |
| `--value` | Intended delivered value |
| `--epic` | Parent epic identity; omitted leaves the feature without a parent epic |

Returns written output paths. Repeating the same request, size, and value leaves an existing feature unchanged; different creation facts cause `FeatureExists`. Other refusals: MissingFact, PartInvalid, ConfigurationMalformed, HandoffInvalid.

The [tutorial](../../tutorial-nwdes-first-feature/) contains a verified creation example.
