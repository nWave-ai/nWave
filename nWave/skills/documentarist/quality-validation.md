---
name: quality-validation
description: Type-specific validation checklists, six quality characteristics, and quality gate thresholds for documentation assessment
---

# Quality Validation

## Six Quality Characteristics

### Accuracy
- **Definition**: Factually correct, technically sound, current
- **Validation**: Expert review; automated testing where possible

### Completeness
- **Definition**: All necessary information present for the document type
- **Validation**: Checklist validation; gap analysis against type requirements

### Clarity
- **Definition**: Easy to understand, logical flow, appropriate reading level
- **Validation**: Readability score 70-80 Flesch

### Consistency
- **Definition**: Uniform terminology, formatting, structure throughout
- **Validation**: Style guide compliance check

### Correctness
- **Definition**: Proper grammar, spelling, punctuation
- **Validation**: Automated spell/grammar check; zero errors target

### Usability
- **Definition**: User achieves their goal efficiently using this document
- **Validation**: Task success assessment; does the doc serve its DIVIO type purpose?

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
- [ ] New user can complete without external references
- [ ] Steps are numbered and sequential
- [ ] Each step has verifiable outcome
- [ ] No assumed prior knowledge
- [ ] Builds confidence, not just competence

### How-to Checklist
- [ ] Clear, specific goal stated upfront
- [ ] Assumes reader knows fundamentals
- [ ] Focuses on single task
- [ ] Ends with task completion indicator
- [ ] No teaching of basics

### Reference Checklist
- [ ] All parameters documented
- [ ] Return values specified
- [ ] Error conditions listed
- [ ] Examples provided for each entry
- [ ] No narrative explanation in entries

### Explanation Checklist
- [ ] Addresses "why" not just "what"
- [ ] Provides context and reasoning
- [ ] Discusses alternatives considered
- [ ] No task-completion steps
- [ ] Builds a conceptual model the reader can apply

## Verdict Criteria

- **approved**: Passes all type-specific validation, no collapse violations, meets quality gate thresholds
- **needs-revision**: Minor issues fixable in place (clarity improvements, missing examples, small gaps)
- **restructure-required**: Collapse detected requiring document split, or fundamental type mismatch
