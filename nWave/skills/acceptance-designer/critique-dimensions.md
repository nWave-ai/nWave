---
name: critique-dimensions
description: Review dimensions for acceptance test quality - happy path bias, GWT compliance, business language purity, coverage completeness, walking skeleton user-centricity, and priority validation
---

# Acceptance Test Critique Dimensions

Load this skill when performing peer review of acceptance tests (during *handoff-develop).

## Dimension 1: Happy Path Bias

**Pattern**: Tests only cover successful scenarios, error paths missing.

Detection: Count success vs error scenarios. Error scenarios should be at least 40% of total.

Examples of missing coverage:
- Login success tested but invalid password not covered
- Payment processing tested but decline/timeout scenarios missing
- Search results tested but empty results and errors absent

Severity: blocker (production error handling untested).

## Dimension 2: GWT Format Compliance

**Pattern**: Scenarios violate Given-When-Then structure.

Violations:
- Missing Given context setup
- Multiple When actions (split into separate scenarios)
- Then with technical assertions instead of business outcomes

Each scenario has: Given (context), When (single action), Then (observable outcome).

Severity: high (tests not behavior-driven).

## Dimension 3: Business Language Purity

**Pattern**: Technical terms leak into acceptance tests.

Terms to flag: database, API, HTTP, REST, JSON, classes, methods, services, controllers, status codes (500, 404), infrastructure terms (Redis, Kafka, Lambda).

Business alternatives:
- "Customer data is stored" not "Database persists record"
- "Order is confirmed" not "API returns 200 OK"
- "Payment fails" not "Gateway throws exception"

Severity: high (tests coupled to implementation).

## Dimension 4: Coverage Completeness

**Pattern**: User stories lack acceptance test coverage.

Validation:
- Map each user story to acceptance test scenarios
- Verify all acceptance criteria have corresponding tests
- Confirm edge cases and boundaries tested

Severity: blocker (unverified requirements).

## Dimension 5: Walking Skeleton User-Centricity

**Pattern**: Walking skeletons describe technical layer connectivity instead of user value delivery.

Detection: Read each `@walking_skeleton` scenario and apply the litmus test:
- Does the title describe a user goal or a technical flow?
- Do the Then steps describe what the user observes or internal system side effects?
- Could a non-technical stakeholder read it and confirm "yes, that is what users need"?

Examples of violations:
- "End-to-end order flow through all layers" (technical framing)
- Then steps like "order row inserted in database" or "message published to queue" (internal side effects)
- Given steps that set up technical state ("Given database contains user record") instead of user context ("Given customer has an account")

Severity: high (skeletons that only prove wiring miss the point -- the first passing skeleton should be demo-able to a stakeholder).

## Dimension 6: Priority Validation

**Pattern**: Tests address secondary concerns while larger gaps exist.

Questions:
1. Is this the largest bottleneck? (Evidence: timing data or gap analysis)
2. Were simpler alternatives considered?
3. Is constraint prioritization correct?
4. Are test design decisions data-justified?

Severity: blocker if wrong problem addressed, high if no measurement data.

## Review Output Format

```yaml
review_id: "accept_rev_{timestamp}"
reviewer: "acceptance-designer (review mode)"

strengths:
  - "{positive test design aspect with example}"

issues_identified:
  happy_path_bias:
    - issue: "Feature {name} only tests success"
      severity: "blocker"
      recommendation: "Add error scenarios: invalid input, timeout, service failure"

  gwt_format:
    - issue: "Scenario has multiple When actions"
      severity: "high"
      recommendation: "Split into separate scenarios"

  business_language:
    - issue: "Technical term '{term}' in scenario"
      severity: "high"
      recommendation: "Replace with: '{business alternative}'"

  coverage_gaps:
    - issue: "User story {US-ID} has no acceptance tests"
      severity: "blocker"
      recommendation: "Create scenarios for all AC of {US-ID}"

  walking_skeleton_centricity:
    - issue: "Walking skeleton '{name}' describes technical flow, not user goal"
      severity: "high"
      recommendation: "Reframe: title as user goal, Then steps as observable user outcomes"

approval_status: "approved|rejected_pending_revisions|conditionally_approved"
```
