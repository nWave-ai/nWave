---
name: nw-user-story-mapping
description: User story mapping knowledge for exploring journeys, release boundaries, activity gaps, and outcome-based prioritization.
user-invocable: false
disable-model-invocation: true
---

# User Story Mapping

Create story maps that organize user stories spatially by activity and priority, then slice releases by outcome impact. Reference: Jeff Patton, "User Story Mapping" (2014). Integrates outcome-based prioritization from Gothelf/Seiden and riskiest-assumption-first from Maurya.

**Output scope**: supply journey steps and human-supplied emotion; mark emotion not supplied when unknown. Describe visible release increments and distinguish proposed, confirmed and open judgments. Name an owner for open questions. The templates below are conceptual reading aids, not a request to author a separate story-map file.

## Story Map Anatomy

| Element | Position | Purpose |
|---------|----------|---------|
| **Backbone** | Top row, left-to-right | User activities in chronological order -- the spine of the journey |
| **Ribs** | Columns under each activity | User tasks broken down vertically by detail and priority |
| **Walking Skeleton** | Horizontal line across all activities | Thinnest possible end-to-end working flow. Not an MVP -- it is the minimum slice that connects ALL activities |
| **Release Slices** | Horizontal bands below skeleton | Coherent groups of stories, each adding incremental value tied to a specific outcome |

Visual structure:

```
Activity A    Activity B    Activity C    Activity D
-----------   -----------   -----------   -----------
Task A.1      Task B.1      Task C.1      Task D.1     <- Walking Skeleton
...........   ...........   ...........   ...........   <- skeleton line
Task A.2      Task B.2      Task C.2      Task D.2     <- Release 1
Task A.3      Task B.3                                  <- Release 1
              Task B.4      Task C.3      Task D.3     <- Release 2
```

## Building the Map

### Step 1: Frame the journey
Identify the user persona and their end-to-end goal. One map per persona-goal pair.

### Step 2: Map the backbone
Write the big activities left-to-right in chronological order. These are verb phrases: "Search products", "Compare options", "Complete purchase". Aim for 4-8 activities.

### Step 3: Fill the ribs
Under each activity, list the tasks that support it. Write as short action phrases (user behaviors). Place more detail and less critical tasks lower.

### Step 4: Prioritize vertically
Reorder tasks within each column: most critical at top, nice-to-have at bottom. Ask: "Which task is essential for this activity to work at all?"

### Step 5: Draw the walking skeleton
Draw a horizontal line that captures exactly one task from each activity -- the thinnest slice that delivers end-to-end flow. Every activity must be represented. If an activity has no task above the line, the skeleton is incomplete.

### Step 6: Slice into releases by outcome
Group remaining tasks into horizontal bands. Each band targets a specific outcome KPI. Name each release by the outcome it achieves, not the features it contains.

**Value-outcome naming (epic · feature · slice).** The naming rule extends to every level — epic-name, feature-name, slice-name. Each name MUST express the value-outcome (what the user GETS), never the mechanism. A good name conveys the value without reading the body; it is a compression of that item's Value statement / outcome KPI. Self-check before finalizing any name: *"Does this name say the VALUE/outcome, or the MECHANISM?"* — if mechanism, RENAME. Avoid as the primary descriptor: `refactor`, `migration`, `port`, `gate`, `schema`, `wiring`, `shared-surfaces`, `evolution`, `infrastructure`, `-aware`, `-handler` (these are HOW, not the value). Example: `atdd-pure-shared-surfaces` → `F-SUSTAINABLE-TEST-SUITE`; `F-RUNNER-RESOLUTION-TARGET-AWARE` → `F-TESTS-RUN-IN-THE-PROJECTS-OWN-RUNNER`.

## Outcome-Based Prioritization

Prioritize releases by outcome impact, not feature completeness. Each release slice targets a specific measurable behavior change.

### Prioritization Formula

**Value** (outcome impact) x **Urgency** (time-sensitivity) / **Effort** (complexity) = **Priority Score**

Where (1-5 scale):
- **Value** (1-5) = outcome impact. 5 = moves north-star KPI significantly. 1 = marginal improvement. In Phase 2.5, estimate from discovery insights; refine once outcome KPI facts are confirmed.
- **Urgency** (1-5) = time-sensitivity. 5 = time-critical or derisks fatal assumption. 1 = evergreen, no deadline.
- **Effort** (1-5) = complexity. 5 = many tasks, cross-cutting, unknowns. 1 = single task, well-understood.
- **Tie-breaking**: Walking Skeleton > Riskiest Assumption > Highest Value.

### Riskiest Assumption First

From Running Lean (Maurya): validate what could kill the product before optimizing what improves it.

| Priority | What to validate | Why |
|----------|-----------------|-----|
| 1st | Walking skeleton | Does the end-to-end flow work at all? |
| 2nd | Release targeting riskiest assumption | Could this assumption kill the product? |
| 3rd | Release targeting highest-value outcome | Which behavior change drives the most impact? |
| 4th+ | Remaining releases by Value x Urgency / Effort | Incremental value delivery |

### Connecting to Outcomes

Each release slice maps to the logic model chain (Gothelf/Seiden):

```
Release Slice -> Output (features built)
             -> Outcome (behavior change: [Who] [Does what] [By how much])
             -> Impact (business KPI moved)
```

## Story Map Template (story-map.md)

```markdown
# Story Map: {feature-name}

## User: {persona}
## Goal: {what they're trying to accomplish}

## Backbone

| Activity 1 | Activity 2 | Activity 3 | Activity N |
|------------|------------|------------|------------|
| Task 1.1   | Task 2.1   | Task 3.1   | Task N.1   |
| Task 1.2   | Task 2.2   | Task 3.2   |            |
|            | Task 2.3   |            |            |

---

### Walking Skeleton
{List the minimum tasks from each activity that form the thinnest end-to-end slice}

### Release 1: {outcome target}
{Tasks included, outcome KPI targeted, rationale}

### Release 2: {outcome target}
{Tasks included, outcome KPI targeted, rationale}
```

## Prioritization Template (prioritization.md)

```markdown
# Prioritization: {feature-name}

## Release Priority

| Priority | Release | Target Outcome | KPI | Rationale |
|----------|---------|---------------|-----|-----------|
| 1 | Walking Skeleton | End-to-end flow works | {KPI} | Validates core assumption |
| 2 | {name} | {outcome} | {KPI} | {why this order} |

## Backlog Suggestions

| Story | Release | Priority | Outcome Link | Dependencies |
|-------|---------|----------|-------------|--------------|
| US-01 | WS | P1 | {KPI-1} | None |
| US-02 | R1 | P2 | {KPI-2} | US-01 |

> **Note**: In Phase 2.5, stories are task-level placeholders (e.g., "Search by category").
> Story IDs (US-01) are assigned in Phase 4 (Requirements). Revisit this table after Phase 4.
```

## Anti-Patterns

| Anti-Pattern | Problem | Fix |
|-------------|---------|-----|
| Feature-first slicing | Release 1 = all of Feature A, Release 2 = all of Feature B. No end-to-end value until late. | Slice ACROSS features by outcome. Each release touches multiple activities. |
| No walking skeleton | Going deep on one activity before connecting end-to-end. Late integration risk. | Draw the skeleton first. One task per activity, thinnest possible. |
| Fat walking skeleton | Too many stories crammed into the skeleton. Defeats the purpose. | Skeleton = exactly the minimum to make the flow work. Move extras to Release 1. |
| Effort-based priority | Ordering by "easy first" instead of outcome impact. Delivers low-value features early. | Prioritize by Value x Urgency / Effort. Easy-but-low-value stories go to later releases. |
| Orphan stories | Stories with no outcome link. No measurable behavior change targeted. | Every story traces to an outcome KPI. If it cannot, question its value. |
| Mechanism-named item | Epic/feature/slice/release named after the mechanism (`refactor`, `migration`, `port`, `gate`, `-aware`, `-handler`) instead of the value. Children never converge to a coherent outcome. | Rename to the value-outcome via the Step 6 self-check. |
| Activity gaps | Some activities have no tasks in a release slice. Breaks end-to-end coherence. | Walking skeleton covers all activities. Later releases may skip activities only if those are already sufficient. |
