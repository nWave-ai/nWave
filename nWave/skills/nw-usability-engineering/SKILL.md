---
name: nw-usability-engineering
description: Cognitive science principles applied to futuristic interface design -- Fitts, Hick, Miller, cognitive load theory, and Nielsen heuristics
disable-model-invocation: true
---

# Usability Engineering for Futuristic Interfaces

## Core Cognitive Laws

### Fitts's Law (Target Acquisition)

**Formula**: Time = a + b * log2(Distance/Width + 1)

**Application**: Important interactive targets must be large enough and close to likely cursor positions.

- Primary actions: minimum 44x44px touch target, 32x32px pointer target
- Screen edges and corners are infinite-width targets (use them for frequent actions)
- Group related actions to minimize cursor travel between sequential operations
- Radial menus (Warframe-style) minimize Fitts distance -- all options equidistant from center

**Futuristic pitfall**: Holographic/floating UI elements tempt designers to scatter controls in space. Every pixel of distance between sequential actions costs time. Cluster related controls even in expansive layouts.

### Hick's Law (Decision Time)

**Formula**: Time = b * log2(n + 1) where n = number of choices

**Application**: Reduce simultaneous choices. Use progressive disclosure.

- Maximum 5-7 visible options at any decision point
- Group into categories first, then reveal details (two 5-option menus faster than one 25-option menu)
- Default/recommended option visually distinguished (larger, brighter, positioned first)
- Remove options rather than disabling them when context makes them irrelevant

**Futuristic pitfall**: Sci-fi interfaces love to display everything at once (NERV control room, Minority Report). Real users need progressive disclosure. Show the operational layer first, reveal engineering details on demand.

### Miller's Law (Working Memory)

**Principle**: Working memory holds 7 +/- 2 chunks simultaneously.

**Application**: Never present more than 7 distinct information groups per view.

- Dashboard panels: 5-7 maximum per viewport
- Navigation items: 5-7 top-level categories
- Form fields per section: 5-7 visible at once (paginate/accordion beyond)
- Data table columns visible without scroll: 5-7 (allow horizontal scroll for detail)
- Chunk related items visually (proximity, shared background, border)

**Futuristic pitfall**: Dense utilitarian displays (Expanse-style) tempt exceeding 7 chunks. Solve with clear visual grouping -- proximity and shared containers turn 20 data points into 5 chunks of 4.

### Cognitive Load Theory

Three types of cognitive load:

| Type | Definition | Design Goal |
|------|-----------|-------------|
| Intrinsic | Inherent complexity of the task | Cannot reduce -- task IS complex |
| Extraneous | Load from poor design | Eliminate -- this is YOUR fault |
| Germane | Load from learning/understanding | Facilitate -- support mental model building |

**Reducing extraneous load**:
- Consistent interaction patterns (same gesture/click always does same type of thing)
- Spatial stability (elements stay in predictable positions)
- Visual hierarchy via contrast, size, position (not decoration)
- Contextual help at point of need (not separate documentation)
- Reduce required memory by keeping state visible

**Supporting germane load**:
- Use metaphors that map to user's existing mental models
- Progressive complexity (basic first, advanced on demand)
- Visual feedback confirming correct mental model ("yes, that's how this works")
- Undo support everywhere (reduces fear of exploration)

## Nielsen's 10 Usability Heuristics (Futuristic Lens)

### 1. Visibility of System Status
System communicates what is happening through appropriate feedback within reasonable time.

Futuristic application: Ambient indicators (color temperature, particle density, background pulse) for persistent state. Explicit notifications only for state changes requiring action. Dead Space's health-on-spine is ideal -- always visible, never intrusive.

### 2. Match Between System and Real World
System uses user's language, follows real-world conventions, information appears natural and logical.

Futuristic application: Sci-fi aesthetic must not override domain language. A medical dashboard should use medical terms, not sci-fi terms. The visual wrapper is futuristic; the content vocabulary is domain-native.

### 3. User Control and Freedom
Users need a clearly marked emergency exit to leave unwanted states without extended dialogue.

Futuristic application: Every modal has visible close. Every action has undo. Every navigation has back. Gestural interfaces (Minority Report-style) need an explicit "cancel" gesture. Never trap users in an animation sequence.

### 4. Consistency and Standards
Users should not have to wonder whether different words, situations, or actions mean the same thing.

Futuristic application: Once a visual pattern means something (glow = interactive, pulse = processing, red = critical), it means that EVERYWHERE. A single inconsistency destroys the entire visual language. Document the semantic mapping and enforce it.

### 5. Error Prevention
Eliminate error-prone conditions or present confirmation before commit.

Futuristic application: Destructive actions require two-step confirmation with distinct interactions (not two identical clicks). Preview results before committing. Constraint inputs to valid ranges rather than validating after entry.

### 6. Recognition Rather Than Recall
Minimize memory load by making objects, actions, and options visible.

Futuristic application: Keep recent actions, relevant options, and system state visible. Command-line-style interfaces need autocomplete and history. Never require users to remember codes, IDs, or sequences.

### 7. Flexibility and Efficiency of Use
Accelerators for experts that do not burden novices. Allow customization.

Futuristic application: Keyboard shortcuts, radial menus, command palettes for power users. Visual affordances for novices. Layer complexity: surface (visual), shortcuts (keyboard), command (direct input).

### 8. Aesthetic and Minimalist Design
Every extra unit of information competes with relevant information and diminishes visibility.

Futuristic application: The hardest heuristic for sci-fi design. Decorative elements (scan lines, particle effects, ambient data streams) must be VERY low opacity and never compete with functional content. Test: cover the decorative layer -- does the interface still work? Good. Now uncover -- does the decoration interfere with any functional element? If yes, reduce or remove.

### 9. Help Users Recognize, Diagnose, and Recover from Errors
Error messages in plain language, indicate the problem precisely, suggest a solution.

Futuristic application: Error states should feel recoverable, not catastrophic. Warm colors (amber) not aggressive (pure red) for recoverable errors. Show what went wrong, what the user can do, and offer a direct action button. Never just "Error occurred."

### 10. Help and Documentation
Best if system is usable without documentation, but provide help focused on user's task.

Futuristic application: Contextual tooltips, inline hints, progressive tutorials. Not a separate help section. Ghost-in-the-Shell-style data overlays on hover/focus that explain what an element does.

## Accessibility as Design Constraint

Accessibility is not a bolt-on. Treat as a primary design constraint:

- **Color**: Never convey information by color alone. Pair with icons, labels, or patterns.
- **Motion**: All animations respect `prefers-reduced-motion`. See interaction-choreography skill.
- **Contrast**: WCAG AA minimum (4.5:1 text, 3:1 large text). Futuristic dark themes need careful testing.
- **Focus indicators**: Visible focus rings on all interactive elements. Glow effects serve double duty as focus indicators.
- **Screen readers**: Semantic HTML, ARIA labels where needed. Decorative elements are `aria-hidden`.
- **Keyboard**: Full keyboard navigation. Tab order follows visual flow. No keyboard traps.

## Information Density Framework

Match information density to use context:

### Level 1 — Glanceable (Destiny sofa-distance)
- 3-5 data points maximum
- Large type, high contrast, single-color accent hierarchy
- Use case: mobile dashboards, at-a-glance status, consumer apps

### Level 2 — Operational (The Expanse cockpit)
- 8-12 data points, organized in spatial zones
- Secondary information accessible but not prominent, color-coded categories
- Use case: operational dashboards, driver/pilot interfaces, team monitors

### Level 3 — Analytical (Iron Man holographic workspace)
- 15-25 data points across multiple panels
- Glassmorphism layering for depth, cross-referencing between panels
- Use case: data analysis, engineering dashboards, investigation tools

### Level 4 — Immersive (NERV command center)
- 25+ data points with ambient data streams
- Requires trained users, utilitarian density with clear grid structure
- Use case: SRE war rooms, trading floors, mission control

**Rule**: Never design Level 4 density for Level 1 users. Match density to expertise and context. The Expanse's faction-specific simplification shows how: Belter interfaces show less by design, reflecting resource scarcity and practical need.

## FUI Design Studios (Reference)

When seeking real-world inspiration for specific interface styles:
- **Territory Studio**: Ghost in the Shell, Blade Runner 2049, Avengers — masters of material experimentation
- **Perception**: Iron Man 2, Captain America, Batman v Superman — polished holographic systems
- **Cantina Creative**: Iron Man 2/3, Avengers, Blade Runner 2049 — Cinema 4D-heavy 3D workflows
- **Jayse Hansen**: Iron Man 3, Avengers 1&2, Star Wars TFA — created the "HUD Bible" for MCU consistency
- **GMUNK**: Tron Legacy, Oblivion — grid-based and minimalist functional design
- **Ash Thorp**: Ghost in the Shell, Ender's Game, Prometheus — high-concept visual design
- **Rhys Yorke**: The Expanse — utilitarian realism, faction differentiation, NASA-informed design

## Evaluation Checklist

Before approving any design:

- [ ] Fitts: primary actions reachable without excessive cursor movement
- [ ] Hick: no decision point presents more than 7 options without grouping
- [ ] Miller: no view contains more than 7 distinct information groups
- [ ] Cognitive load: consistent patterns, spatial stability, visible state
- [ ] Nielsen heuristics: all 10 addressed (not all equally, but none ignored)
- [ ] WCAG AA: contrast ratios, focus indicators, screen reader support
- [ ] Reduced motion: all animations have non-motion alternative
- [ ] Error recovery: all error states show problem + solution + action
