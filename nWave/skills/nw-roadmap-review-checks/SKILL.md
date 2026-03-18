---
name: nw-roadmap-review-checks
description: Roadmap-specific validation checks for architecture reviews. Load when reviewing roadmaps for implementation readiness.
disable-model-invocation: true
---

# Roadmap Review Checks

Six mandatory checks for every roadmap review. Each produces a finding block.

## Check 1: External Validity

Verify completing all steps produces an INVOCABLE feature, not just existing code.

Criteria: at least one step targets entry point integration | acceptance tests invoke through driving ports | clear user invocation path after completion

Severity: BLOCKER if no integration step or invocation path. HIGH if tests at wrong boundary.

```
EXTERNAL VALIDITY CHECK: PASSED|FAILED

Issue: {missing wiring}
Consequence: {what happens without fix}
Required Action: {integration step to add}
```

## Check 2: AC Implementation Coupling

Scan AC for implementation details locking crafter into predetermined structure.

Detection: underscore-prefixed identifiers | method signatures with params | internal class references | specific return types

Severity: HIGH. Flag each coupled AC with rewrite.

- Coupled: `_install_des_module() copies src/des/`
- Rewritten: `DES module importable from installation target after install`

Rationale: AC = WHAT (observable behavior), never HOW (internal structure). Crafter decides during GREEN + REFACTOR.

## Check 3: Step Decomposition Ratio

Calculation: implementation steps / unique production files in `files_to_modify`

Thresholds: acceptable <= 2.0 | warning 2.0-2.5 | reject > 2.5

Identical pattern check: 3+ steps with identical AC differing by substitution -> require batching.

## Check 4: Implementation Code in Roadmap

Verify no implementation code. BLOCKER.

Detection: code snippets/algorithms in descriptions | method implementations in AC | pseudocode/logic | variable names, loops, conditionals

Architect defines WHAT; crafter decides HOW. Roadmap code prevents better solutions via TDD.

## Check 5: Roadmap Concision and Precision

Quantitative thresholds: total words 500 (1-3 steps) / 1500 (4-8) / 3000 (9-15) | step description max 50 words | AC max 5 per step, 30 words each | notes max 100 words

Verbosity detection: multi-sentence blocks -> bullets | qualifiers (comprehensive, robust) -> delete | motivational language -> delete | redundancy -> state once | tutorials -> delete, assume expertise

Precision: every AC single interpretation | testable outcome | business over technical jargon

Severity: BLOCKER if word count exceeds threshold.

## Check 6: Unit Test Boundary Validation

Verify unit tests respect hexagonal boundaries.

Rules: invoke through driving ports only | no domain entity unit tests | behavior focus | never import internal/private modules

- Wrong: `Tests verify TemplateValidator._validate_schema() handles edge cases`
- Right: `When invalid template provided to render_prompt(), ValidationError raised with clear message`

Severity: HIGH.
