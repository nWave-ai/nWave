---
name: nw-ux-desktop-patterns
description: Desktop application UI patterns for product owners. Load when designing native or cross-platform desktop applications, writing desktop-specific acceptance criteria, or evaluating panel layouts and keyboard workflows.
disable-model-invocation: true
---

# Desktop Application UI Patterns

Actionable desktop interface patterns for requirements gathering and design review. Use when target platform is native or cross-platform desktop application.

## Native vs Cross-Platform

**Native advantages**: Platform conventions feel familiar | better system integration (file dialogs, notifications, drag-and-drop) | consistent OS look and feel | better accessibility through native APIs.

**Cross-platform tradeoffs**: Shared codebase reduces cost | visual consistency may conflict with platform expectations | custom rendering may miss OS accessibility features.

**Guidance**: If users primarily on one platform, prioritize native conventions. If cross-platform required, follow each platform's conventions for core interactions (menus, shortcuts, window management) while sharing domain-specific UI.

## Core Desktop UI Elements

### Menu Bar
Primary access point for all commands. Organize by convention: File, Edit, View, then domain-specific, ending with Window and Help. Every item should have keyboard shortcut for frequent actions. Group with separators; submenus sparingly (one level deep preferred).

### Toolbar
Quick access to most common commands (subset of menu bar). Should be configurable: show, hide, rearrange. Every button must have tooltip. Include both icon and text label for primary actions.

### Status Bar
Displays contextual info: document stats, cursor position, connection status, mode indicators. Low-profile: supports awareness without demanding attention. Update in real-time.

### Context Menus
Right-click with small number of relevant actions. Include standard actions (Cut, Copy, Paste) plus domain-specific. Mirror keyboard shortcuts from main menu.

## Document-Centric vs Task-Centric Layouts

### Document-Centric (Word, Photoshop, VS Code)
Central canvas with surrounding tool panels. Users work on one primary artifact. Maximize canvas space; make panels collapsible and dockable. Support zoom, scroll, viewport controls. Auto-save with visible state indicator.

### Task-Centric (Slack, email clients, CRM)
Multiple panels showing different workflow aspects. Users switch between views frequently. Quick navigation between contexts. Support split views and list-detail patterns. Persistent sidebar for task/project navigation.

### Choosing the Right Layout
- Most time creating/editing single artifact: document-centric
- Juggling multiple items with frequent context switching: task-centric
- Hybrid: primary task is document-centric but requires reference panels

## Keyboard Shortcuts

### Platform Conventions
Follow OS standards: Ctrl+C/Cmd+C (copy), Ctrl+Z/Cmd+Z (undo), etc. Display in menus and tooltips for natural learning. Provide reference (Ctrl+/ or ?). All functionality accessible via keyboard (accessibility).

### Designing Shortcuts
Reserve single-key for most frequent actions. Modifier keys for less frequent. Group related shortcuts with same modifier. Avoid OS-level conflicts. Allow customization for power users.

## Drag-and-Drop

Always provide alternative non-drag method (cut/paste, move dialog). Show clear drop targets with visual highlighting. Cursor feedback (copy vs move). Support undo for accidental drops. Ghost/preview of dragged item. Disable drop on invalid targets with "not allowed" cursor.

## Undo/Redo

Support multi-level undo (minimum 20 levels). Make undo stack visible when possible (edit history panel). Distinguish undoable from permanent actions (warn for permanent). Group related actions into single undo steps. Restore exact previous state including selection and scroll position.

## Multi-Window and Panel Management

Allow resize, collapse, dock, and undock panels. Persist layout across sessions. Provide "Reset Layout" option. Support split view (side-by-side editing, comparison). Minimize mode switches: keep related info visible simultaneously. Remember window position and size between sessions.

## Settings and Preferences

Organize by category with left sidebar navigation. Show current value of each setting. Provide search for many-option apps. Sensible defaults so most users never change settings. Distinguish app-level from document-level settings. Support import/export for team consistency.

## Desktop-Specific Anti-Patterns

| Anti-Pattern | Alternative |
|-------------|-------------|
| No keyboard shortcuts | Full keyboard support with discoverable shortcuts |
| Single-level undo | Multi-level undo with visible history |
| Modal settings that reset on cancel | Apply/Cancel with intermediate preview |
| Ignoring OS conventions (custom file dialogs) | Platform-native dialogs for file operations |
| No drag alternative | Always provide cut/paste or move dialog |
| Fixed panel layout with no customization | Dockable, collapsible, resizable panels |
| Losing window state on restart | Persist size, position, layout between sessions |

## Acceptance Criteria Template (Desktop)

```gherkin
Feature: [Feature Name]
  # Platform: desktop ([Windows | macOS | cross-platform])
  # Key heuristics: [applicable Nielsen heuristics]

  Scenario: Keyboard workflow
    Given the user performs [task] using keyboard only
    When they use [shortcut]
    Then [expected result]
    And the shortcut is shown in the menu bar and tooltip

  Scenario: Undo support
    Given the user has performed [action]
    When they press Ctrl+Z / Cmd+Z
    Then the action is reversed
    And the redo action is available via Ctrl+Y / Cmd+Shift+Z

  Scenario: Panel management
    Given the user customizes their panel layout
    When they close and reopen the application
    Then their layout is preserved exactly
    And a Reset Layout option is available in the View menu
```
