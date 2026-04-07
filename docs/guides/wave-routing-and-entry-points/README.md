# Wave Routing: Starting in the Right Place

nWave is not a linear pipeline — it's a graph. You don't always start at DISCOVER. You start where your knowledge gap is.

---

## The Wave Graph

```
┌─────────────┐
│  DISCOVER   │  Problem validation
└──────┬──────┘
       │ (if needed)
       ▼
┌─────────────┐
│  DIVERGE    │  Option evaluation
└──────┬──────┘
       │ (if needed)
       ▼
┌─────────────┐
│  DISCUSS    │  User stories
└──────┬──────┘
       │ (if needed)
       ▼
┌─────────────────────────────┐
│  DESIGN                     │  Architecture
│  (3 specialist architects)  │
└──────┬──────────────────────┘
       │ (if needed)
       ▼
┌─────────────┐
│  DEVOPS     │  Infrastructure
└──────┬──────┘
       │ (if needed)
       ▼
   DISTILL ←──┴──┘  Acceptance tests (always)
       │
       ▼
   DELIVER          Implementation (always)
```

**The invariant**: Every feature ends with DISTILL → DELIVER. No exceptions.

**DESIGN wave routing**: `/nw-design` routes to three specialist architects based on your design scope:
- **System-level** (Titan) — distributed patterns, scalability, caching, load balancing
- **Domain-level** (Hera) — DDD, bounded contexts, event modeling, ES/CQRS
- **Application-level** — component boundaries, hexagonal architecture, tech stack, C4

All three can work interactively ("guide me" mode) or autonomously ("propose" mode). All three write to the shared `docs/product/architecture/brief.md` in their own sections.

---

## Entry Point Matrix

Choose your starting point based on what you already know.

| Work Type | Entry | Waves | Example |
|-----------|-------|-------|---------|
| **New product** | DISCOVER | All 7 | "Build a payment processor" — no context exists |
| **Brownfield feature** | DIVERGE | DIVERGE → DISCUSS → DESIGN → DEVOPS → DISTILL → DELIVER | "Add rate limiting to API" — multiple approaches exist |
| **Feature on known journey** | DISCUSS | DISCUSS → DESIGN → DEVOPS → DISTILL → DELIVER | "Add 2FA to login" — login journey already defined |
| **Technical story** | DESIGN | DESIGN → DISTILL → DELIVER | "Refactor auth module" — scope and approach are clear |
| **Refactoring** | DESIGN | DESIGN → DISTILL → DELIVER | "Extract shared logic" — behavior preserved, structure changes |
| **Bug fix (cause known)** | DISTILL | DISTILL → DELIVER | "Auth token expires too early" — fix is obvious |
| **Bug fix (cause unknown)** | DISCOVER | DISCOVER → DISTILL → DELIVER | "Auth randomly fails — root cause TBD" |
| **Infrastructure** | DEVOPS | DEVOPS → DISTILL → DELIVER | "Add Redis caching layer" |

---

## Skip Validation Checklists

Each wave can be skipped **only if all items in its checklist are true**.

### DISCOVER — Skip if ALL true:

- [ ] `docs/product/jobs.yaml` exists and contains a job matching this feature's problem space
- [ ] The matching job has `status: validated` (not `hypothesized`)
- [ ] The matching job has `validated_by` referencing a real DISCOVER feature-id or `founder-input`

**Example**: You're adding a "remember me" checkbox to the login feature. Login is already a validated job in `jobs.yaml`. Skip DISCOVER. Start at DIVERGE or DISCUSS.

### DIVERGE — Skip if ALL true:

- [ ] Feature has a clear direction (backlog item specifies the approach)
- [ ] No competing solution approaches need evaluation
- [ ] `recommendation.md` already exists for this feature, or direction is self-evident (bugfix, refactoring)

**Example**: Bugfix with clear root cause ("Use bcrypt instead of MD5 for password hashing"). The direction is self-evident. Skip DIVERGE. Start at DISCUSS.

### DISCUSS — Skip if ALL true:

- [ ] `docs/product/journeys/{name}.yaml` exists and covers the behavior this feature changes
- [ ] The journey's `changelog` shows an update within the last 6 months (not stale)
- [ ] Existing user-stories already cover this feature's scope

**Example**: Adding a "forgot password" link to the login page. The login journey is current, and "user recovers forgotten password" is already a story. Skip DISCUSS. Start at DESIGN.

### DESIGN — Skip if ALL true:

- [ ] `docs/product/architecture/brief.md` exists and covers the components this feature touches
- [ ] No new component boundaries need to be drawn
- [ ] No new architectural decision is required (no ADR candidate)
- [ ] The "For Acceptance Designer" section lists the driving port this feature will use

**Example**: Changing the password complexity requirement from 8 to 12 characters. No components change. No new decision. Skip DESIGN. Start at DISTILL.

### DEVOPS — Skip if ALL true:

- [ ] `docs/product/kpi-contracts.yaml` exists and has a contract for this feature's observable behavior
- [ ] No new infrastructure or deployment changes needed

**Example**: Adding a new dashboard metric to the monitoring journey. KPI contracts already cover this behavior. Skip DEVOPS. Start at DISTILL.

---

## How to Decide: The Flowchart

Start here. Follow your answers down.

```
Do you have a validated problem statement?
├─ NO  → Run DISCOVER first
├─ YES → Are there multiple solution approaches you need to evaluate?
        ├─ YES → Run DIVERGE next
        ├─ NO  → Is there a journey (user story map) for this area?
                ├─ NOT CURRENT → Run DISCUSS next
                ├─ CURRENT   → Is the architecture defined for the components you'll touch?
                              ├─ NOT DEFINED → Run DESIGN next
                              ├─ DEFINED    → Does infrastructure/monitoring need changes?
                                            ├─ YES → Run DEVOPS next
                                            ├─ NO  → Start at DISTILL
```

---

## Using `/nw-continue`

If you've started a feature and want to resume, use `/nw-continue`:

```
/nw-continue feature-id
```

This command:
1. Reads all your prior wave artifacts
2. Detects which waves have completed
3. Recommends the next wave to run
4. Skips any waves that meet their skip validation checklist
5. Starts you at the right place

Example: You ran DISCUSS and DESIGN. The tool suggests starting at DEVOPS (or skipping straight to DISTILL if infrastructure is already settled).

---

## When You're Wrong

If you skip a wave and later discover you should have run it, you can go back. Re-run the skipped wave. It will read your prior artifacts and adjust as needed.

**Example**: You skipped DIVERGE on a "clear direction," but DISCUSS reveals three competing approaches. Run DIVERGE — it reads your DISCUSS work and produces options grounded in your requirements.

The waves are flexible. The invariant is fixed: **DISTILL → DELIVER is always at the end**.
