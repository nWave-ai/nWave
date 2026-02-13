# Wave Command Output Paths Reference

## Overview

The nWave workflow generates documentation artifacts organized by feature and wave. This reference documents the complete output path specification for wave commands (DISCUSS, DESIGN, DISTILL, DELIVER) using the feature-based folder structure.

**Last Updated**: 2026-02-13
**Applies to**: nWave commands and all feature documentation
**Organization**: Feature-isolated paths with wave-specific subfolders

## Output Path Pattern

### General Specification

```
docs/feature/{feature-name}/{wave-name}/
```

Where:
- `docs/feature/` = Base feature documentation directory
- `{feature-name}` = Placeholder replaced with actual feature identifier at runtime
- `{wave-name}` = Wave-specific subfolder matching wave command name

### Placeholder Substitution

The `{feature-name}` placeholder is a **required parameter** that must be provided at command invocation. The placeholder follows these conventions:

| Aspect | Rule |
|--------|------|
| Format | Lowercase, hyphen-separated identifier |
| Example | `des` (Deterministic Execution System) |
| Substitution | Runtime replacement by wave command engine |
| Context | Derived from feature branch or explicit parameter |

## Wave-Specific Output Paths

### DISCUSS Wave

**Output Folder**: `docs/feature/{feature-name}/discuss/`

**Deliverables**:

| File | Purpose | Format |
|------|---------|--------|
| `requirements.md` | Feature requirements specification | Markdown |
| `user-stories.md` | User story definitions with acceptance criteria | Markdown |
| `acceptance-criteria.md` | Detailed acceptance criteria for feature completion | Markdown |
| `dor-checklist.md` | Definition of Ready checklist for design handoff | Markdown |

**Input Context**: None (DISCUSS is first documentation wave)

**Cross-Wave References**: Outputs consumed by DESIGN and DISTILL waves

### DESIGN Wave

**Output Folder**: `docs/feature/{feature-name}/design/`

**Deliverables**:

| File | Purpose | Format |
|------|---------|--------|
| `architecture-design.md` | System architecture and design decisions | Markdown |
| `technology-stack.md` | Technology selections with rationale | Markdown |
| `component-boundaries.md` | Component definitions and interfaces | Markdown |
| `data-models.md` | Data structures and relationships | Markdown |
| `diagrams/` | Visual architecture diagrams | SVG/PNG/other |

**Input Context Required**:
```
docs/feature/{feature-name}/discuss/requirements.md
docs/feature/{feature-name}/discuss/user-stories.md
```

**Cross-Wave References**: Outputs consumed by DISTILL and DELIVER waves

### DISTILL Wave

**Output Folder**: `docs/feature/{feature-name}/distill/`

**Deliverables**:

| File | Purpose | Format |
|------|---------|--------|
| `acceptance-tests.feature` | BDD feature file with test scenarios | Gherkin |
| `step-definitions.{language}` | Step implementation for test scenarios | Language-specific |
| `test-scenarios.md` | Test scenario documentation and coverage | Markdown |

**Input Context Required**:
```
docs/feature/{feature-name}/discuss/requirements.md
docs/feature/{feature-name}/discuss/user-stories.md
docs/feature/{feature-name}/discuss/acceptance-criteria.md
docs/feature/{feature-name}/design/architecture-design.md
docs/feature/{feature-name}/design/data-models.md
```

**Cross-Wave References**: Outputs consumed by DELIVER wave

### DELIVER Wave

**Output Folder**: `docs/feature/{feature-name}/deliver/`

**Deliverables**:

| File | Purpose | Format |
|------|---------|--------|
| `production-deployment.md` | Production deployment procedure | Markdown |
| `stakeholder-feedback.md` | Stakeholder feedback and sign-off | Markdown |
| `business-impact-report.md` | Business metrics and impact analysis | Markdown |

**Input Context Required**:
```
docs/feature/{feature-name}/design/architecture-design.md
docs/feature/{feature-name}/design/component-boundaries.md
src/{implementation-path}/               # Generated implementation code
```

**Cross-Wave References**: Final wave outputs; typically consumed by archive/retrospective processes

## Cross-Wave References and Dependencies

### Wave Input Chain

```
DISCUSS (no inputs)
   ↓ outputs to discuss/

DESIGN (reads discuss/)
   ↓ outputs to design/

DISTILL (reads discuss/, design/)
   ↓ outputs to distill/

DELIVER (reads design/, src/)
   ↓ outputs to deliver/
```

### File Consumption Pattern

| Source Wave | Folder | Consumed By |
|-------------|--------|-------------|
| DISCUSS | `discuss/` | DESIGN, DISTILL |
| DESIGN | `design/` | DISTILL, DELIVER |
| DISTILL | `distill/` | DELIVER, Test Execution |
| DELIVER | `deliver/` | Archive, Retrospective |

## Path Structure Examples

### Single Feature: DES (Deterministic Execution System)

Complete path structure after all waves:

```
docs/feature/des/
├── discuss/
│   ├── requirements.md
│   ├── user-stories.md
│   ├── acceptance-criteria.md
│   └── dor-checklist.md
├── design/
│   ├── architecture-design.md
│   ├── technology-stack.md
│   ├── component-boundaries.md
│   ├── data-models.md
│   └── diagrams/
│       ├── system-architecture.svg
│       └── data-flow.svg
├── distill/
│   ├── acceptance-tests.feature
│   ├── step-definitions.py
│   └── test-scenarios.md
└── deliver/
    ├── production-deployment.md
    ├── stakeholder-feedback.md
    └── business-impact-report.md
```

### Multiple Concurrent Features

Feature isolation enables parallel development:

```
docs/feature/
├── des/
│   ├── discuss/
│   ├── design/
│   ├── distill/
│   └── deliver/
├── plugin-system/
│   ├── discuss/
│   ├── design/
│   └── distill/           # DESIGN in progress
└── token-baseline/
    └── discuss/            # DISCUSS in progress
```

## Migration from Legacy Structure

### Legacy (Global Folders) to Current (Feature-Based)

| Legacy Path | Current Path | Wave |
|------------|-------------|------|
| `docs/requirements/` | `docs/feature/{feature-name}/discuss/` | DISCUSS |
| `docs/architecture/` | `docs/feature/{feature-name}/design/` | DESIGN |
| `docs/testing/` | `docs/feature/{feature-name}/distill/` | DISTILL |
| `docs/demo/` | `docs/feature/{feature-name}/deliver/` | DELIVER |

**Deprecation Status**: Legacy paths no longer used; all new features use feature-based structure.

## Edge Cases and Special Conditions

### Placeholder Resolution Failure

**Condition**: `{feature-name}` not provided to wave command

**Resolution**: Command fails with error indicating required parameter missing; review wave command invocation documentation

### Cross-Feature Shared Components

**Condition**: Architecture element shared between multiple features

**Resolution**: Reference shared component in `design/component-boundaries.md` with cross-feature link; maintain separate DISCUSS outputs per feature

### DELIVER Wave Implementation Code

**Condition**: DELIVER wave outputs

**Resolution**: Implementation code goes to `src/{feature-path}/` not `docs/feature/{feature-name}/develop/`; reference location in DELIVER context files

### Partial Wave Completion

**Condition**: Feature stops after DISCUSS or DESIGN wave

**Resolution**: No output folder created for subsequent waves; incomplete folders are valid state in active development

## Examples

### Example 1: DES Feature Post-Design

After DISCUSS and DESIGN waves complete:

```
docs/feature/des/
├── discuss/
│   ├── requirements.md
│   ├── user-stories.md
│   ├── acceptance-criteria.md
│   └── dor-checklist.md
└── design/
    ├── architecture-design.md
    ├── technology-stack.md
    ├── component-boundaries.md
    └── data-models.md
```

**Input for Next Wave**: DISTILL reads both `discuss/` and `design/` folders

### Example 2: Plugin System Feature In Distill Phase

After DISCUSS, DESIGN, and DISTILL waves:

```
docs/feature/plugin-system/
├── discuss/
│   ├── requirements.md
│   └── ...
├── design/
│   ├── architecture-design.md
│   └── ...
└── distill/
    ├── acceptance-tests.feature
    ├── step-definitions.py
    └── test-scenarios.md
```

**Context Files Used**: All from `discuss/` and `design/` folders

### Example 3: Path Reference in DESIGN Wave

Command context section:

```markdown
## Context Files Required

The DESIGN wave reads requirements and user stories from the DISCUSS wave:

- docs/feature/{feature-name}/discuss/requirements.md
- docs/feature/{feature-name}/discuss/user-stories.md
```

**Runtime Substitution Example** (for feature `plugin-system`):

```
- docs/feature/plugin-system/discuss/requirements.md
- docs/feature/plugin-system/discuss/user-stories.md
```

## See Also

- Reference: [nWave Commands Reference](./nwave-commands-reference.md) - Complete command specifications and usage
- How-to: [Installation Guide](../guides/installation-guide.md) - Get nWave installed and configured
