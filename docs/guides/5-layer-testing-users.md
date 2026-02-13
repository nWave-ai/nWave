# Layer 4 for Users

**Version**: 1.5.2
**Date**: 2026-01-22
**Status**: Production Ready

Manual review workflows via CLI and interactive mode.

**Prerequisites**: nwave CLI installed.

**Related Docs**:
- [API Reference](../reference/5-layer-testing-api.md) (contracts)
- [For Developers](5-layer-testing-developers.md) (code)
- [For CI/CD](5-layer-testing-cicd.md) (pipelines)

---

## Quick Start

Request a peer review:

```bash
nwave review \
  --artifact docs/requirements/requirements.md \
  --reviewer business-analyst-reviewer \
  --interactive
```

---

## Basic Review Request

### Step 1: Run Review Command

```bash
nwave review \
  --artifact docs/requirements/requirements.md \
  --reviewer business-analyst-reviewer \
  --interactive
```

### Step 2: Read Output

```
Initiating Layer 4 Peer Review...
Reviewer: business-analyst-reviewer (Scout)
Artifact: docs/requirements/requirements.md

Analyzing artifact for bias, completeness, clarity, testability...

Review Complete
Issues Identified: 8 (2 critical, 3 high, 3 medium, 0 low)
Approval Status: rejected_pending_revisions

Review saved to: reviews/rev_20251006_152330_requirements.yaml

Next Steps:
1. Review feedback: cat reviews/rev_20251006_152330_requirements.yaml
2. Address critical and high issues
3. Re-submit: nwave review --artifact docs/requirements/requirements.md --iteration 2
```

---

## Review Specific Dimensions

Focus review on specific areas:

```bash
# Review only for bias detection
nwave review \
  --artifact docs/requirements/requirements.md \
  --reviewer business-analyst-reviewer \
  --dimensions bias

# Review for completeness and testability
nwave review \
  --artifact docs/requirements/requirements.md \
  --reviewer business-analyst-reviewer \
  --dimensions completeness,testability
```

### Available Dimensions

| Dimension | Description |
|-----------|-------------|
| `bias` | Confirmation bias detection |
| `completeness` | Missing scenarios/stakeholders |
| `clarity` | Vague requirements |
| `testability` | Measurable acceptance criteria |

---

## Interactive Review Mode

Let the CLI guide you through options:

```bash
nwave review --interactive
```

**Prompts**:
```
? Select artifact to review:
  > docs/requirements/requirements.md
    docs/architecture/architecture.md
    tests/acceptance/checkout.feature

? Select reviewer:
  > business-analyst-reviewer (Scout) - Requirements quality
    solution-architect-reviewer (Atlas) - Architecture quality
    acceptance-designer-reviewer (Sentinel) - Test quality

? Review dimensions (select all that apply):
  [x] Confirmation Bias Detection
  [x] Completeness Validation
  [x] Clarity Assessment
  [x] Testability Verification

Initiating review...
```

---

## Interpreting Review Feedback

### View Feedback File

```bash
cat reviews/rev_20251006_152330_requirements.yaml
```

### Key Sections

**1. Strengths** - What's done well:
```yaml
strengths:
  - "Clear business context with quantitative goal (45% -> 25% cart abandonment)"
  - "Well-structured user stories with persona-based format"
```

**2. Critical Issues** - Must fix:
```yaml
issues_identified:
  completeness_gaps:
    - issue: "Performance requirement 'System should be fast' is vague"
      severity: "critical"
      recommendation: "Quantify: 'API responds within 2s (p95)'"
```

**3. Recommendations** - Prioritized actions:
```yaml
recommendations:
  1: "CRITICAL: Quantify performance requirements"
  2: "CRITICAL: Add error handling scenarios"
  3: "HIGH: Re-elicit deployment constraints"
```

**4. Approval Status** - What happens next:
```yaml
approval_status: "rejected_pending_revisions"
next_steps: |
  Address critical and high severity issues before DESIGN wave handoff.
```

---

## Revision and Re-Submission

### Step 1: Address Feedback

Edit your artifact to fix issues:

```bash
vim docs/requirements/requirements.md
```

### Step 2: Re-Submit (Iteration 2)

```bash
nwave review \
  --artifact docs/requirements/requirements.md \
  --reviewer business-analyst-reviewer \
  --iteration 2 \
  --revision-notes revision_notes_v1_to_v2.md
```

### Step 3: Check Result

```
Re-review (Iteration 2)...

Review Complete
Critical Issues Resolved: 2/2 (100%)
High Issues Resolved: 3/3 (100%)

APPROVED
Handoff Ready: Yes
Next Agent: solution-architect
```

---

## Understanding Iteration Limits

**Maximum 2 iterations**:
- **Iteration 1**: Initial review, you revise
- **Iteration 2**: Re-review, approve or escalate

### If Not Approved After 2 Iterations

```
Max iterations exceeded (2/2)
Unresolved Critical Issues: 1
- Performance requirement still vague after revision

Escalation Required
Created escalation ticket: ESC-2025-10-06-001
Assigned to: Human Facilitator (John Smith)
Recommendation: Schedule stakeholder workshop to clarify requirements

Escalation report: escalations/ESC-2025-10-06-001.yaml
```

---

## Choosing the Right Reviewer

| Artifact Type | Reviewer | Focus |
|--------------|----------|-------|
| Requirements | business-analyst-reviewer | Bias, completeness, testability |
| Architecture | solution-architect-reviewer | ADR quality, feasibility |
| Acceptance tests | acceptance-designer-reviewer | Happy path bias, GWT quality |
| Code | software-crafter-reviewer | Implementation bias, complexity |
| Research | knowledge-researcher-reviewer | Source credibility, evidence |

---

## Common Workflows

### Pre-Handoff Review

Before handing off to the next wave:

```bash
# After DISCUSS wave, before DESIGN
nwave review \
  --artifact docs/requirements/requirements.md \
  --reviewer business-analyst-reviewer \
  --fail-on-critical
```

### Quick Bias Check

Fast check for common biases:

```bash
nwave review \
  --artifact docs/architecture/architecture.md \
  --reviewer solution-architect-reviewer \
  --dimensions bias \
  --quick
```

### Full Quality Audit

Comprehensive review of all dimensions:

```bash
nwave review \
  --artifact docs/requirements/requirements.md \
  --reviewer business-analyst-reviewer \
  --dimensions bias,completeness,clarity,testability \
  --verbose
```

---

## Troubleshooting

### Reviewer Not Found

**Error**: `Reviewer agent 'business-analyst-reviewer' not found`

**Fix**:
```bash
# Check available reviewers
ls -1 $NWAVE_REVIEWERS_DIR/

# Verify specific reviewer
cat $NWAVE_REVIEWERS_DIR/business-analyst-reviewer.md

# Re-install if missing
./scripts/install-nwave.sh
```

### Review Takes Too Long

**Error**: `Warning: Review timed out after 300 seconds`

**Fix**:
```bash
export REVIEWER_TIMEOUT_SECONDS="600"  # 10 minutes
nwave review --artifact ...
```

### No Feedback Returned

**Error**: Review completes but file is empty

**Fix**: Use verbose mode:
```bash
nwave review \
  --artifact docs/requirements/requirements.md \
  --reviewer business-analyst-reviewer \
  --verbose \
  --debug
```

---

## Debugging Commands

```bash
# Enable verbose logging
nwave review --artifact ... --verbose --debug

# Check Layer 4 status
nwave status --layer 4

# Validate reviewer agent
nwave validate-agent business-analyst-reviewer

# Test reviewer without changes
nwave test-reviewer business-analyst-reviewer --dry-run
```

---

## Layer 5: Mutation Testing

Layer 5 validates your test suite quality by checking if tests detect code mutations.

### Quick Start

```bash
nwave mutation-test \
  --source src/checkout/ \
  --tests tests/unit/checkout/ \
  --threshold 85
```

### Understanding Output

```
Running Layer 5 Mutation Testing...
Source: src/checkout/
Tests: tests/unit/checkout/

Generating mutants... 127 mutants created
Running tests against mutants...

[████████████████████████████████████████] 127/127

Results:
  Total Mutants: 127
  Killed: 112 (tests caught the mutation)
  Survived: 15 (tests missed the mutation)

Mutation Score: 88.2% (threshold: 85%)
Status: PASSED ✓

Surviving mutants saved to: mutations/surviving_mutants.yaml
```

### Interpreting Mutation Score

| Score | Quality | Action |
|-------|---------|--------|
| ≥ 90% | Excellent | Tests are comprehensive |
| 85-89% | Good | Meets threshold, minor gaps |
| 70-84% | Fair | Add tests for surviving mutants |
| < 70% | Poor | Significant test gaps exist |

### Viewing Surviving Mutants

```bash
cat mutations/surviving_mutants.yaml
```

```yaml
surviving_mutants:
  - file: src/checkout/cart.py
    line: 45
    type: arithmetic_operator
    original: "total = subtotal + tax"
    mutated: "total = subtotal - tax"
    suggestion: "Add test verifying tax is added, not subtracted"

  - file: src/checkout/discount.py
    line: 23
    type: comparison_boundary
    original: "if quantity >= 10:"
    mutated: "if quantity > 10:"
    suggestion: "Add boundary test for exactly 10 items"
```

### Adding Tests for Survivors

For each surviving mutant:

1. **Read the mutation**: What code change was made?
2. **Write a test**: Create a test that would fail if the mutation existed
3. **Re-run**: Verify the mutant is now killed

```bash
# After adding new tests
nwave mutation-test \
  --source src/checkout/ \
  --tests tests/unit/checkout/ \
  --threshold 85
```

### Common Options

```bash
# Focus on specific mutation types
nwave mutation-test \
  --source src/ \
  --tests tests/ \
  --mutation-types arithmetic,comparison,boolean

# Quick mode (fewer mutants, faster)
nwave mutation-test \
  --source src/ \
  --tests tests/ \
  --quick

# Verbose output
nwave mutation-test \
  --source src/ \
  --tests tests/ \
  --verbose
```

---

**Last Updated**: 2026-01-21
**Type**: How-to Guide
**Purity**: 95%+
