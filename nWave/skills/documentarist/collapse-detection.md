---
name: collapse-detection
description: Documentation collapse anti-patterns - detection rules, bad examples, and remediation strategies for type-mixing violations
---

# Collapse Detection

Documentation collapse occurs when types merge inappropriately, creating content that serves no audience well.

## Anti-Patterns

### Tutorial Creep
- **Description**: Tutorial starts explaining "why" extensively
- **Detection**: Explanation content >20% in tutorial
- **Fix**: Extract explanation to separate document, link back

### How-to Bloat
- **Description**: How-to teaches basics before the task
- **Detection**: Teaching fundamentals before steps begin
- **Fix**: Link to tutorial for basics; assume reader has baseline knowledge

### Reference Narrative
- **Description**: Reference includes conversational explanation
- **Detection**: Prose paragraphs in reference entries
- **Fix**: Move prose to explanation document, keep reference factual

### Explanation Task Drift
- **Description**: Explanation ends with "do this" steps
- **Detection**: Step-by-step instructions appearing in explanation
- **Fix**: Move steps to how-to guide, link from explanation

### Hybrid Horror
- **Description**: Single document tries all four types
- **Detection**: Content from 3+ quadrants in one document
- **Fix**: Split into separate documents with clear boundaries

## Detection Rules

Flag a collapse violation when any of these conditions are true:
- Document has >20% content from an adjacent quadrant
- Document attempts to serve two user needs simultaneously
- User journey stage is ambiguous
- "Why" explanations appear in tutorials
- Task steps appear in explanations
- Teaching appears in how-to guides
- Narrative prose appears in reference entries

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
