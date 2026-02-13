---
name: design-methodology
description: Apple LeanUX++ design workflow, journey schema, emotional arc patterns, and CLI UX patterns. Load when transitioning from discovery to visualization or when designing journey artifacts.
---

# Design Methodology (Apple LeanUX++)

## Design Workflow

```
PHASE 1              PHASE 2              PHASE 3              PHASE 4
Journey Mapping      Emotional Design     TUI Prototyping      Integration Check
      |                    |                    |                    |
      v                    v                    v                    v
"What's the flow?"   "How should it feel?"  "What does it look?"  "Does it connect?"
```

### Phase 1: Journey Mapping (1-2 days)
- Techniques: User journey mapping, goal-completion flow, step identification
- Question: "What complete journey is the user trying to accomplish?"
- Output: Journey map with steps, commands, and touchpoints

### Phase 2: Emotional Design (1 day)
- Techniques: Emotional arc design, form follows feeling, transition analysis
- Question: "How should the user FEEL at each step?"
- Output: Emotional annotations on journey map

### Phase 3: TUI Prototyping (1-3 days)
- Techniques: Progressive fidelity, ASCII mockups, TUI design patterns
- Question: "What does each step look like?"
- Output: TUI mockups for each journey step

### Phase 4: Integration Check (1 day)
- Techniques: Shared artifact tracking, horizontal coherence, CLI vocabulary
- Question: "Do all pieces connect properly?"
- Output: Validated journey with integration checkpoints

## Journey Schema

```yaml
journey:
  name: "{Goal Name}"
  goal: "{What user is trying to accomplish}"
  persona: "{User persona reference}"

  emotional_arc:
    start: "{Initial emotional state}"
    middle: "{Journey emotional state}"
    end: "{Final emotional state}"

steps:
  - id: 1
    name: "{Step Name}"
    command: "{CLI command or action}"

    tui_mockup: |
      +-- Step N: {Name} -----------------------------------------+
      | {ASCII representation of CLI output}                       |
      | ${variable} <-- tracked artifact                           |
      +------------------------------------------------------------+

    shared_artifacts:
      - name: "{artifact_name}"
        source: "{single source of truth file}"
        displayed_as: "${variable}"
        consumers: ["{list of places this appears}"]

    emotional_state:
      entry: "{How user feels entering step}"
      exit: "{How user feels after step}"

    integration_checkpoint: |
      {What must be validated before proceeding}

    gherkin: |
      Scenario: {Step description}
        Given {precondition}
        When {action}
        Then {observable outcome}
        And shared artifact "${variable}" matches source

integration_validation:
  shared_artifact_consistency:
    - artifact: "{name}"
      must_match_across: [1, 2, 3]
      failure_message: "{Integration error description}"
```

## Emotional Arc Patterns

### Confidence Building
- Start: Anxious/Uncertain
- Middle: Focused/Engaged
- End: Confident/Satisfied
- Use when: Complex multi-step operations

### Discovery Joy
- Start: Curious
- Middle: Exploring
- End: Delighted
- Use when: Learning new features

### Problem Relief
- Start: Frustrated
- Middle: Hopeful
- End: Relieved
- Use when: Fixing issues or debugging

### Transition Rules
- Build confidence progressively through small wins
- Provide clear feedback at each step
- Error states guide to resolution rather than adding frustration
- Positive-to-negative transitions need explicit warning or buffer step

## Apple Design Principles Applied

- **Form Follows Feeling**: Design for emotion first, function second
- **Concentrated Focus**: One thing done excellently beats many done adequately
- **Material Honesty**: Respect the medium -- CLI should feel like CLI
- **Hidden Quality**: Excellence in details users may never see

## CLI UX Patterns (clig.dev)

### Command Structure
- Pattern: `tool [noun] [verb]` or `tool [verb] [noun]`
- Pick one pattern and use it consistently across the entire journey
- Example: `crafter agent create` or `crafter create agent`

### Feedback Principles
- Responsive: Print something in <100ms
- Progress: Show progress for long operations
- Transparent: Show what is happening, do not hide complexity
- Recoverable: Clear errors with suggested fixes

### Progressive Disclosure
- Level 1 (default): Basic output for common use
- Level 2 (--verbose): Detailed output for power users
- Level 3 (--debug): Diagnostic output for troubleshooting

### Help Design
- Implement --help on every command
- Make help easy to discover
- Provide contextual suggestions

## Output Formats

Three artifact types are produced:

1. **Visual Journey** (`journey-{name}-visual.md`): ASCII flow diagram showing the complete journey with emotional annotations and TUI mockups per step
2. **Structured Schema** (`journey-{name}.yaml`): Machine-readable journey definition following the schema above
3. **Gherkin Scenarios** (`journey-{name}.feature`): Testable acceptance scenarios extracted from each journey step

All artifacts go to `docs/ux/{epic}/`.
