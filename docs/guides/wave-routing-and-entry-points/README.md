# Wave Routing: Starting in the Right Place

nWave is not a linear pipeline — it's a graph. You don't always start at DISCOVER. You start where your knowledge gap is.

A wave exists to answer a question the Request and the current recorded authority leave open. It is never a file you must produce first. When the Request already states the outcome, the root records the clear product facts itself with `nwdes product` verbs; no product owner turn, Quint model, journey or story file is a prerequisite.

---

## The Wave Graph

```
┌─────────────┐
│  DISCOVER   │  Problem validation
└──────┬──────┘
       │ (only if the problem is in doubt)
       ▼
┌─────────────┐
│  DIVERGE    │  Option evaluation
└──────┬──────┘
       │ (only if approaches compete)
       ▼
┌─────────────┐
│  DISCUSS    │  Product decisions
└──────┬──────┘
       │ (only if a product decision is open)
       ▼
┌─────────────────────────────┐
│  DESIGN                     │  Architecture
│  (specialist architects)    │
└──────┬──────────────────────┘
       │ (only if a technical boundary or decision is open)
       ▼
┌─────────────┐
│  DEVOPS     │  Platform constraints
└──────┬──────┘
       │ (only if a platform constraint is open)
       ▼
   DISTILL          Public oracle
       │
       ▼
   DELIVER          Implementation
```

**The gated-route obligation**: a Request delivered through the gated route (`/nw-deliver`, or `/nw-bugfix` for a defect) always compiles its public oracle (DISTILL) and then implements it (DELIVER). That pair belongs to the route, not to every piece of work. When you explicitly select one wave command or a direct task (a discovery, a design consultation, a spike), only the wave you chose runs.

**DESIGN wave routing**: `/nw-design` picks the specialist architect from the unresolved gap, not from habit:
- **System-level** (`nw-system-designer`) — distributed patterns, scalability, caching, load balancing
- **Domain-level** (`nw-ddd-architect`) — DDD, bounded contexts, event modeling, ES/CQRS
- **Application-level** (`nw-solution-architect`) — component boundaries, hexagonal architecture, reuse, tech stack
- **Platform-level** (`nw-platform-architect`) — deployment, environment, observability, recovery

Each architect records its decisions through `nwdes design` verbs and closes with an outcome and diagnostic. nwdes writes the handoff and renders the architecture brief; no architect edits a shared brief or the handoff by hand.

---

## Entry Point Matrix

Choose your starting point from the question that is still unanswered.

| Work Type | Open question | Entry | Waves that can follow, each only while its question is open | Example |
|-----------|---------------|-------|-------------------------------------------------------------|---------|
| **New product** | Is the problem real? | DISCOVER | DIVERGE, DISCUSS, DESIGN, DEVOPS, then DISTILL → DELIVER | "Build a payment processor" — nothing is validated |
| **Brownfield feature, competing approaches** | Which approach? | DIVERGE | DISCUSS, DESIGN, DEVOPS, then DISTILL → DELIVER | "Add rate limiting to API" — several approaches exist |
| **Feature with an open product decision** | Which scope or trade-off? | DISCUSS | DESIGN, DEVOPS, then DISTILL → DELIVER | "Add notifications" — which events users can mute is undecided |
| **Feature with a stated outcome** | Which component boundary or decision? | DESIGN, or DISTILL when authority already settles it | DEVOPS, then DISTILL → DELIVER | "Add 2FA to login" — the Request states the outcome; the root records it |
| **Technical story / refactoring** | Where do boundaries move? | DESIGN, or DISTILL when scope and approach are clear | DISTILL → DELIVER | "Extract shared logic" — behavior preserved, structure changes |
| **Bug fix (cause known)** | None | DISTILL | DELIVER | "Auth token expires too early" — fix is obvious |
| **Bug fix (cause unknown)** | What is the cause? | DISCOVER | DISTILL → DELIVER | "Auth randomly fails — root cause TBD" |
| **Infrastructure** | Which deployment, environment or recovery constraint? | DEVOPS | DISTILL → DELIVER | "Add Redis caching layer" |

DISTILL → DELIVER in the last column is the gated-route obligation described above.

---

## Skip Questions

Run a wave only while its question is open. Each wave can be skipped **when every answer below is true**. Answer from the Request and the recorded authority you can read; the absence of a file, a status or a timestamp never forces a wave to run.

### DISCOVER — Skip if ALL true:

- [ ] The problem is not in doubt: the Request states it, or recorded product facts already validate it
- [ ] No assumption about users or demand needs testing before work starts

Recorded product facts, for example a validated job in `docs/product/jobs.yaml`, are one way to know this. Having no such job does not make DISCOVER mandatory.

**Example**: You're adding a "remember me" checkbox to the login feature. Nobody doubts that users need to stay signed in. Skip DISCOVER. Start at DIVERGE, DISCUSS or DESIGN, whichever question is open.

### DIVERGE — Skip if ALL true:

- [ ] The direction is clear: the Request or the backlog item names the approach, or it is self-evident (bugfix, refactoring)
- [ ] No competing solution approaches need evaluation

**Example**: Bugfix with clear root cause ("Use bcrypt instead of MD5 for password hashing"). The direction is self-evident. Skip DIVERGE.

### DISCUSS — Skip if ALL true:

- [ ] The Request states the outcome: who benefits and what they can observe
- [ ] No genuine ambiguity, scope question or trade-off needs a product owner
- [ ] The root can record the clear product facts (promises and slices) directly with `nwdes product` verbs

No product owner turn, Quint model, journey file or user-story file is required before skipping. Run DISCUSS only when a real product question remains, and give the product owner that question and the public product evidence.

**Example**: Adding a "forgot password" link to the login page. The Request states the outcome and nothing about scope is in question. The root records the promise. Skip DISCUSS. Start at DESIGN or DISTILL.

### DESIGN — Skip if ALL true:

- [ ] Current design authority already covers the components this feature touches
- [ ] No new component boundary needs to be drawn
- [ ] No new architectural decision is required (no ADR candidate)
- [ ] The driving port this feature will use is already identifiable

**Example**: Changing the password complexity requirement from 8 to 12 characters. No components change. No new decision. Skip the DESIGN consultation. Start at DISTILL.

### DEVOPS — Skip if ALL true:

- [ ] No deployment, environment, recovery or observability constraint affects this Request
- [ ] Any such constraint that exists is already stated in current authority

No platform delta means no DEVOPS. An absent KPI contract file never makes DEVOPS necessary. Run it only for a real constraint; the platform architect records it through `nwdes design` verbs, or hands plain advice to the coordinating solution architect.

**Example**: Adding a field to an existing report. Nothing about deployment, environment, recovery or observability changes. Skip DEVOPS. Start at DISTILL.

---

## How to Decide: The Flowchart

Start here. Follow your answers down.

```
Is the problem in doubt?
├─ YES → Run DISCOVER first
├─ NO  → Do competing solution approaches need evaluation?
        ├─ YES → Run DIVERGE next
        ├─ NO  → Is a product ambiguity, scope question or trade-off still open?
                ├─ YES → Run DISCUSS next
                ├─ NO  → (the root records the stated outcome)
                        Is a technical boundary or architectural decision still open?
                        ├─ YES → Run DESIGN next
                        ├─ NO  → Does a deployment, environment, recovery or observability
                                 constraint affect this Request and remain unstated?
                                ├─ YES → Run DEVOPS next
                                ├─ NO  → Start at DISTILL
```

On the gated route, DISTILL → DELIVER follows.

---

## Resuming a Started Feature

nwdes keeps no workflow state and no next-step cursor, and there is no resume command. To pick up a feature after an interruption, read its recorded state yourself, read-only:

```bash
git worktree list
# open lanes/<feature>/docs/feature/<feature>/handoff.json and its rendered briefs
```

Then:
1. Read the prior wave artifacts and the handoff (the [nw-nwdes skill](../../reference/skills/nw-nwdes.md) explains its records).
2. Detect which waves have completed, using the completion rules in [Wave Directory Structure](../wave-directory-structure/).
3. Ask the skip questions above for the waves that remain, answering from the Request and recorded authority.
4. Start the wave command for the first wave whose question is still open. Its role records results through its own `nwdes` verbs; never edit the handoff or recorded authority by hand. When only the closing pair remains, run `/nw-distill`, then `/nw-deliver`.

Example: You ran DISCUSS and DESIGN. Start at DEVOPS only if a platform constraint is open; otherwise go straight to DISTILL.

---

## When You're Wrong

If you skip a wave and later discover you should have run it, you can go back. Re-run the skipped wave. It will read your prior artifacts and adjust as needed.

**Example**: You skipped DIVERGE on a "clear direction," but a product question reveals three competing approaches. Run DIVERGE — it reads your recorded product work and produces options grounded in your requirements.

The waves are flexible. The gated route's obligation is fixed: **DISTILL → DELIVER closes every gated Request**.
