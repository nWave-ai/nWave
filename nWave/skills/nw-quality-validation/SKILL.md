---
name: nw-quality-validation
description: Type-specific validation checklists, six quality characteristics, and quality gate thresholds for documentation assessment
disable-model-invocation: true
---

# Quality Validation

## Six Quality Characteristics

- **Accuracy**: Factually correct, technically sound, current | Validation: expert review, automated testing
- **Completeness**: All necessary info present for doc type | Validation: checklist, gap analysis
- **Clarity**: Easy to understand, logical flow, appropriate level | Validation: Flesch 70-80
- **Consistency**: Uniform terminology, formatting, structure | Validation: style guide compliance
- **Correctness**: Proper grammar, spelling, punctuation | Validation: automated check, zero errors
- **Usability**: User achieves goal efficiently | Validation: task success, DIVIO type purpose served

## Quality Gate Thresholds

| Metric | Threshold |
|--------|-----------|
| Readability (Flesch) | 70-80 |
| Spelling errors | 0 |
| Broken links | 0 |
| Style compliance | 95%+ |
| Type purity | 80%+ single type |

## Type-Specific Validation Checklists

### Tutorial Checklist
- [ ] Completable without external references | [ ] Steps numbered and sequential
- [ ] Each step has verifiable outcome | [ ] No assumed prior knowledge | [ ] Builds confidence

### How-to Checklist
- [ ] Clear goal stated upfront | [ ] Assumes fundamentals known
- [ ] Single task focus | [ ] Ends with completion indicator | [ ] No basics teaching

### Reference Checklist
- [ ] All parameters documented | [ ] Return values specified
- [ ] Error conditions listed | [ ] Examples per entry | [ ] No narrative

### Explanation Checklist
- [ ] Addresses "why" not "what" | [ ] Provides context and reasoning
- [ ] Discusses alternatives | [ ] No task steps | [ ] Builds conceptual model

## Verdict Criteria

- **approved**: Passes all type-specific validation, no collapse violations, meets quality gates
- **needs-revision**: Minor issues fixable in place (clarity, missing examples, small gaps)
- **restructure-required**: Collapse detected requiring split, or fundamental type mismatch
