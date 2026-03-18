---
name: nw-ux-principles
description: Core UX principles for product owners. Load when evaluating interface designs, writing acceptance criteria with UX requirements, or reviewing wireframes and mockups.
disable-model-invocation: true
---

# UX Principles

Evidence-based UX fundamentals for guiding interface design during requirements gathering. Use to evaluate designs, write better AC, and ask the right questions during discovery.

## Nielsen's 10 Usability Heuristics

Apply when reviewing any interface design or writing AC.

| # | Heuristic | Product Owner Action |
|---|-----------|---------------------|
| 1 | **Visibility of system status** | Require feedback for every action within 100ms. Status indicators for all async ops. |
| 2 | **Match system and real world** | Ban internal jargon from UI. Use domain language from user research. |
| 3 | **User control and freedom** | Every destructive action needs undo or confirmation. Navigation always allows going back. |
| 4 | **Consistency and standards** | Require design system. Audit for inconsistent terminology across features. |
| 5 | **Error prevention** | Require input validation, constraints, confirmation for irreversible actions. |
| 6 | **Recognition over recall** | Prefer dropdowns over free text when options known. Show recent items. Contextual help. |
| 7 | **Flexibility and efficiency** | Require keyboard shortcuts for frequent actions. Support mouse and keyboard workflows. |
| 8 | **Aesthetic and minimalist design** | Challenge every UI element: does it serve current task? Remove decorative clutter. |
| 9 | **Help with errors** | Error messages state what happened, why, and what to do next. No raw error codes. |
| 10 | **Help and documentation** | Require contextual help (tooltips, inline guidance). Documentation by task, not feature. |

### Heuristic Evaluation Questions

For each screen or workflow under review:

1. Is system status visible? (loading, saving, errors, success)
2. Does language match user's vocabulary?
3. Can users undo or escape from any state?
4. Are similar things named and behaving consistently?
5. Are error-prone situations prevented or confirmed?
6. Are options visible rather than requiring recall?
7. Are there shortcuts for frequent actions?
8. Is every visible element necessary for current task?
9. Do error messages explain problem and solution?
10. Is contextual help available?

Score each 0 (no problem) to 4 (usability catastrophe). Fix 3s and 4s before launch.

## Don Norman's Design Principles

Six principles explaining why some interfaces feel intuitive.

**Affordances**: What actions an object allows. Digital affordances must be made visible since screens lack physical properties. Button affords clicking; slider affords dragging.

**Signifiers**: Visual indicators communicating where and how to act. Blue underlined word signifies "clickable." Affordances define possibility; signifiers make it discoverable.

**Mapping**: Relationship between controls and effects. Natural mapping uses spatial correspondence (volume slider up = increase). Poor mapping forces memorization.

**Feedback**: Every action must produce perceptible feedback. Silence after action is most common source of confusion. Must be immediate, informative, proportional.

**Constraints**: Limitations guiding correct action. Graying out unavailable options (logical) | red means stop (cultural) | USB plug fits one way (physical).

**Conceptual Models**: Mental image users form about system behavior. When user's model matches system model, interface feels intuitive. Build accurate models through visible structure and consistent behavior.

### Applying Norman's Principles in Requirements

- For every interactive element: what does it afford? How is that signified?
- For every control: is mapping between action and effect natural?
- For every action: what feedback confirms it worked?
- For every error path: what constraints could prevent the error?

## Cognitive Load Laws

### Fitts's Law
Time to reach a target depends on distance and size.
- Make primary action buttons large and close to cursor's likely position
- Place destructive actions away from constructive ones
- Screen edges are easy targets (infinite edge) -- use for important controls
- Minimum touch targets: 44x44px (Apple) or 48x48dp (Material Design)

### Hick's Law
Decision time increases with number and complexity of choices.
- Limit primary navigation to 5-7 items
- Use progressive disclosure to hide advanced options
- Break complex decisions into smaller sequential steps
- Highlight recommended options to reduce decision paralysis

### Miller's Law
Working memory holds approximately 7 (plus or minus 2) items.
- Chunk information into groups of 3-5 items
- Use visual grouping (cards, sections, whitespace) to aid scanning
- Do not require remembering info across pages
- Display codes/numbers in chunks (phone numbers, credit cards)

## Progressive Disclosure

Resolves tension between simplicity for novices and power for experts.

**Core rule**: Show most important options first. Reveal specialized options on request.

**Two success factors**: 1. Correctly splitting features between initial and secondary views (requires user research) | 2. Making path to advanced features obvious through visible, well-labeled controls

**Design limits**: Most interfaces work best with max two disclosure levels. Three or more causes disorientation.

**Distinct from wizards**: Progressive disclosure uses hierarchical navigation (return to initial view). Wizards use linear sequences.

## Accessibility Essentials (WCAG 2.2 AA)

Four principles (POUR) -- the minimum a product owner must require.

| Principle | Key Requirements |
|-----------|-----------------|
| **Perceivable** | Text alternatives for images | captions for video | 4.5:1 contrast ratio | text resizable to 200% |
| **Operable** | Full keyboard operation | no keyboard traps | adequate time limits |
| **Understandable** | Readable text | predictable behavior | input assistance and error identification |
| **Robust** | Valid semantic HTML | ARIA roles where needed | screen reader compatibility |

### Product Owner Minimums

- 4.5:1 contrast ratio for normal text, 3:1 for large text
- All functionality accessible via keyboard
- Focus indicators visible on all interactive elements
- Minimum target size 24x24 CSS pixels
- Form inputs have associated labels
- Error messages identify field and suggest correction
- Page has descriptive title

## UX Review Checklist

Use when reviewing designs or writing AC.

### Visibility and Feedback
- [ ] Every action produces visible feedback within 100ms
- [ ] Loading states shown for operations >1 second
- [ ] Success confirmations for state-changing actions
- [ ] Error states with recovery guidance

### Navigation and Orientation
- [ ] User can answer: Where am I? Where can I go? How do I get back?
- [ ] Primary navigation has 7 or fewer items

### Cognitive Load
- [ ] Choices per decision point <= 7
- [ ] Information chunked into scannable groups
- [ ] Progressive disclosure hides advanced options
- [ ] No requirement to remember info across pages

### Accessibility
- [ ] Contrast ratio >= 4.5:1 for text
- [ ] All functionality accessible via keyboard
- [ ] Focus indicators visible
- [ ] Touch/click targets >= 24x24px
- [ ] Form fields have associated labels

### Consistency
- [ ] Same action looks and behaves the same everywhere
- [ ] Terminology consistent throughout
- [ ] Platform conventions followed
