---
name: nw-divio-framework
description: "Applies the Diataxis four-quadrant documentation framework: tutorials, how-tos, reference, and explanation. Use when classifying documentation types, structuring docs, or auditing content quality."
user-invocable: false
disable-model-invocation: true
---

# DIVIO Documentation Framework

## The Four Quadrants

Exactly four documentation types. Each serves one purpose. Never mix.

### Tutorial
Orientation: Learning | Need: "Teach me" | Key Q: Can newcomer follow without external context?
Purpose: enable first success | Assumption: user knows nothing | Format: step-by-step guided experience
Success: gains competence + confidence | Include: safe repeatable steps, immediate feedback, building blocks
Exclude: problem-solving, assumed knowledge, comprehensive coverage

### How-to Guide
Orientation: Task | Need: "Help me do X" | Key Q: Achieves specific, measurable outcome?
Purpose: accomplish specific objective | Assumption: baseline knowledge, needs goal completion
Format: focused steps to outcome | Success: task completed
Include: clear goal, actionable steps, completion indicator | Exclude: teaching, background, all scenarios

### Reference
Orientation: Information | Need: "What is X?" | Key Q: Factually complete and lookup-ready?
Purpose: accurate lookup | Assumption: user knows what to look for | Format: structured, concise, factual
Success: finds correct info quickly | Include: complete API/function details, parameters, returns, errors
Exclude: narrative, tutorials, opinions

### Explanation
Orientation: Understanding | Need: "Why is X?" | Key Q: Explains reasoning and context?
Purpose: conceptual understanding | Assumption: user wants "why" | Format: discursive, reasoning-focused
Success: understands design rationale | Include: context, reasoning, alternatives, architectural decisions
Exclude: step-by-step, API details, task completion

## Classification Matrix

```
                  PRACTICAL           THEORETICAL
STUDYING:         Tutorial            Explanation
WORKING:          How-to Guide        Reference
```

Adjacent: Tutorial/How-to (both have steps, differ in assumed knowledge) | How-to/Reference (both "at work") | Reference/Explanation (both knowledge depth) | Explanation/Tutorial (both "studying")

## Classification Decision Tree

```
START: What is the user's primary need?

1. Is user learning for the first time?
   YES -> TUTORIAL
   NO  -> Continue

2. Is user trying to accomplish a specific task?
   YES -> Does it assume baseline knowledge?
         YES -> HOW-TO GUIDE
         NO  -> TUTORIAL (reclassify)
   NO  -> Continue

3. Is user looking up specific information?
   YES -> Is it factual/lookup content?
         YES -> REFERENCE
         NO  -> Likely EXPLANATION
   NO  -> Continue

4. Is user trying to understand "why"?
   YES -> EXPLANATION
   NO  -> Re-evaluate (content may need restructuring)
```

## Classification Signals

### Tutorial Signals
**Positive**: "Getting started", "Your first...", "Prerequisites: None", "What you'll learn", "Step 1, Step 2...", "You should see..."
**Red flags**: "Assumes prior knowledge", "If you need to...", "For advanced users..."

### How-to Signals
**Positive**: "How to [verb]", "Before you start" (with prerequisites), "Steps", "Done:" or "Result:"
**Red flags**: "Let's understand what X is...", "First, let's learn about..."

### Reference Signals
**Positive**: "API", "Parameters", "Returns", "Throws", "Type:", Tables of functions/methods
**Red flags**: "This is probably...", "You might want to...", Conversational tone

### Explanation Signals
**Positive**: "Why", "Background", "Architecture", "Design decision", "Trade-offs", "Consider", "Because"
**Red flags**: "1. Create...", "2. Run...", "Step-by-step", "Do this:"
