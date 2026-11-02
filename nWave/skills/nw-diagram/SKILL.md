---
name: nw-diagram
description: "Generates C4 architecture diagrams (context, container, component) in Mermaid or PlantUML. Use when creating or updating architecture visualizations."
user-invocable: true
argument-hint: '[diagram-type] - Optional: --format=[mermaid|plantuml|c4] --level=[context|container|component]'
---

# NW-DIAGRAM: Architecture Diagram Generation

**Wave**: CROSS_WAVE | **Agent**: Morgan (nw-solution-architect), semantic content only | **Command**: `/nw-diagram`

## Overview

Generate architecture diagrams from the existing design context. Supports C4 model levels (context|container|component) in Mermaid|PlantUML|C4 format. Audience-appropriate: high-level context for stakeholders|component details for developers|deployment topology for operations. This standalone visualization does not author or replace architecture authority.

## Context Files Required

- docs/product/architecture/brief.md (SSOT — component boundaries, technology stack, design decisions)

## Workflow

1. **Read Context** — Load `docs/product/architecture/brief.md`. Extract component boundaries, technology stack, and design decisions.
2. **Resolve Configuration** — Determine `diagram_type` (component|deployment|sequence|data|context), `format` (mermaid|plantuml|c4), `level` (context|container|component), and, if files are requested, `output_directory`.
3. **Invoke Agent** — Ask `@nw-solution-architect` for the semantic diagram content in the selected format for `{architecture-component}`, using the brief as context. Do not ask the architect to write diagram files or architecture-document bytes.
4. **Render and Validate** — The caller checks the returned diagram content with the selected renderer. If files were requested, the caller writes the validated diagram source to `output_directory` and checks that the requested files exist; never delegate those writes to the architect.
5. **Handoff** — Return the diagram content or caller-written artifacts to the invoking workflow.

## Success Criteria

- [ ] Diagrams accurately represent current architecture
- [ ] Audience-appropriate detail level applied
- [ ] Diagrams render without syntax errors
- [ ] Requested output files, if any, created by the caller in the configured directory

## Next Wave

**Handoff To**: {invoking-agent-returns-to-workflow}
**Deliverables**: Diagram content in the configured format, and caller-written files if requested

## Examples

### Example 1: Generate C4 container diagram
```
/nw-diagram payment-service --diagram_type=component --format=mermaid --level=container
```
Morgan reads architecture docs and returns Mermaid container diagram content showing service boundaries, data stores, and external integrations; the caller renders it and writes a diagram file if requested.

## Example File Output (when requested)

```
docs/product/architecture/
  payment-service-container.mmd
```
