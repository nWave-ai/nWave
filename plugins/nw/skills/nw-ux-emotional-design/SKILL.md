---
name: nw-ux-emotional-design
description: Emotional design and delight patterns for product owners. Load when designing onboarding flows, empty states, first-run experiences, or evaluating the emotional quality of an interface.
disable-model-invocation: true
---

# Emotional Design and Delight

Patterns for creating interfaces that feel good to use. Use during discovery to map emotional arcs and during requirements to specify delight moments.

## Walter's Hierarchy of User Needs

Four layers satisfied in order (bottom to top):

```
        /\
       /  \
      / PL \     4. PLEASURABLE - Delight, surprise, emotional connection
     /------\
    / USABLE \    3. USABLE - Easy to learn, intuitive, efficient
   /----------\
  / RELIABLE   \   2. RELIABLE - Consistent, dependable, no crashes
 /--------------\
/ FUNCTIONAL     \  1. FUNCTIONAL - It works, serves its purpose
------------------
```

**Key insight**: Delight only works if product is usable. Beautiful animations on buggy, confusing interface make things worse. Invest in foundation before polish.

### Applying the Hierarchy in Requirements
- Phase 1 stories: functionality works correctly
- Phase 2 stories: reliability (error handling, edge cases, recovery)
- Phase 3 stories: usability (simplify flows, reduce steps)
- Phase 4 stories: delight (only after above are solid)

## Surface Delight vs Deep Delight

### Surface Delight (momentary, contextual)
Playful animations | witty microcopy | surprising easter eggs | visually pleasing illustrations

### Deep Delight (sustained, holistic)
Interface anticipates user needs | complex tasks feel effortless | users achieve flow state | tool becomes extension of thinking

**Prioritization rule**: Deep delight generates loyalty and return usage. Surface delight creates momentary reactions but cannot compensate for usability failures. Invest in deep delight first.

### Requirements Implications
- "System suggests most likely next action" (deep) is higher priority than "Save button has satisfying animation" (surface)
- Stories reducing steps, anticipating needs, removing friction are delight stories even if they don't feel "fun"

## Empty States

Empty states (no data, first use, zero results) are opportunities, not dead ends.

### Good Empty State Design
- Explain what will appear when there is content
- Clear call to action to create first item
- Illustration or visual interest making state feel intentional
- Guidance or templates for first-time users

### Anti-Pattern
Blank page with no guidance, or "No results found" with no suggested next step.

### Empty State Checklist for Requirements
- [ ] First-time empty state has onboarding guidance
- [ ] Search empty state suggests alternative queries or filters
- [ ] Error empty state explains what happened and how to recover
- [ ] Each empty state has primary call to action

## Onboarding and First-Run Experience

### Progressive Onboarding (preferred)
- Let users start real work immediately
- Introduce features in context, when relevant
- Tooltips and inline hints dismissing after first use
- "Skip" option for experienced users
- Celebrate first successful action

### Anti-Pattern
Mandatory 8-step walkthrough blocking users from doing anything before completion.

### Onboarding Patterns by Platform

**Web**: Inline hints | contextual tooltips | sample data to explore | "getting started" checklist widget

**Desktop**: First-run wizard for essential setup only (account, preferences), then contextual hints during use

**CLI**: First command outputs welcome message with 2-3 example commands. `--help` is comprehensive. Config file created with sensible defaults and comments.

## Tone of Voice in UI Copy

### Principles
Clear first, clever second | active voice, present tense | address user as "you" | instructions in 1-2 sentences | consistent voice builds trust

### Matching Tone to Context

| Context | Tone | Example |
|---------|------|---------|
| Error message | Empathetic, helpful | "We could not save your changes. Check your connection and try again." |
| Success message | Encouraging, brief | "Project created. You are ready to start." |
| Empty state | Inviting, guiding | "No projects yet. Create your first one to get started." |
| Destructive action | Clear, serious | "This will permanently delete 3 files. This cannot be undone." |
| Loading/waiting | Reassuring | "Setting things up. This usually takes about 30 seconds." |
| Neutral action | Straightforward | "Select a template." |

### When Personality Helps vs Annoys

**Helps when**: user not stressed (onboarding, success, empty states) | low-stakes moment | brand voice well-established

**Annoys when**: user frustrated (errors, failures) | user in a hurry (critical workflows) | humor forced or inconsistent | cleverness obscures message

## Microinteractions That Create Delight

### High-Value Microinteractions
Pull-to-refresh with satisfying animation | skeleton screens instead of blank loading | smooth state transitions (not abrupt swaps) | smart defaults reducing typing | autocomplete learning from usage | undo toast after destructive actions ("Deleted. Undo?")

### Low-Value Microinteractions (skip these)
Decorative loading animations adding no information | sound effects for routine actions | excessive bounce/wobble animations | easter eggs interfering with workflow

### Requirements Pattern for Microinteractions
Specify: trigger (what user does) | feedback (what user sees/feels) | purpose (why this matters for experience)

Example: "When user drags card to new column, card smoothly animates to new position and column header count updates, confirming move was successful."

## Emotional Arc Integration

When mapping emotional arcs during journey discovery:

| Journey Phase | Target Emotion | Design Lever |
|--------------|----------------|--------------|
| First encounter | Curious, welcomed | Clear value proposition, inviting empty state |
| Setup/config | Confident, guided | Progressive onboarding, sensible defaults |
| First success | Accomplished, delighted | Celebration moment, clear confirmation |
| Regular use | Efficient, in flow | Shortcuts, anticipation, minimal friction |
| Error/failure | Supported, not blamed | Empathetic copy, clear recovery path |
| Completion | Satisfied, proud | Summary of accomplishment, next steps |

Use this table when asking emotional arc questions during discovery. Map each journey step to target emotion and identify design lever that achieves it.
