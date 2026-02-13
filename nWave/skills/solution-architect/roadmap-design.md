---
name: roadmap-design
description: Roadmap concision rules, step decomposition efficiency, AC abstraction guidelines, and step-to-scenario mapping. Load when creating implementation roadmaps.
---

# Roadmap Design

## Canonical Format

Use ONLY the compact nested format. See `nWave/templates/roadmap-schema.yaml` for required fields and validation rules. Structure: `roadmap` metadata at top, `phases` list with nested `steps`, `implementation_scope`, and `validation` sections. Phase IDs: two digits (`"01"`). Step IDs: `"NN-MM"` where NN matches parent phase.

## Concision Requirements

Token efficiency at two levels:
1. Roadmap tokens: fewer tokens = faster review/maintenance
2. Implementation tokens: crafter reads roadmap ~35 times (7 phases x 5 steps)

Example: 5000-token roadmap x 35 reads = 175,000 tokens. 1000-token roadmap x 35 reads = 35,000 tokens (80% savings).

### Quantitative Limits
- Step description: max 50 words
- Acceptance criteria per step: max 5
- Each AC: max 30 words
- Step notes: max 100 words
- Target tokens: small feature (1-3 steps) = 500, medium (4-8) = 1500, large (9-15) = 3000

### Include
- WHAT to build (one sentence)
- WHY it matters (brief business value)
- Observable outcomes (testable AC)
- Architectural constraints (ports, tech)
- Integration points (which systems)

### Exclude
- HOW to implement (crafter decides)
- Code snippets or class names
- Algorithm descriptions
- Step-by-step instructions
- Technology tutorials
- Testing strategy (TDD is standard)
- Motivational language
- Redundancy across steps
- Examples when description is clear

### Compression Techniques
- Bullets over prose
- Eliminate qualifiers (very, robust, comprehensive)
- Assume expertise (crafter knows TDD, hexagonal)
- Active voice ("Implement X" not "The system should")
- Omit obvious (do not say "write tests")

## Acceptance Criteria Abstraction

AC describe observable outcomes, never internal implementation.

### Rules
- Describe WHAT the system does (behavior), not HOW (implementation)
- Never reference private methods (underscore prefix)
- Never reference internal class decomposition
- Never prescribe method signatures, parameter names, return types
- The software-crafter decides internal structure during GREEN + REFACTOR

### Good AC Examples
- "DES module importable from installation target after install"
- "DES utility scripts present and executable in scripts directory"
- "Installation uses backup before overwriting existing components"

### Bad AC Examples (implementation-coupled)
- "_install_des_module() copies src/des/ to ~/.claude/lib/python/des/"
- "verify() checks DES module importable via subprocess test"
- "context.installation_verifier._check_agents() called for verification"

## Step Decomposition Efficiency

### Step Ratio Check
Rule: `steps_count / estimated_production_files <= 2.5`
Violation: too many steps for production file count = scenario-driven over-decomposition
Action: merge steps targeting the same production file

### Identical Pattern Detection
Rule: if N steps differ only by a substitution variable (e.g., plugin name), batch into 1 step
Threshold: 3+ identical-pattern steps must be batched
Bad: 4 separate steps for AgentsPlugin, CommandsPlugin, TemplatesPlugin, UtilitiesPlugin
Good: 1 step creating all 4 wrapper plugins

### No-Op Prevention
Rule: each step must add production code. Validation-only steps are not steps.
Bad: "Step 02-05: Validate extraction with integration tests" (no new production code)
Good: validation is part of the preceding step's REVIEW phase

## Step-to-Scenario Mapping

For roadmaps feeding into implementation (DELIVER wave):
1. Read acceptance tests (tests/acceptance/test_*.py) before creating roadmap
2. Count acceptance test scenarios (def test_*)
3. Create approximately 1 step per scenario (flexibility for infrastructure steps)
4. Mark infrastructure steps clearly: "type: infrastructure"
5. Principle: 1 Scenario = 1 Step = 1 TDD Cycle

## Measure Before Plan Gate

Before creating any roadmap, verify:
1. Timing data shows WHERE time is spent
2. Impact ranking shows which component contributes MOST
3. Target validation provides evidence the proposed target is achievable

If any data is missing: halt roadmap creation, request measurement data, offer to help gather metrics. This gate is blocking.

## Simplest Solution Gate

Before proposing multi-phase implementations (>3 steps), document rejected alternatives:

### Alternatives to Consider
1. Configuration-only change (no code)
2. Single-file change (minimal code)
3. Existing tool/library/framework solution
4. Partial implementation (solve 80% simply)

### Documentation Format
```markdown
## Rejected Simple Alternatives

### Alternative 1: {simplest approach}
- What: {description}
- Expected Impact: {% of problem solved}
- Why Insufficient: {evidence-based reason}

### Why Complex Solution Necessary
1. Simple alternatives fail due to: {specific reason with evidence}
2. Complexity justified by: {benefit simple solutions cannot achieve}
```

Minimum 2 alternatives documented. Each requires specific description, expected impact, and evidence-based rejection.
