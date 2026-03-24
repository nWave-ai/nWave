---
name: nw-post-mortem-framework
description: "Blameless post-mortem structure, incident timeline reconstruction, and organizational learning. Load when conducting incident post-mortems, analyzing outages, or building action items from failures."
user-invocable: false
disable-model-invocation: true
---

# Post-Mortem Framework

## Principles

- **Blameless**: focus on systems/processes, not individuals. People make reasonable decisions given available info.
- **Evidence-based**: every finding backed by logs, metrics, or documented actions
- **Action-oriented**: every finding produces concrete, assigned action item
- **Learning-focused**: capture what worked alongside what failed

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
- Time to detect: [duration] -- [how detected]
- Time to respond: [duration] -- [first action]
- Time to mitigate: [duration] -- [mitigation applied]
- Time to resolve: [duration] -- [permanent fix]

## What Went Well
- [positive observations about detection, response, recovery]

## What Could Be Improved
- [areas where detection, response, recovery fell short]

## Action Items
| ID | Action | Owner | Priority | Due Date |
|----|--------|-------|----------|----------|
| 1 | [specific action] | [team/person] | [P0-P3] | [date] |

## Lessons Learned
- [key takeaways for the organization]
```

## Incident Timeline Reconstruction

### Sources
1. Monitoring alerts/dashboards (timestamps) | 2. Deployment logs/CI-CD records
3. Communication channels (Slack, email, incident) | 4. VCS (commits, merges, deploys) | 5. User reports/support tickets

### Quality Checks
Events chronological with verified timestamps | gaps >5 min noted/explained | decision points identified with available info | causal relationships noted

## Response Effectiveness Evaluation

### Detection
Detected by monitoring or users? | Duration onset-to-detection? | Existing alerts relevant? Missing?

### Escalation
Right team at right time? | Procedures followed? | Communication clear to stakeholders?

### Resolution
Mitigation effective? | Rollback considered/viable? | Duration mitigation-to-permanent-fix?

## Organizational Learning

### Knowledge Capture
Document root causes as reusable patterns | update runbooks | share in retrospectives

### Process Improvements
Update monitoring/alerting per detection gaps | revise deployment per rollback effectiveness | strengthen testing for failure scenario

### Action Item Tracking
Every item has owner + due date | track in standups/sprint reviews | verify effectiveness post-deployment
