---
name: nw-css-implementation-recipes
description: Concrete CSS code snippets for futuristic UI patterns -- glassmorphism, neon glows, HUD elements, data grids, holographic effects
disable-model-invocation: true
---

# CSS Implementation Recipes

## Foundation: Custom Properties

Set up a theming layer that all recipes reference:

```css
:root {
  /* Palette (override per theme) */
  --color-base: #0a0e1a;
  --color-surface: #1a1f33;
  --color-accent: #00e5ff;
  --color-accent-secondary: #ff0055;
  --color-warning: #ffab00;
  --color-text-primary: #e0e6f0;
  --color-text-secondary: #7a8ba8;

  /* Depth layers */
  --blur-surface: 8px;
  --blur-elevated: 12px;
  --blur-modal: 20px;
  --opacity-surface: 0.7;
  --opacity-elevated: 0.5;
  --opacity-modal: 0.85;

  /* Motion */
  --duration-micro: 100ms;
  --duration-fast: 175ms;
  --duration-normal: 300ms;
  --duration-slow: 500ms;
  --ease-enter: cubic-bezier(0.0, 0.0, 0.2, 1.0);
  --ease-exit: cubic-bezier(0.4, 0.0, 1.0, 1.0);
  --ease-morph: cubic-bezier(0.4, 0.0, 0.2, 1.0);
  --ease-cyber: cubic-bezier(0.0, 0.8, 0.2, 1.0);

  /* Type */
  --font-display: 'Orbitron', 'Rajdhani', sans-serif;
  --font-body: 'Inter', 'IBM Plex Sans', sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
}
```

## Recipe 1: Glassmorphism Panel

```css
.glass-panel {
  background: rgba(26, 31, 51, var(--opacity-surface));
  backdrop-filter: blur(var(--blur-surface));
  -webkit-backdrop-filter: blur(var(--blur-surface));
  border: 1px solid rgba(0, 229, 255, 0.15);
  border-radius: 8px;
  padding: 1.5rem;
  transition: border-color var(--duration-fast) var(--ease-morph),
              box-shadow var(--duration-fast) var(--ease-morph);
}

.glass-panel:hover {
  border-color: rgba(0, 229, 255, 0.35);
  box-shadow: 0 0 12px rgba(0, 229, 255, 0.1);
}

.glass-panel--elevated {
  backdrop-filter: blur(var(--blur-elevated));
  background: rgba(26, 31, 51, var(--opacity-elevated));
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.glass-panel--modal {
  backdrop-filter: blur(var(--blur-modal));
  background: rgba(26, 31, 51, var(--opacity-modal));
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.5);
}
```

## Recipe 2: Neon Glow Button

```css
.btn-neon {
  font-family: var(--font-display);
  font-size: 0.875rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--color-accent);
  background: transparent;
  border: 1px solid var(--color-accent);
  border-radius: 4px;
  padding: 0.75rem 1.5rem;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: all var(--duration-fast) var(--ease-cyber);
}

.btn-neon:hover {
  background: rgba(0, 229, 255, 0.1);
  box-shadow: 0 0 16px rgba(0, 229, 255, 0.25),
              inset 0 0 16px rgba(0, 229, 255, 0.05);
}

.btn-neon:active {
  transform: scale(0.98);
  box-shadow: 0 0 24px rgba(0, 229, 255, 0.4),
              inset 0 0 24px rgba(0, 229, 255, 0.1);
}

/* Ripple effect */
.btn-neon::after {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at var(--x, 50%) var(--y, 50%),
    rgba(0, 229, 255, 0.3) 0%, transparent 60%);
  opacity: 0;
  transition: opacity var(--duration-normal) var(--ease-enter);
}

.btn-neon:hover::after { opacity: 1; }

/* Variant: filled/primary */
.btn-neon--primary {
  background: var(--color-accent);
  color: var(--color-base);
  font-weight: 600;
}

.btn-neon--primary:hover {
  background: var(--color-accent);
  box-shadow: 0 0 20px rgba(0, 229, 255, 0.5);
}
```

## Recipe 3: HUD Frame / Container

```css
.hud-frame {
  position: relative;
  border: 1px solid rgba(0, 229, 255, 0.2);
  padding: 1rem;
}

/* Corner accents */
.hud-frame::before,
.hud-frame::after {
  content: '';
  position: absolute;
  width: 12px;
  height: 12px;
  border-color: var(--color-accent);
  border-style: solid;
}

.hud-frame::before {
  top: -1px; left: -1px;
  border-width: 2px 0 0 2px;
}

.hud-frame::after {
  bottom: -1px; right: -1px;
  border-width: 0 2px 2px 0;
}

/* Label bar */
.hud-frame__label {
  position: absolute;
  top: -0.6rem;
  left: 1.5rem;
  background: var(--color-base);
  padding: 0 0.5rem;
  font-family: var(--font-display);
  font-size: var(--text-xs, 0.64rem);
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--color-accent);
}
```

## Recipe 4: Scan-Line Overlay

```css
.scan-lines {
  position: relative;
}

.scan-lines::after {
  content: '';
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0, 0, 0, 0.05) 2px,
    rgba(0, 0, 0, 0.05) 4px
  );
  pointer-events: none;
  z-index: 1;
}

/* Animated scan beam */
.scan-lines--animated::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    180deg,
    transparent 0%,
    rgba(0, 229, 255, 0.03) 50%,
    transparent 100%
  );
  height: 30%;
  animation: scan-beam 4s linear infinite;
  pointer-events: none;
  z-index: 2;
}

@keyframes scan-beam {
  0%   { transform: translateY(-100%); }
  100% { transform: translateY(400%); }
}
```

## Recipe 5: Data Grid / Monitoring Table

```css
.data-grid {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  border-collapse: collapse;
  width: 100%;
}

.data-grid th {
  font-family: var(--font-display);
  font-size: 0.64rem;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: var(--color-text-secondary);
  text-align: left;
  padding: 0.5rem 1rem;
  border-bottom: 1px solid rgba(0, 229, 255, 0.2);
  font-weight: 500;
}

.data-grid td {
  padding: 0.5rem 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  font-variant-numeric: tabular-nums;
  color: var(--color-text-primary);
}

.data-grid tr:hover td {
  background: rgba(0, 229, 255, 0.05);
}

/* Status cells */
.data-grid .status--nominal { color: #4caf50; }
.data-grid .status--warning { color: #ffab00; }
.data-grid .status--critical {
  color: #ff0055;
  animation: pulse-critical 1.5s ease-in-out infinite;
}

@keyframes pulse-critical {
  0%, 100% { opacity: 1; }
  50%      { opacity: 0.6; }
}
```

## Recipe 6: Animated Gradient Border

```css
@property --angle {
  syntax: '<angle>';
  initial-value: 0deg;
  inherits: false;
}

.gradient-border {
  position: relative;
  border-radius: 8px;
  padding: 1px; /* border width */
  background: conic-gradient(
    from var(--angle),
    var(--color-accent),
    transparent 30%,
    transparent 70%,
    var(--color-accent)
  );
  animation: rotate-border 3s linear infinite;
}

.gradient-border > * {
  background: var(--color-surface);
  border-radius: 7px;
  padding: 1.5rem;
}

@keyframes rotate-border {
  to { --angle: 360deg; }
}

/* Use for loading states only -- remove animation when loaded */
.gradient-border--idle {
  animation: none;
  background: linear-gradient(135deg,
    rgba(0, 229, 255, 0.2),
    transparent 50%,
    rgba(0, 229, 255, 0.1)
  );
}
```

## Recipe 7: Holographic Shimmer

```css
.holo-shimmer {
  position: relative;
  overflow: hidden;
}

.holo-shimmer::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    105deg,
    transparent 40%,
    rgba(0, 229, 255, 0.06) 45%,
    rgba(0, 229, 255, 0.12) 50%,
    rgba(0, 229, 255, 0.06) 55%,
    transparent 60%
  );
  animation: shimmer 3s ease-in-out infinite;
  pointer-events: none;
}

@keyframes shimmer {
  0%   { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}
```

## Recipe 8: Status Indicator (Diegetic)

```css
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
  vertical-align: middle;
  margin-right: 0.5rem;
}

.status-dot--nominal {
  background: #4caf50;
  box-shadow: 0 0 6px rgba(76, 175, 80, 0.4);
}

.status-dot--warning {
  background: #ffab00;
  box-shadow: 0 0 6px rgba(255, 171, 0, 0.4);
  animation: pulse-warning 2s ease-in-out infinite;
}

.status-dot--critical {
  background: #ff0055;
  box-shadow: 0 0 8px rgba(255, 0, 85, 0.5);
  animation: pulse-critical 1s ease-in-out infinite;
}

@keyframes pulse-warning {
  0%, 100% { box-shadow: 0 0 6px rgba(255, 171, 0, 0.4); }
  50%      { box-shadow: 0 0 12px rgba(255, 171, 0, 0.7); }
}
```

## Recipe 9: Typewriter / Terminal Text

```css
.typewriter {
  font-family: var(--font-mono);
  overflow: hidden;
  white-space: nowrap;
  border-right: 2px solid var(--color-accent);
  animation:
    typing 2s steps(40, end) forwards,
    blink-caret 0.75s step-end infinite;
  width: 0;
}

@keyframes typing {
  to { width: 100%; }
}

@keyframes blink-caret {
  0%, 100% { border-color: var(--color-accent); }
  50%      { border-color: transparent; }
}

/* For JS-driven character-by-character (better control) */
.terminal-char {
  opacity: 0;
  animation: char-appear 50ms var(--ease-enter) forwards;
}
```

## Recipe 10: Reduced Motion Overrides

```css
@media (prefers-reduced-motion: reduce) {
  .scan-lines--animated::before,
  .holo-shimmer::after,
  .gradient-border { animation: none; }

  .status-dot--warning,
  .status-dot--critical { animation: none; }

  .typewriter {
    animation: none;
    width: auto;
    border-right: none;
  }

  /* Replace motion with instant state changes */
  * {
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
  }
}
```

## Tailwind Integration Notes

When using Tailwind CSS, these recipes translate to:

- **Glassmorphism**: `backdrop-blur-sm bg-slate-900/70 border border-cyan-400/15 rounded-lg`
- **Neon button**: Custom plugin or `@apply` with `ring-cyan-400/25 hover:ring-2 hover:shadow-[0_0_16px_rgba(0,229,255,0.25)]`
- **Status colors**: Extend `colors` in config with semantic names (`nominal`, `caution`, `critical`)
- **HUD corners**: Custom component (pseudo-elements not available via utility classes alone)
- **Motion**: Extend `transitionTimingFunction` with cyber/glitch curves

For complex recipes (HUD frame, gradient border, scan lines), create Tailwind components or use CSS files alongside utilities. Do not force complex pseudo-element patterns into utility classes.

## Performance Checklist

- [ ] All animations use `transform` and `opacity` only
- [ ] `backdrop-filter` used sparingly (costly -- max 3-4 layered panels visible)
- [ ] `will-change` set on animating elements, removed after completion
- [ ] No `box-shadow` animations (use pseudo-element opacity trick instead)
- [ ] `@media (prefers-reduced-motion)` overrides present for all animations
- [ ] Tested at 4x CPU throttle in Chrome DevTools
