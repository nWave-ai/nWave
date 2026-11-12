# document

`document` renders briefs and HTML pages from canonical handoffs. Uses the [common write options](index.md#common-write-options).

| Option | Meaning |
|---|---|
| `--product` | Render project product documents; omitted renders the selected feature or epic |
| `--handoff` | Repeatable feature handoff input for project aggregation; omission adds none |
| `--overview` | Project scope only: write `docs/product/overview.md` and `overview.html` (vision, roadmap, backlog and the decision list) instead of the project brief; implies `--product`; refuses `--feature` and `--handoff` |

Feature and epic mode use their configured handoff. Project aggregation replaces supplied feature sections and preserves other feature sections. Returns written or unchanged paths.

`--product` alone writes the project brief and never the overview; `--overview`, with or without `--product`, writes only the two overview files and never the brief, so the two options write different documents into the same `docs/product` directory. A write that fails on the overview page leaves `overview.md` already new while the refusal names only the page; a rerun after the block is removed brings both files to their current bytes. A process killed between the two writes is not covered by a test.

## Readable brief check

If the readable brief is on, `document` checks each markdown brief that it writes. The check covers the feature brief, the product brief from `--product`, and the overview from `--overview`. It also applies if `documents.html` is false.

The charter close and the design close run the same check on the briefs they write. Their refusal has the same form.

A Mermaid diagram refuses the command if its block has no `%% alt:` line, has more than one, has an empty one, or has more than 25 distinct nodes. The WHAT line names the brief file, the diagram number and its rule. The WHY and HOW lines give the fix. The command writes no file.

If the readable brief is off, no diagram is checked.

Refusals: MissingFact, PartInvalid, ConfigurationMalformed, HandoffInvalid, FeatureUnknown, DestinationInvalid. See the verified rendering command in the [tutorial](../../tutorial-nwdes-first-feature/).
