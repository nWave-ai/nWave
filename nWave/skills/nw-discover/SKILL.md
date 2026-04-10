---
name: nw-discover
description: "Conducts evidence-based product discovery through customer interviews and assumption testing. Use at project start to validate problem-solution fit."
user-invocable: true
argument-hint: '[product-concept] - Optional: --interview-depth=[overview|comprehensive] --output-format=[md|yaml]'
---

# NW-DISCOVER: Evidence-Based Product Discovery

**Wave**: DISCOVER | **Agent**: Scout (nw-product-discoverer)

## Overview

Execute evidence-based product discovery through assumption testing and market validation. First wave in nWave (DISCOVER > DISCUSS > SPIKE > DESIGN > DEVOPS > DISTILL > DELIVER).

Scout establishes product-market fit through rigorous customer development using Mom Test interviewing principles and continuous discovery practices.

## Context Files Required

- docs/project-brief.md — Initial product vision (if available)
- docs/market-context.md — Market research and competitive landscape (if available)

## Previous Artifacts

None (DISCOVER is the first wave).

## Wave Decisions Summary

Before completing DISCOVER, produce `docs/feature/{feature-id}/discover/wave-decisions.md`:

1. **Record Key Decisions** — List each decision as `[D1] {decision}: {rationale} (see: {source-file})`. Gate: every major discovery choice has a rationale entry.
2. **Record Constraints** — List each constraint established from evidence. Gate: all constraints have an evidence source.
3. **Record Validated Assumptions** — List each assumption confirmed, with confidence level. Gate: confidence level stated for each.
4. **Record Invalidated Assumptions** — List each assumption disproved, with evidence reference. Gate: evidence reference present for each invalidation.

This summary enables downstream waves to quickly assess DISCOVER outcomes without reading all artifacts.

## Document Update (Back-Propagation)

Not applicable (DISCOVER is the first wave — no prior documents to update).

## Agent Invocation

1. **Dispatch Agent** — Invoke `@nw-product-discoverer` with `Execute *discover for {product-concept-name}`. Gate: agent dispatched.
2. **Provide Context Files** — Pass `docs/project-brief.md` and `docs/market-context.md` if available. Gate: available context files referenced.
3. **Apply Configuration** — Set `interactive: high`, `output_format: markdown`, `interview_depth: comprehensive`, `evidence_standard: past_behavior`. Gate: configuration confirmed.

## Peer Review Gate

1. **Dispatch Reviewer** — Invoke `@nw-product-discoverer-reviewer` before handoff to DISCUSS. Gate: reviewer dispatched, all discovery artifacts available.
2. **Verify Review Scope** — Reviewer checks: evidence quality (past behavior, not future intent), interview coverage and threshold compliance, assumption validation rigor (G1-G4 gates), lean canvas coherence with interview findings. Gate: all four dimensions assessed.
3. **Handle Rejection** — On REJECTION: revise artifacts per reviewer findings and re-submit. Gate: max 2 attempts; escalate to user if unresolved.
4. **Confirm Approval** — Block handoff to DISCUSS until reviewer returns APPROVED. Gate: explicit approval received.

## Success Criteria

Refer to Scout's quality gates in ~/.claude/agents/nw/nw-product-discoverer.md.

- [ ] All 4 decision gates passed (G1-G4)
- [ ] Minimum interview thresholds met per phase
- [ ] Evidence quality standards met (past behavior, not future intent)
- [ ] Peer review approved by @nw-product-discoverer-reviewer
- [ ] Handoff accepted by product-owner (DISCUSS wave)

## Next Wave

**Handoff To**: nw-product-owner (DISCUSS wave)
**Deliverables**: See Scout's handoff package specification in agent file

## Examples

### Example 1: New SaaS product discovery
```
/nw-discover invoice-automation
```
Scout conducts customer development interviews, validates problem-solution fit through Mom Test questioning, and produces a lean canvas with evidence-backed assumptions.

## Expected Outputs

```
docs/feature/{feature-id}/discover/
  problem-validation.md
  opportunity-tree.md
  solution-testing.md
  lean-canvas.md
  interview-log.md
  wave-decisions.md
```
