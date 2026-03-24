---
name: nw-collapse-detection
description: "Detects documentation collapse anti-patterns where doc types merge inappropriately. Use when reviewing documentation quality, auditing content structure, or fixing type-mixing violations."
user-invocable: false
disable-model-invocation: true
---

# Collapse Detection

Documentation collapse = types merge inappropriately, serving no audience well.

## Anti-Patterns

### Tutorial Creep
Description: Tutorial explains "why" extensively | Detection: explanation >20% | Fix: extract to separate doc, link back

### How-to Bloat
Description: How-to teaches basics first | Detection: teaching fundamentals before steps | Fix: link to tutorial, assume baseline

### Reference Narrative
Description: Reference includes conversational prose | Detection: prose paragraphs in entries | Fix: move to explanation doc, keep factual

### Explanation Task Drift
Description: Explanation ends with "do this" steps | Detection: step-by-step in explanation | Fix: move steps to how-to, link

### Hybrid Horror
Description: Single doc tries all four types | Detection: 3+ quadrants in one doc | Fix: split with clear boundaries

## Detection Rules

Flag collapse when:
- >20% content from adjacent quadrant | Two user needs served simultaneously | Ambiguous user journey stage
- "Why" in tutorials | Task steps in explanations | Teaching in how-tos | Narrative in references

## Bad Examples for Calibration

### Tutorial with Task Focus
```markdown
# Getting Started
If you need to deploy to production, follow these steps...
```
**Problem**: Assumes user knows what "deploy to production" means. A tutorial should assume nothing.

### How-to Teaching Basics
```markdown
# How to Configure Authentication
First, let's understand what authentication is. Authentication is...
```
**Problem**: Should assume user knows what authentication is. Link to a tutorial instead.

### Reference with Opinions
```markdown
## login(username, password)
This is probably the most important function you'll use...
```
**Problem**: Reference should be factual, not opinionated. Remove "probably the most important" editorializing.

### Explanation with Steps
```markdown
# Why We Use Microservices
... therefore, you should: 1. Create a service, 2. Deploy it...
```
**Problem**: Steps belong in a how-to guide. The explanation should end with reasoning and link to the how-to for action.
