---
description: "Conducts evidence-based product discovery through customer interviews and assumption testing. Use at project start to validate problem-solution fit."
argument-hint: "[product-concept] - Optional: --interview-depth=[overview|comprehensive] --output-format=[md|yaml]"
---

# NW-DISCOVER: Evidence-Based Product Discovery

**Wave**: DISCOVER | **Agent**: Scout (nw-product-discoverer)

## Overview

Execute evidence-based product discovery through assumption testing and market validation. First wave in nWave (DISCOVER > DIVERGE > DISCUSS > DESIGN > DEVOPS > DISTILL > DELIVER).

Scout establishes product-market fit through rigorous customer development using Mom Test interviewing principles and continuous discovery practices.

## Delivery route

Use nwdes for delivery: read `nw-nwdes`. Discovery evidence informs product
intent; it does not create a delivery plan or a second feature handoff.
When proceeding to DISCUSS, the host creates or selects the nwdes feature and
builds the installed Product Owner's prompt with `nwdes prompt`. The PO records
selected evidence-backed promises, scope and decisions through Bash with
`nwdes product` recording verbs, then closes. The host renders it with `nwdes document`;
neither discovery prose nor a copied role reply replaces that authority.

## Context Files Required

- docs/project-brief.md — Initial product vision (if available)
- docs/market-context.md — Market research and competitive landscape (if available)

## Previous Artifacts

None (DISCOVER is the first wave).

## SSOT Update

DISCOVER writes its lasting facts directly to the durable product SSOT — not
to a per-wave decision file. Update the artifact that owns each fact:
validated/invalidated assumptions and problem evidence go to
`docs/product/vision.md` and/or `docs/product/jobs.yaml` (create under
`docs/product/` if it does not yet exist — this is SSOT bootstrap); a
quantified KPI baseline goes to `docs/product/kpi-contracts.yaml`. Preserve
provenance (source, sample size, date, confidence) inline in the updated
artifact. Downstream waves read these SSOT files directly; there is no
DISCOVER decision-summary ledger to assess instead.

## Document Update (Back-Propagation)

Not applicable (DISCOVER is the first wave — no prior documents to update).

## Agent Invocation

@nw-product-discoverer

Execute \*discover for {product-concept-name}.

**Context Files:** docs/project-brief.md (if available) | docs/market-context.md (if available)

**Configuration:**
- interactive: high | output_format: markdown
- interview_depth: comprehensive | evidence_standard: past_behavior


## Success Criteria

Refer to Scout's quality gates in ~/.claude/agents/nw/nw-product-discoverer.md.

- [ ] All 4 decision gates passed (G1-G4)
- [ ] Minimum interview thresholds met per phase
- [ ] Evidence quality standards met (past behavior, not future intent)
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

DISCOVER returns concise evidence directly — problem validation, opportunity
assessment, solution testing signal, lean-canvas shape and interview
citations — and updates only the durable product SSOT it owns:

```
docs/product/
  vision.md and/or jobs.yaml     (updated with validated/invalidated assumptions + provenance)
  kpi-contracts.yaml             (updated, if a quantified baseline was established)
```
