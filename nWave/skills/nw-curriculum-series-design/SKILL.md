---
name: nw-curriculum-series-design
description: Arc-level curriculum design for multi-session workshop series — spiral curriculum, Bloom's progression across 6- and 12-session arcs, session opening/closing rituals, between-session transfer with spaced/interleaved practice, LARS assignment templates, and series-level capstone assessment models
disable-model-invocation: true
agent: nw-workshopper
---

---
## North Star: The Arc Is an Architectural Structure

**C-02 Constraint**: This skill activates when a user specifies series mode — N sessions × D duration. A multi-session program is NOT a collection of independent sessions. It is an architecturally coherent structure where every session opening, every between-session activity, and every session closing serves the arc-level outcome.

**Design the arc before designing the sessions.**

---

# Curriculum and Series Design — Practitioner Reference

## When to Activate

Activate when the user specifies **series mode** (C-02): 2 or more sessions with defined duration per session.

- "6 sessions, 4 hours each"
- "12 workshops over 3 months"
- Any mention of multiple sessions, cohorts, or a recurring program

For single-session design, this skill is dormant. Session-level facilitation is owned by `tbr-methodology.md` and `pedagogy-bloom-andragogy.md`.

---

## Scope Boundary

| Concern | Owned By |
|---------|----------|
| Within-session 4C structure | tbr-methodology.md |
| Individual activity facilitation | pedagogy-bloom-andragogy.md |
| Arc-level Bloom's progression | This skill |
| Between-session spacing | This skill |
| Session-count/duration planning (C-02) | This skill |
| Arc-level learning outcomes | This skill |

---

## Part 1: Spiral Curriculum

Three principles define the spiral (Bruner, 1960):

1. **Revisitation** — same topics recur across sessions; no topic is taught once and set aside
2. **Increasing Complexity** — each revisit presents greater sophistication: more nuanced, more interconnected, more abstractly framed
3. **Contextual Connection** — each revisit explicitly builds on prior encounters

**Applied**: A 6-session Kubernetes networking series does not cover Pod networking in Session 1 and drop it. It introduces Pod networking (Understand → Session 1), applies it in a lab (Apply → Session 2), uses it to analyze Service routing failures (Analyze → Session 3), and integrates it into a full network policy design (Evaluate/Create → Session 5).

### Identifying Big Ideas — UbD Enduring Understanding Filter

| Ring | Content Type | Spiral? |
|------|-------------|---------|
| Ring 1 (largest) | Worth being familiar with — background context | No |
| Ring 2 | Important to know and do — key skills | Sometimes |
| Ring 3 (smallest) | Enduring understandings — big ideas recalled in 5 years | Yes |

Reserve spiral treatment for the **3–5 Ring 3 concepts** central to the program's enduring understanding. In IT security: "defense in depth" and "trust is never implicit."

**Essential questions** make enduring understandings operational — open, generative questions that recur across the series and are never fully answered in one session. Example: "When is eventual consistency acceptable?" recurs at Apply (Session 2), Analyze (Session 4), Evaluate (Session 6).

---

## Part 2: Bloom's Arc Design

### The Spiral-Taxonomy Map

Bloom's distributes across the arc as a spiral — dominant level ascends; new sub-topics are still introduced at Remember/Understand each session.

**6-Session Arc**:

| Session | Dominant Bloom's Levels | What Changes |
|---------|------------------------|--------------|
| 1 | Remember + Understand | Introduce big ideas; build mental models |
| 2 | Understand + Apply | First application; retrieve Session 1 at start |
| 3 | Apply + Analyze | Deeper practice; analysis of failure; retrieve Sessions 1–2 |
| 4 | Analyze + Evaluate | Comparative judgment; debugging; retrieve Sessions 1–3 |
| 5 | Evaluate + Create | Design decisions; original artifact; retrieve Sessions 1–4 |
| 6 | Create + (all levels) | Capstone integration; all prior knowledge in novel context |

**Critical caveat**: Dominant level is not exclusive. Each session still introduces new sub-topics at Remember/Understand.

**12-Session Arc** (same spiral, stretched):

| Sessions | Dominant Bloom's Levels |
|----------|------------------------|
| 1–3 | Remember + Understand |
| 4–6 | Understand + Apply |
| 7–9 | Apply + Analyze |
| 10–11 | Analyze + Evaluate |
| 12 | Evaluate + Create (capstone) |

### Scope and Sequence Chart

Primary arc design artifact — produced before session-level planning.

- **Columns** = sessions (1 through N)
- **Rows** = topics/concepts
- **Cells** = Bloom's level at which the topic appears
- **Color-code**: Introduction (I) / Development (D) / Mastery (M)

Prerequisite violations are immediately visible: Topic B in session N with Topic A not yet introduced.

### Arc-Level vs. Session-Level Outcome Hierarchy

```
Arc-level outcome (1 per program)
    → Session-level outcomes (1–3 per session)
        → Activity-level objectives (within each session)
```

**Design sequence (backward)**:
1. Define the arc-level outcome (Evaluate or Create level Bloom's verb)
2. Design the capstone first
3. Identify which session outcomes are non-negotiable to make the capstone possible
4. Map topics to sessions with Bloom's levels
5. Then design individual sessions

**Rule**: Sessions cannot be designed without knowing which arc-level outcome they serve.

---

## Part 3: Session Openings — Retrieval Bridge

Every session must open with explicit retrieval reconnecting learners to prior content. Without this, the spacing between sessions does not produce retention benefit (Bjork desirable difficulty principle).

The C1 Connections phase is the canonical slot. In Session N, C1 asks: "What do you remember from last session, and how does today's topic extend that?"

### Five Retrieval Bridge Techniques

| Technique | Description | Best For |
|-----------|-------------|----------|
| Retrieval quiz | 3–5 low-stakes questions on prior session key concepts (not graded) | Factual/conceptual content |
| "What stuck?" round | Each participant shares one thing still remembered from last session | Any series, session 2+ |
| Running concept map | Participants add to the concept map built in prior sessions | Interconnected conceptual content |
| Artifact debrief | Participants share the between-session application artifact (LARS model) | Practice-heavy programs |
| Essential question revisit | Repose the arc-level essential question with "how does last week change your answer?" | Programs with enduring understandings |

**Rule**: The retrieval opening is not optional. It is the mechanism that activates the spacing benefit.

---

## Part 4: Session Closings — Preview Seed

Every session close includes three elements (within C4 Conclusions, final 5 minutes):

1. **Commitment articulation** — participants write a specific between-session application commitment
2. **Accountability partner** — they share their commitment with one other participant
3. **Preview seed** — facilitator previews the next session with a teaser question

**Example**: "Next time we'll find out why the networking pattern you just practiced breaks in this specific production scenario — bring your diagram."

**Note**: The Zeigarnik mechanism attribution (uncompleted tasks retained better) is commonly cited as the psychological basis but was not independently verified. The technique itself is well-supported as practitioner best practice.

---

## Part 5: Between-Session Transfer

### Spacing Formula

Optimal inter-session gap (Cepeda et al., 2008): approximately 20% of the desired retention period.

| Retention Goal | Optimal Inter-Session Gap |
|---------------|--------------------------|
| 4 weeks post-series | 5–8 days (weekly cadence) |
| 8–12 weeks post-series | 1–2 weeks (bi-weekly cadence) |
| 6 months post-series | 2–4 weeks apart |

**Program format guidance**: 6×4h targeting 4–8 weeks retention → weekly/bi-weekly. 12×2h targeting longer retention → bi-weekly.

### Interleaving Across Sessions

| Practice Type | Use When | Sessions |
|--------------|----------|---------|
| Blocked (one concept at a time) | Genuinely novel concepts, first encounter | Sessions 1–2 |
| Interleaved (mixing prior concepts) | Concepts available for mixing; discrimination skills needed | Sessions 3+ |

**Interleaved task example**: "Apply the Service routing pattern from Session 2, then revisit your Pod networking diagram from Session 1 and identify one thing you would change now."

### LARS Assignment Template (Columbia Teachers College)

| Phase | When | What |
|-------|------|------|
| **L — Learning** | Session N | Introduce concept with active engagement |
| **A — Application** | Between sessions | Participant implements in their own context, produces artifact |
| **R — Reflection** | Session N+1 opening | Written reflection on what they tried, what happened |
| **S — Sharing** | Session N+1 | Small-group sharing of artifacts |

**Key principle**: The between-session application is not homework — it is the real learning.

**LARS task quality criteria**:
- (a) requires retrieval of session content (not passive review)
- (b) applies in the learner's real work context
- (c) produces a concrete artifact to bring back
- (d) scoped for available time (not more than 1–2 hours for weekly cadence)

**LARS task template**:
```
This week:
1. [Retrieve and apply the specific technique from today's session] in [your real context].
2. [Produce a specific artifact: diagram / screenshot / written reflection / annotated code].
3. Write 2–3 sentences: "What I tried" and "What surprised me."
4. Bring the artifact to Session [N+1] — you will share it in a small group.
```

---

## Part 6: Series-Level Assessment — Capstone Models

A capstone requires participants to "integrate and apply previous knowledge rather than acquire new skills."

**Design rule**: Specify the capstone before designing sessions (backward design). The capstone task determines which session outcomes are non-negotiable.

### Four Capstone Models

| Model | Description | Best For |
|-------|-------------|----------|
| **Magnet** | Compiled portfolio of strongest artifacts from across the program | Any series |
| **Mandate** | Evidence aligned to external professional standards or certification competencies | Programs mapped to industry standards (CKA, AWS) |
| **Mirror** | Reflective review of growth arc; participant analyzes own development from Session 1 to N | Leadership, soft-skills, coaching programs |
| **Mountaintop** | Interdisciplinary collaboration across tracks; participants from different specializations solve a shared challenge | Multi-track IT programs |

### Capstone Design Principles

1. Task cannot be solved using only the final session's content — must synthesize cumulatively
2. Apply learning in a novel context — not a repeat of any session exercise
3. Work independently (or in small groups) — no facilitator scaffolding
4. Present results to an audience — real or simulated stakeholder
5. Evaluation criteria are explicit and externally referential

### Placement

- **6-session arc**: Session 6 or post-series deliverable within 1–2 weeks
- **12-session arc**: Session 12, or final 2 sessions dedicated to capstone work and presentation

---

## Quick Reference: Series Design Checklist

### Arc-Level (Before Session Planning)

- [ ] Define the ONE arc-level outcome (Bloom's Evaluate or Create level)
- [ ] Identify 3–5 enduring understandings (Ring 3 UbD filter)
- [ ] Write 1–3 essential questions that recur across all sessions
- [ ] Design the capstone (Magnet / Mandate / Mirror / Mountaintop?)
- [ ] Confirm capstone requires integration of all prior learning
- [ ] Build the scope and sequence chart (sessions × topics × Bloom's levels)
- [ ] Verify prerequisite ordering
- [ ] Select inter-session cadence based on retention goal

### Per-Session Design

- [ ] C1 Connections = retrieval bridge opening (technique from Part 3)
- [ ] C3 Concrete Practice includes at least one spiral revisit of a prior-session concept
- [ ] C4 Conclusions = commitment + accountability partner + preview seed
- [ ] Between-session LARS task: retrieval + real context application + artifact + 1–2h scope

**Evidence**: Spiral curriculum (Bruner 1960); UbD three-ring filter (Wiggins & McTighe); Cepeda 20% spacing rule; LARS model (Columbia CPET); Capstone models (University of Hawaii). All High confidence.
