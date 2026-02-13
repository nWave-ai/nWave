---
name: divio-framework
description: DIVIO/Diataxis four-quadrant documentation framework - type definitions, classification decision tree, and signal catalog
---

# DIVIO Documentation Framework

## The Four Quadrants

There are exactly four types of documentation. Each serves one purpose. Never mix them.

### Tutorial
- **Orientation**: Learning
- **User need**: "Teach me"
- **Key question**: Can a newcomer follow this without external context?
- **Purpose**: Enable newcomers to achieve first success
- **Assumption**: User knows nothing; you are the instructor
- **Format**: Step-by-step guided experience
- **Success**: User gains competence and confidence
- **Must include**: Safe repeatable steps, immediate feedback, building blocks
- **Must exclude**: Problem-solving, assumed knowledge, comprehensive coverage

### How-to Guide
- **Orientation**: Task
- **User need**: "Help me do X"
- **Key question**: Does this achieve a specific, measurable outcome?
- **Purpose**: Help user accomplish specific objective
- **Assumption**: User has baseline knowledge; needs goal completion
- **Format**: Focused step-by-step to outcome
- **Success**: User completes the task
- **Must include**: Clear goal, actionable steps, completion indicator
- **Must exclude**: Teaching fundamentals, background context, all possible scenarios

### Reference
- **Orientation**: Information
- **User need**: "What is X?"
- **Key question**: Is this factually complete and lookup-ready?
- **Purpose**: Provide accurate lookup for specific information
- **Assumption**: User knows what to look for
- **Format**: Structured, concise, factual entries
- **Success**: User finds correct information quickly
- **Must include**: Complete API/function details, parameters, return values, errors
- **Must exclude**: Narrative explanations, tutorials, opinions

### Explanation
- **Orientation**: Understanding
- **User need**: "Why is X?"
- **Key question**: Does this explain reasoning and context?
- **Purpose**: Build conceptual understanding and context
- **Assumption**: User wants to understand "why"
- **Format**: Discursive, reasoning-focused prose
- **Success**: User understands design rationale
- **Must include**: Context, reasoning, alternatives considered, architectural decisions
- **Must exclude**: Step-by-step instructions, API details, task completion

## Classification Matrix

```
                  PRACTICAL           THEORETICAL
STUDYING:         Tutorial            Explanation
WORKING:          How-to Guide        Reference
```

Adjacent characteristics:
- Tutorial / How-to: Both have steps (differ in assumption of knowledge)
- How-to / Reference: Both serve "at work" needs
- Reference / Explanation: Both provide knowledge depth
- Explanation / Tutorial: Both serve "studying" context

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
