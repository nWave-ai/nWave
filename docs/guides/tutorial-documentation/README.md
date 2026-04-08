# Tutorial: Creating Quality Documentation

**Time**: ~12 minutes (5 steps)
**Platform**: macOS, Linux, or Windows
**Prerequisites**: Python 3.10+, Claude Code with nWave installed
**What this is**: A walkthrough of `/nw-document` -- nWave's documentation generator. You will create a small Python module, then use `/nw-document` to generate DIVIO-compliant documentation for it. The result is a polished reference document that Quill (the documentarist agent) writes and reviews automatically.

---

## Setup

Run from a directory where you want the tutorial project created (e.g. `~/projects`):

```bash
curl -fsSL https://raw.githubusercontent.com/nWave-ai/nWave/main/docs/guides/tutorial-documentation/setup.py | python3
```

Prefer to read first? See [manual-setup.md](./manual-setup.md).

## After setup you should have

- A `string-utils/` directory with `string_utils.py` containing three functions: `slugify`, `truncate`, `word_count`
- Each function has docstrings — `/nw-document` will use these as input but produce DIVIO-compliant docs around them

---

## What You'll Build

A reference document for a Python string utilities module -- generated, classified, and quality-checked by nWave's documentation pipeline.

**Before**: You stare at your code, open a blank `README.md`, write three lines, get interrupted, and never come back. Six months later, nobody (including you) remembers what the module does.

**After**: You run one command and get a structured, type-appropriate document that follows the DIVIO documentation framework. It is classified as the right type (tutorial, how-to, reference, or explanation), checked for quality, and ready to commit.

**Why this matters**: Most documentation fails because it mixes purposes -- a "getting started" guide that also tries to be an API reference and an architecture explainer. The DIVIO framework solves this by separating documentation into four distinct types, each with its own rules. `/nw-document` enforces this automatically, so your docs stay focused and useful.

---

## Step 1 of 5: Open the project (~1 minute)

After running setup, `cd string-utils` and open Claude Code in that directory:

```bash
cd string-utils
```

The project contains a single file `string_utils.py` with three functions (`slugify`, `truncate`, `word_count`), each already documented with docstrings. `/nw-document` will read those docstrings and produce a polished DIVIO-compliant reference document around them.

This tutorial doesn't need a virtualenv or pytest — `/nw-document` works on any Python file with docstrings.

---

## Step 2 of 5: Generate Documentation (~3-4 minutes)

Run the document command, specifying a reference document type:

```
/nw-document "string_utils module" --type=reference
```

The documentation pipeline starts. You will see phases scroll by:

```
● nw-researcher(Gathering evidence on string_utils)       <- Research phase (~1 min)
● nw-researcher-reviewer(Review research)                 <- Research review (~30s)
● nw-documentarist(Writing reference documentation)       <- Writing phase (~1 min)
● nw-documentarist-reviewer(Review documentation)         <- Doc review (~30s)
```

This takes 3-4 minutes. The pipeline researches your code, writes the document, and reviews it automatically.

> **AI output varies between runs.** Your generated documentation will differ from the examples in this tutorial. The agents produce content based on your specific code. What matters is the structure and type classification, not exact wording.

> **If the command does not start**: Run `/nw-help` to verify nWave is installed. If `/nw-document` is not listed, reinstall nWave.

*Next: you will read the generated documentation and understand the DIVIO types.*

---

## Step 3 of 5: Review the Generated Reference Document (~2 minutes)

After the pipeline finishes, Quill produces a reference document. The output path will be shown in the handoff summary, typically:

```
docs/reference/string-utils-module.md
```

Open it. A reference document follows this general shape:

```markdown
# string_utils Module Reference

## Overview
String utility functions for common text transformations.

## Functions

### slugify(text: str) -> str
Convert text to a URL-friendly slug.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| text | str  | The input string to slugify |

**Returns:** A lowercase, hyphen-separated string safe for URLs.

**Example:**
...

### truncate(text: str, max_length: int = 100, suffix: str = "...") -> str
...

### word_count(text: str) -> int
...
```

**Your output will differ** in phrasing and detail. What matters is that a reference document:

- **Describes the machinery** -- Parameters, return types, behavior
- **Is information-oriented** -- States facts, does not teach or persuade
- **Has consistent structure** -- Every function follows the same format

This is a *reference* document -- one of four documentation types in the DIVIO framework. You will see the other types in Step 5.

*Next: you will look at how Quill validated the document's quality.*

---

## Step 4 of 5: Check Documentation Quality (~2 minutes)

The pipeline also produces a validation report alongside the document. Check the handoff summary for the validation file path, typically:

```
docs/reference/string-utils-module.md.validation.yaml
```

The validation report follows this structure:

```yaml
documentation_review:
  document: docs/reference/string-utils-module.md
  classification:
    type: reference
    confidence: high
    signals: [parameter tables, return type annotations, no tutorial steps, ...]
  validation:
    passed: true
    checklist_results:
      - item: "Complete parameter documentation"
        passed: true
      - item: "Consistent structure across entries"
        passed: true
      - item: "No tutorial or how-to content mixed in"
        passed: true
  collapse_detection:
    clean: true
    violations: []
  verdict: approved
```

Three things to check:

1. **Verdict**: "approved" means the document passed all quality gates. "needs-revision" means Quill found issues and revised automatically.
2. **Collapse detection**: Should be `clean: true`. A "collapse" means content from one DIVIO type leaked into another -- for example, tutorial steps appearing in a reference document.
3. **Checklist results**: Each item shows whether a specific quality rule passed.

<details>
<summary>Collapse pattern types (advanced)</summary>

Quill detects five collapse patterns:

- **Tutorial creep** -- Step-by-step instructions in a reference
- **How-to bloat** -- Teaching fundamentals before task steps
- **Reference narrative** -- Storytelling in an API reference
- **Explanation task drift** -- Procedural steps in a conceptual explainer
- **Hybrid horror** -- Content from 3+ types in one document

</details>

> **If the verdict is "needs-revision"**: This is normal. The pipeline handles revisions automatically -- Quill rewrites based on reviewer feedback. The final output you see has already been revised. Check the iteration count in the handoff summary.

> **If the validation file is missing**: The pipeline may have encountered an error. Check the Claude Code output for error messages. Common cause: insufficient code to document (the module needs at least one function with a docstring).

*Next: you will try generating a different documentation type and wrap up.*

---

## Step 5 of 5: Try a Different Documentation Type (~2 minutes)

Generate a how-to guide for the same module to see how the output changes:

```
/nw-document "truncating user input with string_utils" --type=howto
```

Watch for how the output differs from the reference document:

- **Structure changes**: Instead of parameter tables, you get numbered steps focused on solving a specific problem
- **Tone changes**: Instead of "Parameters: text (str)" you get "Pass the user's input to truncate()"
- **Scope changes**: The how-to focuses on one task (truncating input), not the entire module

This demonstrates the core DIVIO principle: same code, different documentation types, different structures. Each type serves a different reader need.

### What You Built

You produced two documentation artifacts:

1. **A reference document** -- Information-oriented, describing the string_utils API
2. **A how-to guide** -- Task-oriented, showing how to solve a specific problem

Both were automatically classified, validated for type purity, checked for collapse patterns, and reviewed for quality.

### When to Use `/nw-document`

- You have code with no documentation and need to start somewhere
- You want to ensure existing docs follow DIVIO principles
- You need a specific type of document (reference for an API, tutorial for onboarding, how-to for common tasks)
- You want quality validation on documentation before committing

### The Four DIVIO Types

| Type | Purpose | Orientation | Example |
|------|---------|-------------|---------|
| **Tutorial** | Teach a beginner | Learning-oriented | "Build your first slug generator" |
| **How-to** | Solve a specific problem | Task-oriented | "How to truncate user input safely" |
| **Reference** | Describe the machinery | Information-oriented | "string_utils API reference" (what you generated in Step 2) |
| **Explanation** | Discuss concepts | Understanding-oriented | "Why URL slugification matters for SEO" |

The key insight: each type has different rules. A reference document should not try to teach (that is a tutorial's job). A how-to should not explain architecture (that is an explanation's job). Mixing types is the most common documentation failure -- Quill prevents this automatically.

If you omit `--type`, the command will ask you to choose interactively.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `/nw-document` does not start | Make sure nWave is installed. Run `/nw-help` to verify the command is listed. |
| Pipeline takes more than 5 minutes | Complex modules with many functions take longer. This is normal. For large codebases, scope the topic to a single module or component. |
| Collapse violations in the validation report | The pipeline auto-revises up to 2 times. If collapse persists, it means the content genuinely spans multiple types. Consider generating separate documents for each type. |
| Generated doc is too short or generic | Add more docstrings to your code. Quill works best with functions that have type hints, docstrings, and clear parameter descriptions. |
| Validation file is missing | Check Claude Code output for errors. The module needs at least one function with a docstring for Quill to produce useful output. |
| "needs-revision" verdict after all iterations | The document is usable but has minor issues. Review the recommendations in the validation YAML and apply them manually, or re-run with a narrower scope. |

---

**Last Updated**: 2026-02-18
