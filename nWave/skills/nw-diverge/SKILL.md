---
name: nw-diverge
description: "Generates 3-5 divergent design directions through JTBD analysis, competitive research, structured brainstorming, and taste evaluation before convergence. Use when the team has a validated problem but hasn't chosen a solution approach."
user-invocable: true
argument-hint: '[feature-id] --work-type=[new-product|brownfield|pivot]'
---

# NW-DIVERGE

## Authority

DIVERGE updates the durable `docs/product/jobs.yaml` (the validated job,
opportunity scores, changelog). It never writes a per-delivery decision
ledger. `recommendation.md` and its supporting artifacts are the ephemeral
workspace read while this delivery is open, not a second authority.

## Dispatch

Before dispatching `nw-diverger`, the host writes
`docs/feature/{feature-id}/diverge/request.md`: the requester's own words,
verbatim, in quoted blocks. The line above each block marks its source:
`source: requester-verbatim` (copied from the requester's own turn text or a
requester-authored file, quoted or cited by path) or `source: host-summary`
(anything the host paraphrased). The source label is host-attested: the
reviewer verifies quotes against the blocks it marks, not the label itself.
The diverger and its reviewer read this file;
neither creates nor edits it. If it is missing, the diverger returns
`NEEDS_INPUT` asking the host for it.

## Required Pass

1. **Job (JTBD)** -- extract and elevate the job from the request or
   `docs/product/vision.md`/DISCOVER evidence, at strategic or physical
   level, not tactical. Produce functional/emotional/social statements and
   minimum 3 ODI outcome statements.
2. **Competitive research** -- invoke `nw-researcher` for evidence-grounded
   mapping of how existing products serve the job, including at least one
   non-obvious alternative.
3. **Brainstorming** -- frame the HMW question, apply SCAMPER, generate 6
   structurally diverse options (mechanism, assumption and cost differ) by
   stating a probability per candidate and sampling the tails; name each
   option and mark its `name_origin` per `nw-requester-words`.
4. **Taste evaluation** -- apply the DVF filter, score surviving options on
   the 4 locked-weight taste criteria, produce a traceable ranking with a
   dissenting case for the second-place option.
5. **Peer review** -- `nw-diverger-reviewer` validates all 5 dimensions,
   maximum 2 revision iterations.

## Handoff

Update `docs/product/jobs.yaml` once with the validated job and a changelog
entry referencing this feature-id. Return the recommendation and decision
statement; do not author a `wave-decisions.md` or any other per-wave ledger.

```text
DIVERGE-RESULT
verdict: PASS | NEEDS_INPUT
job: <JOB-id, statement>
options: <count generated, count survived>
recommended: <direction phrased by mechanism in the requester's vocabulary> -- <one-line rationale>
dissent: <second-place direction phrased by mechanism> -- <why it might win under different assumptions>
ssot: <docs/product/jobs.yaml updated>
```

The recommended and dissent lines use the mechanism in the requester's
vocabulary; coined handles and their name_origin stay in the scoring table
inside taste-evaluation.md. New terms carry the `[new]` marker per
`nw-requester-words`. Relay this wording to the requester as returned.

## Human-readable authority

Return changed feature decisions to the Product Owner rather than editing a
generated brief. Use current full briefs and HTML when useful; `jobs.yaml` is
not itself a generated feature brief. Read `nw-doc-as-artifact` for human review.
No wave-entry preference or expansion offer is required.
