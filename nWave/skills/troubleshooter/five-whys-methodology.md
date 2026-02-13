---
name: five-whys-methodology
description: Toyota 5 Whys methodology with multi-causal branching, evidence requirements, and validation techniques
---

# Five Whys Methodology

## Philosophical Foundation

Taiichi Ohno's principle: "By repeating why five times, the nature of the problem as well as its solution becomes clear."

Core tenets:
- Scientific, evidence-based investigation
- Address fundamental causes, not visible symptoms
- Solve problems to prevent future occurrences
- Use findings for continuous improvement (Kaizen)

## Multi-Causal Investigation

Complex problems often have multiple contributing root causes. Investigate them comprehensively:

- **Parallel investigation**: investigate all observable symptoms and conditions simultaneously
- **Branch analysis**: follow each cause branch through all five WHY levels
- **Cross-cause validation**: ensure multiple causes do not contradict each other
- **Comprehensive solution**: address all identified root causes, not just the primary one

## WHY Level Definitions

### WHY 1: Symptom Investigation
- Purpose: what is immediately observable?
- Investigate all observable symptoms and conditions
- Each cause branch continues through all 5 levels independently
- Evidence: document verifiable evidence for each observed symptom

Example:
```
WHY 1A: Path not found [Evidence: file exists but wrong context -- Windows vs WSL paths]
WHY 1B: Permission denied [Evidence: user context mismatch between host and container]
WHY 1C: Timing issues [Evidence: race conditions with file system operations]
```

### WHY 2: Context Analysis
- Purpose: why does this condition exist?
- Follow each WHY 1 cause through context analysis
- Check if context factors connect multiple causes
- Examine system, environment, and operational context

### WHY 3: System Analysis
- Purpose: why do these conditions persist?
- Examine how the system enables multiple failure modes
- Identify how multiple causes interact systemically
- Analyze system design and architecture decisions

### WHY 4: Design Analysis
- Purpose: why was this not anticipated?
- Review design assumptions that contributed to the problem
- Identify all design blind spots, not just the primary one
- Trace design decisions to their original context and assumptions

### WHY 5: Root Cause Identification
- Purpose: what are the fundamental causes?
- Multiple root causes are acceptable and expected for complex issues
- Ensure all contributing root causes are identified
- Focus on the deepest level causal factors

## Validation and Verification

### Evidence Requirements
- Each WHY level must have verifiable evidence for all causes at that level
- Root causes must explain all symptoms collectively, not just the primary issue
- Solutions must address all identified root causes

### Backwards Chain Validation
1. For each root cause, trace forward through the causal chain to the symptom
2. Ask: "If this root cause exists, would it produce this symptom?" -- must be yes
3. Cross-validate: multiple root causes must not contradict each other
4. Completeness check: "Are we missing any contributing factors?" at each level

### Solution Completeness
- Every identified root cause must have a corresponding solution
- Solutions should prevent recurrence, not just mitigate current symptoms
- Use findings to improve overall system design and processes

## Branch Documentation Format

```
PROBLEM: [clear problem statement]

WHY 1A: [symptom] [Evidence: ...]
  WHY 2A: [context] [Evidence: ...]
    WHY 3A: [system factor] [Evidence: ...]
      WHY 4A: [design factor] [Evidence: ...]
        WHY 5A: [root cause] [Evidence: ...]
        -> ROOT CAUSE A: [fundamental cause]
        -> SOLUTION A: [prevention strategy]

WHY 1B: [symptom] [Evidence: ...]
  WHY 2B: [context] [Evidence: ...]
    ...

CROSS-VALIDATION:
- Root Cause A + Root Cause B: [consistent/contradictory]
- All symptoms explained: [yes/no, gaps if any]
```
