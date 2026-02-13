---
name: discovery-workflow
description: 4-phase discovery workflow with decision gates, phase transitions, success metrics, and state tracking
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
- **Duration**: 1-2 weeks
- **Min interviews**: 5
- **Techniques**: Mom Test interviews, Job Mapping
- **Core question**: Is this a real problem worth solving?

### Phase 2: Opportunity Mapping
- **Duration**: 1-2 weeks
- **Min interviews**: 10 cumulative
- **Techniques**: Opportunity Solution Tree, Opportunity Algorithm
- **Core question**: Which problems matter most?

### Phase 3: Solution Testing
- **Duration**: 2-4 weeks
- **Min interviews**: 5 per iteration
- **Techniques**: Hypothesis testing, Prototypes
- **Core question**: Does our solution actually work?

### Phase 4: Market Viability
- **Duration**: 2-4 weeks
- **Min interviews**: 5 + stakeholders
- **Techniques**: Lean Canvas, 4 Big Risks
- **Core question**: Can we build a viable business?

## Decision Gates

### G1: Problem to Opportunity
- **Proceed**: 5+ confirm pain + willingness to pay
- **Pivot**: Problem exists but differs from expected
- **Kill**: <20% confirm problem

### G2: Opportunity to Solution
- **Proceed**: Top 2-3 opportunities score >8 (out of max 20)
- **Pivot**: New opportunities discovered
- **Kill**: All opportunities low-value
- **Scoring**: Opportunity Score = Importance + Max(0, Importance - Satisfaction). Importance and Satisfaction each 1-10. Max score = 20. Score >8 means high importance with satisfaction gap.

### G3: Solution to Viability
- **Proceed**: >80% task completion, usability validated
- **Pivot**: Works but needs refinement
- **Kill**: Fundamental usability blocks

### G4: Viability to Build
- **Proceed**: All 4 risks addressed, model validated
- **Pivot**: Model needs adjustment
- **Kill**: No viable model found

## Success Metrics

### Phase 1: Problem Validation
| Metric | Target |
|--------|--------|
| Problem confirmation | >60% (3+ of 5 interviews) |
| Frequency | Weekly+ occurrence |
| Current spending | >$0 on workarounds |
| Emotional intensity | Frustration evident |

**Done when**: 5+ interviews completed, >60% confirmation rate, articulated in customer's words, 3+ specific examples documented.

**Threshold rationale**: 60% aligns with Mom Test guidance -- 3 of 5 consistent signals = proceed, <20% = kill. Combined with qualitative markers (spending, emotion) provides sufficient confidence.

### Phase 2: Opportunity Mapping
| Metric | Target |
|--------|--------|
| Opportunities identified | 5+ distinct |
| Top opportunity scores | >8 out of max 20 |
| Job step coverage | 80%+ have identified needs |
| Strategic alignment | Stakeholder confirmed |

**Done when**: Opportunity Solution Tree complete, top 2-3 prioritized, team aligned on priority.

### Phase 3: Solution Testing
| Metric | Target |
|--------|--------|
| Task completion | >80% |
| Value perception | >70% "would use/buy" |
| Comprehension | <10 sec to understand value |
| Key assumptions validated | >80% proven |

**Done when**: 5+ users tested per iteration, core flow usable, value + feasibility confirmed.

### Phase 4: Market Viability
| Metric | Target |
|--------|--------|
| Four big risks | All green/yellow |
| Channel validated | 1+ viable |
| Unit economics | LTV > 3x CAC (estimated) |
| Stakeholder signoff | Legal, finance, ops |

**Done when**: Lean Canvas complete, all risks acceptable, go/no-go documented.

## State Tracking Schema

Track discovery progress across sessions:

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
| 1 to 2 | G1 | 5+ interviews, >60% problem confirmation, problem in customer words, 3+ specific examples |
| 2 to 3 | G2 | OST complete, top 2-3 opportunities identified, scores >8, team alignment |
| 3 to 4 | G3 | 5+ users tested, >80% task completion, core flow usable, value + feasibility validated |
| 4 to handoff | G4 | Lean Canvas complete, all 4 risks acceptable, go/no-go documented, stakeholder sign-off |
