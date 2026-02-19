# Skill Building Reference: Extracted from Anthropic's Official Guide

> Source: "The Complete Guide to Building Skills for Claude" (Anthropic, January 2026)
> Additional sources: Anthropic Platform Docs (Skill Authoring Best Practices), Claude Code Docs (Extend Claude with Skills), Claude 4.6 Prompting Best Practices
> Extracted: 2026-02-19
> Purpose: Actionable reference for nw-agent-builder when creating/improving agent skills and command files

---

## 1. Skill Anatomy

### 1.1 Required Structure

```
skill-name/                      # kebab-case directory name
  SKILL.md                       # Required entrypoint (case-sensitive)
  scripts/                       # Optional: executable code
  references/                    # Optional: documentation loaded on-demand
  assets/                        # Optional: templates, icons, fonts for output
```

For Claude Code specifically, `.claude/commands/` files also work as skills. A `.md` file at `.claude/commands/review.md` and a skill at `.claude/skills/review/SKILL.md` both create `/review`. If both exist with the same name, the skill takes precedence.

### 1.2 YAML Frontmatter (Critical for Discovery)

```yaml
---
name: skill-name-in-kebab-case    # Required. Max 64 chars. Lowercase + numbers + hyphens only.
description: >-                    # Required. Max 1024 chars. No XML tags.
  What it does. Use when [specific trigger phrases].
  Written in third person.
---
```

**Claude Code additional frontmatter fields:**

| Field | Purpose |
|-------|---------|
| `argument-hint` | Hint shown during autocomplete: `[issue-number]` |
| `disable-model-invocation` | `true` = only user can invoke (for side-effects like deploy) |
| `user-invocable` | `false` = only Claude can invoke (background knowledge) |
| `allowed-tools` | Restrict tools: `Read, Grep, Glob` |
| `context` | `fork` = run in isolated subagent |
| `agent` | Subagent type when `context: fork` (`Explore`, `Plan`, custom) |
| `model` | Override model for this skill |
| `hooks` | Lifecycle hooks scoped to this skill |

**Description is the single most important field.** It determines whether Claude loads the skill at all. At startup, only name + description are pre-loaded (~50-100 tokens per skill). The full SKILL.md body loads only when Claude decides the skill matches the current task.

**Description formula:** `[What it does] + [When to use it] + [Key trigger phrases]`

**Description rules:**
- Third person always ("Processes files..." not "I process files...")
- Include specific keywords users would naturally say
- Include file types if relevant (`.pdf`, `.xlsx`, `.docx`)
- Under 1024 characters
- No XML tags

### 1.3 Body Content

The markdown body after frontmatter contains the actual instructions. Key constraints:

- **Under 500 lines** for optimal performance
- Move detailed docs to `references/` directory
- Keep references **one level deep** from SKILL.md (no nested reference chains)
- For reference files over 100 lines, include a table of contents at the top
- Use imperative/infinitive form for writing instructions

### 1.4 String Substitutions (Claude Code)

| Variable | Description |
|----------|-------------|
| `$ARGUMENTS` | All arguments passed when invoking |
| `$ARGUMENTS[N]` or `$N` | Specific argument by 0-based index |
| `${CLAUDE_SESSION_ID}` | Current session ID |
| `` !`command` `` | Shell command output injected before skill loads |

---

## 2. Prompt Engineering Patterns

### 2.1 Core Principle: Concise is Key

The context window is a shared resource. Default assumption: **Claude is already very smart.** Only add context Claude does not already have.

Challenge each piece of information:
- "Does Claude really need this explanation?"
- "Can I assume Claude knows this?"
- "Does this paragraph justify its token cost?"

**Good** (~50 tokens):
```markdown
## Extract PDF text
Use pdfplumber for text extraction:
[code example]
```

**Bad** (~150 tokens):
```markdown
## Extract PDF text
PDF (Portable Document Format) files are a common file format...
[explanation of what PDFs are before showing the code]
```

### 2.2 Degrees of Freedom

Match instruction specificity to task fragility:

| Freedom Level | When to Use | Style |
|--------------|-------------|-------|
| **High** | Multiple valid approaches, context-dependent | Text guidelines |
| **Medium** | Preferred pattern exists, some variation OK | Pseudocode with parameters |
| **Low** | Fragile operations, consistency critical | Exact scripts, no modification |

**Analogy:** Narrow bridge with cliffs = low freedom (exact steps). Open field = high freedom (general direction).

### 2.3 Claude 4.6-Specific Prompt Patterns

These patterns apply to skill instructions targeting current models:

1. **Remove anti-laziness language.** "CRITICAL", "MANDATORY", "ABSOLUTE", "be thorough", "think carefully" -- all amplify already-proactive behavior and cause runaway thinking or rewrite loops. Use normal language: "Use this tool when..."

2. **Be explicit about desired behavior.** Claude responds to clear, specific instructions. If you want thoroughness, describe what thorough looks like, do not just say "be thorough."

3. **Add context/motivation.** Explain WHY a behavior matters. Claude generalizes from explanations better than from bare commands.

4. **Tell Claude what to DO, not what NOT to do.** Instead of "Do not use markdown," say "Respond in flowing prose paragraphs."

5. **Examples teach better than descriptions.** 2-3 input/output pairs teach Claude patterns more effectively than pages of written rules.

6. **Match prompt style to desired output.** The formatting of your prompt influences response formatting.

### 2.4 Effective Instruction Patterns

**Template Pattern** -- Provide output format templates:
```markdown
## Report structure
ALWAYS use this exact template structure:
[template]
```

**Examples Pattern** -- Input/output pairs:
```markdown
## Commit message format
Example 1:
Input: Added user authentication with JWT tokens
Output: feat(auth): implement JWT-based authentication
```

**Conditional Workflow Pattern** -- Decision trees:
```markdown
1. Determine the modification type:
   **Creating new content?** -> Follow "Creation workflow" below
   **Editing existing content?** -> Follow "Editing workflow" below
```

**Checklist Pattern** -- For complex multi-step workflows:
```markdown
Copy this checklist and track your progress:
- [ ] Step 1: Read all source documents
- [ ] Step 2: Identify key themes
...
```

---

## 3. Input/Output Contracts

### 3.1 Argument Handling

Skills receive arguments via `$ARGUMENTS` substitution. Document expected arguments in `argument-hint`:

```yaml
---
name: fix-issue
argument-hint: "[issue-number]"
description: Fix a GitHub issue by number
disable-model-invocation: true
---
Fix GitHub issue $ARGUMENTS following our coding standards.
```

For multiple arguments, use positional access:
```markdown
Migrate the $0 component from $1 to $2.
```

### 3.2 Dynamic Context Injection

Use `` !`command` `` for preprocessing:
```yaml
---
name: pr-summary
---
## Pull request context
- PR diff: !`gh pr diff`
- Changed files: !`gh pr diff --name-only`
```

Commands run BEFORE Claude sees the skill content. Claude receives the output, not the command.

### 3.3 Error Handling in Scripts

Scripts should **solve, not punt**. Handle errors explicitly rather than letting them bubble to Claude:

```python
# GOOD: Handle errors explicitly
def process_file(path):
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        print(f"File {path} not found, creating default")
        with open(path, "w") as f:
            f.write("")
        return ""

# BAD: Punt to Claude
def process_file(path):
    return open(path).read()  # Just fails
```

### 3.4 Verifiable Intermediate Outputs

For complex operations, use the **plan-validate-execute** pattern:
1. Analyze input
2. Create plan file (e.g., `changes.json`)
3. Validate plan with a script
4. Execute only after validation passes
5. Verify output

Make validation scripts verbose with specific error messages to help Claude self-correct.

---

## 4. Composition Patterns

### 4.1 Progressive Disclosure (Three-Level Loading)

| Level | What Loads | When | Token Cost |
|-------|-----------|------|------------|
| 1. Metadata | name + description | Always (startup) | ~50-100 per skill |
| 2. SKILL.md body | Full instructions | When skill triggers | <5k words target |
| 3. Bundled resources | References, scripts | As needed by Claude | Zero until accessed |

### 4.2 Reference Organization Patterns

**Pattern 1: High-level guide with references**
```markdown
# PDF Processing
## Quick start
[essentials]
## Advanced features
- Form filling: See [FORMS.md](FORMS.md)
- API reference: See [REFERENCE.md](REFERENCE.md)
```

**Pattern 2: Domain-specific organization**
```
bigquery-skill/
  SKILL.md (overview + navigation)
  reference/
    finance.md
    sales.md
    product.md
```

**Pattern 3: Conditional details**
```markdown
For simple edits, modify XML directly.
**For tracked changes**: See [REDLINING.md](REDLINING.md)
```

### 4.3 Subagent Execution

Set `context: fork` to run a skill in isolation (its own context, no conversation history):

```yaml
---
name: deep-research
context: fork
agent: Explore
---
Research $ARGUMENTS thoroughly...
```

**When to fork:** Tasks that can run in parallel, require isolated context, or involve independent workstreams.

**When NOT to fork:** Simple tasks, sequential operations, single-file edits, tasks needing shared state. Claude 4.6 has a strong predilection for subagents and may overuse them.

### 4.4 Skill Priority and Namespacing

| Level | Path | Scope |
|-------|------|-------|
| Enterprise | Managed settings | All org users |
| Personal | `~/.claude/skills/` | All your projects |
| Project | `.claude/skills/` | This project only |
| Plugin | `<plugin>/skills/` | Where plugin enabled |

Higher-priority locations win on name conflicts (enterprise > personal > project). Plugin skills use `plugin-name:skill-name` namespace.

### 4.5 MCP Tool References

Always use fully qualified tool names: `ServerName:tool_name`

```markdown
Use the BigQuery:bigquery_schema tool to retrieve schemas.
Use the GitHub:create_issue tool to create issues.
```

### 4.6 Workflow Orchestration (Five Common Patterns)

1. **Sequential Workflow Orchestration** -- Multi-step with explicit dependencies and validation gates at each stage
2. **Multi-MCP Coordination** -- Workflows spanning multiple services with clear phase separation and data passing
3. **Iterative Refinement** -- Output quality improves through validation loops (run validator -> fix -> repeat)
4. **Context-Aware Tool Selection** -- Same outcome via different tools depending on context, with clear decision trees
5. **Domain-Specific Intelligence** -- Specialized knowledge embedded before action, with audit trails

---

## 5. Anti-Patterns

### 5.1 Discovery Anti-Patterns

| Anti-Pattern | Problem | Fix |
|-------------|---------|-----|
| Vague description | "Helps with documents" | Specific: "Extract text and tables from PDF files. Use when working with .pdf files" |
| Missing trigger phrases | Claude never loads the skill | Include keywords users actually say |
| First/second person description | "I can help you..." | Third person: "Processes Excel files and generates reports" |
| Description over 1024 chars | Validation failure | Trim to essentials |

### 5.2 Structure Anti-Patterns

| Anti-Pattern | Problem | Fix |
|-------------|---------|-----|
| SKILL.md over 500 lines | Context bloat, degraded performance | Split to references/ |
| Deeply nested references | Claude partially reads with `head -100` | Keep references one level deep |
| Extraneous files (README.md, CHANGELOG.md, etc.) | Noise, not for AI consumption | Only include what the agent needs |
| Windows-style paths (`scripts\helper.py`) | Breaks on Unix | Always forward slashes |
| `README.md` inside skill folder | Confuses skill discovery | Remove; SKILL.md is the entrypoint |

### 5.3 Instruction Anti-Patterns

| Anti-Pattern | Problem | Fix |
|-------------|---------|-----|
| Aggressive language ("CRITICAL", "MANDATORY", "MUST") | Claude 4.6 overtriggers on these | Normal language: "Use this when..." |
| Anti-laziness prompts ("be thorough", "think carefully") | Amplifies already-proactive behavior, causes runaway thinking | Remove entirely or describe desired behavior specifically |
| Explaining what Claude already knows | Wastes tokens | Only add non-obvious context |
| Too many options without defaults | Confuses: "use pypdf, or pdfplumber, or PyMuPDF..." | Provide one default with escape hatch |
| Inconsistent terminology | Confuses Claude: mixing "API endpoint", "URL", "path" | Pick one term, use it throughout |
| Time-sensitive information | Becomes wrong: "before August 2025, use old API" | Use "current method" + collapsible "old patterns" section |
| Negative instructions | "Do not use markdown" | Positive: "Respond in flowing prose paragraphs" |
| Voodoo constants | `TIMEOUT = 47` -- why? | Document every value: `TIMEOUT = 30  # HTTP requests typically complete within 30s` |

### 5.4 Script Anti-Patterns

| Anti-Pattern | Problem | Fix |
|-------------|---------|-----|
| Punting errors to Claude | Script just fails, Claude guesses | Handle errors explicitly with helpful messages |
| Assuming packages installed | "Use the pdf library" | Explicit: `pip install pypdf`, then show usage |
| Not testing scripts | Bugs surface at runtime | Test every script by running it |

---

## 6. Quality Criteria

### 6.1 Anthropic's Official Checklist

**Core Quality:**
- [ ] Description is specific and includes key terms
- [ ] Description includes both what + when
- [ ] SKILL.md body under 500 lines
- [ ] Additional details in separate files (if needed)
- [ ] No time-sensitive information
- [ ] Consistent terminology throughout
- [ ] Examples are concrete, not abstract
- [ ] File references one level deep
- [ ] Progressive disclosure used appropriately
- [ ] Workflows have clear steps

**Code and Scripts:**
- [ ] Scripts solve problems rather than punt to Claude
- [ ] Error handling is explicit and helpful
- [ ] No voodoo constants (all values justified)
- [ ] Required packages listed and verified
- [ ] No Windows-style paths
- [ ] Validation/verification steps for critical operations
- [ ] Feedback loops for quality-critical tasks

**Testing:**
- [ ] At least three evaluations created
- [ ] Tested with relevant models (Haiku, Sonnet, Opus)
- [ ] Tested with real usage scenarios
- [ ] Team feedback incorporated

### 6.2 Three Testing Dimensions

1. **Triggering Tests:** Does it load for relevant queries? Does it NOT load for unrelated ones?
2. **Functional Tests:** Correct outputs, API calls succeed, error handling works, edge cases covered
3. **Performance Comparison:** Prove improvement vs baseline (tokens consumed, message count, error rates)

### 6.3 Evaluation-Driven Development

Build evaluations BEFORE writing extensive documentation:
1. Run Claude on representative tasks WITHOUT a skill -- document failures
2. Create three evaluation scenarios testing those gaps
3. Measure baseline performance
4. Write MINIMAL instructions to address gaps
5. Iterate: run evaluations, compare, refine

### 6.4 Iterative Development with Two Claudes

- **Claude A** (expert): helps design and refine the skill
- **Claude B** (agent): tests the skill on real tasks
- Observe Claude B's behavior, bring insights back to Claude A
- Each iteration improves based on real agent behavior, not assumptions

---

## 7. Examples from the Guide

### 7.1 Minimal Skill (Claude Code)

```yaml
---
name: explain-code
description: Explains code with visual diagrams and analogies. Use when explaining how code works, teaching about a codebase, or when the user asks "how does this work?"
---

When explaining code, always include:

1. **Start with an analogy**: Compare the code to something from everyday life
2. **Draw a diagram**: Use ASCII art to show flow, structure, or relationships
3. **Walk through the code**: Explain step-by-step what happens
4. **Highlight a gotcha**: What's a common mistake or misconception?

Keep explanations conversational. For complex concepts, use multiple analogies.
```

### 7.2 Side-Effect Skill (Deploy)

```yaml
---
name: deploy
description: Deploy the application to production
disable-model-invocation: true
---

Deploy $ARGUMENTS to production:
1. Run the test suite
2. Build the application
3. Push to the deployment target
4. Verify the deployment succeeded
```

### 7.3 Reference Content Skill

```yaml
---
name: api-conventions
description: API design patterns for this codebase
---

When writing API endpoints:
- Use RESTful naming conventions
- Return consistent error formats
- Include request validation
```

### 7.4 Forked Subagent Skill

```yaml
---
name: deep-research
description: Research a topic thoroughly
context: fork
agent: Explore
---

Research $ARGUMENTS thoroughly:
1. Find relevant files using Glob and Grep
2. Read and analyze the code
3. Summarize findings with specific file references
```

### 7.5 Skill-Creator Description (Anthropic's Own)

```yaml
name: skill-creator
description: Guide for creating effective skills. This skill should be used when users want to create a new skill (or update an existing skill) that extends Claude's capabilities with specialized knowledge, workflows, or tool integrations.
```

---

## 8. Gap Analysis: nWave Commands vs. Anthropic Best Practices

### 8.1 What nWave Commands Do Well

| Practice | nWave Status | Evidence |
|----------|-------------|---------|
| YAML frontmatter with description | Present in all commands | `forge.md`, `research.md`, etc. |
| `argument-hint` field | Used in several commands | `distill.md`, `execute.md` |
| Clear expected outputs section | Consistent across commands | All commands document output paths |
| Success criteria checklists | Strong | Every command has checkbox criteria |
| Agent invocation pattern | Well-structured | `@agent-name` + `*command` pattern |
| Context files required section | Good | Explicit dependency documentation |
| Wave-based handoff documentation | Excellent | Next Wave + Deliverables in each |
| Interactive decision points | Good pattern | `discuss.md`, `distill.md`, `design.md` |
| Examples section | Present in most | 1-3 examples per command |

### 8.2 Gaps and Improvement Opportunities

| Gap | Anthropic Recommendation | nWave Current State | Recommended Action |
|-----|-------------------------|--------------------|--------------------|
| **Description specificity** | Include trigger phrases, keywords users would say | Descriptions are functional but generic ("Evidence-driven knowledge research with source verification") | Add specific trigger phrases: "Use when the user asks to research a topic, verify claims, or find authoritative sources on a subject" |
| **Description person** | Always third person | Mostly fine, but some are noun phrases rather than verb phrases | Standardize to gerund or verb-phrase descriptions |
| **Body line count** | Under 500 lines | `execute.md` is 176 lines, reasonable; but agent definitions referenced may be large | Audit agent definition files for size; split if >500 lines |
| **Progressive disclosure** | Move detailed docs to references/ | Commands are flat `.md` files, no supporting directories | Migrate complex commands (execute, forge) to skill directory format with references/ |
| **Naming convention** | Gerund form preferred: `processing-pdfs` | Verb form: `forge`, `research`, `distill` | Acceptable (Anthropic lists verb form as "acceptable alternative"), but consider gerund for new skills |
| **Aggressive language** | Avoid CRITICAL/MANDATORY/ABSOLUTE | `execute.md` line 99: "CRITICAL: Only the executing agent calls the CLI" | Soften: "Only the executing agent calls the CLI. A log entry without actual execution is invalid." |
| **Degrees of freedom** | Match specificity to task fragility | Generally good, but not explicitly categorized | Document freedom level per instruction section |
| **Feedback loops** | Run validator -> fix -> repeat pattern | Implicit in TDD cycle, not explicit in command structure | Add explicit validation loop instructions where applicable |
| **Skill directory format** | `skill-name/SKILL.md` + optional dirs | Using `.claude/commands/nw/*.md` flat files | Consider migrating to `.claude/skills/nw-*/{SKILL.md, references/}` for complex skills |
| **Invocation control** | `disable-model-invocation`, `user-invocable` | Not used | Add `disable-model-invocation: true` to side-effect commands (execute, finalize, deliver) |
| **allowed-tools** | Restrict tool access per skill | Not used | Add `allowed-tools` to read-only commands (review, research) |
| **context: fork** | Run heavy tasks in isolated subagent | Not used at command level (done at orchestrator level) | Consider `context: fork` for research, review commands |
| **Testing evaluations** | 3+ evaluations per skill | No formal evaluation framework | Create evaluation scenarios for each command |
| **Dynamic context injection** | `` !`command` `` preprocessing | Not used | Useful for commands that need git status, branch info |
| **Avoid explaining the obvious** | Claude already knows common concepts | Some commands explain wave ordering, TDD basics | Trim explanations Claude would already know |

### 8.3 Priority Recommendations

**High Priority (immediate impact):**

1. **Improve descriptions** -- Add trigger phrases and ensure third-person verb phrases. This directly affects whether Claude loads the right command.

2. **Soften aggressive language** -- Replace CRITICAL/MANDATORY/ABSOLUTE with normal instructions. Claude 4.6 overtriggers on these.

3. **Add `disable-model-invocation: true`** to side-effect commands (execute, finalize, deliver) to prevent Claude from auto-triggering destructive workflows.

**Medium Priority (structural improvements):**

4. **Migrate complex commands to skill directories** -- `execute.md` and `forge.md` would benefit from a `references/` directory for DES templates, validation schemas, etc.

5. **Add `allowed-tools` restrictions** -- Read-only commands like review and research should restrict tool access.

6. **Add dynamic context injection** -- Commands that need project state (execute, review) can use `` !`command` `` for git status, branch info.

**Low Priority (polish):**

7. **Create formal evaluation scenarios** for each command.

8. **Trim obvious explanations** that Claude already knows.

9. **Add table of contents** to any referenced file over 100 lines.

---

## Appendix A: Invocation Control Quick Reference

| Frontmatter | User Can Invoke | Claude Can Invoke | When Loaded |
|-------------|:-:|:-:|-------------|
| (default) | Yes | Yes | Description always; full on invoke |
| `disable-model-invocation: true` | Yes | No | Description NOT in context |
| `user-invocable: false` | No | Yes | Description always; full on invoke |

## Appendix B: Skill Location Priority

Enterprise > Personal (`~/.claude/skills/`) > Project (`.claude/skills/`) > Plugin (`<plugin>/skills/`)

Commands at `.claude/commands/` have equal priority to skills at the same level, but skills win on name conflict.

## Appendix C: Token Budget for Skill Descriptions

The description budget scales dynamically at **2% of the context window**, with a fallback of **16,000 characters**. If you have many skills, some may be excluded. Check with `/context` command. Override with `SLASH_COMMAND_TOOL_CHAR_BUDGET` env var.

## Appendix D: Categories of Skills

| Category | Purpose | Example |
|----------|---------|---------|
| **Document and Asset Creation** | Generate consistent output | Frontend design, report generation |
| **Workflow Automation** | Multi-step processes with methodology | Skill-creator, deployment pipeline |
| **MCP Enhancement** | Coordinate tool access + domain expertise | Sentry code review, BigQuery analysis |

## Appendix E: Problem-First vs Tool-First Skills

- **Problem-first:** User describes an outcome, skill orchestrates the right tools. "Set up my project workspace."
- **Tool-first:** User already has tools, skill provides expertise and best practices. "Help me use BigQuery effectively."
