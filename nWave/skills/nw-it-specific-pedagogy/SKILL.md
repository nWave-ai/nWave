---
name: nw-it-specific-pedagogy
description: IT-specific learning formats — coding katas, coding dojos, mob/ensemble programming, TDD workshops, architecture katas, refactoring katas — with facilitation rules, format selection logic, group size constraints, and activity sequencing for technical skill development
disable-model-invocation: true
agent: nw-workshopper
---

# IT-Specific Pedagogy

## Core Principle

Use IT-specific formats when the objective is a habit requiring muscle memory (TDD, refactoring, collaborative coding). If "watch a video" could achieve the outcome, generic activities suffice.

| Objective | Generic Sufficient? | IT Format Required |
|-----------|---------------------|--------------------|
| Understanding what TDD is | Yes | — |
| Practicing TDD | No | Kata progression |
| Collaborative code quality habits | No | Coding Dojo / Mob |
| Architecture trade-off reasoning | Partially | Architecture Kata |
| Legacy code confidence | No | Gilded Rose / Characterization Testing |
| Team coding standards | No | Code Smell Hunt + mob refactoring |
| Design principles application | No | Refactoring Golf / Object Calisthenics |

---

## Format 1: Coding Kata

**Definition**: A small, fixed programming problem practiced repeatedly, with attention on technique (TDD cycle, refactoring, incremental design), not problem-solving. The problem is deliberately trivial so cognitive load goes entirely to the technique.

### Kata Format Variants

| Format | Who Codes | Best For |
|--------|-----------|----------|
| Solo kata | Individual, alone | Individual skill automation |
| Prepared kata | Facilitator, observed | Showing ideal form; demonstration |
| Randori (Dojo) | Group rotation at keyboard | Collaborative practice, 4-10 people |
| Code Retreat | Pairs rotate, code deleted | Exploring multiple approaches in one day |

### Classic Kata Catalogue

| Kata | Learning Outcome | Correct Audience |
|------|-----------------|------------------|
| FizzBuzz | TDD first steps; baby steps | Complete TDD beginners |
| String Calculator (Osherove) | Incremental design; growing requirements | Beginners with basic test tool comfort |
| Roman Numerals | Algorithm evolution; emergent design | Comfortable with red-green-refactor |
| Bowling Game (Martin) | Lookahead state; deferred computation | TDD intermediate |
| Tennis | Object design; state machine; multiple valid designs | Intermediate |
| Prime Factors | Transformation Priority Premise | Intermediate; clean TDD discipline |
| Gilded Rose (Bache) | Characterization testing; legacy code entry | TDD fluent |
| Conway's Game of Life | Emergent design under constraints | Code Retreat only; advanced |

**Selection rule**: FizzBuzz and String Calculator are correct entry points for TDD-naive groups. Never use Gilded Rose as a first kata — it assumes TDD fluency.

### Designing a Kata for a Specific Outcome

1. Fix the problem (removes problem-solving overhead)
2. Name the technique being practiced (e.g., "This session focuses solely on the refactor step")
3. Apply one constraint that makes the anti-pattern impossible
4. Time-box sessions (20-30 min beginners; 45 min advanced)
5. Close with retrospective: "What did you notice about the technique, not the code?"

---

## Format 2: Coding Dojo

**Definition**: Group practice session with single keyboard and projector, explicit facilitation rules, and retrospective. Kata is the problem; Dojo is the container.

### Non-Negotiable Facilitation Rules

1. **One keyboard, one projector** — all code visible at all times
2. **Pair at keyboard (driver + navigator)** — rotate every 5-7 minutes
3. **No criticism from observers** — questions and suggestions only
4. **Everyone codes** — nobody is permanently a spectator
5. **Retrospective always closes** — 15-20 minutes: what did we learn?
6. **Egoless programming norm** — state at start: "deleting your code is good behavior"

### Session Structure

```
Introduction (5 min)      — kata, rules, learning focus
Coding (70-90 min)        — pairs rotate every 5-7 min
Retrospective (15-20 min) — technique insight, not code review
```

### Group Size Constraints

| Group Size | Format | Notes |
|------------|--------|-------|
| 4-6 | Randori | Optimal |
| 7-10 | Randori | Workable — facilitate debates actively |
| 11-20 | Split into parallel dojos | Shared retrospective |
| 20+ | Mob sub-groups or Architecture Katas | Dojo format degrades |

Above 10: each participant's keyboard time drops below 10 minutes in a 90-minute session.

| Format | Use When |
|--------|----------|
| Prepared kata | Showing ideal TDD form; introducing a new kata; demonstrating a refactoring pattern |
| Randori | Building collaborative habits; team TDD practice; no solution needs to be reached |

---

## Format 3: Mob / Ensemble Programming

**Core rule**: "For an idea to go from your head into the computer, it MUST go through someone else's hands."

### Roles

| Role | Responsibility | Pedagogical Purpose |
|------|---------------|---------------------|
| Driver | Types only; translates spoken instructions; makes no design decisions | Reduces ego; makes authorship collective |
| Navigator | Holds current design direction; speaks in intent ("extract this method"), not keystrokes | Forces verbalization of reasoning |
| Mob | All others: researching, anticipating, challenging | Real-time peer review; knowledge transfer |

**Navigator rule**: Speak at the highest abstraction level the driver can act on.

### Rotation and Group Sizing

| Context | Rotation Interval | Group Size |
|---------|------------------|------------|
| Workshop / learning | 4-5 minutes | 4-6 |
| Experienced production team | 10-15 minutes | 4-7 |
| Maximum before splitting | — | 7 |

**Large groups (8-20)**: Split into parallel mobs of 4-6. Same problem, different groups. Reconvene to compare solutions.

| Workshop Context | Appropriate Problem |
|-----------------|---------------------|
| Teaching TDD | Classic kata (FizzBuzz, String Calculator) |
| Legacy code awareness | Gilded Rose or Parrot kata |
| Team coding standards | Real codebase section with identified code smell |
| Architecture thinking | Architecture kata (design-only mob) |

---

## Format 4: TDD Workshop Design

### Three Failure Modes to Detect and Counter

| Failure Mode | Observable Signal | Intervention |
|--------------|------------------|--------------|
| Test-last disguised as TDD | Test passes on first run every time | Ask: "What did you think the implementation would be before writing the test?" |
| Testing implementation details | Tests break on refactoring without behavior change | Ask: "Does this test describe what the code does for users, or how it does it?" |
| Skipping the refactor step | Pairs stop after green, move to next test | Timer: force 5-minute refactor consideration after every green |

### Workshop Activity Sequence

**Stage 1 — Worked Example (30-45 min)**: Facilitator writes code live with narration. Explicitly verbalize uncertainty. Visible mistakes are essential — they model recovery behavior. Do NOT use a polished prepared demo.

**Stage 2 — Completion Exercise (45-60 min)**: Provide a half-completed kata. Participants continue in the same style. The existing structure prevents mental-design-first patterns.

**Stage 3 — Independent Kata (60-90 min)**: Full kata from scratch, in pairs. Facilitator circulates using the three detection questions. FizzBuzz for TDD novices; String Calculator for basic comfort.

**Stage 4 — Constrained Kata (advanced only)**: "TDD as if you meant it" — all production code must first appear inside the test file. Makes test-last technically impossible.

### Chicago vs London School

| School | Alias | Approach | Teach First When |
|--------|-------|----------|-----------------|
| Chicago / Classicist | Inside-Out, Detroit | State-based tests; real collaborators | TDD novices; domain algorithm katas |
| London / Mockist | Outside-In | Interaction-based tests; mock collaborators | Post-TDD-fluency; layered architecture |

**Sequencing rule**: Chicago school always first. Mixing both in a beginners' session causes confusion.

### Samman Learning Hour (Emily Bache)

```
Framing talk        (10-15 min) — context, concept, why it matters
Demonstration/kata  (15-20 min) — facilitator shows technique live
Pair kata exercise  (30-45 min) — participants practice
Retrospective       (10 min)    — what did you notice?
```

---

## Format 5: Architecture Katas

**Definition**: Small-group exercise where teams design a system from a brief requirement, then present to and are questioned by peer groups.

### Session Structure

```
Problem assignment     (5 min)   — each group gets a different kata
Requirement discovery  (10 min)  — interview moderator as "customer"
Design phase           (20-30 min) — sketch components, integrations, quality attributes
Presentation + Q&A     (10 min/group) — present; other groups challenge
Peer voting            (5 min)   — groups vote; moderator facilitates discussion
```

| Parameter | Value |
|-----------|-------|
| Per group | 3-5 people |
| Optimal number of groups | 4-10 |
| Total participants | 12-50 |

Peer review teaches that architecture is a communication artifact. Voting de-centers the facilitator.

---

## Format 6: Refactoring Katas and Code Smell Workshops

| Activity | Starting Material | Learning Outcome | Audience |
|----------|------------------|-----------------|----------|
| Characterization Testing (Gilded Rose) | Untested messy code | Adding tests before refactoring | TDD fluent |
| Refactoring Golf | Before/after code pair | Minimum safe steps | Refactoring intermediate |
| Code Smell Scavenger Hunt | Real codebase | Identify smells; mob-refactor | Any team with legacy code |
| Parrot / Theatrical Players (Bache) | Structured kata | Specific refactoring patterns | Refactoring intermediate |

**Non-negotiable sequencing rule**: Characterization testing must precede refactoring in any legacy code workshop.

### Code Smell Scavenger Hunt — Steps

1. Brief slide per smell: what it is, signals, targeted refactoring
2. Teams search assigned sections (15 min)
3. Post-it results; dot-vote most impactful example
4. Mob-refactor the top vote (20-30 min)
5. Retrospective: "Does this appear elsewhere in our codebase?"

---

## Format 7: Live Coding vs Prepared Demo

| Format | Use When | Do NOT Use When |
|--------|----------|-----------------|
| Prepared demo | Showing finished form; inspiration | Teaching process; technique instruction |
| Live coding — facilitator only | Modeling thought process; showing mistakes | Replacing hands-on practice |
| Participatory live coding | Technique instruction; habit formation | Passive orientation sessions |

Participatory live coding produces superior outcomes vs polished demos for skill acquisition. The instructor making visible mistakes is a feature — it models recovery behavior.

**Five highest-priority tips (Carpentries)**:
1. **Go slowly** — narrate every step; give participants time to catch up
2. **Mirror learner environment** — same IDE, font size, terminal
3. **Stick to prepared material** — avoid improvisation
4. **Embrace mistakes openly** — demonstrate diagnosis and recovery
5. **Real-time feedback** — sticky notes (green = OK, red = help)

---

## Format 8: Code Retreat

**Definition**: Full-day practice event. 5-6 sessions of 45 minutes, always Conway's Game of Life. Code deleted after every session. Pairs rotate. Different constraints each session.

**When to use**: When participants need multiple valid design approaches and delivery pressure must be completely removed. Assumes TDD baseline — not appropriate for beginners.

| Session | Constraint | Purpose |
|---------|-----------|---------|
| 1 | None | Establish baseline |
| 2 | Mute pairing | Communication through code; naming discipline |
| 3 | No return values | Exposes design assumptions |
| 4 | TDD as if you meant it | Makes test-last technically impossible |
| 5 | Find the Loophole | Exposes weak test coverage |
| 6 | No constraints | Integrate learnings |

**Code deletion rule**: Eliminates ego investment and delivery pressure.

---

## Format Selection Quick-Reference

| Learning Objective | Group Size | Time Available | Recommended Format |
|-------------------|------------|----------------|-------------------|
| TDD basics, first exposure | Any | 90 min | Worked example + FizzBuzz pairs |
| TDD practice, some experience | 4-10 | 90-120 min | Dojo Randori with String Calculator |
| TDD mindset shift, constrained | 4-10 | 2+ hours | Completion → independent → TDD-as-if-you-meant-it |
| Collaborative coding habits | 4-7 | 60-90 min | Mob programming |
| Multiple design approaches | TDD-fluent | Full day | Code Retreat |
| Architecture thinking | 12-50 | 2-3 hours | Architecture Katas |
| Legacy code refactoring | 4-10 | 90-120 min | Gilded Rose with mob |
| Team code quality norms | 4-20 | 90 min | Code Smell Scavenger Hunt |
| OO design principles (advanced) | 4-10 | 45 min+ | Object Calisthenics — use constraint-kata approach from Format 1 with nine rules as constraints |

**Contra-Indicators:**
- **Mob programming**: Group > 7, hostile dynamics, one expert dominating navigator role
- **Code Retreat**: TDD novices without baseline red-green-refactor; sessions < full day
- **Katas**: No IDE setup; non-negotiable delivery pressure
- **Randori**: Group > 10; no working shared screen/projector
