---
name: hexagonal-testing
description: 5-layer agent output validation, I/O contract specification, vertical slice development, and test doubles policy with per-layer examples
---

# Hexagonal Testing and Output Validation

## 5-Layer Output Validation Framework

Validates the agent's OUTPUTS, not TDD testing methodology.

### Layer 1: Unit Testing (Output Validation)

Validate individual software-crafter outputs.

```yaml
structural_checks:
  - required_elements_present: true
  - format_compliance: true
  - quality_standards_met: true

quality_checks:
  - completeness: "All required components present"
  - clarity: "Unambiguous and understandable"
  - testability: "Can be validated"

test_data_quality:
  real_data: "Use real API responses as golden masters"
  edge_cases: "Test null, empty, malformed, boundary conditions"
  assertions: "Assert expected counts, not just 'any results'"
```

### Layer 2: Integration Testing (Handoff Validation)

Validate handoffs to next agent. Next agent must consume outputs without clarification.

- Deliverables complete: all expected artifacts present
- Validation status clear: quality gates passed/failed explicit
- Context sufficient: next agent can proceed without re-elicitation

### Layer 3: Adversarial Output Validation

Challenge output quality through adversarial scrutiny of generated code:

- SQL injection vulnerabilities in generated queries?
- XSS vulnerabilities in generated UI code?
- Null/undefined/empty input handling?
- Integer overflow/underflow conditions?
- Graceful failure vs crash?
- Exception handling appropriateness?

Pass criteria: all critical challenges addressed, edge cases documented and handled.

For peer review and escalation protocols, load the review-dimensions skill.

## Input/Output Contract

### Inputs

- **Required**: user_request (non-empty command string), context_files (existing readable file paths)
- **Optional**: configuration (YAML/JSON), previous_artifacts (outputs from prior wave for handoff)

### Outputs

- **Primary**: code artifacts (src/**/*, strictly necessary only), documentation (docs/develop/, minimal essential)
- **Secondary**: validation_results (gate pass/fail status), handoff_package (deliverables, next_agent, validation_status)
- **Policy**: any document beyond code/test files requires explicit user approval before creation

### Side Effects

- **Allowed**: file creation (src/**, tests/** only), file modification with audit trail, log entries
- **Forbidden**: unsolicited documentation, deletion without approval, external API calls, credential access
- **Requires permission**: documentation beyond code/test files, summary reports, analysis documents

### Error Handling

- Invalid input: validate first, clear error, do not proceed with partial inputs
- Processing error: log context, return to safe state, actionable user message
- Validation failure: report failed gates, withhold artifacts, suggest remediation

## Vertical Slice Development

Complete business capability per slice: UI -> Application -> Domain -> Infrastructure for a specific feature. Slices developed and deployed independently. Focus on business capability over technical layer.

For test doubles policy and violation examples, load the tdd-methodology skill.
