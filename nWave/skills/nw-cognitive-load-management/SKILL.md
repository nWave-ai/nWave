---
name: nw-cognitive-load-management
description: Cognitive Load Theory (Sweller) applied to tutorial design — intrinsic/extraneous/germane load management, concept budgeting, and progressive disclosure
disable-model-invocation: true
---

# Cognitive Load Management for Tutorials

Applying Cognitive Load Theory (Sweller) to tutorial design. The goal: maximize germane load (schema building) by minimizing extraneous load (bad design).

## The Three Loads

| Load Type | Definition | Tutorial Author's Job |
|-----------|-----------|----------------------|
| Intrinsic | Complexity inherent to the material | Sequence concepts to manage element interactivity |
| Extraneous | Caused by poor instructional design | Eliminate ruthlessly |
| Germane | Effort building mental schemas | Maximize through worked examples and practice |

## Concept Budgeting

Each tutorial step has a concept budget of 3. A "concept" is any idea the reader must hold in working memory to complete the step.

### Counting Concepts

Examples of what counts as one concept:
- A new CLI command and its primary flag
- A file format (e.g., PPM image format)
- An architectural pattern (e.g., middleware pipeline)
- A new API endpoint and its required parameters

Examples of what does NOT count (already in working memory for most developers):
- Running a command in a terminal
- Editing a file
- Standard Git operations
- Common data types (strings, lists, dicts)

### When You Exceed the Budget

If a step requires 4+ concepts:
1. Split the step into two steps
2. Introduce concept N in step K, use it in step K+1
3. Provide a worked example that demonstrates multiple concepts together (reduces interactivity)

## Worked Example Effect

Show complete working code first, then explain. Do not ask users to assemble code from descriptions.

**Pattern**:
```
Here is the complete handler:

\`\`\`python
{complete, working code}
\`\`\`

Let's break this down:
- Line 1-3: {what and why}
- Line 5: {what and why}
```

**Anti-pattern**:
```
First, import the handler module. Then create a function that
accepts a request parameter. Inside the function, validate the
input using... Now type this code:

\`\`\`python
{code}
\`\`\`
```

The anti-pattern forces the reader to build the code mentally from prose, then compare against the actual code -- double the cognitive load.

## Split-Attention Avoidance

Code and its explanation must be co-located. Never separate them by more than a glance.

**Good**: Inline comments explaining non-obvious lines
```python
token = jwt.encode(
    {"user_id": user.id, "exp": expiry},  # exp = auto-expiration
    SECRET_KEY,
    algorithm="HS256"  # HMAC-SHA256, sufficient for session tokens
)
```

**Good**: Explanation immediately after the code block, referencing specific lines

**Bad**: Code on one page, explanation on another
**Bad**: "See the configuration reference for details on these options"
**Bad**: Diagram with labels in a separate legend

## Expertise Reversal Awareness

Detailed explanations help novices but slow experts. Address both:

1. Keep the main path lean (action -> verify)
2. Put detailed explanations in collapsible sections or "What just happened?" blocks
3. Offer a "fast track" callout for experienced readers: "Already familiar with JWT? Skip to Step 4."
4. Link to reference docs for readers who want depth, instead of inlining it

## Scaffolding and Fading

Early steps provide more support. Later steps provide less.

- **Step 1**: Full code, detailed explanation, expected output, troubleshooting
- **Step 3**: Full code, brief explanation, expected output
- **Step 5**: Code with inline comments only, verification command
- **Final step**: "Now try adding {feature} on your own. Hint: use {function}."

This mirrors the Zone of Proximal Development: start within reach, gradually extend.

## Chunking Patterns

Group related information into meaningful units:

- **Command chunk**: command + flags + expected output = one visual block
- **Config chunk**: file path + content + explanation = one visual block
- **Concept chunk**: term + one-sentence definition + example = one visual block

Use visual grouping (code blocks, callout boxes, headers) to reinforce chunks. Never scatter parts of the same chunk across multiple sections.
