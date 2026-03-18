---
name: nw-five-whys-methodology
description: Toyota 5 Whys methodology with multi-causal branching, evidence requirements, and validation techniques
disable-model-invocation: true
---

# Five Whys Methodology

## Philosophical Foundation

Taiichi Ohno: "By repeating why five times, the nature of the problem as well as its solution becomes clear."

Core tenets: scientific evidence-based investigation | address fundamental causes not symptoms | solve to prevent recurrence | use findings for Kaizen

## Multi-Causal Investigation

Complex problems have multiple root causes. Investigate comprehensively:
- **Parallel**: investigate all symptoms/conditions simultaneously
- **Branch**: follow each cause through all five WHY levels
- **Cross-cause**: ensure multiple causes don't contradict
- **Comprehensive**: address all root causes, not just primary

## WHY Level Definitions

### WHY 1: Symptom Investigation
What is immediately observable? Investigate all symptoms. Each branch continues independently. Document verifiable evidence per symptom.

```
WHY 1A: Path not found [Evidence: file exists but wrong context -- Windows vs WSL paths]
WHY 1B: Permission denied [Evidence: user context mismatch between host and container]
WHY 1C: Timing issues [Evidence: race conditions with file system operations]
```

### WHY 2: Context Analysis
Why does this condition exist? Follow each WHY 1 through context. Check if factors connect multiple causes. Examine system/environment/operational context.

### WHY 3: System Analysis
Why do conditions persist? How system enables multiple failure modes. How causes interact systemically. Analyze design/architecture decisions.

### WHY 4: Design Analysis
Why not anticipated? Review design assumptions. Identify all design blind spots. Trace decisions to original context.

### WHY 5: Root Cause Identification
Fundamental causes. Multiple root causes expected for complex issues. Ensure all contributing causes identified. Focus on deepest level.

## Validation and Verification

### Evidence Requirements
Each WHY level must have verifiable evidence for all causes. Root causes must explain all symptoms collectively. Solutions must address all root causes.

### Backwards Chain Validation
1. Trace each root cause forward to symptom | 2. "If this exists, would it produce this symptom?" = must be yes
3. Cross-validate: multiple roots must not contradict | 4. Completeness: "Missing contributing factors?" at each level

### Solution Completeness
Every root cause -> corresponding solution | Prevent recurrence, not just mitigate | Use findings for system improvement

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
