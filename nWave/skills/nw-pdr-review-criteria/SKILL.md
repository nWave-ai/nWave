---
name: nw-pdr-review-criteria
description: Evidence quality validation and decision gate criteria for product discovery reviews
disable-model-invocation: true
---

# Review Criteria -- Product Discovery Review

## Evidence Quality Validation

### Past Behavior Indicators (Good)
"Tell me about the last time..." | "When did you last..." | "What happened when..." | "Walk me through how you..." | "What did you try..." | "How much have you spent on..."
Specific dates, dollar amounts, named tools, concrete examples, emotional frustration language

### Future Intent Red Flags (Reject)
"Would you use/pay/like..." | "Do you think..." | "Imagine if..." | "What if we..."
Flag and reject if >20% of evidence is future-intent.

### Validation Thresholds
- Past behavior ratio: >80% (reject if fail, require re-interview)
- Specific examples: min 3 concrete per finding (warn if fail)
- Customer language: quotes in customer words, not paraphrased (warn if fail)

## Sample Size Minimums

| Phase | Minimum | High Confidence | Notes |
|-------|---------|-----------------|-------|
| 1: Problem | 5 | 10 | Interviews required |
| 2: Opportunity | 10 | 20 | Quantitative supplements, not replaces |
| 3: Solution | 5 per iteration | 3 iterations max | Before decision |
| 4: Viability | 5 | -- | Stakeholder review required |

Pivot decision rule: min 5 consistent signals. Block decisions on fewer.

## Decision Gate Criteria

### G1: Problem to Opportunity
Proceed: 5+ confirm pain + willingness to pay | Pivot: differs from expected | Kill: <20% confirm
Checks: 5+ interviews, >60% confirmation, customer words, 3+ examples

### G2: Opportunity to Solution
Proceed: top 2-3 score >8 (0-20) | Pivot: new opportunities | Kill: all low-value
Checks: OST complete with 5+, scores correct (Importance + Max(0, Importance - Satisfaction)), top >8/20

### G3: Solution to Viability
Proceed: >80% task completion, usability validated | Pivot: needs refinement | Kill: fundamental blocks
Checks: 5+ users/iteration, >80% completion, core flow usable, value validated

### G4: Viability to Build
Proceed: 4 risks addressed, model validated | Pivot: adjustment needed | Kill: no viable model
Checks: Lean Canvas complete, all risks green/yellow, stakeholder sign-off

## Bias Types

### Confirmation Bias (critical)
Signals: only positive quotes | skeptics not interviewed | disconfirming evidence dismissed | same questions for "right" answers
Fix: include skeptics, actively seek disconfirming evidence

### Selection Bias (high)
Signals: all existing customers | no churned/non-adopters | lacks diversity | single-enthusiast referral chain
Fix: random/diverse selection, include skeptics and non-users

### Discovery Theater (critical)
Signals: conclusion decided before research | findings match hypothesis perfectly | no surprises | idea-in = idea-shipped
Fix: track idea evolution, expect 50%+ ideas to change

### Sample Size Problem (high)
Signals: major decisions on 2-3 interviews | single quote as "validation" | pivot on one signal
Fix: min 5 interviews per segment, 5+ signals for decisions

## Anti-Patterns

### Interview Anti-Patterns
| Pattern | Detection | Bad | Good | Severity |
|---------|-----------|-----|------|----------|
| Leading questions | Suggests desired answer | "Don't you think this would save time?" | "Tell me about the last time you tried to save time on this" | high |
| Future-intent | Hypothetical behavior | "Would you use this feature?" | "What have you tried to solve this problem?" | critical |
| Compliments as validation | Accepting "that's cool" | "They loved the idea!" | "They committed to follow-up and referral" | high |
| Talking > listening | >30% interviewer talk | Long questions, short responses | Open questions, extended answers | medium |

### Process Anti-Patterns
| Pattern | Detection | Severity |
|---------|-----------|----------|
| Skipping to solutions | Solution before problem validated | critical |
| Demographic segmentation | Segments by demographics not jobs | medium |
| Building before testing | Code before Phase 3 | critical |

### Strategic Anti-Patterns
| Pattern | Detection | Severity |
|---------|-----------|----------|
| Premature pivoting | Direction change on 1-2 signals (need 5+) | high |
| Solution love | Defending despite evidence, dismissing critics | high |
| Sole source of truth | Only quant OR qual, not both | medium |

## Pre-Approval Checklist

### Evidence Quality
- [ ] Past behavior ratio >80% | [ ] No critical future-intent | [ ] Customer language preserved

### Sample Sizes
- [ ] Phase 1: 5+ | [ ] Phase 2: 10+ | [ ] Phase 3: 5+/iteration | [ ] Phase 4: 5+ with stakeholders

### Decision Gates
- [ ] All gates properly evaluated | [ ] Criteria documented with evidence | [ ] Decision justified

### Bias Check
- [ ] No confirmation bias | [ ] No selection bias | [ ] No discovery theater | [ ] Sample size adequate

### Anti-Patterns
- [ ] No critical interview anti-patterns | [ ] No critical process anti-patterns | [ ] No critical strategic anti-patterns

## Approval Decision

- **Approved**: all checks pass, no critical issues. Formal handoff to product-owner.
- **Conditionally approved**: minor issues only (no critical/high). Approval with recommendations.
- **Rejected**: any critical/high issue. Structured rejection with remediation. Blocks handoff.
