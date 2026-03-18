---
name: nw-sci-fi-design-patterns
description: Catalog of UI patterns from games, anime, and films with analysis of why they work -- structural principles extractable to real interfaces
disable-model-invocation: true
---

# Sci-Fi Design Patterns

## Pattern Categories

### 1. Diegetic UI (Interface Lives in the World)

**Source**: Dead Space (health bar on spine), Iron Man (JARVIS holographic workspace), Mass Effect (Omni-tool)

**Why it works**: Eliminates the cognitive split between "looking at the interface" and "being in the experience." Users stay immersed. Information is spatially anchored to the object it describes.

**Extractable principles**:
- Status indicators attached to the element they describe (badge on avatar, not separate panel)
- Context menus appear at the point of interaction, not in a fixed sidebar
- Progress indicators are part of the action element (button fills as it processes)
- Health/status of a system component shown ON the component representation

**Key insight**: Dead Space's diegetic UI works because it eliminates the split-attention effect from Cognitive Load Theory — information in the same visual plane as the game world means eyes never dart to screen corners. The trade-off (harder to parse quickly) is intentional for horror, but for productivity tools, make diegetic elements easy to read.

**Deeper examples**: Navigation waypoint (glowing floor line instead of minimap), holographic inventory that exists in real-time (enemies can attack while browsing), stasis energy as wearable semicircular meter.

**Web/App translation**: Inline editing|contextual toolbars|progress-as-button-state|status-as-color-on-node (monitoring dashboards)

### 2. Holographic Layering (Depth Through Transparency)

**Source**: Iron Man (JARVIS floating panels), Minority Report (gesture layers), Halo (holographic briefings)

**Why it works**: Creates spatial hierarchy without consuming screen real estate. Background layers provide context; foreground layers demand attention. Parallax between layers communicates depth.

**Extractable principles**:
- 3-4 depth layers: background (environmental/ambient) | mid-ground (contextual/secondary) | foreground (primary interaction) | overlay (urgent/modal)
- Each layer has distinct opacity range: background 10-30% | mid-ground 40-60% | foreground 70-90% | overlay 90-100%
- Blur increases with depth (backdrop-filter: blur scales per layer)
- Interactive elements always on foreground or overlay -- never bury clickable things in background layers

**Web/App translation**: Glassmorphism with semantic layers|modal stacking with blur gradients|dashboard panels at different z-depths with transparency

### 3. Scan-Line / Data Stream Aesthetic

**Source**: Ghost in the Shell (Standalone Complex), Blade Runner 2049, The Matrix

**Why it works**: Communicates "live data" and "processing" without explicit loading spinners. The visual noise IS the signal that the system is alive and working. Creates atmosphere of technological depth.

**Extractable principles**:
- Subtle horizontal scan-line overlays (1px lines at 5-10% opacity) on data-heavy panels
- Monospaced typography for data values (not for labels)
- Numbers that increment/decrement with visible digit transitions
- Background data streams (scrolling hex, log entries) behind primary content at very low opacity

**Web/App translation**: CSS pseudo-element scan-lines on cards|counting animations on metrics|scrolling log panels as ambient background|typewriter effects on status messages

### 4. Utilitarian / Belter Style (Function as Aesthetic)

**Source**: The Expanse (Belter ship interfaces), Alien (Nostromo terminals), Evangelion (NERV control panels)

**Why it works**: Raw functionality creates its own beauty. Dense information displays feel competent and trustworthy. Users who need power tools want density, not whitespace. The interface looks like it was built by engineers for engineers.

**Extractable principles**:
- High information density with clear grid structure
- Color used semantically only (green=nominal, amber=warning, red=critical, blue=informational)
- Monospaced fonts, ALL CAPS for labels, mixed case for values
- Minimal decoration -- borders are thin lines, not shadows or gradients
- Status communicated through color temperature shifts across the entire panel, not individual alerts

**Web/App translation**: Terminal-style dashboards|grid-based monitoring|semantic-only color palettes|data tables with inline sparklines

### 5. Neural / Organic Interface

**Source**: Ghost in the Shell (brain-computer interfaces), Warframe (modular organic UI), Sword Art Online (AR menus)

**Why it works**: Organic curves and flowing animations feel responsive and alive. The interface appears to react to the user rather than just executing commands. Creates intimacy between user and system.

**Extractable principles**:
- Rounded containers with flowing transitions (not snapping)
- Elements that slightly breathe (subtle scale oscillation, 0.5-1% over 3-4 seconds)
- Connection lines between related elements (bezier curves, not straight lines)
- Radial menus and circular navigation patterns
- Particle effects at interaction points (click ripples, hover auras)

**Web/App translation**: Radial menus for power-user shortcuts|breathing indicators for active/live elements|bezier connections in node graphs|ripple effects on interaction

### 6. Minimal AI Interface

**Source**: Her (OS1 interface), Blade Runner 2049 (Joi), Steins;Gate (future gadgets)

**Why it works**: When the AI is the interface, chrome disappears. Conversation becomes the UI. Visual elements serve the dialogue, not the reverse. Maximum content, minimum decoration.

**Extractable principles**:
- Large typography as primary interface element
- Generous whitespace (the anti-density approach)
- Single focal point per screen state
- Transitions are content-driven (new text appears, old fades) not chrome-driven (panels slide)
- Color used as emotional indicator, not categorical

**Key insight (Her)**: "Notably missing in OS1 is a face or any other visual anthropomorphic aspect. She exists across various displays and devices, in some psychological ether between them." — the disembodied AI principle leverages imagination over visual representation.

**Web/App translation**: Chat interfaces|voice-first UIs|single-purpose screens|ambient color theming that shifts with context

### 7. Faction-as-Design-System (Interface as Identity)

**Source**: The Expanse (faction-specific UIs), Blade Runner 2049 (technology strata), Star Citizen (manufacturer-specific MFDs), Tron Legacy (blue=programs, orange=corruption)

**Why it works**: Interface aesthetics communicate social class, culture, and institutional identity instantly. Rhys Yorke (The Expanse): "immediately as soon as the shot opened in a ship, I wanted the viewer to know that they were on a Martian ship, an Earth fleet ship, or a Belter ship."

**Extractable principles**:
- Different user roles/contexts get visually distinct but structurally consistent interfaces
- Color temperature signals faction/role (cool=institutional, warm=independent, neutral=utilitarian)
- Technology fidelity reflects status (pristine=premium, degraded=worn, lo-fi=resourceful)
- Blade Runner 2049's three strata: LAPD (degraded, screen-burned), Wallace Corp (pristine black-and-white), Street-level (barely functional)

**Web/App translation**: Multi-tenant SaaS branding|role-based dashboard theming|white-label design systems|admin vs user visual differentiation

### 8. Threshold-Based Decision UI (Data Drives Consequence)

**Source**: Psycho-Pass (Crime Coefficient system), Cyberpunk 2077 (scanner analysis), Evangelion (MAGI consensus voting)

**Why it works**: The interface doesn't just display data — it triggers consequences at defined thresholds. Users see exactly where they stand relative to action boundaries.

**Extractable principles**:
- Clear numerical thresholds with color-coded zones (green < 100, yellow 100-299, red > 300)
- The interface itself transforms at thresholds (Psycho-Pass Dominator physically reconfigures)
- Consensus visualizations for multi-system decisions (MAGI's three-way voting display)
- Scanning interfaces that fill/progress as analysis completes (Cyberpunk 2077's expanding circle reticle)

**Web/App translation**: SLA dashboards with action thresholds|budget burn-rate indicators|security scoring with escalation triggers|build health monitors

### 9. HUD-as-Gameplay / Configurable UI (NieR Paradigm)

**Source**: NieR:Automata (chip system), Warframe (modular UI), Cyberpunk 2077 (implant-justified HUD)

**Why it works**: Users control their own information density. The interface becomes a resource to allocate, not a fixed frame.

**Extractable principles**:
- HUD elements are equippable/removable — users choose their information density
- NieR's chip system: unequip health bar to free resources for other features
- Warframe's Orbiter: spatial UI hub where physical locations map to different systems
- "Narrative-justified non-diegetic UI" — Cyberpunk frames traditional HUD as cybernetic implant output

**Design wisdom (Hisayoshi Kijima, NieR)**: "I want your grandmother to be able to use them" — all menus operable with joystick + two buttons only. Warm beige palette (not cold cyan), information through thickness/darkness variations rather than color.

**Web/App translation**: Customizable dashboards|widget-based layouts|user-controlled information density|progressive feature revelation

## Pattern Selection Guide

| Project Emotional Tone | Primary Pattern | Secondary Pattern |
|----------------------|----------------|-------------------|
| Power / Control | Utilitarian (Belter) | Scan-Line |
| Wonder / Exploration | Holographic Layering | Neural / Organic |
| Intimacy / Trust | Minimal AI | Neural / Organic |
| Urgency / Operations | Utilitarian (Belter) | Diegetic UI |
| Immersion / Gaming | Diegetic UI | Holographic Layering |
| Futuristic / Corporate | Holographic Layering | Scan-Line |
| Multi-tenant / Branding | Faction-as-Design-System | Holographic Layering |
| Monitoring / SRE | Threshold-Based Decision | Utilitarian (Belter) |
| Customizable / Power User | Configurable UI (NieR) | Utilitarian (Belter) |

## Combining Patterns

Most effective designs combine 2 patterns. Three creates visual noise. One can feel flat.

**Strong combinations**: Diegetic + Utilitarian (operational dashboards)|Holographic + Neural (creative tools)|Minimal AI + Scan-Line (data-driven chat)|Utilitarian + Scan-Line (monitoring/SRE)

**Weak combinations**: Minimal AI + Utilitarian (contradictory density philosophies)|Neural + Scan-Line (organic + mechanical clash)|All three decorative patterns simultaneously (noise)
