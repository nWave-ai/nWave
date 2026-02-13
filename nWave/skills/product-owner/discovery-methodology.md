---
name: discovery-methodology
description: Question-first approach to understanding user journeys. Load when starting a new journey design or when the discovery phase needs deepening.
---

# Discovery Methodology

Discover journeys through deep questioning before any sketching. The sketch is proof of understanding, not the starting point.

## Session Flow

### Phase 1: Goal Discovery (First 5-10 minutes)
Focus: What is the user trying to accomplish?

Questions:
- "What's the ultimate goal you're trying to achieve?"
- "What triggers this journey? When does a user start this?"
- "How will you know when you've succeeded?"
- "What's the happy path in your mind?"

### Phase 2: Mental Model (10-20 minutes)
Focus: What does the user EXPECT to see?

Questions:
- "Walk me through step by step -- what do you type, what do you see?"
- "At this step, what information appears on screen?"
- "What would you need to see to feel confident?"
- "Where do you think this data comes from?"
- "What's your mental model of how this works?"

### Phase 3: Emotional Journey (5-10 minutes)
Focus: How should the user FEEL?

Questions:
- "How should you feel at the start? Anxious? Curious? Confident?"
- "What's the emotional arc -- where's the peak tension?"
- "How should you feel when it's done?"
- "Where might you feel frustrated or lost?"
- "What would make this feel satisfying vs frustrating?"

### Phase 4: Shared Artifacts (5-10 minutes)
Focus: What data is shared across steps?

Questions:
- "What information appears in multiple places?"
- "Where does the version number come from? Where is it shown?"
- "If this path changes, what else breaks?"
- "Who owns this piece of data?"
- "What paths or URLs are reused across steps?"

### Phase 5: Error Paths (5 minutes)
Focus: What could go wrong?

Questions:
- "What's the most likely failure?"
- "What should the user see when it fails?"
- "How does the user recover?"
- "What would a helpful error message look like?"

### Phase 6: Integration Points
Focus: How do steps connect?

Questions:
- "What did the previous step produce that this step needs?"
- "What does this step produce that the next step needs?"
- "Are there any hidden dependencies between steps?"
- "What external systems or files does this touch?"

### Phase 7: CLI UX Specifics
Focus: What commands and output does the user expect?

Questions:
- "What command would you naturally type for this?"
- "What flags or options do you expect?"
- "How verbose should the output be by default?"
- "Should there be a --dry-run option?"

## Question Format

Use AskUserQuestion with structured options:
- 2-4 concrete options based on design methodology
- Options represent real design alternatives
- Include an "Other" option for open-ended input
- Each option includes its design implication

## Sketch Readiness Criteria

Ready to sketch ONLY when all of these can be answered:
- Complete happy path described (no "and then something happens")
- Each step has expected output defined
- Emotional arc is explicit and coherent
- Shared artifacts identified with sources
- At least major error paths acknowledged

If ANY criterion is unclear -- ask more questions.

## When to Question

Always ask first when:
- User requests a sketch -- ask before sketching
- User describes a feature -- ask to understand the journey context
- User mentions a command -- ask what they expect to see

Continue asking until:
- User can describe complete happy path without gaps
- All shared artifacts identified with sources
- Emotional arc is explicit and coherent
- Error paths are at least acknowledged

## Anti-Patterns

- Jumping to sketching before understanding the mental model
- Assuming you know what the user expects
- Filling in gaps with your own assumptions
- Skipping emotional journey questions
- Ignoring shared artifact tracking

Instead:
- Ask one more question when uncertain
- Reflect back understanding for user validation
- Make the user articulate their mental model explicitly
- Map emotional states at every step
- Document every ${variable} and its source
