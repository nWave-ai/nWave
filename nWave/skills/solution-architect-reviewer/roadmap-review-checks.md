---
name: roadmap-review-checks
description: Roadmap-specific validation checks for architecture reviews. Load when reviewing roadmaps for implementation readiness.
---

# Roadmap Review Checks

Six mandatory checks applied to every roadmap review. Each produces a finding block in the review output.

## Check 1: External Validity

Verify that completing all roadmap steps produces an INVOCABLE feature, not just existing code.

Validation criteria:
- At least one step targets entry point integration (wiring into the system)
- Acceptance tests invoke through driving ports, not internal components
- Clear user invocation path exists after all steps complete

Severity: BLOCKER if no integration step or no user invocation path. HIGH if tests at wrong boundary.

Finding format:
```
EXTERNAL VALIDITY CHECK: PASSED|FAILED

Issue: {description of missing wiring}
Consequence: {what happens if steps completed without fix}
Required Action: {specific integration step to add}
```

## Check 2: AC Implementation Coupling

Scan acceptance criteria for implementation details that lock the crafter into predetermined structure.

Detection patterns:
- Underscore-prefixed identifiers (`_method`, `_property`)
- Method signatures with parameter lists
- Internal class references (private helpers, internal modules)
- Specific return types or data structures

Severity: HIGH. Action: flag each coupled AC with rewrite suggestion.

Example:
- Coupled: `_install_des_module() copies src/des/`
- Rewritten: `DES module importable from installation target after install`

Rationale: AC describes WHAT (observable behavior), never HOW (internal structure). The crafter decides implementation during GREEN + REFACTOR phases.

## Check 3: Step Decomposition Ratio

Verify step count is proportional to production files.

Calculation: count implementation steps / count unique production files in `files_to_modify`.

Thresholds:
- Acceptable: <= 2.0
- Warning: 2.0 - 2.5
- Reject: > 2.5

Identical pattern check: detect 3+ steps with identical AC structure differing only by substitution. Require batching into single step.

## Check 4: Implementation Code in Roadmap

Verify roadmap contains no implementation code. This is a BLOCKER.

Detection patterns:
- Code snippets or algorithms in step descriptions
- Detailed method implementations in acceptance criteria
- Algorithm pseudocode or implementation logic
- Variable names, loops, conditionals in roadmap text

The solution architect defines WHAT; the software crafter decides HOW. Roadmap code prevents better solutions from emerging through TDD.

## Check 5: Roadmap Concision and Precision

Quantitative thresholds:
- Total word count: 500 (1-3 steps), 1500 (4-8 steps), 3000 (9-15 steps)
- Step description: max 50 words
- Acceptance criteria: max 5 per step, max 30 words each
- Step notes: max 100 words

Verbosity detection:
- Multi-sentence blocks without bullets -> convert to bullets
- Qualifiers (comprehensive, robust, very, important) -> delete
- Motivational language (This is important because...) -> delete
- Redundancy across steps -> state once, reference
- Technical tutorials (explaining TDD, hexagonal) -> delete, assume expertise

Precision checks:
- Every AC has one interpretation (no vague terms)
- AC describes testable outcome (no "good performance")
- Business terminology over technical jargon

Severity: BLOCKER if word count exceeds threshold.

## Check 6: Unit Test Boundary Validation

Verify unit test strategy respects hexagonal architecture boundaries.

Rules:
- Unit tests invoke through driving ports only (public interfaces)
- No unit tests for domain entities directly
- Tests focus on behavior, not implementation
- Tests never import internal modules or private methods

Examples:
- Wrong: `Tests verify TemplateValidator._validate_schema() handles edge cases`
- Right: `When invalid template provided to render_prompt(), ValidationError raised with clear message`

Severity: HIGH.
