---
name: nw-discovery-workflow
description: 4-phase discovery workflow with decision gates, phase transitions, success metrics, and state tracking
disable-model-invocation: true
---

# Discovery Workflow

## 4-Phase Overview

```
PHASE 1              PHASE 2              PHASE 3              PHASE 4
Problem Validation   Opportunity Mapping  Solution Testing     Market Viability
      |                    |                    |                    |
      v                    v                    v                    v
"Is this real?"      "Which matters?"     "Does it work?"      "Viable business?"
```

## Phase Details

### Phase 1: Problem Validation
Duration: 1-2 weeks | Min interviews: 5 | Techniques: Mom Test, Job Mapping
Core question: Is this a real problem worth solving?

### Phase 2: Opportunity Mapping
Duration: 1-2 weeks | Min interviews: 10 cumulative | Techniques: OST, Opportunity Algorithm
Core question: Which problems matter most?

### Phase 3: Solution Testing
Duration: 2-4 weeks | Min interviews: 5 per iteration | Techniques: hypothesis testing, prototypes
Core question: Does our solution actually work?

### Phase 4: Market Viability
Duration: 2-4 weeks | Min interviews: 5 + stakeholders | Techniques: Lean Canvas, 4 Big Risks
Core question: Can we build a viable business?

## Decision Gates

### G1: Problem to Opportunity
Proceed: 5+ confirm pain + willingness to pay | Pivot: problem differs from expected | Kill: <20% confirm

### G2: Opportunity to Solution
Proceed: top 2-3 score >8 (max 20) | Pivot: new opportunities discovered | Kill: all low-value
Scoring: Score = Importance + Max(0, Importance - Satisfaction). Each 1-10. >8 = high importance with satisfaction gap.

### G3: Solution to Viability
Proceed: >80% task completion, usability validated | Pivot: needs refinement | Kill: fundamental blocks

### G4: Viability to Build
Proceed: all 4 risks addressed, model validated | Pivot: model needs adjustment | Kill: no viable model

## Success Metrics

### Phase 1: Problem Validation
| Metric | Target |
|--------|--------|
| Problem confirmation | >60% (3+ of 5) |
| Frequency | Weekly+ |
| Current spending | >$0 on workarounds |
| Emotional intensity | Frustration evident |

Done when: 5+ interviews, >60% confirmation, articulated in customer words, 3+ examples.
Threshold: 60% aligns with Mom Test -- 3/5 consistent signals = proceed, <20% = kill. Combined with qualitative markers.

### Phase 2: Opportunity Mapping
| Metric | Target |
|--------|--------|
| Opportunities identified | 5+ distinct |
| Top scores | >8 / max 20 |
| Job step coverage | 80%+ |
| Strategic alignment | Stakeholder confirmed |

Done when: OST complete, top 2-3 prioritized, team aligned.

### Phase 3: Solution Testing
| Metric | Target |
|--------|--------|
| Task completion | >80% |
| Value perception | >70% "would use/buy" |
| Comprehension | <10 sec to understand |
| Key assumptions validated | >80% proven |

Done when: 5+ users per iteration, core flow usable, value + feasibility confirmed.

### Phase 4: Market Viability
| Metric | Target |
|--------|--------|
| Four big risks | All green/yellow |
| Channel validated | 1+ viable |
| Unit economics | LTV > 3x CAC (estimated) |
| Stakeholder signoff | Legal, finance, ops |

Done when: Lean Canvas complete, all risks acceptable, go/no-go documented.

## State Tracking Schema

```yaml
current_phase: "1|2|3|4"
phase_started: "ISO timestamp"
interviews_completed: "count by phase"
assumptions_tracked: "list with risk scores"
opportunities_identified: "list with scores"
decision_gates_evaluated: "G1|G2|G3|G4 status"
artifacts_created: "list of file paths"
```

## Phase Transition Requirements

| Transition | Gate | Requirements |
|-----------|------|-------------|
| 1 to 2 | G1 | 5+ interviews, >60% confirmation, customer words, 3+ examples |
| 2 to 3 | G2 | OST complete, top 2-3 identified, scores >8, team alignment |
| 3 to 4 | G3 | 5+ users tested, >80% task completion, core flow usable, validated |
| 4 to handoff | G4 | Lean Canvas complete, 4 risks acceptable, go/no-go, stakeholder sign-off |
