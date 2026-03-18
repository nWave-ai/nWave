---
name: nw-assessment-kirkpatrick
agent: nw-workshopper
description: Kirkpatrick New World Model applied to workshop design — assessment checkpoints, behavioral commitment instruments, rubric design, and Level 3 required drivers
disable-model-invocation: true
---

# Assessment and Kirkpatrick Methodology for Workshop Design

## The Core Principle: Design Backwards from Level 4

1. Level 4: What organizational outcome does this workshop serve?
2. Level 3: What behaviors must participants perform on the job?
3. Level 2: What knowledge, skills, attitude, confidence, and commitment are needed?
4. Level 1: What experience will produce that learning while feeling relevant?

Every design decision must connect back to Level 3. If you cannot answer "how does this activity contribute to participants applying skill X at work?", cut it.

---

## The Four Kirkpatrick Levels (New World Model)

### Level 1: Reaction
**Measure**: Relevance, not enjoyment. The only L1 question predicting L3 transfer: "How relevant is this to your most pressing current challenges?"

**Post-workshop questions**:
- "How relevant was this content to your current work?" (1-10)
- "How many opportunities will you have to apply this in the next 30 days?" (1-10)
- "How confident are you that you can apply this?" (1-10)
- NPS: "Would you recommend this to a colleague?" (0-10)

**What NOT to ask**: Satisfaction metrics ("Did you enjoy the presenter?", "Was the room comfortable?") — predict nothing about behavioral transfer.

**30-day follow-up**: "Looking back, how relevant was the workshop to challenges you actually encountered?" Captures true relevance after real-world exposure.

### Level 2: Learning = Knowledge + Skills + Attitude + Confidence + Commitment

| Component | How to assess in-workshop | Failure symptom |
|-----------|--------------------------|-----------------|
| Knowledge | Quiz, recall, explain-it-back | Cannot define/explain |
| Skill | Role play, scenario, demonstration | Knows but can't do |
| Attitude | Discussion, reflection prompt | "That won't work here" |
| Confidence | Self-rating 0-10 | High skill, low confidence |
| Commitment | Written if-then instrument | No specific next action |

**Confidence and Commitment are the bridge to Level 3.** High knowledge + zero confidence = no transfer. High confidence + vague intent = no transfer.

---

## GRASPS Performance Tasks — Level 2 Assessment Design

| Element | Question | IT Workshop Example |
|---------|----------|---------------------|
| **G**oal | What is the participant trying to accomplish? | "Debug a failing Kubernetes NetworkPolicy before escalation window closes" |
| **R**ole | What role does the participant play? | "You are the on-call SRE for a production cluster" |
| **A**udience | Who is the participant performing for? | "Your team lead who needs a root-cause summary within 20 minutes" |
| **S**ituation | What is the context and constraints? | "A pod can't reach the database. You have cluster access and 15 minutes." |
| **P**roduct | What tangible output must be produced? | "A written diagnosis with the exact policy change needed" |
| **S**tandards | How will success be evaluated? | "Correctly identifies selector mismatch; recommends minimal policy change" |

A GRASPS task mirroring real work is simultaneously L2 assessment (during workshop) and L3 predictor (30 days post). Design using actual scenarios from participants' real work.

**GRASPS Validation Checklist:**
- [ ] Situation mirrors a real scenario participants will encounter
- [ ] Product is observable and evaluable (not just "discuss")
- [ ] Standards are explicit enough two facilitators agree on pass/fail
- [ ] Task completable in available time (20-30 min typical)
- [ ] A failing participant can diagnose WHY they failed

---

## Level 3: Behavior

**When to measure**: 30 days (first application window) and 60-90 days (habit formation).

**Follow-up survey**:
- "Have you used [specific skill] in your work since the workshop?" (Yes/No + example)
- "How often per week do you apply this?"
- "What is getting in the way of applying more consistently?"
- "Has your manager created opportunities for you to practice?"

### Level 4: Results
Must be identified **before** the workshop is designed. If you don't know what L4 looks like, you cannot confirm L3 behaviors are the right ones to train for.

---

## The Required Drivers Model (Level 3 Support)

Without required drivers, ~85% of trained content is never applied.

**Support Drivers** (help motivated participants):
- Job aids at point of need (checklists, reference cards)
- Refresher micro-sessions (15-min monthly)
- Peer coaching / accountability pairs
- Manager coaching (not evaluating)

**Accountability Drivers** (enforce application for less-motivated participants):
- Written commitment instruments with named check-in dates
- Manager check-in conversations (30-day, 60-day)
- Performance review criteria referencing trained behaviors
- Peer teaching assignments

**IT context example**: After a Kubernetes security workshop — (1) manager assigns reviewing one production NetworkPolicy per week for 4 weeks; (2) team adopts 'policy-first' deployment checklist item; (3) participants peer-review each other's policy PRs.

**Design rule**: Include at least 2 support + 2 accountability drivers. Support-only produces enthusiasm that fades; accountability-only produces resentment.

---

## 30-Day Behavioral Commitment Instruments

### The If-Then Format
**Evidence**: Gollwitzer & Sheeran meta-analysis (94 studies, d=0.65). If-then plans install automatic behavioral triggers.

```
When [specific situation I will encounter in my work], I will [specific action using today's skill].

Situation: ___________________________
Action: ______________________________
First opportunity: ___________________
My accountability partner: ____________
Check-in date: 30 days from today = ___
```

**Critical Constraints**:
- Specificity beats generality: "When I start a retrospective on Thursday afternoons" beats "when I do retrospectives"
- One or two commitments beats five — participants complete fewer, more specific commitments
- Deploy attitude check before commitment — if attitude is uncertain, address it first
- Public commitment with an accountability partner doubles follow-through vs. private commitment

**Timing**: Deploy 10-15 minutes before session end — after skill practice (L2 Skills) and confidence discussion (L2 Confidence), before formal close.

---

## Formative Assessment Checkpoints

**Observable behavior principle**: Assess only what participants visibly do.

Observable Apply/Analyze indicators:
- Correctly works through a novel scenario
- Identifies what is missing or wrong in a case study
- Explains concept using an example from their own context
- Chooses between two approaches and justifies the choice

**Not observable**: head nodding, attentiveness, "I get it" statements.

### Checkpoint Techniques

**Fist-to-Five** (rapid pulse): 0 = "no idea", 5 = "could teach this". Use as directional gauge — social anchoring means participants wait to see others.

**Thumbs Up/Sideways/Down**: Trigger: if >30% sideways or down, slow down.

**Exit Ticket** (most reliable): Single written prompt requiring Apply level — "Write one example from your current work where you could use [skill] in the next week."

**Scenario Check** (highest signal): 2-3 sentence case; participants write what they would do and why. Observe convergence on correct approach.

### When to Adjust (Trigger Criteria)
- >30% show fist or 1-2 fingers
- Exit tickets restate presented content rather than generate own examples (Understanding, not Apply)
- No participant produces a novel unprompted example
- Correct terminology applied incorrectly (vocabulary, not conceptual understanding)
- Multiple "yes but in my context..." objections — attitude or relevance gap

### Invisible Assessment
- Listen to pair discussion — what language are participants using?
- Observe scenario exercise — who is stuck? Who is confident?
- Ask "walk me through your reasoning" during break

---

## Assessment Rubric Design

Use analytic rubrics (3-4 criteria, 1-4 scale) for role plays, scenario analysis, case study responses. Holistic rubric for quick in-session scoring.

```
Criterion: [Skill being assessed]
4 - Exemplary: [does X with Y quality AND demonstrates Z]
3 - Proficient: [does X accurately without prompting]
2 - Approaching: [does X with minor errors or requires prompting]
1 - Developing: [attempts X but significant errors OR cannot initiate]
```

**Share rubrics before the activity** — participants who know criteria engage at higher cognitive levels from the start.

**Self-assessment instrument**:
```
Using the rubric, rate yourself: ___
Evidence (what you actually did): ___
One thing you would do differently: ___
```

---

## Manager/Stakeholder Briefing Design

**Pre-Training Brief (1 week before)**:
1. What the participant will learn (jargon-free)
2. The 2-3 critical behaviors expected post-training
3. What conditions the manager should create (assign a project using the skill, create 20 min/week for practice)
4. What NOT to do: evaluate performance on new skill within first 2 weeks

**Post-Training Brief (within 3 days)**:
1. What the participant committed to (if-then instrument text)
2. Observable behaviors to look for ("You'll know it's working when Alex does X")
3. 30-day check-in date and 3 coaching questions:
   - "Have you had a chance to try [commitment]? What happened?"
   - "What made it easier or harder than expected?"
   - "What would help you do this more consistently?"

---

## Quick Reference: Level Alignment Table

| Kirkpatrick Level | What to design | What to assess | Timing |
|------------------|----------------|----------------|--------|
| L1 Reaction | Relevance to real challenges | Relevance rating + NPS (not satisfaction) | Immediate post; 30-day repeat |
| L2 Learning | All 5 components: K, S, A, Conf, Commit | Formative checkpoints + commitment instrument | During and end of workshop |
| L3 Behavior | Required drivers: support + accountability | 30-day and 60-90 day behavioral surveys | 30 days and 60-90 days post |
| L4 Results | Identify BEFORE designing; connect to L3 | KPIs established pre-training | Quarterly |

**Design decision checklist** — for every module, answer:
- Learning activity: "Will this develop the specific skill participants need on the job?"
- Assessment: "Am I observing Apply/Analyze level, or just recall?"
- Commitment: "Does the if-then specify the exact situation and exact action?"
- Manager brief: "Does this give them enough to notice and reinforce the critical behaviors?"
