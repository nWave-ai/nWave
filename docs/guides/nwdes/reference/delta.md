# delta

`delta` compares two handoff files. It takes no repository or project root.

| Option | Meaning |
|---|---|
| `--previous` | Previous handoff file |
| `--new` | New handoff file |

Prints ADDED, REMOVED, or REPLACED with field paths, followed by `AFFECTED S<n>` lines in numeric order. Equal handoffs produce no output. Facts compare by text, not assigned F IDs. The command does not select rework or verification.

Affected slices are those whose own design changes, plus the old and new governed slices of a shared D/K record whose text changes, or only the slices gaining/losing membership when its text is unchanged. Retained D/K records match by ID, not position; absent records have no members. No prose declares the affected set.

The host runs a separate design review only when a shared decision or ADR changes, using the delta to inspect the change; the final whole-candidate review stays distinct from embedded per-slice refinement feedback. `AFFECTED` reports changed slice projections, not a dispatch instruction or verdict.

Entries withdrawn by upstream replacement appear as ordinary `REMOVED` differences. `delta` does not emit replacement-command `WITHDRAWN` notices, choose a repair owner or remediation route, dispatch roles, or mark rework complete.

Refusals: MissingFact, HandoffInvalid. The [tutorial](../../tutorial-nwdes-first-feature/) compares a handoff with itself.
