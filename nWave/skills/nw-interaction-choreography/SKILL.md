---
name: nw-interaction-choreography
description: Animation principles, timing, easing curves, and choreography sequences for futuristic interfaces -- motion as communication
disable-model-invocation: true
---

# Interaction Choreography

## Motion Philosophy

Every animation communicates exactly one thing: spatial relationship, state change, hierarchy shift, or attention redirection. If you cannot name what a motion communicates, remove it.

## Timing Framework

### Duration Scale

```
--duration-instant:  0ms        -- immediate state (disabled toggle)
--duration-micro:    80-120ms   -- micro-feedback (button press, toggle)
--duration-fast:     150-200ms  -- hover states, tooltips, color transitions
--duration-normal:   250-350ms  -- panel open/close, content swap
--duration-slow:     400-600ms  -- major layout shifts, page transitions
--duration-dramatic: 800-1200ms -- onboarding reveals, hero animations
```

### Rule of Perceptible Motion
- Under 100ms: perceived as instant (use for feedback acknowledgment)
- 100-300ms: perceived as responsive (primary interaction range)
- 300-600ms: perceived as animated (layout and navigation)
- Over 600ms: perceived as cinematic (use sparingly -- first impressions, celebrations)

## Easing Curves

### Futuristic Easing Library

```css
/* Entrance -- elements appearing */
--ease-enter: cubic-bezier(0.0, 0.0, 0.2, 1.0);     /* decelerate into place */
--ease-enter-sharp: cubic-bezier(0.0, 0.0, 0.1, 1.0); /* snap into position (HUD feel) */

/* Exit -- elements leaving */
--ease-exit: cubic-bezier(0.4, 0.0, 1.0, 1.0);       /* accelerate out */
--ease-exit-sharp: cubic-bezier(0.4, 0.0, 0.8, 1.0);  /* quick departure */

/* State change -- morphing in place */
--ease-morph: cubic-bezier(0.4, 0.0, 0.2, 1.0);      /* standard Material-style */
--ease-bounce: cubic-bezier(0.34, 1.56, 0.64, 1.0);   /* slight overshoot (playful) */

/* Sci-fi signature -- sharp start, elastic end */
--ease-cyber: cubic-bezier(0.0, 0.8, 0.2, 1.0);      /* immediate response, gentle settle */
--ease-glitch: steps(8, end);                           /* digital artifact feel */
```

### Easing Selection Guide

| Interaction Type | Easing | Rationale |
|-----------------|--------|-----------|
| Button press | ease-enter-sharp | Immediate feedback, decisive |
| Panel open | ease-enter | Smooth revelation |
| Panel close | ease-exit-sharp | Quick, respectful of attention |
| Hover glow | ease-morph | Gentle state acknowledgment |
| Error shake | ease-bounce | Attention + slight playfulness |
| Data refresh | ease-cyber | Responsive start, settle into new values |
| Loading pulse | ease-morph (looped) | Rhythmic, non-distracting |
| Glitch effect | ease-glitch | Digital/mechanical feel |

## Choreography Sequences

### Staggered Reveal (Grid/List Items)

Items enter sequentially with delay multiplication:

```
Item 1: delay 0ms,   duration 300ms
Item 2: delay 50ms,  duration 300ms
Item 3: delay 100ms, duration 300ms
Item N: delay (N-1)*50ms
```

Cap at 400ms total stagger (8 items). Beyond that, reveal in groups.
Direction: top-left to bottom-right (reading order) or center-out (radial).

### Panel Expansion

1. Border appears (0-80ms): 1px border fades in at accent color
2. Background fills (80-200ms): glassmorphism backdrop fades in
3. Content enters (200-400ms): text and elements fade-up with stagger
4. Interactive elements activate (400-500ms): buttons/inputs become responsive

Collapse: reverse order, 60% of expand duration (faster exit than enter).

### State Transitions (Status Changes)

Nominal -> Warning:
1. Border color transition (200ms, ease-morph)
2. Background ambient color shift (300ms, ease-morph)
3. Status indicator pulse once (400ms, ease-bounce)
4. Settle into new steady state

Warning -> Critical:
1. Quick flash (80ms white at 10% overlay)
2. Border + background snap to critical color (150ms, ease-enter-sharp)
3. Status indicator begins steady pulse (1.5s cycle)

### Navigation Transitions

**Slide**: Content exits left (ease-exit, 200ms) while new content enters right (ease-enter, 250ms, 50ms delay). Maintains spatial metaphor (forward = left-to-right).

**Crossfade**: Old content fades out (ease-exit, 150ms) while new fades in (ease-enter, 200ms, 100ms overlap). Use when spatial direction is meaningless.

**Morph**: Shared elements transform between states (ease-morph, 300ms). Hero images, cards that expand to detail views. Maintains object permanence.

## Micro-Interactions

### Button States
```
Idle:        scale(1.0), glow(0)
Hover:       scale(1.0), glow(accent 25%), border-opacity -> 60%, 150ms ease-morph
Active/Down: scale(0.98), glow(accent 40%), 80ms ease-enter-sharp
Release:     scale(1.0), ripple-out from click point, 300ms ease-enter
Loading:     border-gradient rotation (1.5s linear infinite), content fade to 60%
Success:     brief glow pulse (accent, 400ms ease-bounce), icon morph
Error:       horizontal shake (3 cycles, 4px amplitude, 300ms), border flash critical
```

### Toggle/Switch
```
Off -> On:  thumb slides right (200ms ease-cyber), track fills with accent (150ms)
On -> Off:  thumb slides left (150ms ease-exit-sharp), track drains (120ms)
```

### Input Focus
```
Unfocused -> Focused: bottom-border expands from center (250ms ease-enter), label floats up (200ms ease-morph), glow appears (200ms)
Focused -> Unfocused: glow fades (150ms), label settles if empty (200ms), border returns to default (150ms)
```

### Tooltip / Popover
```
Trigger: 500ms hover delay (avoid false triggers)
Enter: fade-up 8px + opacity 0->1, 200ms ease-enter, from anchor point
Exit: fade-down 4px + opacity 1->0, 120ms ease-exit-sharp (faster than enter)
```

## Scroll-Linked Effects

- **Parallax**: Background layers scroll at 0.3-0.5x content speed. Foreground elements at 1.0x. Creates depth without interaction cost.
- **Reveal on scroll**: Elements fade-up as they enter viewport (IntersectionObserver, threshold 0.15). Once revealed, stay revealed (no reverse animation).
- **Sticky headers**: Shrink transition (height 64px -> 48px) on scroll-down, expand on scroll-up. Use transform for GPU acceleration.

## Reduced Motion

Every choreography MUST have a `prefers-reduced-motion` alternative:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

For semantic animations (state changes communicating information): replace motion with instant color/opacity changes. The information must still be communicated, just without movement.

## Performance Rules

- Use `transform` and `opacity` for animations (GPU-composited, no layout thrashing)
- Declare `will-change` on elements that will animate (remove after animation completes)
- Avoid animating `width`, `height`, `top`, `left`, `margin`, `padding` -- these trigger layout
- Cap simultaneous animations at 8-12 elements. Beyond that, group into batches.
- Test at 4x slowdown in DevTools to catch jank
