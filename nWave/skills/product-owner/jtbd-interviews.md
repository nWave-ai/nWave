---
name: jtbd-interviews
description: JTBD discovery techniques adapted for AI product owner context. Four Forces extraction, job dimension probing, question banks, and anti-patterns for interactive feature discovery conversations.
---

# JTBD Discovery Techniques

Use when conducting interactive discovery conversations to uncover jobs users are trying to accomplish. Adapted from Bob Moesta's Switch interview methodology for AI-guided feature discovery — the user describes their situation, Luna extracts forces and jobs through structured questioning.

## Four Forces Extraction

Map user responses to Four Forces of Progress. Each force has characteristic language patterns to listen for and prompts to surface them.

### Force 1: Push of Current Situation

**User says**: "I'm frustrated that..." | "It keeps breaking when..." | "I waste so much time on..." | "The last straw was when..."

**Prompts**:
- "What's your biggest frustration with how things work now?"
- "Tell me about the worst experience with the current approach."
- "What finally made this intolerable?"
- "What triggered this request — was there a specific incident?"

### Force 2: Pull of New Solution

**User says**: "I want to be able to..." | "I imagine being able to..." | "My colleague said it could..." | "I need it to..."

**Prompts**:
- "What would the ideal outcome look like?"
- "What could you do that you can't do now?"
- "What specific capability excites you most about this?"
- "If this worked perfectly, what would change in your workflow?"

### Force 3: Anxiety of New Solution

**User says**: "I'm worried that..." | "What if it doesn't..." | "I'm not sure I can learn..." | "The risk is..."

**Prompts**:
- "What concerns do you have about this new approach?"
- "What could go wrong that would make you regret this change?"
- "What would need to be true for you to feel safe adopting this?"
- "Is there anything that almost made you not request this?"

### Force 4: Habit of Present

**User says**: "I'm used to..." | "At least with the old way, I know..." | "I've already invested..." | "My team is comfortable with..."

**Prompts**:
- "What do you like about the current approach, despite its problems?"
- "What feels safe or familiar about staying as-is?"
- "What would you have to give up or relearn?"
- "What workaround have you built that actually works well enough?"

## Force Balance Assessment

After extracting forces, assess the balance:

| Balance | Meaning | Action |
|---------|---------|--------|
| Strong Push + Strong Pull | High motivation to switch | Proceed — real demand |
| Strong Pull only | Shiny feature syndrome | Probe for Push — is there real pain? |
| Strong Push + Weak Pull | Pain without clear solution | Explore solution space before committing |
| Strong Anxiety or Habit | Adoption barriers | Address anxiety in design; plan migration path |

**Critical rule**: Stories driven only by Pull without Push are low-priority candidates. Real jobs have real frustrations.

## Job Dimension Probing

### Functional Jobs (surface first)

The practical task the user is trying to accomplish.

**Questions**:
- "What are you trying to get done?"
- "Walk me through the steps you take today."
- "What does 'success' look like in practical terms?"
- "What tools or resources do you use currently?"

### Emotional Jobs (require deeper probing)

How the user wants to feel during and after.

**Questions**:
- "How does the current situation make you feel?"
- "What are you worried about at that point?"
- "When it works (or fails), how does that feel?"
- "What feeling are you trying to avoid?"

### Social Jobs (often unarticulated)

How the user wants to be perceived by others.

**Questions**:
- "Who else is involved or aware of this?"
- "What would your team/manager/stakeholders think?"
- "How does this affect how others see you or your work?"
- "Is there anyone you're trying to impress or reassure?"

## Question Bank: Deepening Techniques

Use these patterns to go deeper when surface-level answers are insufficient.

| Technique | Pattern | When to Use |
|-----------|---------|-------------|
| Timeline probe | "When did you first realize this was a problem?" | User gives vague frustration without specifics |
| Contrast probe | "How is this different from [related thing]?" | User conflates multiple concerns |
| Consequence probe | "What happens if you don't solve this?" | User can't articulate urgency |
| Concrete probe | "Can you give me a specific example?" | User speaks in generalities |
| Inversion probe | "What would make this feature useless to you?" | User gives only positive requirements |
| Scale probe | "How often does this happen? Daily? Weekly?" | User describes pain without magnitude |

## Anti-Patterns

| Anti-Pattern | Problem | Fix |
|--------------|---------|-----|
| Asking hypotheticals | People are poor predictors of future behavior | Ask about past events that already happened |
| Yes/no questions | Shallow data, no insight | Open-ended: "Tell me about a time when..." |
| Leading the witness | Contaminates data | Stay neutral; do not suggest answers or validate |
| Asking about features | Gets wants, not jobs | Ask about struggles and desired progress |
| Rushing to solutions | Misses real job | 80% of interview on problem, 20% on solutions |
| Accepting first answer | Surface-level understanding | Probe deeper: "Can you say more about that?" |
| Projecting emotions | Assumes how user feels | Ask directly: "How did that make you feel?" |
| Skipping social dimension | Misses organizational context | Always ask who else is affected or aware |

## Synthesis Pattern

After extracting forces and dimensions, synthesize into job story format:

```
When [situation/push], I want to [motivation/pull], so I can [outcome/functional+emotional].
```

Validate with user: "Did I capture that correctly?" Refine until the user confirms.

If multiple jobs emerge, note each separately — opportunity scoring (load `jtbd-opportunity-scoring`) determines priority.

## Cross-References

- For core JTBD theory and job story format: load `jtbd-core` skill
- For prioritization using opportunity scoring: load `jtbd-opportunity-scoring` skill
- For translating discoveries to BDD scenarios: load `jtbd-bdd-integration` skill
- For original Switch interview methodology (human-to-human customer research): see Bob Moesta, "Demand-Side Sales 101"
