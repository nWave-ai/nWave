# document

`document` renders briefs and HTML pages from canonical handoffs. Uses the [common write options](index.md#common-write-options).

| Option | Meaning |
|---|---|
| `--product` | Render project product documents; omitted renders the selected feature or epic |
| `--handoff` | Repeatable feature handoff input for project aggregation; omission adds none |

Feature and epic mode use their configured handoff. Project aggregation replaces supplied feature sections and preserves other feature sections. Returns written or unchanged paths.

Refusals: MissingFact, PartInvalid, ConfigurationMalformed, HandoffInvalid, FeatureUnknown, DestinationInvalid. See the verified rendering command in the [tutorial](../../tutorial-nwdes-first-feature/).
