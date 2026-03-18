---
name: nw-online-facilitation-miro-boards
description: Evidence-based methodology for designing online workshop sessions with correct duration/energy management, Miro board architecture, modality selection criteria, and complete artifact templates
disable-model-invocation: true
agent: nw-workshopper
---

# Online Facilitation and Miro Board Architecture

## Core Principles

1. **Zoom fatigue is mechanistic.** Four independent causes: excessive close-range eye contact, cognitive overload from nonverbal processing, self-monitoring via self-view, physical movement restriction. Each has a specific structural mitigation — design them in.
2. **The 8-second attention span is fabricated.** Design for real humans: meaningful 10-20 minute interactive tasks sustain full engagement.
3. **90 minutes is the upper bound for continuous live online work.** Structure all sessions around this constraint.
4. **Hybrid systematically disadvantages remote participants.** Avoid hybrid when equity of contribution matters.

---

## Zoom Fatigue — Structural Mitigations

| Cause | Mitigation | How to Build In |
|-------|-----------|----------------|
| Close-face eye contact | Reduce screen size | Pre-briefing: "Resize Zoom to 1/3 of screen" |
| Cognitive nonverbal load | Camera-off periods | Specify "cameras optional" during individual work |
| Self-view anxiety | Hide self-view | Pre-briefing: "Right-click your video, Hide Myself" |
| Movement restriction | Audio-only options | Permit phone audio during non-visual segments |
| Cumulative exposure | Break cadence | Mandatory 10-min break every 60-90 min; away from screen |

**Camera policy**: Cameras-on for social activities (check-ins, discussion, icebreakers); optional for individual work. State this policy explicitly at session open.

---

## Session Duration and Energy Architecture

### Optimal Structure for a 4-Hour Online Workshop

```
Opening              15 min  — welcome, ground rules, Miro orientation
Block 1              90 min  — 3-4 activities, max 20-25 min each
Break                20 min  — AWAY FROM SCREEN (state this explicitly)
Block 2              80 min  — 3-4 activities, max 20-25 min each
Close                15 min  — synthesis, commitments, next steps
Total               220 min (~3h 40min + 20min break = 4h)
```

### Attention Energy Curve

- **Minutes 0-15**: Orientation / low cognitive demand
- **Minutes 15-60**: Peak attention — place highest-stakes activities here
- **Minutes 60-90**: Attention dips — use collaborative formats that distribute cognitive load
- **Post-break**: Second peak — good for synthesis, prioritization, commitments
- **Final 20 min**: Cognitive fatigue high — close, not new content

### Activity Sizing Heuristics

| Activity Type | Duration | Notes |
|--------------|----------|-------|
| Icebreaker / check-in | 5-10 min | First 15 min of session |
| Individual reflection | 5-8 min | Silent heads-down; camera optional |
| Pair discussion | 8-15 min | Both must contribute |
| Breakout group (3-4) | 10-20 min | Complex tasks need 15+ min |
| Full-group share-out | 10-15 min | 2-3 min per group; structured round-robin |
| Plenary facilitated discussion | 15-25 min | Needs strong facilitation to prevent dominance |
| Prioritization / dot voting | 5-10 min | Silent synchronous; Miro voting tools |

### Break Design

Breaks restore directed attention only when they provide genuine disengagement. State explicitly: "Step away from your screen. Walk, stretch, look out a window. No checking email."

Re-energizer at block transitions (not replacing breaks): 2-minute stretch with instruction, brief creative prompt, or music-based transition during board reset.

---

## Breakout Room Best Practices

**Optimal group size**: 3-4 participants. Pairs guarantee both engage — use for sensitive topics. Groups of 5+ risk non-participation.

| Group Size | Minimum Time | Best Use |
|-----------|-------------|---------|
| 2 (pair) | 8 min | Reflection, peer coaching, sensitive topics |
| 3 (triad) | 10 min | Balanced diversity, structured critique |
| 4 (quad) | 12 min | Ideation, prioritization, team exercises |
| 5-6 | 15 min | Use only when diversity of perspectives required |

**Pre-briefing**: Assign explicit roles (facilitator, timekeeper, note-taker) before sending groups. State the exact task. Display the task in the Miro frame for reference. Check in at the midpoint.

**Post-breakout**: Each group shares one key insight (2 minutes max). Park excess content in a dedicated Miro frame.

---

## Miro Board Architecture

### Structural Patterns — Choose One Per Workshop

| Pattern | Use When |
|---------|---------|
| Linear | Single cohort, sequential flow — frames left-to-right |
| Cascading Linear | Same as linear but visually chunked with bold connectors |
| Day-by-Day Agenda | Multi-day programs — each row = one day |
| Swim Lanes | Parallel workstreams or groups |
| Workshop Table | Complex navigation with many activity types |

For most learning workshops: **Linear** for single-day, **Day-by-Day** for multi-day.

### Frame Design Rules

1. **Consistent frame sizing** throughout the entire board.
2. **24pt font** baseline body text; 36-48pt headers; 16-18pt annotations.
3. **Design at 100% zoom**; view full frame at 20-25% zoom. Content legible at 25% = well-sized.
4. **"Start Here" frame** mandatory — session goals, how to use Miro, facilitator bios, timezone reference.
5. **Parking Lot frame** always present — off to the side, clearly labeled.

### Frame Layout Per Activity

```
┌─────────────────────────────────────────────┐
│ ACTIVITY TITLE (large header, color-coded)  │
│ Instructions: What / How / How long         │
├─────────────────────────────────────────────┤
│ Working Area                                │
│ (sticky note zones, templates, canvases)    │
├─────────────────────────────────────────────┤
│ [Facilitator notes — hidden frame, separate]│
└─────────────────────────────────────────────┘
```

### Breakout Group Frame Sizing

Base unit: A4 equivalent = ~960x1360 pixels

| Group Size | Frame Width | Note |
|-----------|-------------|------|
| Individual | 960px | One A4 column |
| Pair | 1920px | 2x A4 width |
| Triad | 2880px | 3x A4 width |
| Quad | 3840px | 4x A4 width |
| Full group (8-12) | 6000-8000px | Use sticky columns |

**Critical rule**: All breakout frames for the same group size must be identical dimensions.

**Mixed-modality rule**: When an activity has individual work then group synthesis, size to the largest group phase — not the individual section. Four individuals synthesizing together need a quad-width frame (3840px), not four individual frames.

| Activity structure | Frame sizing basis |
|-------------------|--------------------|
| Pure individual work | Per-person: 960px × number of participants |
| Breakout group only | Group dimension (see table) |
| Individual → group synthesis | Group dimension (largest phase drives size) |
| Full-group plenary with individual input columns | 6000-8000px; labeled participant columns |

### Color Zone Semantics

| Color | Zone Purpose |
|-------|-------------|
| Blue / teal header | Information / content — presentation frames, reference |
| Yellow / amber header | Active collaboration — brainstorm, ideation, sticky notes |
| Green header | Breakout groups — group work frames |
| Purple / violet header | Opening / closing rituals — check-ins, commitments |
| Grey / neutral | Support areas — parking lot, instructions, notes |
| Red / orange accent | Energy / attention — timers, call-to-action |

Limit palette to 3-5 colors. Color-code frame headers, not entire frames — backgrounds remain white/light.

### 4C Workshop Structure — Zone Mapping

| Phase | Time Proportion | Frame Color | Key Miro Features |
|-------|----------------|-------------|-------------------|
| C1 — Connections | 10-15% | Purple/violet | Private Mode (prevent anchoring), per-person sticky colors |
| C2 — Concepts | 15-25% | Blue/teal | Hide/Reveal (reveal each chunk on cue), Presentation Mode |
| C3 — Concrete Practice | 50-60% | Green (breakout) / Yellow (synthesis) | Zoom Breakout Rooms synced with Miro frames; voting dots |
| C4 — Conclusions | 10-15% | Purple/violet (mirrors C1) | Individual sticky columns, "Exit Ticket" template |

**Board real estate rule**: C3 should occupy 40-60% of total frame count. A 90-minute board: 1 C1 + 1-2 C2 + 3-5 C3 + 1 C4.

**Non-linear sequencing**: The 4C model supports micro-cycles — 10 min C2 chunk immediately followed by 10 min C3 practice, repeated 3-4 times, rather than one large C2 block then one large C3 block.

### Facilitator-Only Content — Hide/Reveal

- **Hide/Reveal Frames** (board owner and co-owner only): hidden frames invisible to participants until deliberately revealed. Assign co-owner role to co-facilitators.
- **Private Mode**: hides all sticky note text from other participants during independent ideation; prevents anchoring. End private mode to reveal all notes simultaneously.
- **Visual Notes Pane**: unreliable for confidential content — may open automatically for others. Prefer hidden frames.

### Board Build Time Estimates

| Workshop Type | Experienced | First-time |
|--------------|-------------|------------|
| 2-hour, template-based | 2-3 hours | 5-7 hours |
| 4-hour, template-based | 4-6 hours | 10-14 hours |
| 4-hour, from scratch | 8-12 hours | 16-24 hours |
| Multi-day (6+ hours) | 12-20 hours | 30+ hours |

Build a template library. First build costs most; second use of a template costs ~30% of original.

---

## Series Board Architecture

For programs with multiple sessions, use one-board-per-session organized in a Miro Space, with a Series Index Board as navigation hub.

| Approach | Use When |
|----------|---------|
| One board per session + INDEX | 4+ sessions; participants new to Miro |
| Consolidated multi-session board | 2-3 sessions; participants experienced with Miro |

### Naming Convention

```
[ProgramCode] S[NN] — [Topic Short Title]
```

Example: `AGILE101 S01 — Foundations and Team Agreements`

Rules: Program code first. Session number zero-padded (S01, S02). INDEX board uses same prefix.

### Miro Space Structure

```
Space: [Program Name] — [Cohort Identifier]
  Section: Navigation
    Board: [CODE] INDEX — Program Navigation Hub
  Section: Module 1 — [Module Name]
    Board: [CODE] S01 — [Topic]
    Board: [CODE] S02 — [Topic]
```

Create Sections in intended display order — Sections cannot currently be reordered through the standard UI.

### Series Index Board — Required Elements

1. Program header: name, cohort dates, facilitator names
2. Visual progress map: all sessions as linked cards; completed sessions marked "Complete"; current session highlighted
3. Participant roster with dot-voting attendance tracker (one column per session)
4. "How to use Miro" reference frame
5. Next session details: date, time, Zoom link — updated before each session

### Per-Session Board Structure

Every session board after Session 1 must begin with a **"Previous Session Summary" frame**:

```
┌──────────────────────────────────────────────────────────────────┐
│  PREVIOUS SESSION: [Title of S[NN-1]]                            │
│  [3-5 key takeaways — pre-populated by facilitator]             │
│                                                                  │
│  [Prompt sticky area]: "One thing I remember from last session:" │
│                                                                  │
│  [Back to INDEX] button    [View S[NN-1] Board] button          │
└──────────────────────────────────────────────────────────────────┘
```

Include a persistent navigation strip: `[Home: INDEX Board] | Session N of M | [← Previous] | [Next →]`

### Template Duplication — Critical Rule

Use **"Link to"** (not "Insert link") for internal cross-frame navigation — these links survive duplication. External links always reference the original board after duplication — update them manually immediately after duplicating.

### Archive Convention

At session close: export PDF → attach to INDEX board → add "Session Complete — [date]" banner frame (locked). Participants retain PDF; no ongoing Miro access needed.

---

## Modality Selection

**Choose pure online when**: participants are geographically distributed; session under 4 hours; equity of contribution required; cost and access matter.

**Choose pure in-person when**: activities require physical co-presence; trust-building is primary purpose; full-day or multi-day immersive format.

**Choose hybrid only when**: organizational constraints make pure formats impossible AND you have dual facilitators AND all participants have individual devices AND "virtual-first" design applies throughout.

**Avoid hybrid when**: equity of contribution is critical or you lack a dedicated online facilitator.

### Hybrid Minimum Requirements

1. Dual facilitators: one in-room, one dedicated online
2. Individual devices for all in-room participants
3. Virtual-first agenda: online participants speak first each round
4. Digital-first documentation: all outputs on Miro, not physical boards
5. Explicit session transition management for remote attendees

---

## Workshop Artifact Templates

### Participant Agenda (Public)

```
[Workshop Name] — [Date] — [Duration]
Purpose: [One sentence]
What you'll walk away with: [3 bullets]

Time    Block           Purpose
00:00   Welcome         Orient, connect, ground rules
00:15   [Activity 1]    [Why this matters]
...
02:20   Commitments     What will you do differently?
02:40   Close
```

### Commitment Device (Post-Workshop)

```
My commitment from today:

Current state:    [What's true now]
Desired state:    [What I want to be true]
First action:     [Specific, observable, by DATE]
Accountability:   [Name of person I will tell]
```

### Post-Workshop Follow-Up Sequence

| Timing | Artifact | Purpose |
|--------|---------|---------|
| Day 1 | Summary + commitment recap | Reinforce + document |
| Day 3 | "You committed to X. What's one small action you've taken?" | Activate retrieval |
| Day 7 | Case study or example in practice | Contextual reinforcement |
| Day 14 | Peer check-in invitation | Social accountability |
| Day 28 | "One month ago you committed to X. What's changed?" | Transfer assessment |

---

## Common Failure Modes and Fixes

| Failure Mode | Symptom | Fix |
|-------------|---------|-----|
| Zoom fatigue baked in | Continuous video, no breaks, self-view on | Build mitigations structurally (see table above) |
| Activity bloat | Every activity runs 30% over time | Set timers on Miro; have explicit cut points in guide |
| Hybrid inequity | Remote participants stop contributing | Assign online facilitator; virtual-first speaking order |
| Navigation confusion | Participants lost on Miro board | Add "Start Here" frame; use facilitator "Follow Me" |
| Breakout groups stall | Groups return with nothing | Assign roles + post exact task on frame before sending |
| Engagement loss after break | People don't return | Re-energizer on return; pair check-in |
| Content reveal spoils anticipation | Participants read ahead | Use Hide/Reveal frames for staged content |
| Facilitator note leak | Private notes visible to participants | Use hidden frames (owner/co-owner only) |
