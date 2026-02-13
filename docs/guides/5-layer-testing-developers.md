# Layer 4 for Developers

**Version**: 1.5.2
**Date**: 2026-01-22
**Status**: Production Ready

Programmatic integration guide for invoking Layer 4 peer review in code.

**Prerequisites**: Python 3.11+ or TypeScript/Node.js environment.

**Related Docs**:
- [API Reference](../reference/5-layer-testing-api.md) (contracts)
- [For Users](5-layer-testing-users.md) (CLI)
- [For CI/CD](5-layer-testing-cicd.md) (pipelines)

---

## Quick Start

```python
from nwave.layer4 import ReviewOrchestrator

orchestrator = ReviewOrchestrator()
result = orchestrator.request_review(
    artifact=artifact,
    reviewer_agent_id="business-analyst-reviewer"
)

if result.approved:
    print("Ready for handoff")
```

---

## Basic Invocation

### Python

```python
from nwave.agents import load_agent, invoke_review
from nwave.layer4 import ReviewOrchestrator

# Step 1: Load primary agent and produce artifact
business_analyst = load_agent("business-analyst")
artifact = business_analyst.execute("*gather-requirements", context={
    "stakeholder_interviews": "interviews/stakeholders.md",
    "business_context": "context/ecommerce_checkout.md"
})

# Step 2: Trigger Layer 4 peer review
orchestrator = ReviewOrchestrator()
review_result = orchestrator.request_review(
    artifact=artifact,
    reviewer_agent_id="business-analyst-reviewer",
    auto_iterate=True,
    max_iterations=2
)

# Step 3: Handle review outcome
if review_result.approved:
    handoff_package = orchestrator.create_handoff_package(
        artifact=review_result.final_artifact,
        review_approval=review_result.approval_document,
        next_agent="solution-architect"
    )
    print(f"Artifact approved. Handoff to {handoff_package.next_agent}")
else:
    print(f"Review failed after {review_result.iteration_count} iterations")
    print(f"Unresolved issues: {review_result.unresolved_critical_issues}")
    orchestrator.escalate_to_human(review_result)
```

### TypeScript

```typescript
import { loadAgent, ReviewOrchestrator } from '@nwave/agents';

async function executeWithPeerReview() {
  // Step 1: Produce artifact
  const businessAnalyst = await loadAgent('business-analyst');
  const artifact = await businessAnalyst.execute('*gather-requirements', {
    stakeholderInterviews: 'interviews/stakeholders.md',
    businessContext: 'context/ecommerce_checkout.md'
  });

  // Step 2: Request peer review
  const orchestrator = new ReviewOrchestrator();
  const reviewResult = await orchestrator.requestReview({
    artifact,
    reviewerAgentId: 'business-analyst-reviewer',
    autoIterate: true,
    maxIterations: 2
  });

  // Step 3: Handle outcome
  if (reviewResult.approved) {
    const handoffPackage = orchestrator.createHandoffPackage({
      artifact: reviewResult.finalArtifact,
      reviewApproval: reviewResult.approvalDocument,
      nextAgent: 'solution-architect'
    });
    console.log(`Artifact approved. Handoff to ${handoffPackage.nextAgent}`);
  } else {
    console.log(`Review failed after ${reviewResult.iterationCount} iterations`);
    await orchestrator.escalateToHuman(reviewResult);
  }
}
```

---

## Custom Review Criteria

Customize review focus with specific criteria:

```python
from nwave.layer4 import ReviewOrchestrator, ReviewCriteria

custom_criteria = ReviewCriteria(
    critical_bias_patterns=["technology_assumption", "happy_path_only"],
    required_completeness_dimensions=["stakeholders", "error_scenarios", "performance"],
    clarity_thresholds={
        "measurability_percentage": 0.90,
        "vagueness_tolerance": 0.05
    },
    testability_requirements={
        "acceptance_criteria_testable": 0.95
    }
)

review_result = orchestrator.request_review(
    artifact=artifact,
    reviewer_agent_id="business-analyst-reviewer",
    criteria=custom_criteria
)
```

---

## Event Callbacks

Add callbacks for monitoring and integration:

```python
review_result = orchestrator.request_review(
    artifact=artifact,
    reviewer_agent_id="business-analyst-reviewer",
    on_issue_detected=lambda issue: log_to_monitoring(issue),
    on_approval=lambda approval: notify_team(approval),
    on_rejection=lambda rejection: create_escalation_ticket(rejection)
)
```

---

## Error Handling

Handle specific error conditions:

```python
from nwave.layer4.exceptions import (
    ReviewerNotFoundError,
    MaxIterationsExceededError,
    ReviewerDisagreementError,
    ArtifactValidationError
)

try:
    review_result = orchestrator.request_review(
        artifact=artifact,
        reviewer_agent_id="business-analyst-reviewer"
    )
except ReviewerNotFoundError as e:
    print(f"Reviewer not found: {e.reviewer_id}")
    print(f"Available reviewers: {e.available_reviewers}")

except MaxIterationsExceededError as e:
    print(f"Max iterations exceeded: {e.iteration_count}/{e.max_iterations}")
    print(f"Unresolved issues: {e.unresolved_issues}")
    escalate_to_human_facilitator(e)

except ReviewerDisagreementError as e:
    print(f"Deadlock on issue: {e.issue_id}")
    print(f"Primary stance: {e.primary_stance}")
    print(f"Reviewer stance: {e.reviewer_stance}")
    escalate_for_mediation(e)

except ArtifactValidationError as e:
    print(f"Artifact failed Layer 1 validation: {e.validation_errors}")
    print("Fix Layer 1 issues before requesting Layer 4 review")
```

---

## Review Orchestration API

### ReviewOrchestrator Methods

| Method | Description |
|--------|-------------|
| `request_review(...)` | Request peer review |
| `create_handoff_package(...)` | Create handoff package |
| `escalate_to_human(...)` | Escalate failed review |
| `get_review_status(review_id)` | Check review status |
| `cancel_review(review_id)` | Cancel ongoing review |

### Example: Full Workflow

```python
orchestrator = ReviewOrchestrator()

# Request review
result = orchestrator.request_review(
    artifact=artifact,
    reviewer_agent_id="business-analyst-reviewer",
    auto_iterate=True,
    max_iterations=2
)

# Check metrics
print(f"Duration: {result.metrics.review_duration_ms}ms")
print(f"Issues: {result.metrics.issue_count}")
print(f"Quality: {result.metrics.quality_scores}")

# Create handoff if approved
if result.approved:
    package = orchestrator.create_handoff_package(
        artifact=result.final_artifact,
        review_approval=result.approval_document,
        next_agent="solution-architect"
    )
```

---

## Testing Reviewer Invocation

### Unit Test Example

```python
import pytest
from nwave.layer4 import ReviewOrchestrator
from nwave.layer4.mocks import MockReviewer

def test_review_approval():
    orchestrator = ReviewOrchestrator()
    orchestrator.set_reviewer(MockReviewer(approval_status="approved"))

    result = orchestrator.request_review(
        artifact=sample_artifact,
        reviewer_agent_id="business-analyst-reviewer"
    )

    assert result.approved is True
    assert result.iteration_count == 1

def test_review_rejection():
    orchestrator = ReviewOrchestrator()
    orchestrator.set_reviewer(MockReviewer(
        approval_status="rejected_pending_revisions",
        issues=[{"severity": "critical", "issue": "test"}]
    ))

    result = orchestrator.request_review(
        artifact=sample_artifact,
        reviewer_agent_id="business-analyst-reviewer",
        auto_iterate=False
    )

    assert result.approved is False
    assert len(result.unresolved_critical_issues) == 1
```

---

## Troubleshooting

### ReviewerNotFoundError

**Cause**: Reviewer agent not installed or wrong ID.

**Fix**:
```python
# List available reviewers
from nwave.agents import list_reviewers
print(list_reviewers())

# Verify installation
import os
reviewers_dir = os.environ.get("NWAVE_REVIEWERS_DIR")
print(os.listdir(reviewers_dir))
```

### Timeout Issues

**Cause**: Review taking too long.

**Fix**:
```python
orchestrator = ReviewOrchestrator(
    timeout_seconds=600  # Increase to 10 minutes
)
```

### Layer 1 Validation Failure

**Cause**: Artifact doesn't pass basic validation.

**Fix**: Run Layer 1 tests first:
```python
from nwave.layer1 import validate_artifact

errors = validate_artifact(artifact)
if errors:
    print(f"Fix these before Layer 4: {errors}")
```

---

## Layer 5: Mutation Testing

Layer 5 validates that your test suite effectively catches defects by introducing mutations.

### Basic Mutation Test

```python
from nwave.layer5 import MutationOrchestrator

orchestrator = MutationOrchestrator()
result = orchestrator.run_mutation_tests(
    source_path="src/checkout/",
    test_path="tests/unit/checkout/",
    mutation_score_threshold=0.85  # 85% minimum
)

if result.passed:
    print(f"Mutation score: {result.score:.1%} (threshold: 85%)")
else:
    print(f"FAILED: {result.score:.1%} < 85%")
    print(f"Surviving mutants: {len(result.surviving_mutants)}")
```

### TypeScript

```typescript
import { MutationOrchestrator } from '@nwave/layer5';

const orchestrator = new MutationOrchestrator();
const result = await orchestrator.runMutationTests({
  sourcePath: 'src/checkout/',
  testPath: 'tests/unit/checkout/',
  mutationScoreThreshold: 0.85
});

if (result.passed) {
  console.log(`Mutation score: ${(result.score * 100).toFixed(1)}%`);
}
```

### Targeting Specific Mutations

```python
from nwave.layer5 import MutationOrchestrator, MutationConfig

config = MutationConfig(
    mutation_types=[
        "arithmetic_operator",    # + → -
        "comparison_boundary",    # < → <=
        "boolean_literal",        # true → false
        "return_value"            # return x → return None
    ],
    exclude_patterns=["**/test_*.py", "**/conftest.py"],
    parallel_workers=4
)

result = orchestrator.run_mutation_tests(
    source_path="src/",
    test_path="tests/",
    config=config
)
```

### Analyzing Surviving Mutants

```python
for mutant in result.surviving_mutants:
    print(f"File: {mutant.file_path}:{mutant.line_number}")
    print(f"Type: {mutant.mutation_type}")
    print(f"Original: {mutant.original_code}")
    print(f"Mutated:  {mutant.mutated_code}")
    print(f"Suggestion: Add test to detect this mutation")
    print("---")
```

---

**Last Updated**: 2026-01-21
**Type**: How-to Guide
**Purity**: 95%+
