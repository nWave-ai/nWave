---
name: nw-interviewing-techniques
description: "Mom Test questioning toolkit with JTBD analysis, assumption testing, and hypothesis design. Load when preparing customer interviews, validating product assumptions, or designing discovery questions."
user-invocable: false
disable-model-invocation: true
---

# Interviewing Techniques

## Questioning Toolkit by Purpose

### Problem Discovery
Understand if problem is real and worth solving.
- "Tell me about the last time you [encountered this problem]."
- "What was the hardest part about that?"
- "What did you do about it?" | "What don't you love about that solution?" | "What else have you tried?"

### Understanding the Job
Map the job-to-be-done and desired outcomes.
- "What are you ultimately trying to accomplish?"
- "Walk me through your process step by step."
- "At each step, how do you know if you've succeeded?"
- "What slows you down or frustrates you most?" | "What workarounds have you created?"

### Probing Assumptions
Challenge beliefs and uncover truth.
- "What makes you believe that?" | "What would need to be true for this to work?"
- "What could we assume instead?" | "What would change your mind?"

### Testing Commitment
Distinguish interest from commitment.
- "Would you be willing to [specific action]?" | "What would you pay for this?"
- "Can you introduce me to someone else with this problem?" | "When can we schedule a follow-up?"

### Exploring Implications
Understand impact and urgency.
- "If this were solved, what would change?" | "What would that enable you to do?"
- "What would happen if we didn't solve this?"

## Interview Conduct Rules

**Do**: Ask about past specifics | Open, non-directive questions | Seek commitment not praise | Keep informal | 80% listening | Talk about their life first

**Avoid**: Future behavior questions | Leading questions | Accepting compliments as validation | Talking >20% | Mentioning idea before understanding problem | Formal settings

## Assumption Challenging

### Triggers
Challenge when: belief without evidence | prediction about future | negative feedback dismissed | skipping to solution | single data point relied on

### Challenge Format
1. "What evidence supports this?" -- specific past examples
2. "What would disprove this?" -- falsification criteria
3. "What's the opposite assumption?" -- explore alternatives
4. "Who would disagree and why?" -- disconfirming perspectives

Tone: curious and supportive, not confrontational -- goal is truth-seeking.

## Assumption Testing Framework

### Assumption Categories
| Category | Core Question |
|----------|--------------|
| Value | Will customers want this? |
| Usability | Can customers use this? |
| Feasibility | Can we build this? |
| Viability | Does this work for our business? |

### Risk Scoring

| Factor | Weight | Low (1) | Medium (2) | High (3) |
|--------|--------|---------|------------|----------|
| Impact if wrong | 3 | Minor adjustment | Significant rework | Solution fails |
| Uncertainty | 2 | Have data | Mixed signals | Speculation |
| Ease of testing | 1 | Days, low cost | Weeks, moderate | Months, high cost |

**Risk Score** = (Impact x 3) + (Uncertainty x 2) + (Ease x 1)

| Priority | Score | Action |
|----------|-------|--------|
| Test first | > 12 | Immediate |
| Test soon | 8-12 | Schedule |
| Test later | < 8 | Backlog |

### Hypothesis Template

```
We believe [doing X] for [user type] will achieve [outcome].
We will know this is TRUE when we see [measurable signal].
We will know this is FALSE when we see [counter-signal or absence of signal].
```

### Test Methods by Category

| Category | Methods |
|----------|---------|
| Value | Landing page, Fake door, Mom Test interviews |
| Usability | Prototype testing, 5-second tests, Task completion |
| Feasibility | Spike, Technical prototype, Expert review |
| Viability | Lean Canvas review, Stakeholder interviews |

### Decision Rules

| Result | Criteria | Action |
|--------|----------|--------|
| Proven | >80% meet success criteria | Proceed |
| Disproven | <20% meet criteria | Pivot or kill |
| Inconclusive | 20-80% | Increase sample, try different method, segment |
