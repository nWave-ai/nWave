# Journey: /nw:new -- Start a New Feature with Guided Questions

**Version**: 1.0.0
**Date**: 2026-02-21
**Epic**: wizard-commands

## Emotional Arc

```
Confidence
  ^
  |                                              **** CONFIDENT
  |                                         ****      "I'm in the right wave"
  |                                    ****
  |                               ****
  |                          ****  ORIENTED
  |                     ****       "I see my options"
  |                ****
  |           ****  CURIOUS
  |      ****      "This is asking me the right things"
  | ****
  |*  UNCERTAIN
  |   "I have an idea but don't know where to start"
  +-------------------------------------------------> Time
   Invoke       Describe      Classify      Launch
```

## Happy Path Flow

```
+------------------+     +--------------------+     +------------------+
|  1. USER TYPES   |     |  2. DESCRIBE       |     |  3. CLASSIFY     |
|  /nw:new         | --> |  FEATURE           | --> |  FEATURE TYPE    |
|                  |     |                    |     |                  |
|  Feeling:        |     |  Feeling:          |     |  Feeling:        |
|  Uncertain,      |     |  Curious --        |     |  Oriented --     |
|  hopeful         |     |  "it's asking me   |     |  "it knows what  |
|                  |     |   the right Qs"    |     |   kind of work   |
|                  |     |                    |     |   this is"       |
+------------------+     +--------------------+     +------------------+
                                                           |
                                                           v
+------------------+     +--------------------+     +------------------+
|  6. WAVE         |     |  5. CONFIRM &      |     |  4. RECOMMEND    |
|  LAUNCHES        | <-- |  LAUNCH            | <-- |  STARTING WAVE   |
|                  |     |                    |     |                  |
|  Feeling:        |     |  Feeling:          |     |  Feeling:        |
|  Confident --    |     |  Confident --      |     |  Relieved --     |
|  "I didn't have  |     |  "Yes, that's      |     |  "I don't have   |
|   to figure out  |     |   exactly what I   |     |   to pick the    |
|   which command" |     |   want to do"      |     |   command myself" |
+------------------+     +--------------------+     +------------------+
```

## Step-by-Step Interaction

### Step 1: Invoke

```
User types:
> /nw:new

Claude responds:
+-------------------------------------------------------+
|  nWave: New Feature Wizard                             |
|                                                        |
|  Let's get your feature started. I'll ask a few        |
|  questions to figure out the right workflow for you.    |
|                                                        |
|  What do you want to build or improve?                 |
|  (Describe it in a sentence or two)                    |
+-------------------------------------------------------+
```

### Step 2: Describe Feature

```
User types:
> Add rate limiting to the API gateway

Claude responds:
+-------------------------------------------------------+
|  Got it: "Add rate limiting to the API gateway"        |
|                                                        |
|  A few quick questions to find the right starting      |
|  point:                                                |
|                                                        |
|  1. Is this a new feature, or changing existing        |
|     behavior?                                          |
|     > New feature                                      |
|                                                        |
|  2. Does this project already have nWave artifacts     |
|     under docs/feature/?                               |
|     > [auto-detected: No -- greenfield]                |
|                                                        |
|  3. Do you have clear requirements, or do you need     |
|     to explore the problem space first?                |
|     > I have a rough idea but need to flesh it out     |
+-------------------------------------------------------+
```

### Step 3: Classify Feature Type

```
Claude responds:
+-------------------------------------------------------+
|  Based on your answers:                                |
|                                                        |
|  Feature type:  Backend (API/infrastructure)           |
|  Project state: Greenfield (no prior nWave artifacts)  |
|  Readiness:     Needs requirements discovery           |
+-------------------------------------------------------+
```

### Step 4: Recommend Starting Wave

```
Claude responds:
+-------------------------------------------------------+
|  Recommended starting wave: DISCUSS                    |
|                                                        |
|  Why: You have a concept but need to define            |
|  requirements, acceptance criteria, and user stories   |
|  before designing architecture.                        |
|                                                        |
|  This will run: /nw:discuss "rate-limiting"            |
|  with configuration:                                   |
|    - feature_type: Backend                             |
|    - walking_skeleton: Depends (evaluate first)        |
|    - research_depth: Lightweight                       |
|                                                        |
|  After DISCUSS, the next wave will be DESIGN.          |
|                                                        |
|  Want to proceed? [Y/n]                                |
+-------------------------------------------------------+
```

### Step 5: Confirm and Launch

```
User types:
> Y

Claude responds:
+-------------------------------------------------------+
|  Launching DISCUSS wave for "rate-limiting"...         |
|                                                        |
|  Project ID: rate-limiting                             |
|  Output: docs/feature/rate-limiting/discuss/           |
|                                                        |
|  Handing off to @product-owner (Luna)                  |
+-------------------------------------------------------+
```

### Step 6: Wave Launches

The command delegates to `/nw:discuss` with the derived configuration. The user is now inside the DISCUSS wave conversation with Luna.

## Error Paths

### E1: User description is too vague

```
User types:
> /nw:new
> Make things better

Claude responds:
+-------------------------------------------------------+
|  I need a bit more to work with. Can you tell me:     |
|                                                        |
|  - What system or component are you improving?         |
|  - What problem are you solving?                       |
|  - Who benefits from this change?                      |
|                                                        |
|  Example: "Add rate limiting to prevent API abuse"     |
+-------------------------------------------------------+
```

### E2: User wants to skip to a specific wave

```
User types:
> /nw:new
> I already have requirements, just want to design

Claude responds:
+-------------------------------------------------------+
|  If you already have requirements artifacts, you       |
|  might want /nw:continue instead -- it detects your    |
|  current progress and picks up where you left off.     |
|                                                        |
|  Or if you want to jump straight to DESIGN:            |
|  /nw:design "your-feature-name"                        |
|                                                        |
|  Want me to check for existing artifacts first? [Y/n]  |
+-------------------------------------------------------+
```

### E3: Feature name conflicts with existing project

```
Claude responds:
+-------------------------------------------------------+
|  A project "rate-limiting" already exists under        |
|  docs/feature/rate-limiting/ with DISCUSS artifacts.   |
|                                                        |
|  Options:                                              |
|  1. Continue that project (/nw:continue)               |
|  2. Start fresh with a different name                  |
|  3. Archive the old one and start over                 |
|                                                        |
|  Which would you prefer? [1/2/3]                       |
+-------------------------------------------------------+
```

## Shared Artifacts

| Artifact | Source | Consumed By |
|----------|--------|-------------|
| Feature description (string) | User input (Step 2) | Wave command argument |
| Feature type classification | Wizard classification (Step 3) | DISCUSS configuration |
| Project ID (kebab-case) | Derived from description | docs/feature/{project-id}/ path |
| Recommended wave | Wizard logic (Step 4) | Command dispatch |
| Walking skeleton decision | Auto-detection + user input | DISCUSS configuration |
| Research depth | Wizard inference | DISCUSS configuration |
