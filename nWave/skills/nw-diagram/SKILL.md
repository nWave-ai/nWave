---
name: nw-diagram
description: "Generates accessible, legible C4 architecture diagrams (context, container, component) in Mermaid or PlantUML under 12 checkable rules. Use when creating, updating or reviewing architecture diagrams, or when documents.readable_brief is enabled."
user-invocable: true
argument-hint: '[diagram-type] - Optional: --format=[mermaid|plantuml|c4] --level=[context|container|component]'
---

# NW-DIAGRAM: Accessible Architecture Diagrams

**Wave**: CROSS_WAVE | **Agent**: Morgan (nw-solution-architect), semantic content only | **Command**: `/nw-diagram`

## Overview

Generate architecture diagrams from the existing design context, as C4 levels (context|container|component) in Mermaid|PlantUML|C4. A correct diagram that a person cannot read has failed. Every rule below is checkable from the source text, without rendering. This standalone visualization does not author or replace architecture authority. Reviewers (documentarist) apply the same rules.

## Context Files Required

- docs/product/architecture/brief.md (SSOT — component boundaries, technology stack, design decisions)

## Legibility and accessibility rules

Colour, contrast, text alternative and screen-reader duties come from the accessibility section of `nw-usability-engineering` ("Accessibility as Design Constraint"). The rules apply them to diagram source.

|#|Rule|Check in the source|
|---|---|---|
|R1|Title inside the block|C4: a `title` line. Other types: front matter `title:` as first lines. `accTitle`/`accDescr` where the type supports them (flowchart, sequence)|
|R2|Prose description directly above the block|1-3 sentences starting `This diagram shows:` immediately before the fence. HTML shows it above the diagram|
|R3|At most 25 nodes per block (provisional limit)|Count node ids. Above 25, split by subsystem or wave and link the blocks in prose|
|R4|Node label at most 40 characters and 2 line breaks|Count characters per label. Detail goes to the description or a table|
|R5|Reading direction stated and standard|`TD` for phased flows, `LR` for pipelines. `BT` only for Mikado trees, with a sentence saying goals sit on top|
|R6|Colour never the only signal|Each class also differs by shape, dash style or label prefix|
|R7|Contrast declared and sufficient|Each `classDef` sets `fill`, `stroke` and `color`. Fill vs stroke at least 3:1, fill vs text at least 4.5:1, recalculated from the hex codes|
|R8|Legend when styles exist|A `classDef` or `style` means a `LEGEND` subgraph with one node per class|
|R9|Human names for groups above 8 nodes|Each `subgraph` title is a subsystem name, not a code|
|R10|Short edge labels, not repeated|At most 4 words. The same label at most 4 times. Otherwise group the edges or drop the label|
|R11|Acronyms and ids expanded once|Every acronym or id (E1, SYS-4) appears expanded in the title, legend or description|
|R12|One C4 level per block|No context, container and component elements in one block. The title names the level (L1, L2, L3)|

Old diagrams under `docs/archive` stay as they are. The rules bind new and regenerated diagrams.

## Workflow

1. **Read Context** — Load `docs/product/architecture/brief.md`. Extract component boundaries, technology stack, and design decisions.
2. **Resolve Configuration** — Determine `diagram_type` (component|deployment|sequence|data|context), `format` (mermaid|plantuml|c4), `level` (context|container|component), and, if files are requested, `output_directory`.
3. **Invoke Agent** — Ask `@nw-solution-architect` for the semantic diagram content in the selected format for `{architecture-component}`, using the brief as context and R1-R12. Do not ask the architect to write diagram files or architecture-document bytes.
4. **Check and Render** — The caller checks R1-R12 on the returned source and returns each failed rule to the architect with its rule id. Then it checks the content with the selected renderer. If files were requested, the caller writes the validated source to `output_directory` and checks that the files exist; never delegate those writes to the architect.
5. **Handoff** — Return the diagram content or caller-written artifacts to the invoking workflow.

## Success Criteria

- [ ] Diagrams accurately represent current architecture
- [ ] Audience-appropriate detail level applied
- [ ] R1-R12 hold for every block, or the exception is named in the description
- [ ] Diagrams render without syntax errors
- [ ] Requested output files, if any, created by the caller in the configured directory

## Next Wave

**Handoff To**: {invoking-agent-returns-to-workflow}
**Deliverables**: Diagram content in the configured format, and caller-written files if requested

## Examples

### Example 1: Generate a C4 container diagram
```
/nw-diagram payment-service --diagram_type=component --format=mermaid --level=container
```
Morgan returns Mermaid container content with a `title` line naming L2, at most 25 nodes, short labels and a description sentence. The caller checks R1-R12, renders it and writes a file if requested.

### Example 2: A phase map with 71 nodes (fails R3, R4, R8)
Split it into one block per wave. Shorten each label to 40 characters and move the detail into the description. Add a `LEGEND` subgraph for the four `classDef` classes and give each class its own shape.

## Example File Output (when requested)

```
docs/product/architecture/
  payment-service-container.mmd
```
