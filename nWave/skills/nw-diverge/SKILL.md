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

## Required Pass

1. **Job (JTBD)** -- extract and elevate the job from the request or
   `docs/product/vision.md`/DISCOVER evidence, at strategic or physical
   level, not tactical. Produce functional/emotional/social statements and
   minimum 3 ODI outcome statements.
2. **Competitive research** -- invoke `nw-researcher` for evidence-grounded
   mapping of how existing products serve the job, including at least one
   non-obvious alternative.
3. **Brainstorming** -- frame the HMW question, apply SCAMPER, generate 6
   structurally diverse options (mechanism, assumption and cost differ).
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
recommended: <option> -- <one-line rationale>
dissent: <second-place option> -- <why it might win under different assumptions>
ssot: <docs/product/jobs.yaml updated>
```

## Human-readable authority

Return changed feature decisions to the Product Owner rather than editing a
generated brief. Use current full briefs and HTML when useful; `jobs.yaml` is
not itself a generated feature brief. Read `nw-doc-as-artifact` for human review.
No wave-entry preference or expansion offer is required.
