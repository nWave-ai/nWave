---
name: nw-futuristic-color-typography
description: Color palettes, font pairing, and visual treatments for sci-fi aesthetics -- concrete values with rationale
disable-model-invocation: true
---

# Futuristic Color and Typography

## Color Philosophy

Futuristic palettes derive from two forces: **environmental lighting** (what kind of world is this?) and **semantic clarity** (what does each color mean?). Decoration-driven color fails in both dimensions.

### Why Dark UI is Universal in Sci-Fi

Not arbitrary fashion — grounded in visual perception science:
1. **Contrast and Focus**: Dark backgrounds create maximum contrast for luminous elements
2. **Reduced Eye Strain**: In dark environments, dark interfaces reduce brightness adaptation fatigue
3. **Visual Hierarchy**: On dark backgrounds, any colored element commands immediate attention
4. **Atmospheric Enhancement**: Dark themes support dramatic, mysterious aesthetics
5. **Power Efficiency**: On OLED displays, dark pixels consume less energy

**Rules**: Never use pure black (`#000000`) for backgrounds — use dark desaturated tones with subtle blue/teal tint. Never use pure white (`#FFFFFF`) for text — use slightly dimmed white. "The best futuristic palettes feel like city lights on wet asphalt: mostly dark, with a few sharp signals that pull your eye exactly where you want it."

## Palette Archetypes

### 1. Cybernetic Cool (Cyberpunk / Ghost in the Shell)

**Mood**: Technological, sharp, electric
**Base**: Deep navy/charcoal (`#0a0e1a` to `#1a1f33`)
**Primary accent**: Electric cyan (`#00e5ff`) -- attention, interactive elements
**Secondary accent**: Magenta/pink (`#ff0055`) -- alerts, destructive actions
**Tertiary**: Amber (`#ffab00`) -- warnings, caution states
**Surface**: Frosted dark (`#1a1f33` at 80% opacity with 8px blur)
**Text**: Cool white (`#e0e6f0`) primary | Muted blue-gray (`#7a8ba8`) secondary

### 2. Warm Utilitarian (The Expanse / Alien)

**Mood**: Industrial, competent, lived-in
**Base**: Dark warm gray (`#1c1a17` to `#2a2722`)
**Primary accent**: Warm amber (`#e8a020`) -- active, nominal
**Secondary accent**: Soft green (`#4caf50`) -- confirmed, success
**Tertiary**: Coral red (`#ef5350`) -- critical, failure
**Surface**: Matte dark (`#2a2722` at 95% opacity, minimal blur)
**Text**: Warm white (`#f0ebe0`) primary | Muted tan (`#8a8070`) secondary

### 3. Clean Holographic (Iron Man / Halo)

**Mood**: Premium, spatial, expansive
**Base**: Near-black with blue undertone (`#080c14`)
**Primary accent**: Soft blue (`#4da6ff`) -- interactive, links
**Secondary accent**: Gold (`#ffd740`) -- highlights, achievements
**Tertiary**: Soft red (`#ff5252`) -- errors
**Surface**: Glass layers (`#ffffff` at 5-15% opacity, 12-20px blur)
**Text**: Pure white (`#ffffff`) primary | Soft blue-white (`#b0c4de`) secondary

### 4. Organic Neural (Warframe / Sword Art Online)

**Mood**: Living, responsive, intimate
**Base**: Deep purple-black (`#0d0a14`)
**Primary accent**: Bioluminescent teal (`#00bfa5`) -- living/active
**Secondary accent**: Soft violet (`#b388ff`) -- secondary actions
**Tertiary**: Warm coral (`#ff8a65`) -- attention needed
**Surface**: Translucent purple (`#1a0e2e` at 70% opacity, 6px blur)
**Text**: Soft lavender-white (`#e8e0f0`) primary | Muted purple (`#9080a8`) secondary

## Semantic Color Layer

Regardless of palette archetype, maintain consistent semantic mapping:

| Semantic | Role | Example States |
|----------|------|---------------|
| Nominal | System healthy, default active | Running, connected, synced |
| Caution | Attention needed, not critical | Degraded, approaching limit |
| Critical | Immediate action required | Down, error, breach |
| Informational | Neutral data, no action needed | Logs, metadata, timestamps |
| Interactive | Clickable, hoverable, editable | Buttons, links, inputs |
| Disabled | Not available, grayed | Locked features, pending states |

## Typography

### Font Pairing Strategy

Futuristic typography pairs a **display/heading** face (geometric or monospaced, carries the aesthetic) with a **body** face (highly readable, carries the content).

| Style | Display Font | Body Font | Mono Font |
|-------|-------------|-----------|-----------|
| Cybernetic | Orbitron, Rajdhani, Exo 2 | Inter, IBM Plex Sans | JetBrains Mono, Fira Code |
| Utilitarian | Share Tech, Barlow | Source Sans 3, Roboto | Source Code Pro, IBM Plex Mono |
| Holographic | Montserrat, Poppins (light weights) | Inter, Nunito Sans | Cascadia Code, Iosevka |
| Organic | Quicksand, Comfortaa | Nunito, Rubik | Victor Mono, Maple Mono |
| Retro-Futuristic | Space Mono, OCR-A | Exo, Inter | Space Mono, OCR-B |
| Japanese/Eva-style | Matisse EB (Fontworks) | Noto Sans JP | M PLUS 1 Code |

**Evangelion Typography Legacy**: Director Anno chose **Matisse EB** — bold, condensed, Mincho-esque, creating a "loud, foreboding" aesthetic. Used desktop typesetting when all anime subcontractors hand-painted type, giving unprecedented typographic control. Described as "solid Japanese typography combined with a Swiss sensibility." Established the convention of type-based anime visual identities.

**Sci-fi fonts shine as display typefaces** — pair with clean, simple secondary fonts for body text. Titles, HUD elements, and interface labels benefit from geometric display fonts; data readouts and body text need legibility first.

### Type Scale (1.25 ratio, 16px base)

```
--text-xs:   0.64rem   (10.24px) -- captions, timestamps
--text-sm:   0.80rem   (12.80px) -- secondary labels
--text-base: 1.00rem   (16.00px) -- body text
--text-lg:   1.25rem   (20.00px) -- subheadings
--text-xl:   1.563rem  (25.00px) -- section titles
--text-2xl:  1.953rem  (31.25px) -- page titles
--text-3xl:  2.441rem  (39.06px) -- hero/display
--text-4xl:  3.052rem  (48.83px) -- dramatic/splash
```

### Kinetic Typography Rules

- **State labels**: Uppercase, letter-spacing 0.15em, font-weight 500-600
- **Data values**: Tabular numerals (font-variant-numeric: tabular-nums), monospaced
- **Transitions**: Text color transitions over 200-300ms, never instant
- **Entry animations**: Fade-up (translateY 8px + opacity 0->1) over 300ms for content blocks
- **Number changes**: Counter animation with digit-by-digit transition (odometer style)

## Visual Treatments

### Glassmorphism Depth System

```
Layer 0 (Background):  no blur, full opacity, darkest
Layer 1 (Surface):     backdrop-blur: 8px,  bg-opacity: 60-80%
Layer 2 (Elevated):    backdrop-blur: 12px, bg-opacity: 40-60%
Layer 3 (Modal/Focus): backdrop-blur: 20px, bg-opacity: 70-90%
```

### Glow and Emission

- **Interactive glow**: `box-shadow: 0 0 12px {accent}40` (25% opacity accent) on hover/focus
- **Active emission**: `box-shadow: 0 0 20px {accent}60, 0 0 4px {accent}80` on active state
- **Status glow**: `box-shadow: 0 0 8px {semantic-color}30` as ambient indicator
- **Text glow**: `text-shadow: 0 0 8px {color}40` for emphasized headings only (sparingly)

### Border Treatments

- **Standard**: 1px solid with accent color at 20-30% opacity
- **Active/focused**: 1px solid accent at 60-80%
- **Gradient border**: Use `border-image: linear-gradient(...)` for premium feel on key containers
- **Animated border**: Gradient rotation via `@property` for loading states

## Accessibility Integration

Every palette must pass:
- **AA contrast** (4.5:1) for all text against its background
- **AA large text** (3:1) for headings 18px+ or bold 14px+
- Semantic colors distinguishable without color alone (icons, patterns, labels)
- Test tool: plug values into WebAIM contrast checker or axe DevTools
