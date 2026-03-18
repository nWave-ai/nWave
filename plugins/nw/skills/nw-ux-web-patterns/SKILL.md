---
name: nw-ux-web-patterns
description: Web UI design patterns for product owners. Load when designing web application interfaces, writing web-specific acceptance criteria, or evaluating responsive designs.
disable-model-invocation: true
---

# Web UI Patterns

Actionable web interface patterns for requirements gathering and design review. Use when the target platform is web (browser-based applications).

## Navigation Patterns

| Pattern | When to Use | When to Avoid |
|---------|-------------|---------------|
| **Top navigation bar** | 5-7 primary sections, marketing/content sites | Deep hierarchies with 20+ sections |
| **Side navigation** | Complex apps with many sections, admin dashboards | Simple sites with few pages |
| **Breadcrumbs** | Deep hierarchies, e-commerce categories | Flat site structures |
| **Command palette** (Cmd+K) | Power user tools, developer-facing apps | Consumer apps targeting non-technical users |
| **Tab bar** (mobile) | 3-5 primary destinations | More than 5 destinations |
| **Hamburger menu** | Secondary navigation, mobile space constraints | Primary navigation users need frequently |
| **Mega menu** | Large sites with categorized content | Simple sites, mobile interfaces |

**Navigation must answer three questions**: Where am I? Where can I go? How do I get back?

Key principles: consistent placement across all pages | highlight current location | limit primary nav to 5-7 items (Hick's Law) | provide search as alternative for content-heavy apps

## Form Design

### Layout
- Labels above input fields (highest completion rates in eye-tracking studies)
- One column layouts outperform multi-column for most forms
- Group related fields with visual proximity and clear section headings
- Primary action buttons left-aligned with form fields

### Validation: Reward Early, Punish Late
- Validate on blur (when user leaves field), not while typing
- Remove error messages immediately when user corrects the field
- Show success indicators only when helpful (e.g., password strength)
- Validation summary at top for longer forms, plus inline errors

### Error Messages Must Include
1. What went wrong (plain language) | 2. Where the error is (highlight field) | 3. How to fix it (specific guidance, not "invalid input")

### Progressive Forms
- Split long forms across multiple steps (one-thing-per-page pattern)
- Show progress indicators for multi-step forms
- Allow saving progress and returning later
- Reduce fields through smart defaults and progressive disclosure

## Data Display Patterns

| Pattern | Best For | Key Considerations |
|---------|----------|-------------------|
| **Tables** | Structured data with multiple attributes, comparison | Sortable columns, fixed headers, responsive collapse |
| **Cards** | Browsable collections with images/summaries | Consistent sizes, clear click targets, max 3-4 per row |
| **Lists** | Sequential items, search results, feeds | Clear boundaries, scannable titles, secondary info on right |
| **Dashboards** | KPI monitoring, status overviews | Important metrics top-left, max 7 widgets, allow customization |

### Pagination vs Infinite Scroll
- **Pagination**: Goal-directed tasks (search, admin panels) -- gives position and control
- **Infinite scroll**: Discovery browsing (social media, galleries) -- reduces friction

## Responsive Design

### Mobile-First Approach
Design mobile layout first, then enhance for larger screens. Ensures core content and functionality are prioritized.

### Breakpoints (starting points)
360-480px: Mobile | 768px: Tablet | 1024-1280px: Small desktop | 1440px+: Large desktop

### Key Techniques
- **Fluid typography**: `clamp()` for smooth scaling; `rem`/`em` over `px` for accessible sizing
- **Container queries**: Components respond to container size (not viewport), enabling reusable components
- **Responsive images**: Serve appropriate sizes; use `srcset` and `picture` elements

## Component Patterns

| Component | Use For | Anti-pattern |
|-----------|---------|-------------|
| **Modal dialog** | Decisions requiring immediate attention; blocks until resolved | Information not requiring action; stacking modals |
| **Toast/snackbar** | Non-critical confirmation ("Item saved") | Critical errors or info users must not miss |
| **Drawer/sheet** | Supplementary content or filters alongside main view | Primary content or complex multi-step forms |
| **Popover/tooltip** | Contextual help or previews on hover/focus | Critical info or complex interactions |
| **Command palette** | Quick action access via keyboard | Only navigation method (need visual alternatives) |

## Motion and Micro-interactions

### When Motion Helps
Showing cause and effect (button press ripple) | Guiding attention to changes (new item slides in) | Providing feedback (spinners, progress bars) | Explaining spatial relationships (drawer slides from side) | Maintaining context during transitions (shared element transitions)

### When Motion Distracts
Decorative animations with no function | Animations delaying task completion | Rapid/large-scale motion (respect `prefers-reduced-motion`) | Looping animations that cannot be paused

**Duration guidelines**: 100-200ms for simple state changes | 200-500ms for complex transitions | never exceed 500ms for functional animations

## Design System Guidance

### When to Use Existing vs Custom

| Situation | Recommendation |
|-----------|---------------|
| Internal tools, admin dashboards | Use existing system (Material UI, Ant Design, Radix) |
| Consumer product with strong brand | Custom system on headless library (Radix, Headless UI) |
| MVP or prototype | Use existing system; customize later |
| Platform with strict brand guidelines | Custom system, adopt token architecture from established systems |

**Established systems to evaluate**: Material Design (Google) | Fluent Design (Microsoft) | Carbon (IBM) | Polaris (Shopify) | Primer (GitHub) | Lightning (Salesforce)

### Design Tokens
Atomic values defining visual design: colors, spacing, typography, shadows.

| Level | Example | Purpose |
|-------|---------|---------|
| **Global** | `color-blue-500: #3B82F6` | Raw palette values |
| **Semantic** | `color-primary: {color-blue-500}` | Meaningful names |
| **Component** | `button-bg: {color-primary}` | Component-specific references |

Use 8px spacing grid. Use modular typography scale (1.25 or 1.333 ratio).

## Web-Specific Anti-Patterns

| Anti-Pattern | Alternative |
|-------------|-------------|
| Autoplay video with sound | Mute by default, user-initiated play |
| Full-page interstitials on mobile | Inline or bottom-sheet prompts |
| Captchas for every action | Risk-based authentication, invisible captchas |
| Horizontal scrolling for content | Responsive layout fitting viewport |
| Form validation only on submit | Inline validation with reward-early-punish-late |
| Mystery meat navigation (icons only) | Label all nav items; icons supplement, not replace |
| Stacking modals | Inline expansion or navigate to new page |

## Acceptance Criteria Template (Web)

```gherkin
Feature: [Feature Name]
  # Platform: web
  # Key heuristics: [applicable Nielsen heuristics]
  # Accessibility: WCAG 2.2 AA

  Scenario: Happy path
    Given [context]
    When [user action]
    Then [expected visible result]
    And system provides feedback within 100ms
    And the action can be undone via [mechanism]

  Scenario: Error state
    Given [context leading to error]
    When [user action that triggers error]
    Then an error message explains what happened
    And the error message suggests what to do next
    And the error is shown inline next to the relevant field

  Scenario: Empty state
    Given no [resources] exist yet
    When the user navigates to the [resource] view
    Then a helpful message explains what [resources] are
    And a clear call to action creates the first one

  Scenario: Keyboard accessibility
    Given the user navigates with keyboard only
    When they tab through the interface
    Then all interactive elements are reachable
    And focus indicators are visible
```
