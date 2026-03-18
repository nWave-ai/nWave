---
name: nw-backward-design-ubd
agent: nw-workshopper
description: Backward design using UbD (Understanding by Design) — how to apply the 3-stage framework to every workshop, write transfer goals, design essential questions, and identify/fix coverage-trap designs
disable-model-invocation: true
---

# Backward Design and UbD for Workshop Design

## The Core Discipline

Design backward. Three stages, in order — never skip, never reverse.

**Stage 1: Desired Results** — What must participants independently do after this session?
**Stage 2: Acceptable Evidence** — How will you know they got there, inside the session?
**Stage 3: Learning Plan** — What activities produce that evidence?

Complete Stage 1 fully before Stage 2, and Stage 2 before any activities. The moment you start with an activity, you have entered a twin sin.

---

## Stage 1: The Goal Hierarchy

### Transfer Goal (apex)
What participants will independently do in their real world, without prompting.

Format: "Participants will be able to independently use their learning to [real-world performance verb phrase]."

The word "independently" means: in a novel situation, without a facilitator telling them when and how. This IS the behavioral transfer statement from C-05.

Examples:
- "...to diagnose whether a performance gap is a skill deficit or a motivation deficit before deciding on an intervention."
- "...to design a 90-minute workshop agenda that ties every activity to an observable evidence checkpoint."

### Enduring Understanding
The non-obvious insight that makes transfer possible.

Format: "Participants will understand that [transferable principle as a complete sentence]."

Test: if answerable with one word, it is a topic label, not an enduring understanding. A correctly formed EU contains a verb ("that X causes Y").

Examples:
- "Participants will understand that what feels like a motivation problem is usually a clarity problem about expected behavior."
- "Participants will understand that engaging activities without intellectual purpose produce memorable experiences but no durable learning."

### Essential Question
The open-ended inquiry that surfaces the enduring understanding. Not answered with a fact. Not rhetorical.

Characteristics: open-ended | thought-provoking (generates discussion) | requires justification | recurs throughout the session | points toward the EU.

Announce at session open. Return at midpoint. Close with it explicitly.

### Knowledge and Skills (base)
What participants must acquire to reach the EU and execute the transfer goal. These are learning objectives — they support everything above.

---

## Connecting UbD Stage 1 to Behavioral Change (C-05)

| UbD Field | C-05 Requirement | IT Example |
|-----------|-----------------|------------|
| Enduring Understanding | The "why this changes behavior" | "Debugging is faster when you understand the error surface" |
| Essential Question | Triggers behavioral reflection | "What do you now do differently when a Pod fails to start?" |
| Transfer Goal | **Behavioral transfer statement** | "When a Kubernetes deployment fails in production, participants will check logs before restarting pods" |
| Knowledge/Skills | Supporting knowledge (stepping stones) | "Define Pod lifecycle states" |

**C-05 validation rule**: Every Stage 1 outcome at Apply level or above must have a Transfer Goal in Mager format ([Actor] will [observable behavior] [condition] [criterion]). "Remember" and "Understand" level outcomes are acceptable only as stepping stones.

---

## The Three-Ring Prioritization

- **Inner ring**: The 1-3 insights that must survive the session. Gets maximum time. Every agenda item must support at least one inner-ring understanding.
- **Middle ring**: Facts, processes, frameworks — introduced and practiced, not drilled to mastery in one session.
- **Outer ring**: Context, enrichment. Convert to pre-reading or resource handout. Remove from agenda.

**Diagnostic**: If more than 3 topics in the inner ring for a 90-minute session → coverage trap. If outer ring exceeds 20% of agenda time → cut.

---

## UbD for Workshop Series (C-02)

**Arc-level Stage 1**:
- Enduring Understandings span the full arc
- Essential Questions recur with increasing depth
- Transfer Goal applies at series completion

**Session-level Stage 1**:
- Session outcomes feed the arc Transfer Goal
- Bloom's levels progress across sessions
- GRASPS tasks are session-specific but simulate the same real-world context

**Key constraint**: Session-level "Understand" outcomes are only acceptable if a later session's "Apply" outcome explicitly builds on them. The arc must end at Apply level or higher for every strand.

---

## Stage 2: Evidence Before Activities

### Formative Checkpoint (mid-session)
Low-stakes, non-graded. Options: brief written response, small group synthesis reported out, confidence vote, think-aloud pair share. Design it so you can scan the room in 3 minutes and know whether to adjust.

### Performance Task (end-of-session)
Culminating demonstration that participants have reached the EU and are on the path to transfer.

Useful formats: revised plan/artifact they take back | peer-teaching exchange | case analysis using session framework | commitment card (one behavior change, one date, one accountability partner).

GRASPS design template:
- **Goal**: What challenge does the task pose?
- **Role**: Who is the participant acting as?
- **Audience**: For whom is the output intended?
- **Situation**: In what context does this occur?
- **Product or Performance**: What will they produce?
- **Standards**: By what criteria will success be judged?

*Citation*: Wiggins, G., & McTighe, J. (2005). *Understanding by Design* (Expanded 2nd ed.). ASCD.

---

## Stage 3: WHERETO Sequencing

| Letter | Element | Minimum for 90-min workshop |
|--------|---------|----------------------------|
| **W** | Where are we going? | State transfer goal; name essential question |
| **H** | Hook and hold | Open with provocation: case, data, failure story, challenge question — NOT a learning objectives slide |
| **E** | Equip | Core content, examples, frameworks |
| **R** | Rethink / revise | Mid-session check: "Does your answer to the EQ change after this?" |
| **E** | Evaluate | Performance task or formative checkpoint |
| **T** | Tailor | Choice in application exercise; optional depth path |
| **O** | Organize | Concrete → abstract; surface EU explicitly at close |

**Minimum viable WHERETO (90 min)**: W+H: 10 min | E: 40 min | R: 10 min | E: 20 min | O: 10 min

### WHERETO + 4C Compatibility

| WHERETO Element | 90-min session | 4h session |
|-----------------|---------------|------------|
| W+H (Where/Hook) | 10 min (Connections) | 20 min |
| E (Equip) | 20 min (Concepts) | 45 min |
| R (Rethink) | Built into activities | Explicit reflection |
| E (Evaluate) | Final 5 min (Conclusions) | 15 min |
| T (Tailor) | Activity selection per audience | Multiple tracks |
| O (Organize) | Pre-workshop design | Pre-workshop design |

---

## The Six Facets — What a Single Session Can Deliver

| Facet | Achievable in single session? | Design tactic |
|-------|------------------------------|---------------|
| Explanation | Yes | "In your own words, explain why..." |
| Interpretation | Yes | Case analysis: "What does this situation mean?" |
| Application | Yes (near transfer) | Practice with real job context |
| Perspective | Possible | Structured debate or devil's advocate round |
| Empathy | Possible | Persona exercise, role-play |
| Self-knowledge | Partial | "What assumption did this session challenge?" |

Do not claim far transfer as a session outcome unless you have explicitly designed for abstraction + bridging.

---

## Near vs. Far Transfer

**Near transfer**: Applying to a similar context. Reliable from a single well-designed session.
- Use examples from participants' actual job context
- Have participants draft the specific artifact they will use next week

**Far transfer**: Applying an abstract principle to a structurally different context. Requires explicit design.
- Teach the underlying principle explicitly, not just the procedure
- **Bridging** (Perkins & Salomon): (1) name the principle, (2) generate two contexts where it applies, (3) name failure modes
- Plan follow-up: reflection journal, peer coaching, manager check-in at 30 days
- Document: "This session targets near transfer of [X]. Far transfer of [Y] requires follow-up."

---

## The Twin Sins — Diagnostic and Fix

### Activity Trap
**Test**: For each activity, ask "Which enduring understanding does this build toward, and what evidence will it produce?" Cannot answer = activity is suspect.

**Fix**: Redesign to produce observable evidence, or cut and convert to pre-work.

### Coverage Trap
**Test**: Count distinct topics. If inner ring exceeds 3 topics, or no time for WHERETO stages R and E → coverage trap.

**Fix**: Apply three-ring prioritization. Convert outer-ring content to a "dig deeper" handout. Protect inner ring by cutting until R and E have adequate time.

---

## Quick Reference: Minimum Viable Backward Design

Complete in this order before designing any activities:

```
1. TRANSFER GOAL
   "Participants will be able to independently use their learning to..."

2. ENDURING UNDERSTANDING(S) (max 2-3 per session)
   "Participants will understand that..."

3. ESSENTIAL QUESTION(S) (max 1-2 per session)
   "What open question should every participant have a provisional answer to?"

4. EVIDENCE CHECKPOINTS
   - Formative (mid-session): [observable, low-stakes, 3-minute scan]
   - Performance task (end of session): [GRASPS-designed, traceable to transfer goal]

5. ACTIVITY SEQUENCE (Stage 3 — last)
   Design backward from the performance task.
   Apply WHERETO checklist.
   Apply three-ring test: cut outer ring; protect inner ring.
```

If you start at step 5, you have entered a twin sin. Stop. Return to step 1.
