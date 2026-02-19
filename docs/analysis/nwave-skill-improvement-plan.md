# nWave Skill Improvement Plan

> Based on: Anthropic's "Complete Guide to Building Skills for Claude" (January 2026)
> Audit date: 2026-02-19
> Scope: 18 commands, 25 agent definitions (13 primary + 12 reviewers)

---

## 1. Per-Command Audit

| Command | Lines | Current Description | Issues | Recommended Changes | Priority |
|---------|-------|-------------------|--------|---------------------|----------|
| `deliver` | 262 | "Execute complete DELIVER wave: roadmap > execute-all > finalize" | (1) Section header "CRITICAL BOUNDARY RULES" with NEVER/MUST/ALL-CAPS throughout (lines 18-28). (2) No `disable-model-invocation`. (3) Longest command at 262L -- approaching density limit. (4) Description uses imperative, not third-person. | Soften aggressive language to direct statements. Add `disable-model-invocation: true`. Rewrite description: "Orchestrates the full DELIVER wave end-to-end. Use when all prior waves are complete and the feature is ready for implementation." | HIGH |
| `execute` | 175 | "Execute atomic task with state tracking" | (1) "CRITICAL" at line 99, "MUST NEVER" at line 100, "NEVER" at line 107, "MUST" at line 111. (2) Description too generic -- no trigger phrases. (3) No `disable-model-invocation`. (4) `{{MANDATORY_PHASES}}` placeholder at line 163 references build injection that may not resolve at runtime. | Soften language. Add `disable-model-invocation: true`. Description: "Dispatches a single roadmap step to a specialized agent for TDD execution. Use when implementing a specific step from a roadmap." | HIGH |
| `roadmap` | 130 | "Create comprehensive planning document" | (1) "You MUST execute these 3 steps in order. Do NOT skip any step." (line 27). (2) Description is vague -- "comprehensive planning document" does not indicate roadmap.yaml. (3) No `disable-model-invocation`. | Soften to "Execute these 3 steps in order." Add `disable-model-invocation: true`. Description: "Creates a phased roadmap.yaml for a feature goal. Use when planning implementation steps before execution." | HIGH |
| `finalize` | 99 | "Summarize achievements, archive to docs/evolution, clean up feature files" | (1) No `disable-model-invocation` (has side effects: archiving, cleanup). (2) Description is good but missing trigger phrases. | Add `disable-model-invocation: true`. Description: "Archives a completed feature to docs/evolution/ and cleans up workflow files. Use after all implementation steps pass and mutation testing completes." | MEDIUM |
| `mutation-test` | 114 | "Mutation testing quality gate for test suite validation" | (1) "MUST" at line 95. (2) "mandatory" in section header line 87. (3) Description acceptable but could add trigger phrases. | Soften: "The agent restores source files even if the mutation run errors out." Description: "Runs feature-scoped mutation testing to validate test suite quality. Use after implementation to verify tests catch real bugs (kill rate >= 80%)." | MEDIUM |
| `review` | 111 | "Expert critique and quality review - Types: roadmap, step, task, implementation" | (1) Description is good. (2) Could benefit from `allowed-tools: Read, Glob, Grep` since reviews are read-only dispatchers. | Add `allowed-tools: Read, Glob, Grep, Task`. | LOW |
| `document` | 143 | "Create evidence-based DIVIO-compliant documentation" | (1) No aggressive language (clean). (2) Description could add trigger phrases. (3) Good progressive disclosure candidate -- move DIVIO type details to references/. | Description: "Creates evidence-based documentation following DIVIO/Diataxis principles. Use when writing tutorials, how-to guides, reference docs, or explanations." | LOW |
| `discuss` | 150 | "UX journey design, requirements gathering, and business analysis" | (1) No aggressive language (clean). (2) Description is noun-phrase, not verb-phrase. | Description: "Conducts UX journey design and requirements gathering through interactive discovery. Use when starting feature analysis, defining user stories, or creating acceptance criteria." | LOW |
| `design` | 104 | "Architecture design with visual representation" | (1) No aggressive language (clean). (2) Description too short -- missing trigger phrases. | Description: "Designs system architecture with C4 diagrams and technology selection. Use when defining component boundaries, choosing tech stacks, or creating architecture documents." | LOW |
| `devops` | 171 | "Platform readiness, CI/CD, infrastructure, and deployment design" | (1) No aggressive language (clean). (2) Description acceptable. (3) 8 decision points make it the most interactive command -- consider whether all are needed per invocation. | Description: "Designs CI/CD pipelines, infrastructure, observability, and deployment strategy. Use when preparing platform readiness for a feature." | LOW |
| `distill` | 124 | "Acceptance test creation and business validation" | (1) No aggressive language (clean). (2) Description acceptable. | Description: "Creates E2E acceptance tests in Given-When-Then format from requirements and architecture. Use when preparing executable specifications before implementation." | LOW |
| `discover` | 75 | "Evidence-based product discovery and market validation" | (1) No aggressive language (clean). (2) Description acceptable. | Description: "Conducts evidence-based product discovery through customer interviews and assumption testing. Use at project start to validate problem-solution fit." | LOW |
| `diagram` | 68 | "Architecture diagram management" | (1) Description too vague. | Description: "Generates C4 architecture diagrams (context, container, component) in Mermaid or PlantUML. Use when creating or updating architecture visualizations." | LOW |
| `forge` | 46 | "Create and validate new specialized agents" | (1) No aggressive language (clean). (2) Description acceptable but could add trigger phrases. | Description: "Creates new specialized agents using the 5-phase workflow (ANALYZE > DESIGN > CREATE > VALIDATE > REFINE). Use when building a new AI agent or validating an existing agent specification." | LOW |
| `mikado` | 66 | "[EXPERIMENTAL] Complex refactoring roadmaps with visual tracking" | (1) No issues. Good size. | No changes needed. | LOW |
| `refactor` | 87 | "Systematic refactoring with Mikado Method" | (1) Description mentions Mikado but the command is about RPP (Refactoring Priority Premise). Mikado is optional. | Description: "Applies the Refactoring Priority Premise (RPP) levels L1-L6 for systematic code refactoring. Use when improving code quality through structured refactoring passes." | MEDIUM |
| `research` | 82 | "Evidence-driven knowledge research with source verification" | (1) No aggressive language (clean). (2) Missing `argument-hint`. | Add `argument-hint: "[topic] - Optional: --skill-for=[agent-name] --research-depth=[overview|detailed|comprehensive|deep-dive]"`. | LOW |
| `root-why` | 67 | "Root cause analysis and debugging" | (1) No aggressive language (clean). (2) Description acceptable. | No changes needed. | LOW |

### Command Totals

- Total lines across 18 commands: **2,074**
- Average: **115 lines/command**
- Largest: `deliver` (262), `execute` (175), `devops` (171)
- Smallest: `forge` (46), `mikado` (66), `root-why` (67)

---

## 2. Per-Agent Audit

### Primary Agents (13)

| Agent | Lines | Issues | Recommended Changes | Priority |
|-------|-------|--------|---------------------|----------|
| `nw-software-crafter` | 363 | (1) "MUST" at line 290. (2) At 363 lines, near the 400-line boundary. (3) Description starts with "DELIVER wave" (not a verb phrase). | Soften line 290. Rewrite description to verb-phrase with trigger phrases. Consider extracting RPP/Mikado methodology to skills/. | MEDIUM |
| `nw-functional-software-crafter` | 285 | (1) Description starts with "DELIVER wave". (2) Significant overlap with nw-software-crafter -- evaluate if this should be a skill rather than a separate agent. | Rewrite description. Evaluate merge into nw-software-crafter with a functional-paradigm skill. | MEDIUM |
| `nw-product-owner` | 239 | (1) Description is very long (over 200 chars). (2) No aggressive language. | Trim description to essentials: "Conducts UX journey design and requirements gathering with BDD acceptance criteria. Use when defining user stories, emotional arcs, or enforcing Definition of Ready." | LOW |
| `nw-solution-architect` | 232 | (1) No aggressive language. (2) Description is good. | No significant changes. | LOW |
| `nw-platform-architect` | 226 | (1) No aggressive language. (2) Description is good. | No significant changes. | LOW |
| `nw-tutorialist` | 232 | (1) No aggressive language. (2) Description is good. | No significant changes. | LOW |
| `nw-acceptance-designer` | 205 | (1) No aggressive language. (2) Description is good. | No significant changes. | LOW |
| `nw-product-discoverer` | 201 | (1) Description mentions "DISCUSS wave PRE-REQUIREMENTS phase" but agent is for DISCOVER wave. Potential confusion. | Fix description to reference DISCOVER wave. | MEDIUM |
| `nw-agent-builder` | 287 | (1) Clean -- this agent already follows its own anti-pattern guidelines. (2) References CRITICAL/MANDATORY only as anti-pattern examples. | No changes needed. | LOW |
| `nw-troubleshooter` | 139 | (1) No issues. (2) Has WebSearch and WebFetch -- appropriate for investigation. | No changes needed. | LOW |
| `nw-researcher` | 125 | (1) No issues. Good size. | No changes needed. | LOW |
| `nw-documentarist` | 145 | (1) Uses `model: haiku` -- good cost efficiency. | No changes needed. | LOW |
| `nw-data-engineer` | 112 | (1) No issues. Good size. | No changes needed. | LOW |

### Reviewer Agents (12)

| Agent | Lines | Issues | Priority |
|-------|-------|--------|----------|
| `nw-product-owner-reviewer` | 174 | No issues | LOW |
| `nw-tutorialist-reviewer` | 171 | No issues | LOW |
| `nw-software-crafter-reviewer` | 152 | No issues | LOW |
| `nw-acceptance-designer-reviewer` | 150 | No issues | LOW |
| `nw-researcher-reviewer` | 144 | No issues | LOW |
| `nw-product-discoverer-reviewer` | 143 | No issues | LOW |
| `nw-solution-architect-reviewer` | 136 | No issues | LOW |
| `nw-agent-builder-reviewer` | 118 | No issues | LOW |
| `nw-documentarist-reviewer` | 117 | No issues | LOW |
| `nw-data-engineer-reviewer` | 116 | No issues | LOW |
| `nw-troubleshooter-reviewer` | 105 | No issues | LOW |
| `nw-platform-architect-reviewer` | 100 | No issues | LOW |

All reviewer agents are well-sized (100-174 lines). No aggressive language detected in any reviewer.

---

## 3. Cross-Cutting Improvements

### 3.1 Description Formula Standardization

**Current state**: Descriptions vary between noun phrases ("Architecture diagram management"), imperative ("Execute complete DELIVER wave"), and verb phrases ("Use for DESIGN wave"). Some are under 30 characters, others over 200.

**Anthropic formula**: `[What it does (verb phrase, third person)] + [When to use it (trigger phrases)]`

**Standard to adopt**:
```
"{Verb-phrase describing action}. Use when {trigger condition with keywords users would say}."
```

All 18 commands and 13 primary agents should follow this formula.

### 3.2 Aggressive Language Audit

Every occurrence of CRITICAL/MANDATORY/MUST/NEVER/ABSOLUTE across commands and agents:

| File | Line | Text | Suggested Replacement |
|------|------|------|-----------------------|
| `commands/nw/deliver.md` | 18 | `## CRITICAL BOUNDARY RULES` | `## Boundary Rules` |
| `commands/nw/deliver.md` | 20 | `**NEVER implement roadmap steps directly.** ALL step implementation MUST be delegated` | `Delegate all step implementation to @nw-software-crafter via the Task tool with DES markers. The orchestrator coordinates; it does not implement.` |
| `commands/nw/deliver.md` | 22 | `**NEVER write phase entries to execution-log.yaml.**` | `Only the software-crafter subagent that performed TDD work appends phase entries. Writing entries yourself causes finalize to detect the violation and block.` |
| `commands/nw/deliver.md` | 51 | `Step IDs MUST use NN-NN format` | `Step IDs use NN-NN format (two digits, dash, two digits).` |
| `commands/nw/deliver.md` | 71 | `NEVER write execution-log entries yourself` | `Only the executing agent writes execution-log entries.` |
| `commands/nw/execute.md` | 99 | `CRITICAL: Only the executing agent calls the CLI.` | `Only the executing agent calls the CLI.` |
| `commands/nw/execute.md` | 100 | `The orchestrator MUST NEVER write phase entries` | `The orchestrator does not write phase entries -- only the agent that performed the work.` |
| `commands/nw/execute.md` | 107 | `- NEVER write execution-log entries for phases you did not execute` | `- Write execution-log entries only for phases you actually executed` |
| `commands/nw/execute.md` | 111 | `you MUST commit before returning` | `commit before returning` |
| `commands/nw/execute.md` | 161 | `MANDATORY_PHASES` | Schema reference label -- acceptable (not instruction language) |
| `commands/nw/mutation-test.md` | 95 | `The agent MUST restore source files` | `The agent restores source files even if the mutation run errors out.` |
| `commands/nw/roadmap.md` | 27 | `You MUST execute these 3 steps in order. Do NOT skip any step.` | `Execute these 3 steps in order.` |
| `agents/nw/nw-software-crafter.md` | 290 | `Every test MUST fail if you break the production code` | `Every test fails if you break the production code it covers.` |

**Total occurrences**: 13 actionable instances across 4 command files and 1 agent file.

### 3.3 `disable-model-invocation` Candidates

Commands with side effects that should only be user-triggered:

| Command | Side Effects | Recommendation |
|---------|-------------|----------------|
| `deliver` | Creates files, runs full TDD pipeline, commits, pushes | `disable-model-invocation: true` |
| `execute` | Runs TDD cycle, modifies source code, commits | `disable-model-invocation: true` |
| `finalize` | Archives, deletes feature files, pushes | `disable-model-invocation: true` |
| `roadmap` | Creates roadmap.yaml via CLI tool | `disable-model-invocation: true` |

Commands that are safe for model invocation (read-only or advisory):

| Command | Reason |
|---------|--------|
| `review` | Read-only analysis |
| `research` | Read + web search, creates docs but no side effects |
| `diagram` | Creates diagram files but low risk |
| `document` | Creates docs but low risk |

### 3.4 `allowed-tools` Candidates

| Command | Current Tools (inherited) | Recommended `allowed-tools` | Rationale |
|---------|--------------------------|----------------------------|-----------|
| `review` | All | `Read, Glob, Grep, Task` | Dispatches to reviewer; no writes needed from command itself |
| `research` | All | `Read, Glob, Grep, Task, WebSearch, WebFetch` | Research is read + web; no writes from command |
| `diagram` | All | `Read, Glob, Grep, Write, Task` | Needs Write for diagram output, no Bash needed |
| `forge` | All | `Read, Write, Edit, Glob, Grep, Task` | Agent creation needs file ops, no Bash needed |

### 3.5 Progressive Disclosure Candidates

Commands over 150 lines that would benefit from `references/` extraction:

| Command | Lines | Extractable Content | Savings |
|---------|-------|-------------------|---------|
| `deliver` | 262 | DES template details, quality gate specifications, phase descriptions | ~100 lines to references/des-template.md and references/quality-gates.md |
| `execute` | 175 | DES prompt template (lines 39-112), resume logic (lines 133-145) | ~80 lines to references/des-prompt-template.md |
| `devops` | 171 | 8 decision points with options (lines 18-99) | ~80 lines to references/decision-points.md |
| `discuss` | 150 | Phase 1/Phase 2 artifact tables, decision points | ~50 lines to references/ |

**Note**: Migration to skill directory format (`~/.claude/skills/nw-deliver/SKILL.md` + `references/`) required for this. Currently flat `.md` files under `.claude/commands/nw/`.

### 3.6 Dynamic Context Injection Opportunities

Commands that could benefit from `!`command`` preprocessing:

| Command | Injection | Value |
|---------|-----------|-------|
| `deliver` | `` !`git branch --show-current` `` | Auto-detect current branch for commit context |
| `execute` | `` !`cat docs/feature/*/execution-log.yaml 2>/dev/null \| head -5` `` | Pre-load project context |
| `review` | `` !`git diff --stat HEAD~1` `` | Show recent changes for review scope |
| `finalize` | `` !`ls docs/feature/ 2>/dev/null` `` | List available projects for completion |

**Caution**: Dynamic injection runs at skill load time, not invocation time. Only useful for always-relevant context. Project-specific paths with wildcards may not resolve correctly.

---

## 4. Migration Plan

### Phase 1: Quick Wins (1-2 days)

**Impact: High. Effort: Low. Risk: None.**

1. **Standardize all 18 command descriptions** using the formula: `"{Verb phrase}. Use when {trigger}."` (see Section 1 for each command's new description)

2. **Soften 13 aggressive language instances** (see Section 3.2 table for exact replacements)

3. **Add `disable-model-invocation: true`** to deliver, execute, finalize, roadmap (4 commands)

4. **Add missing `argument-hint`** to research.md

5. **Fix nw-product-discoverer description** (references DISCUSS wave instead of DISCOVER wave)

6. **Trim nw-product-owner description** (currently over 200 chars)

### Phase 2: Structural Changes (3-5 days)

**Impact: Medium. Effort: Medium. Risk: Low (test after each change).**

1. **Add `allowed-tools`** to review, research, diagram, forge commands (4 commands)

2. **Migrate deliver.md and execute.md to skill directory format**:
   ```
   ~/.claude/skills/nw-deliver/
     SKILL.md              (150 lines -- orchestration only)
     references/
       des-template.md     (DES prompt template)
       quality-gates.md    (gate specifications)

   ~/.claude/skills/nw-execute/
     SKILL.md              (100 lines -- dispatch logic only)
     references/
       des-prompt-template.md  (full 9-section template)
       resume-logic.md         (resume vs restart decision)
   ```

3. **Evaluate nw-functional-software-crafter merge**: Consider merging as a skill of nw-software-crafter with a `functional-paradigm` skill file, reducing agent count by 1 (and its reviewer by 1).

4. **Extract RPP methodology from nw-software-crafter** (currently 363 lines) to a skill file, reducing core to ~280 lines.

### Phase 3: Advanced (1-2 weeks)

**Impact: Variable. Effort: High. Risk: Medium.**

1. **Create evaluation scenarios** for the 5 most-used commands (deliver, execute, roadmap, review, research):
   - 3 triggering tests per command (does it load for relevant queries?)
   - 3 functional tests per command (correct outputs?)
   - 1 performance comparison (tokens consumed before/after Phase 1+2 changes)

2. **Add dynamic context injection** to deliver and finalize commands (see Section 3.6)

3. **Evaluate `context: fork`** for research and review commands -- these are independent workstreams that could run in isolated subagents

4. **Trim obvious explanations** -- audit each command for content Claude already knows (e.g., explaining what TDD is, what kebab-case means). Estimated ~5-10% token savings across commands.

---

## 5. Concrete Before/After Examples

### Example 1: `execute.md` Frontmatter

**Before:**
```yaml
---
description: "Execute atomic task with state tracking"
argument-hint: '[agent] [step-id] - Example: @software-crafter "01-01"'
---
```

**After:**
```yaml
---
description: "Dispatches a single roadmap step to a specialized agent for TDD execution. Use when implementing a specific step from a roadmap.yaml plan."
argument-hint: '[agent] [project-id] [step-id] - Example: @nw-software-crafter "auth-upgrade" "01-01"'
disable-model-invocation: true
---
```

### Example 2: `deliver.md` Aggressive Language Section

**Before (lines 18-28):**
```markdown
## CRITICAL BOUNDARY RULES

1. **NEVER implement roadmap steps directly.** ALL step implementation MUST be delegated to @nw-software-crafter via the Task tool with DES markers. You are the ORCHESTRATOR — you coordinate, you do not implement.

2. **NEVER write phase entries to execution-log.yaml.** Only the software-crafter subagent that performed the TDD work may append phase entries. If you write entries yourself, finalize will detect the violation and block.

3. **Extract step context from roadmap.yaml ONLY for the Task prompt.**
```

**After:**
```markdown
## Boundary Rules

1. **Delegate all implementation.** Step implementation goes to @nw-software-crafter via the Task tool with DES markers. The orchestrator coordinates; it does not implement.

2. **Only executing agents write log entries.** The software-crafter subagent that performed TDD work appends phase entries. Finalize detects and blocks entries written by non-executing agents.

3. **Extract step context for the Task prompt.** Grep the roadmap for the step_id with ~50 lines context, extract fields, and pass them in the DES template.
```

### Example 3: `review.md` with `allowed-tools`

**Before:**
```yaml
---
description: "Expert critique and quality review - Types: roadmap, step, task, implementation"
argument-hint: '[agent] [artifact-type] [artifact-path] - Example: @software-crafter task "roadmap.yaml"'
---
```

**After:**
```yaml
---
description: "Dispatches an expert reviewer agent to critique workflow artifacts. Use when a roadmap, implementation, or step needs quality review before proceeding."
argument-hint: '[agent] [artifact-type] [artifact-path] - Example: @nw-software-crafter task "roadmap.yaml"'
allowed-tools: Read, Glob, Grep, Task
---
```

---

## 6. Summary Metrics

| Metric | Current | After Phase 1 | After Phase 2 |
|--------|---------|---------------|---------------|
| Commands with aggressive language | 4 / 18 | 0 / 18 | 0 / 18 |
| Commands with `disable-model-invocation` | 0 / 18 | 4 / 18 | 4 / 18 |
| Commands with `allowed-tools` | 0 / 18 | 0 / 18 | 4 / 18 |
| Descriptions following formula | ~5 / 18 | 18 / 18 | 18 / 18 |
| Agents over 300 lines | 2 / 25 | 2 / 25 | 1 / 25 |
| Commands using skill directory format | 0 / 18 | 0 / 18 | 2 / 18 |
| Commands using dynamic context injection | 0 / 18 | 0 / 18 | 0 / 18 |
| Evaluation scenarios | 0 | 0 | 0 (Phase 3) |

**Estimated token savings from Phase 1 alone**: ~15-20% reduction in wasted context from aggressive language overtriggering on Opus 4.6.
