---
name: nw-ad-critique-dimensions
description: "Reviews acceptance test quality across happy path bias, GWT compliance, business language, and coverage. Use when peer-reviewing acceptance tests or validating BDD scenario completeness."
user-invocable: false
disable-model-invocation: true
---

# Acceptance Test Critique Dimensions

Load when performing peer review of acceptance tests (during *handoff-develop).

## Dimension 1: Happy Path Bias

**Pattern**: Only successful scenarios, error paths missing.

Detection: Count success vs error scenarios. Error should be at least 40%. Missing coverage examples: login success but no invalid password | Payment processed but no decline/timeout | Search results but no empty/error cases.

Severity: blocker (production error handling untested).

## Dimension 2: GWT Format Compliance

**Pattern**: Scenarios violate Given-When-Then structure.

Violations: Missing Given context | Multiple When actions (split into separate scenarios) | Then with technical assertions instead of business outcomes. Each scenario: Given (context), When (single action), Then (observable outcome).

Severity: high (tests not behavior-driven).

## Dimension 3: Business Language Purity

**Pattern**: Technical terms leak into acceptance tests.

Flag: database, API, HTTP, REST, JSON, classes, methods, services, controllers, status codes (500, 404), infrastructure (Redis, Kafka, Lambda).

Business alternatives: "Customer data is stored" not "Database persists record" | "Order is confirmed" not "API returns 200 OK" | "Payment fails" not "Gateway throws exception"

Severity: high (tests coupled to implementation).

## Dimension 4: Coverage Completeness

**Pattern**: User stories lack acceptance test coverage.

Validation: Map each story to scenarios | Verify all AC have corresponding tests | Confirm edge cases and boundaries tested.

Severity: blocker (unverified requirements).

## Dimension 5: Walking Skeleton User-Centricity

**Pattern**: Walking skeletons describe technical layer connectivity instead of user value.

Detection litmus test for `@walking_skeleton` scenarios:
- Title describes user goal or technical flow?
- Then steps describe user observations or internal side effects?
- Could non-technical stakeholder confirm "yes, that is what users need"?

Violations: "End-to-end order flow through all layers" (technical framing) | Then "order row inserted in database" (internal side effects) | Given "database contains user record" instead of "customer has an account"

Severity: high (skeletons that only prove wiring miss the point -- first skeleton should be demo-able to stakeholder).

## Dimension 6: Priority Validation

**Pattern**: Tests address secondary concerns while larger gaps exist.

Questions: 1. Is this the largest bottleneck? (timing data or gap analysis) | 2. Simpler alternatives considered? | 3. Constraint prioritization correct? | 4. Test design decisions data-justified?

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
