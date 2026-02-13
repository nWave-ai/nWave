# 5-Layer Testing API Reference

**Version**: 2.0
**Date**: 2026-02-13
**Status**: Production Ready

API contracts, interfaces, configuration schemas, and technical specifications for nWave 5-layer testing framework and reviewer agent architecture.

**Related Documentation**:
- **How-to guides:** Setup, configuration, and integration examples
- **Architecture docs:** Design patterns, agent pipeline flow, and layer relationships
- **Reviewer agents:** Individual agent specifications at `~/.claude/agents/nw/`

---

## Input Contracts

### ReviewRequest

```typescript
interface ReviewRequest {
  artifact: Artifact;                    // Artifact to review
  reviewerAgentId: string;               // Reviewer agent ID (e.g., "business-analyst-reviewer")
  autoIterate?: boolean;                 // Auto-handle revision cycles (default: true)
  maxIterations?: number;                // Max revision iterations (default: 2)
  criteria?: ReviewCriteria;             // Custom review criteria (optional)
  callbacks?: ReviewCallbacks;           // Event callbacks (optional)
}
```

### Artifact

```typescript
interface Artifact {
  id: string;
  path: string;                          // File path (e.g., "docs/requirements/requirements.md")
  content: string;                       // Artifact content
  metadata: {
    created: string;                     // ISO 8601 timestamp
    agent_id: string;                    // Primary agent ID
    command: string;                     // Command executed
    version: string;                     // Artifact version
  };
}
```

### ReviewCriteria

```typescript
interface ReviewCriteria {
  critical_bias_patterns: string[];      // e.g., ["technology_assumption", "happy_path_only"]
  required_completeness_dimensions: string[];
  clarity_thresholds: {
    measurability_percentage: number;    // 0.0-1.0
    vagueness_tolerance: number;         // 0.0-1.0
  };
  testability_requirements: {
    acceptance_criteria_testable: number; // 0.0-1.0
  };
}
```

---

## Output Contracts

### ReviewResult

```typescript
interface ReviewResult {
  approved: boolean;                     // True if review approved
  iterationCount: number;                // Number of iterations (1 or 2)
  finalArtifact: Artifact;               // Final approved/escalated artifact
  approvalDocument?: ReviewApproval;     // Approval document if approved
  reviewFeedback: ReviewFeedback[];      // All review feedback (iterations)
  unresolvedCriticalIssues?: Issue[];    // Critical issues if not approved
  escalationRequired: boolean;           // True if human escalation needed
  metrics: ReviewMetrics;                // Performance and quality metrics
}
```

### ReviewApproval

```typescript
interface ReviewApproval {
  reviewId: string;
  reviewer: string;
  approvalTimestamp: string;
  qualityAssessment: {
    completenessScore: number;           // 0.0-1.0
    clarityScore: number;                // 0.0-1.0
    testabilityScore: number;            // 0.0-1.0
  };
  handoffReadiness: "READY" | "CONDITIONAL" | "NOT_READY";
}
```

### ReviewFeedback

```typescript
interface ReviewFeedback {
  reviewId: string;
  iteration: number;
  strengths: string[];
  issues: Issue[];
  recommendations: string[];
  approvalStatus: "approved" | "rejected_pending_revisions" | "conditionally_approved";
}
```

### Issue

```typescript
interface Issue {
  category: "confirmation_bias" | "completeness_gaps" | "clarity_issues" | "testability_concerns";
  issue: string;
  impact: string;
  recommendation: string;
  severity: "critical" | "high" | "medium" | "low";
  location?: string;
}
```

### ReviewMetrics

```typescript
interface ReviewMetrics {
  reviewDurationMs: number;
  issueCount: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
  qualityScores: {
    completeness: number;
    clarity: number;
    testability: number;
  };
}
```

---

## Error Types

### Exception Classes

```python
class ReviewerNotFoundError(Exception):
    """Raised when reviewer agent not found."""
    reviewer_id: str
    available_reviewers: list[str]

class MaxIterationsExceededError(Exception):
    """Raised when max iterations reached without approval."""
    iteration_count: int
    max_iterations: int
    unresolved_issues: list[Issue]

class ReviewerDisagreementError(Exception):
    """Raised when reviewer and primary agent deadlock."""
    issue_id: str
    primary_stance: str
    reviewer_stance: str

class ArtifactValidationError(Exception):
    """Raised when artifact fails Layer 1 validation."""
    validation_errors: list[str]
```

---

## Configuration Reference

### Environment Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `NWAVE_HOME` | path | `$HOME/.nwave` | Installation directory |
| `NWAVE_AGENTS_DIR` | path | `$HOME/.claude/agents/nw` | Agents directory |
| `NWAVE_REVIEWERS_DIR` | path | `$HOME/.claude/agents/nw` | Reviewers directory (same as agents) |
| `LAYER4_AUTO_TRIGGER` | bool | `true` | Auto-trigger after Layer 1 pass |
| `LAYER4_MAX_ITERATIONS` | int | `2` | Maximum revision iterations |
| `LAYER4_FAIL_ON_CRITICAL` | bool | `true` | Fail pipeline on critical issues |
| `LAYER4_ESCALATION_EMAIL` | string | - | Escalation email address |
| `LAYER4_METRICS_ENABLED` | bool | `true` | Enable metrics collection |
| `REVIEWER_TIMEOUT_SECONDS` | int | `300` | Review timeout (seconds) |
| `REVIEWER_CACHE_ENABLED` | bool | `true` | Cache review results |
| `REVIEWER_PARALLEL_REVIEWS` | int | `4` | Parallel review concurrency |

### Configuration File Schema

**Location**: `.nwave/layer4.yaml`

```yaml
layer4:
  # Automation settings
  automation:
    auto_trigger: boolean                # Auto-trigger after Layer 1
    trigger_on:                          # Trigger events
      - layer_1_pass
      - critical_handoff_points
    async: boolean                       # Async execution (default: false)

  # Iteration settings
  iterations:
    max: integer                         # Max iterations (default: 2)
    escalate_on_limit: boolean           # Escalate on max (default: true)

  # Approval criteria
  approval:
    block_on_critical: boolean           # Block on critical issues
    block_on_high_count: integer         # Block threshold for high issues
    require_explicit_approval: boolean

  # Reviewer settings
  reviewers:
    timeout_seconds: integer             # Review timeout
    cache_reviews: boolean               # Enable caching
    parallel_reviews: integer            # Concurrency limit

  # Metrics and monitoring
  metrics:
    enabled: boolean
    export_to:                           # Export destinations
      - prometheus
      - datadog
      - cloudwatch
    alert_on:                            # Alert triggers
      - critical_issues_detected
      - approval_rate_below_threshold

  # Escalation
  escalation:
    email: string                        # Escalation email
    slack_channel: string                # Slack channel
    create_ticket: boolean               # Create ticket
    ticket_system: string                # jira, github, etc.
```

### Example Configuration

```yaml
layer4:
  automation:
    auto_trigger: true
    trigger_on:
      - layer_1_pass
      - critical_handoff_points
    async: false

  iterations:
    max: 2
    escalate_on_limit: true

  approval:
    block_on_critical: true
    block_on_high_count: 3
    require_explicit_approval: true

  reviewers:
    timeout_seconds: 300
    cache_reviews: true
    parallel_reviews: 4

  metrics:
    enabled: true
    export_to:
      - prometheus
      - datadog
    alert_on:
      - critical_issues_detected
      - approval_rate_below_threshold

  escalation:
    email: "team@example.com"
    slack_channel: "#quality-alerts"
    create_ticket: true
    ticket_system: "jira"
```

---

## Pass/Fail Criteria

### Blocking Criteria (Fail Pipeline)

| Condition | Threshold | Description |
|-----------|-----------|-------------|
| `critical_issues_count` | `> 0` | Any critical issue blocks |
| `high_issues_count` | `> 3` | More than 3 high issues block |
| `approval_status` | `!= approved` | Only approved proceeds |
| `completeness_score` | `< 0.90` | 90% completeness required |
| `testability_score` | `< 0.85` | 85% testability required |

### Warning Criteria (Pass with Warnings)

| Condition | Threshold | Action |
|-----------|-----------|--------|
| `high_issues_count` | `> 0` | Notify team |
| `medium_issues_count` | `> 5` | Notify team |
| `iteration_count` | `> 1` | Log quality concern |

---

## Metrics Schema

### Review Metrics

```yaml
layer4_review_duration_seconds:
  type: histogram
  description: Review duration in seconds
  labels: [reviewer, artifact_type]

layer4_issues_per_review:
  type: counter
  description: Issues identified per review
  labels: [reviewer, severity]

layer4_approval_rate:
  type: gauge
  description: Approval rate (0.0-1.0)
  labels: [reviewer]

layer4_iteration_count:
  type: histogram
  description: Iterations to approval
  labels: [reviewer, artifact_type]
```

---

## CLI Commands Reference

| Command | Description |
|---------|-------------|
| `nwave review --artifact <path> --reviewer <id>` | Request review |
| `nwave review --interactive` | Interactive review mode |
| `nwave review --iteration 2` | Re-submit for iteration 2 |
| `nwave status --layer 4` | Check Layer 4 status |
| `nwave validate-agent <id>` | Validate reviewer agent |
| `nwave test-reviewer <id> --dry-run` | Test reviewer |
| `nwave escalate --issue <path>` | Escalate issue |
| `nwave mediate --issue <id>` | Request mediation |

### Command Flags

| Flag | Description |
|------|-------------|
| `--fail-on-critical` | Fail on critical issues |
| `--output-format <json\|yaml\|text>` | Output format |
| `--dimensions <list>` | Review dimensions |
| `--verbose` | Verbose output |
| `--debug` | Debug mode |
| `--dry-run` | Dry run (no changes) |

---

## Framework Overview

The nWave framework includes:
- **11 Primary Agents:** product-discoverer, product-owner, solution-architect, acceptance-designer, software-crafter, platform-architect, researcher, troubleshooter, data-engineer, documentarist, agent-builder
- **11 Reviewer Agents:** Matching reviewers for each primary agent (e.g., product-discoverer-reviewer)
- **5 Testing Layers:** Layer 1-5 validation, review, and adversarial verification pipeline

All reviewer agents are installed to `~/.claude/agents/nw/` via `pipx install nwave-ai && nwave-ai install`.

---

**Last Updated**: 2026-02-13
**Type**: Reference
**Purity**: 98%+
**DIVIO Classification**: Reference (lookup-focused API contracts and configuration schemas)
