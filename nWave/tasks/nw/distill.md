---
description: "Creates E2E acceptance tests in Given-When-Then format from requirements and architecture. Use when preparing executable specifications before implementation."
argument-hint: "[story-id] - Optional: --test-framework=[cucumber|specflow|pytest-bdd] --integration=[real-services|mocks]"
---

# NW-DISTILL: Acceptance Test Creation and Business Validation

**Wave**: DISTILL (wave 5 of 6)
**Agent**: Quinn (nw-acceptance-designer)

## Overview

Create E2E acceptance tests from requirements, architecture, and infrastructure design using Given-When-Then format. Produces executable specifications that bridge business requirements and technical implementation. Infrastructure design from DEVOP informs test environment setup.

## Interactive Decision Points

Before proceeding, the orchestrator asks the user:

### Decision 1: Feature Scope
**Question**: What is the scope of this feature?
**Options**:
1. Core feature -- primary application functionality
2. Extension -- modular add-on or integration
3. Bug fix -- regression tests for a known defect

### Decision 2: Test Framework
**Question**: Which test framework to use?
**Options**:
1. pytest-bdd -- Python BDD framework
2. Cucumber -- Ruby/JS BDD framework
3. SpecFlow -- .NET BDD framework
4. Custom -- user provides details

### Decision 3: Integration Approach
**Question**: How should integration tests connect to services?
**Options**:
1. Real services -- test against actual running services
2. Test containers -- ephemeral containers for dependencies
3. Mocks for external only -- real internal, mocked external services

### Decision 4: Infrastructure Testing
**Question**: Should acceptance tests cover infrastructure concerns?
**Options**:
1. Yes -- include CI/CD validation, deployment smoke tests
2. No -- functional acceptance tests only

## Context Files Required

- docs/feature/{feature-name}/discuss/requirements.md
- docs/feature/{feature-name}/discuss/user-stories.md
- docs/feature/{feature-name}/design/architecture-design.md
- docs/feature/{feature-name}/design/component-boundaries.md
- docs/feature/{feature-name}/design/technology-stack.md
- docs/feature/{feature-name}/deliver/* (infrastructure design from DEVOP wave)

## Agent Invocation

@nw-acceptance-designer

Execute \*create-acceptance-tests for {feature-name}.

Context files: see Context Files Required above.

**Configuration:**

- test_type: {from Decision 1: core | extension | bugfix}
- test_framework: {from Decision 2: specflow | cucumber | pytest-bdd}
- integration_approach: {from Decision 3}
- infrastructure_testing: {from Decision 4}
- interactive: moderate
- output_format: gherkin

## Success Criteria

- [ ] All user stories have corresponding acceptance tests
- [ ] Step methods call real production services (no mocks at acceptance level)
- [ ] One-at-a-time implementation strategy established (@skip/@pending tags)
- [ ] Tests exercise driving ports, not internal components (hexagonal boundary)
- [ ] Walking skeleton created first with user-centric scenarios that deliver observable user value (features only; optional for bugs)
- [ ] Infrastructure test scenarios included (if Decision 4 = Yes)
- [ ] Handoff package ready for software-crafter (DELIVER wave)

## Examples

### Example 1: Core feature acceptance tests
```
/nw:distill payment-webhook --test-framework=pytest-bdd --integration=real-services
```
Quinn creates Given-When-Then acceptance tests from requirements and architecture, establishes walking skeleton first, then milestone features with @skip tags for one-at-a-time implementation.

## Next Wave

**Handoff To**: nw-software-crafter (DELIVER wave)
**Deliverables**: Feature files, step definitions, test-scenarios.md, walking-skeleton.md

## Expected Outputs

```
tests/{test-type-path}/{feature-name}/acceptance/
  walking-skeleton.feature
  milestone-{N}-{description}.feature
  integration-checkpoints.feature
  steps/
    conftest.py
    {domain}_steps.py

docs/feature/{feature-name}/distill/
  test-scenarios.md
  walking-skeleton.md
  acceptance-review.md
```

Bug fix regression tests use a separate structure:

```
tests/regression/{component-or-module}/
  bug-{ticket-or-description}.feature     (acceptance: reproduces the defect scenario)
  steps/
    conftest.py
    {domain}_steps.py

tests/unit/{component-or-module}/
  test_{module}_bug_{ticket-or-description}.py  (unit: isolates the defect)
```
