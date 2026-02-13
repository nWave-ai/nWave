---
name: review-criteria
description: Evidence quality validation and decision gate criteria for product discovery reviews
---

# Review Criteria -- Product Discovery Review

## Evidence Quality Validation

### Past Behavior Indicators (Good)
- "Tell me about the last time..."
- "When did you last..."
- "What happened when..."
- "Walk me through how you..."
- "What did you try..."
- "How much have you spent on..."
- Specific dates, dollar amounts, named tools, concrete examples, emotional frustration language

### Future Intent Red Flags (Reject)
- "Would you use/pay/like..."
- "Do you think..."
- "Imagine if..."
- "What if we..."
- Flag and reject if >20% of evidence is future-intent

### Validation Thresholds
- Past behavior ratio: >80% of evidence from past behavior (reject if fail, require re-interview)
- Specific examples: minimum 3 concrete examples per finding (warn if fail)
- Customer language: quotes in customer's words, not paraphrased (warn if fail)

## Sample Size Minimums

| Phase | Minimum | High Confidence | Notes |
|-------|---------|-----------------|-------|
| Phase 1: Problem | 5 | 10 | Interviews required |
| Phase 2: Opportunity | 10 | 20 | Quantitative supplements but does not replace interviews |
| Phase 3: Solution | 5 per iteration | 3 iterations max | Before decision |
| Phase 4: Viability | 5 | -- | Stakeholder review required |

Pivot decision rule: minimum 5 consistent signals. Block any pivot/proceed/kill decision on fewer.

## Decision Gate Criteria

### G1: Problem to Opportunity
- Proceed: 5+ confirm pain + willingness to pay
- Pivot: problem exists but differs from expected
- Kill: <20% confirm problem
- Checks: 5+ interviews, >60% confirmation, articulated in customer words, 3+ examples

### G2: Opportunity to Solution
- Proceed: top 2-3 opportunities score >8 (scale 0-20)
- Pivot: new opportunities discovered
- Kill: all opportunities low-value
- Checks: OST complete with 5+ opportunities, scores calculated correctly (Importance + Max(0, Importance - Satisfaction)), top >8/20
- Note: score >8 means importance minimum 8 with satisfaction gap

### G3: Solution to Viability
- Proceed: >80% task completion, usability validated
- Pivot: works but needs refinement
- Kill: fundamental usability blocks
- Checks: 5+ users per iteration, >80% task completion, core flow usable without assistance, value assumptions validated

### G4: Viability to Build
- Proceed: all 4 risks addressed, model validated
- Pivot: model needs adjustment
- Kill: no viable model found
- Checks: Lean Canvas complete, value/usability/feasibility/viability risks all green/yellow, stakeholder sign-off

## Bias Types

### Confirmation Bias (severity: critical)
- Signals: only positive quotes cited, skeptics not interviewed, disconfirming evidence dismissed, same questions to get "right" answers
- Fix: include skeptics, actively seek disconfirming evidence

### Selection Bias (severity: high)
- Signals: all interviewees are existing customers, no churned/non-adopters, lacks diversity, referral chain from single enthusiast
- Fix: random/diverse selection, include skeptics and non-users

### Discovery Theater (severity: critical)
- Signals: conclusion decided before research, findings perfectly match hypothesis, no surprises or pivots, idea-in equals idea-shipped
- Fix: track idea evolution, expect 50%+ ideas to change significantly

### Sample Size Problem (severity: high)
- Signals: major decisions on 2-3 interviews, single quote as "validation", pivot on one signal, proceed on one enthusiast
- Fix: minimum 5 interviews per segment, 5+ signals for decisions

## Anti-Patterns

### Interview Anti-Patterns
| Pattern | Detection | Bad Example | Good Example | Severity |
|---------|-----------|-------------|--------------|----------|
| Leading questions | Suggests desired answer | "Don't you think this would save time?" | "Tell me about the last time you tried to save time on this" | high |
| Future-intent questions | Hypothetical behavior | "Would you use this feature?" | "What have you tried to solve this problem?" | critical |
| Compliments as validation | Accepting "that's cool" | "They loved the idea!" | "They committed to follow-up and referral" | high |
| Talking > listening | >30% interviewer talk time | Long questions, short responses | Open questions, extended answers | medium |

### Process Anti-Patterns
| Pattern | Detection | Severity |
|---------|-----------|----------|
| Skipping to solutions | Solution discussed before problem validated | critical |
| Demographic segmentation | Segments by demographics not jobs | medium |
| Building before testing | Code before Phase 3 validation | critical |

### Strategic Anti-Patterns
| Pattern | Detection | Severity |
|---------|-----------|----------|
| Premature pivoting | Direction change on 1-2 signals (need 5+) | high |
| Solution love | Defending solution despite evidence, dismissing critics | high |
| Sole source of truth | Only quant OR qual, not both | medium |

## Pre-Approval Checklist

### Evidence Quality
- [ ] Past behavior ratio >80%
- [ ] No critical future-intent evidence
- [ ] Customer language preserved

### Sample Sizes
- [ ] Phase 1: 5+ interviews
- [ ] Phase 2: 10+ data points
- [ ] Phase 3: 5+ per iteration
- [ ] Phase 4: 5+ with stakeholders

### Decision Gates
- [ ] All completed gates properly evaluated
- [ ] Gate criteria documented with evidence
- [ ] Proceed/pivot/kill decision justified

### Bias Check
- [ ] No confirmation bias detected
- [ ] No selection bias detected
- [ ] No discovery theater patterns
- [ ] Sample size adequate for decisions

### Anti-Patterns
- [ ] No critical interview anti-patterns
- [ ] No critical process anti-patterns
- [ ] No critical strategic anti-patterns

## Approval Decision

- **Approved**: all checks pass, no critical issues. Formal approval for handoff to product-owner.
- **Conditionally approved**: minor issues only (no critical/high). Approval with documented recommendations.
- **Rejected**: any critical or high-severity issue. Structured rejection with remediation guidance. Blocks handoff until resolved.
