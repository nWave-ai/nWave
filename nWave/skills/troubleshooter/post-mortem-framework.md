---
name: post-mortem-framework
description: Blameless post-mortem structure, incident timeline reconstruction, response evaluation, and organizational learning
---

# Post-Mortem Framework

## Principles

- **Blameless**: focus on systems and processes, not individuals. People make reasonable decisions given the information they had at the time.
- **Evidence-based**: every finding backed by logs, metrics, or documented actions
- **Action-oriented**: every finding produces a concrete, assigned action item
- **Learning-focused**: capture what worked well alongside what failed

## Post-Mortem Document Structure

```markdown
# Post-Mortem: [Incident Title]

**Date**: [incident date]
**Duration**: [start to resolution]
**Severity**: [P0-P3]
**Author**: [analyst]

## Summary
[2-3 sentence overview: what happened, impact, resolution]

## Timeline
| Time | Event | Source |
|------|-------|--------|
| HH:MM | [event] | [log/metric/report] |

## Impact
- Users affected: [number/percentage]
- Duration of impact: [time]
- Business impact: [quantified if possible]
- Systems affected: [list]

## Root Cause Analysis
[5 Whys analysis with evidence at each level]

## Detection and Response
- Time to detect: [duration] -- [how it was detected]
- Time to respond: [duration] -- [first response action]
- Time to mitigate: [duration] -- [mitigation applied]
- Time to resolve: [duration] -- [permanent fix applied]

## What Went Well
- [positive observations about detection, response, or recovery]

## What Could Be Improved
- [areas where detection, response, or recovery fell short]

## Action Items
| ID | Action | Owner | Priority | Due Date |
|----|--------|-------|----------|----------|
| 1 | [specific action] | [team/person] | [P0-P3] | [date] |

## Lessons Learned
- [key takeaways for the organization]
```

## Incident Timeline Reconstruction

### Sources for Timeline Building
1. Monitoring alerts and dashboards (timestamps)
2. Deployment logs and CI/CD pipeline records
3. Communication channels (Slack, email, incident channels)
4. Version control (commits, merges, deploys)
5. User reports and support tickets

### Timeline Quality Checks
- Events are in chronological order with verified timestamps
- Gaps longer than 5 minutes are noted and explained
- Decision points are identified with available information at that time
- Causal relationships between events are noted

## Response Effectiveness Evaluation

### Detection
- Was the issue detected by monitoring or by users?
- How long between onset and detection?
- Were existing alerts relevant? Were any alerts missing?

### Escalation
- Was the right team engaged at the right time?
- Were escalation procedures followed?
- Was communication clear to stakeholders?

### Resolution
- Was the mitigation approach effective?
- Was rollback considered and was it viable?
- How long between mitigation and permanent fix?

## Organizational Learning

### Knowledge Capture
- Document root cause findings as reusable patterns
- Update runbooks with new failure scenarios
- Share learnings in team retrospectives

### Process Improvements
- Update monitoring and alerting based on detection gaps
- Revise deployment procedures based on rollback effectiveness
- Strengthen testing to cover the failure scenario

### Action Item Tracking
- Every action item has an owner and due date
- Track completion in team standups or sprint reviews
- Verify effectiveness of implemented actions after deployment
