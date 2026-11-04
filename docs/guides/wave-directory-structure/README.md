# Wave Directory Structure

Where nWave's artifacts live in v4, and which earlier locations were removed.

## Delivery features: one feature directory

Every delivery feature has one **feature directory**: `docs/feature/{id}/`. The
`nwdes.feature.directory` setting selects the base directory (default
`docs/feature`); nwdes appends `/<ID>`.

```
docs/feature/{id}/
  handoff.json       the one canonical record of the feature
  brief.md           briefs rendered by nwdes document (with .html versions)
  architecture.md
  acceptance.md
  runs/              run records, for example runs/craft.S1.json, runs/review.candidate.json
```

The handoff holds what the roles recorded: the request, promises, slices,
design facts, expectations, acceptance rows and examination verdicts. Run
records capture what each role closed. nwdes renders the briefs beside the
handoff; they are the reading surface for humans. See
[Understanding delivery artifacts](../understanding-delivery-artifacts/).

There is no per-wave subdirectory and no per-wave ledger inside the feature
directory.

## Product SSOT: docs/product/

Durable product files live under `docs/product/` and are updated in place
instead of copied per feature. A wave command updates them when its skill
says so:

| Command | Updates |
|---|---|
| `/nw-discover` | `docs/product/vision.md` and/or `docs/product/jobs.yaml` (SSOT bootstrap); a quantified KPI baseline goes to `docs/product/kpi-contracts.yaml` |
| `/nw-diverge` | `docs/product/jobs.yaml`: the validated job, opportunity scores and a changelog entry |

`/nw-diverge` writes no `wave-decisions.md` and no other per-wave ledger. Its
`recommendation.md` and supporting analysis are working files while the
delivery is open, not durable authority.

## Removed in v4: the per-wave runtime records

Earlier versions wrote per-wave subdirectories under the feature directory,
ending in a `deliver/` phase tracked by two JSON files:

```
docs/feature/{id}/
  discover/ ... discuss/ ... design/ ... devops/ ... distill/ ... deliver/
  deliver/roadmap.json
  deliver/execution-log.json
  wave-decisions.md
```

v4 removed this workflow:

- The delivery record is the nwdes handoff and its run records.
- `roadmap.json` and `execution-log.json` are retired. No converter exists.
- The installed hooks block every direct write to `execution-log.json`.
- `wave-decisions.md` is retired; no current wave writes a per-wave ledger.
- A 3.x delivery in progress is finished on 3.22.2 or restarted from the
  original request with `nwdes feature new`
  ([Migrate from nWave 3.x](../migrating-from-3x.md)).

Existing per-wave trees in your repository are read-only history. Read them
for context; do not extend them and do not rebuild their records.

## Reading progress

nwdes keeps no workflow state and has no resume command. Read the artifacts
yourself (see [Wave Routing](../wave-routing-and-entry-points/)). A DELIVER
run is complete when every slice in `docs/feature/{id}/handoff.json` has an
accepted craft run, the whole-candidate review and the examiner verdicts are
accepted, and the candidate is integrated.

A slice's acceptance oracle lives at the path the slice declares
(`nwdes slice set --oracle`). nWave fixes no test directory.

## Cross-feature artifacts

| Location | Content | Written by |
|---|---|---|
| Your repository's ADR files | Architecture decision records | solution-architect, recorded through `nwdes design` verbs |
| `docs/evolution/` | Historical post-completion archives; the current route writes none | - (existing files only) |

## Feature ID Derivation

When you run `/nw-deliver` or any wave command, nWave derives a feature ID
from your description:

1. Strip common prefixes: "implement", "add", "create", "build"
2. Remove English stop words: "a", "the", "to", "for", "with", "and", "in", "on", "of"
3. Convert to kebab-case (lowercase, hyphens)
4. Limit to 5 segments maximum

**Examples:**

- "Add rate limiting to the API gateway" → `rate-limiting-api-gateway`
- "OAuth2 upgrade" → `oauth2-upgrade`

The ID names the feature directory `docs/feature/{id}/`.
