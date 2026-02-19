---
description: "Creates evidence-based documentation following DIVIO/Diataxis principles. Use when writing tutorials, how-to guides, reference docs, or explanations."
argument-hint: "[topic/component] - Optional: --type=[tutorial|howto|reference|explanation] --research-depth=[overview|detailed|comprehensive|deep-dive]"
---

# NW-DOCUMENT: DIVIO Documentation Creation

**Wave**: CROSS_WAVE
**Agent**: Orchestrator (self)
**Agents**: Nova (nw-researcher), Scholar (nw-researcher-reviewer), Quill (nw-documentarist), nw-documentarist-reviewer

## Overview

Create evidence-based, DIVIO-compliant documentation by orchestrating research and writing phases with peer review at each gate. Cross-wave capability for any nWave phase.

## Context Files Required

- ~/.claude/nWave/data/config/trusted-source-domains.yaml - Embed inline in researcher prompt
- ~/.claude/agents/nw/nw-researcher.md - Extract research methodology for prompt
- ~/.claude/agents/nw/nw-documentarist.md - Extract DIVIO framework and templates for prompt

## Command Syntax

```bash
/nw:document [topic] [--type=tutorial|howto|reference|explanation] [--research-depth=overview|detailed|comprehensive|deep-dive]
```

If `--type` omitted, ask the user. If `--research-depth` omitted, auto-select: tutorial->overview, howto->detailed, reference->comprehensive, explanation->deep-dive.

## Orchestration Phases

Sub-agents have no Skill tool access. Embed all domain knowledge (trusted sources, DIVIO framework, review criteria) inline in each Task prompt. Read from agent definition files and config at orchestration time.

```
Phase 1: Research        @nw-researcher
Phase 1.5: Research Review  @nw-researcher-reviewer
Phase 2: Documentation      @nw-documentarist
Phase 2.5: Doc Review       @nw-documentarist-reviewer
Phase 3: Handoff
```

### Phase 0: Pre-Flight

1. Validate topic is non-empty, type and depth are valid if provided
2. If type not specified, present DIVIO type selection:
   - TUTORIAL ("Teach me") / HOW-TO ("Help me do X") / REFERENCE ("What is X?") / EXPLANATION ("Why is X?")
3. Determine output location: `docs/{tutorials|howto|reference|explanation}/{topic-kebab-case}.md`
4. Read and cache: trusted-source-domains.yaml, nw-researcher.md, nw-documentarist.md

### Phase 1: Research (@nw-researcher)

Invoke via Task tool. Prompt must include:
- Topic, documentation type, and research depth
- Complete trusted-source-domains.yaml content (inline)
- Type-specific research focus areas (from nw-researcher.md)
- Quality gates: trusted sources only, 3+ sources per claim, citation coverage >95%, source reputation >=0.80
- Output location: `data/research/{topic-kebab-case}-for-{type}-doc.md`

### Phase 1.5: Research Review (@nw-researcher-reviewer)

Invoke via Task tool. Prompt must include:
- Path to research artifact
- Review focus: source verification, bias detection, evidence quality, cross-reference validation, documentation readiness
- Quality gates (same as Phase 1)
- Output format: append YAML review metadata to research document
- Verdicts: APPROVED / NEEDS_REVISION / REJECTED

### Phase 2: Documentation (@nw-documentarist)

Invoke via Task tool. Prompt must include:
- Topic, type, research artifact path
- Complete DIVIO framework principles (from nw-documentarist.md)
- Type-specific validation rules and template structure (from nw-documentarist.md)
- Collapse detection anti-patterns (from nw-documentarist.md)
- Quality gates: type purity >=80%, Flesch 70-80, zero spelling errors, zero broken links, style >=95%
- Output: documentation file + validation report (.validation.yaml)

### Phase 2.5: Documentation Review (@nw-documentarist-reviewer)

Invoke via Task tool. Prompt must include:
- Path to documentation artifact
- Review focus: classification accuracy, validation completeness, collapse detection, recommendation quality, quality scores, verdict appropriateness
- Quality gates (same as Phase 2)
- Output format: append YAML review metadata to documentation file
- Verdicts: APPROVED / NEEDS_REVISION / RESTRUCTURE_REQUIRED

### Phase 3: Handoff

Verify all deliverables exist and both reviews show APPROVED. Present summary:
- Research artifact path, documentation path, validation report path
- Quality gate results (type purity, readability, collapse status)
- Review outcomes and iteration count

## Review Iteration Protocol

Applies identically to both review gates (Phase 1.5 and Phase 2.5):

1. **APPROVED**: Proceed to next phase
2. **NEEDS_REVISION**: Extract critiques, re-invoke producing agent with feedback, re-invoke reviewer. Max 2 cycles. Escalate to user after 2 failed cycles.
3. **REJECTED / RESTRUCTURE_REQUIRED**: Escalate to user immediately with options: restart, adjust scope, accept with issues, or cancel.

## Examples

### Example 1: Tutorial with auto-depth
```bash
/nw:document "Getting Started with nWave" --type=tutorial
```
Orchestrator auto-selects overview depth, invokes researcher, reviews, invokes documentarist, reviews, outputs to `docs/tutorials/getting-started-with-nwave.md`.

### Example 2: Explanation with explicit depth
```bash
/nw:document "Why nWave Uses Hexagonal Architecture" --type=explanation --research-depth=deep-dive
```
Full 4-phase pipeline with deep-dive research. Output to `docs/explanation/`.

### Example 3: Interactive type selection
```bash
/nw:document "Mikado Method Integration"
```
Orchestrator prompts user to select DIVIO type before proceeding.

## Success Criteria

- [ ] Research document created with trusted sources and cross-references
- [ ] Research review: APPROVED (max 2 iteration cycles)
- [ ] Documentation follows DIVIO type template with >=80% type purity
- [ ] Documentation review: APPROVED (max 2 iteration cycles)
- [ ] All deliverables exist: research, documentation, validation report
- [ ] No collapse anti-patterns detected

## Error Handling

- Insufficient sources: offer continue with gaps, expand scope, or cancel
- Review iteration limit exceeded: escalate to user with persistent issues
- Collapse detected: offer split into separate docs, revise scope, or accept

## Next Wave

**Handoff To**: Invoking workflow
**Deliverables**:
- Research: `data/research/{topic}-for-{type}-doc.md`
- Documentation: `docs/{type-dir}/{topic-kebab-case}.md`
- Validation: `docs/{type-dir}/{topic-kebab-case}.md.validation.yaml`
