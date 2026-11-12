---
name: nw-divio-framework
description: DIVIO/Diataxis four-quadrant documentation framework - type definitions, classification decision tree, and signal catalog
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

## JTBD-First Resolution (When in doubt, ask the JTBD)

Provenance: Ale 2026-05-02. "La JTBD ci dice quale need stiamo soddisfando."

When the four-types decision tree is ambiguous, OR when a stylistic decision inside a chosen type has plausible alternatives (ordering, fold-vs-keep, scratch-vs-real-data, prose-vs-table, etc.), DO NOT pick by aesthetic preference. **Return to the document's JTBD and let the answer fall out.**

Each Diataxis type maps to a canonical JTBD:

| Type | Canonical JTBD | Implied constraints |
|---|---|---|
| **Tutorial** | "Build my mental model of X by doing it once, end-to-end, **without risking my real project state**." | Reproducible, safe, self-contained, cause-effect visible |
| **How-to** | "**Fix this specific situation right now**; don't teach me fundamentals." | Problem-statement first, decision tree, no preamble, link forward to Tutorial for newcomers |
| **Reference** | "Look up a **specific answer** (flag, exit code, schema field, error message)." | ctrl-F friendly, dense, alphabetical/systematic, no narrative, separate H2 per lookup category |
| **Explanation** | "**Understand the design rationale** so I can extend or critique it." | Discursive, links to evidence (probes, RCAs, ADRs), no how-to instructions, no command examples beyond the minimum needed for context |

### Application: resolving a stylistic dispute

Worked example, Tutorial Q: scratch directory vs use the project's seeded data?
- JTBD: "Build mental model end-to-end **without risking my real project state**."
- Constraint surfaced: "without risking" → seeded data DOES risk contamination → scratch wins.
- Constraint surfaced: "end-to-end" → cause-effect visible → seeded data hides cause-effect under pre-existing entries → scratch wins.

Worked example, Reference Q: fold three short sections into one "Notes"?
- JTBD: "Look up a specific answer."
- Constraint surfaced: "specific answer" → ctrl-F friendly → 3 distinct H2 entries are 3 distinct landing points → folding hurts the JTBD.
- Verdict: keep separate.

Worked example, README "Learn More" Q: alphabetical or semantic grouping?
- JTBD on a README is "I'm new; show me docs in the order I should read them" — pedagogical browsing, NOT lookup.
- Constraint surfaced: "in the order I should read them" → semantic grouping (install adjacent, authoring adjacent, troubleshooting last) → wins.
- Alphabetical serves a DIFFERENT JTBD ("I know the doc name") which has another surface (file system / search).

### Decision protocol

When facing a stylistic ambiguity inside a chosen type:
1. Restate the document's JTBD in one sentence (use the canonical JTBD as the starting point, refine if the doc is more specific).
2. List the constraints implied by that JTBD (be concrete: "reproducible", "ctrl-F friendly", "links to evidence").
3. Compare each candidate option against the constraint list.
4. Pick the option satisfying the most constraints. If tied, pick the option that fails the FEWEST constraints (loss-aversion).

This procedure replaces aesthetic debate with a falsifiable check.

### Anti-pattern: collapse via JTBD-blending

Some authors blend two JTBDs in one document ("a Tutorial that's also a Reference"). This is the same collapse pattern the four-types-only rule rejects, surfaced via the JTBD lens. Detection: if the document has TWO canonical JTBDs in tension (e.g. "build mental model" AND "look up specific answer"), flag for splitting.

### Diagrams

A diagram has no DIVIO type of its own. It takes the type of the section that holds it, and it must serve that section's JTBD: an Explanation diagram shows structure and reasons; a Reference diagram is a lookup aid with a description above it. Every diagram follows the accessibility rules R1-R12 of `nw-diagram`.
