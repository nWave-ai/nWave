# Journey: /nw:continue -- Detect Progress and Resume

**Version**: 1.0.0
**Date**: 2026-02-21
**Epic**: wizard-commands

## Emotional Arc

```
Confidence
  ^
  |                                         **** RELIEVED
  |                                    ****      "I'm right back where I was"
  |                               ****
  |                          ****  RECOGNIZED
  |                     ****       "It found my work"
  |                ****
  |           ****  HOPEFUL
  |      ****      "Let's see if it remembers"
  | ****
  |*  DISORIENTED
  |   "Where was I yesterday?"
  +-------------------------------------------------> Time
   Invoke       Scan        Show Status    Resume
```

## Happy Path Flow

```
+------------------+     +--------------------+     +------------------+
|  1. USER TYPES   |     |  2. SCAN FOR       |     |  3. SHOW         |
|  /nw:continue    | --> |  FEATURE STATE     | --> |  STATUS          |
|                  |     |                    |     |                  |
|  Feeling:        |     |  Feeling:          |     |  Feeling:        |
|  Disoriented --  |     |  Hopeful --        |     |  Recognized --   |
|  "I was working  |     |  scanning happens  |     |  "it found my    |
|   on something   |     |  automatically     |     |   project and    |
|   yesterday"     |     |                    |     |   knows where    |
|                  |     |                    |     |   I am"          |
+------------------+     +--------------------+     +------------------+
                                                           |
                                                           v
                          +--------------------+     +------------------+
                          |  5. WAVE           |     |  4. CONFIRM &    |
                          |  RESUMES           | <-- |  LAUNCH          |
                          |                    |     |                  |
                          |  Feeling:          |     |  Feeling:        |
                          |  Relieved --       |     |  Relieved --     |
                          |  "seamless pickup, |     |  "yes, that's    |
                          |   zero friction"   |     |   exactly where  |
                          |                    |     |   I left off"    |
                          +--------------------+     +------------------+
```

## Step-by-Step Interaction

### Step 1: Invoke

```
User types:
> /nw:continue
```

### Step 2: Scan for Feature State

The command scans `docs/feature/` for project directories and checks which wave artifacts exist.

**Wave detection rules** (artifact presence determines completed waves):

| Wave | Artifacts That Indicate Completion |
|------|-----------------------------------|
| DISCOVER | `docs/discovery/problem-validation.md`, `lean-canvas.md` |
| DISCUSS | `docs/feature/{id}/discuss/requirements.md`, `user-stories.md` |
| DESIGN | `docs/feature/{id}/design/architecture-design.md` |
| DEVOP | `docs/feature/{id}/deliver/platform-architecture.md` |
| DISTILL | `tests/**/walking-skeleton.feature` or `docs/feature/{id}/distill/test-scenarios.md` |
| DELIVER | `docs/feature/{id}/execution-log.yaml` with all steps COMMIT/PASS |

### Step 3: Show Status

#### 3a: Single project found

```
+-------------------------------------------------------+
|  nWave: Continue Feature                               |
|                                                        |
|  Found project: rate-limiting                          |
|                                                        |
|  Wave Progress:                                        |
|  [##########] DISCOVER  -- complete                    |
|  [##########] DISCUSS   -- complete                    |
|  [######    ] DESIGN    -- in progress                 |
|               (architecture-design.md exists,          |
|                no ADRs yet)                             |
|  [          ] DEVOP     -- not started                 |
|  [          ] DISTILL   -- not started                 |
|  [          ] DELIVER   -- not started                 |
|                                                        |
|  Recommended: Resume DESIGN wave                       |
|  This will run: /nw:design rate-limiting               |
|                                                        |
|  Want to continue? [Y/n]                               |
+-------------------------------------------------------+
```

#### 3b: Multiple projects found

```
+-------------------------------------------------------+
|  nWave: Continue Feature                               |
|                                                        |
|  Found 2 active projects:                              |
|                                                        |
|  1. rate-limiting                                      |
|     Last wave: DESIGN (in progress)                    |
|     Last modified: 2026-02-20                          |
|                                                        |
|  2. user-notifications                                 |
|     Last wave: DISCUSS (complete)                      |
|     Last modified: 2026-02-18                          |
|                                                        |
|  Which project? [1/2]                                  |
+-------------------------------------------------------+
```

#### 3c: No projects found

```
+-------------------------------------------------------+
|  nWave: Continue Feature                               |
|                                                        |
|  No active projects found under docs/feature/.         |
|                                                        |
|  To start a new feature, use: /nw:new                  |
+-------------------------------------------------------+
```

#### 3d: DELIVER wave -- partial execution

```
+-------------------------------------------------------+
|  nWave: Continue Feature                               |
|                                                        |
|  Found project: rate-limiting                          |
|                                                        |
|  Wave Progress:                                        |
|  [##########] DISCOVER  -- complete                    |
|  [##########] DISCUSS   -- complete                    |
|  [##########] DESIGN    -- complete                    |
|  [##########] DEVOP     -- complete                    |
|  [##########] DISTILL   -- complete                    |
|  [######    ] DELIVER   -- in progress                 |
|               Steps 01-01 through 02-01 complete       |
|               Next step: 02-02                         |
|               (.develop-progress.json found)           |
|                                                        |
|  Recommended: Resume DELIVER wave                      |
|  This will run: /nw:deliver "rate-limiting"            |
|  (auto-resumes from step 02-02)                        |
|                                                        |
|  Want to continue? [Y/n]                               |
+-------------------------------------------------------+
```

### Step 4: Confirm and Launch

```
User types:
> Y

Claude responds:
+-------------------------------------------------------+
|  Resuming DESIGN wave for "rate-limiting"...           |
|                                                        |
|  Handing off to @solution-architect (Morgan)           |
+-------------------------------------------------------+
```

### Step 5: Wave Resumes

The command delegates to the appropriate `/nw:{wave}` command. For DELIVER, the existing resume logic in deliver.md handles picking up from `.develop-progress.json`.

## Error Paths

### E1: Ambiguous state -- artifacts from non-adjacent waves

```
+-------------------------------------------------------+
|  Warning: Project "rate-limiting" has artifacts for    |
|  DISCUSS and DELIVER but skipped DESIGN and DISTILL.   |
|                                                        |
|  This may indicate manual wave execution or            |
|  incomplete previous work.                             |
|                                                        |
|  Options:                                              |
|  1. Resume from DESIGN (fill the gap)                  |
|  2. Continue DELIVER (accept current state)            |
|  3. Show all artifacts for manual review               |
|                                                        |
|  Which would you prefer? [1/2/3]                       |
+-------------------------------------------------------+
```

### E2: Corrupted or incomplete artifacts

```
+-------------------------------------------------------+
|  Project "rate-limiting" has a DISCUSS directory but   |
|  requirements.md is empty (0 bytes).                   |
|                                                        |
|  Recommendation: Re-run DISCUSS wave to regenerate     |
|  requirements.                                         |
|                                                        |
|  This will run: /nw:discuss "rate-limiting"            |
|  Want to proceed? [Y/n]                                |
+-------------------------------------------------------+
```

## Shared Artifacts

| Artifact | Source | Consumed By |
|----------|--------|-------------|
| Project ID | Derived from docs/feature/{id}/ directory name | Wave command argument |
| Wave progress map | Artifact scanning logic | Status display, recommendation |
| Last modified timestamp | File system metadata | Multi-project ordering |
| .develop-progress.json | DELIVER wave resume state | DELIVER step resume |
| execution-log.yaml | DELIVER wave execution state | Step completion detection |
| Recommended wave | Detection logic | Command dispatch |
