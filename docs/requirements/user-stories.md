# User Stories: Wizard Commands (/nw:new, /nw:continue, and /nw:ff)

**Epic**: wizard-commands
**Date**: 2026-02-21
**Status**: Draft -- pending DoR validation

---

## US-001: Start a New Feature Through Guided Questions

### Problem (The Pain)
Kenji Nakamura is a backend developer who just installed nWave for his team's API project. He wants to add rate limiting but faces 18 commands in the reference and 6 waves he has never heard of. He finds it overwhelming to figure out whether he should start with `/nw:discover`, `/nw:discuss`, or `/nw:design`. He currently opens the tutorial, reads through the wave descriptions, makes a guess, and sometimes picks the wrong entry point -- wasting a full agent conversation before realizing he should have started earlier in the pipeline.

### Who (The User)
- Developer using nWave (new or returning) who has a feature idea
- Working in Claude Code's conversational interface
- Motivated to start building, not to study the nWave methodology first

### Solution (What We Build)
A `/nw:new` command that asks the user to describe their feature in plain language, asks 2-3 clarifying questions (new vs. existing behavior, requirements readiness), classifies the work, and launches the correct wave command with the right configuration -- so the user never has to choose between `/nw:discover`, `/nw:discuss`, or `/nw:design` themselves.

### Domain Examples

#### Example 1: Greenfield backend feature (Happy Path)
Sofia Reyes types `/nw:new` and describes "Add rate limiting to the API gateway." The wizard asks if this is new or existing behavior (new), detects no `docs/feature/` artifacts (greenfield), and asks if she has clear requirements (she has a rough idea). The wizard recommends DISCUSS wave, shows the rationale ("Define user stories and acceptance criteria"), and launches `/nw:discuss "rate-limiting"` with `feature_type=backend, walking_skeleton=depends, research_depth=lightweight`.

#### Example 2: Feature that needs problem validation first
Kenji Nakamura types `/nw:new` and describes "Build a customer feedback portal." He says he has not validated whether customers actually want this. The wizard recommends DISCOVER wave ("Need to validate the problem space first") and launches `/nw:discover "customer-feedback-portal"`.

#### Example 3: Vague description (Error Path)
Priya Sharma types `/nw:new` and says "Make things better." The wizard cannot classify this and asks three specific follow-up questions: what system, what problem, who benefits. It provides an example ("Add rate limiting to prevent API abuse") to anchor expectations. Priya refines to "Reduce API response times for the search endpoint" and the wizard proceeds.

#### Example 4: Name conflict with existing project
Tomoko Hayashi types `/nw:new` and describes "Add rate limiting to the payment service." The wizard detects `docs/feature/rate-limiting/` already exists with DISCUSS artifacts. It offers three options: continue that project, start fresh with a different name, or archive and restart. Tomoko picks "Start fresh with a different name" and the wizard asks for a distinguishing name, deriving `payment-rate-limiting`.

### UAT Scenarios (BDD)

#### Scenario 1: Greenfield feature with clear requirements starts at DISCUSS
```gherkin
Given Sofia Reyes has no prior nWave artifacts under docs/feature/
When Sofia types "/nw:new"
And Sofia describes "Add rate limiting to the API gateway"
And Sofia indicates she has clear requirements but no formal documentation
Then the wizard recommends starting at DISCUSS wave
And the wizard shows rationale "Define user stories and acceptance criteria"
When Sofia confirms
Then the wizard launches "/nw:discuss" with project ID "rate-limiting"
And passes feature_type="backend" to the DISCUSS configuration
```

#### Scenario 2: Feature needing problem validation starts at DISCOVER
```gherkin
Given Kenji Nakamura has no prior nWave artifacts under docs/feature/
When Kenji types "/nw:new"
And Kenji describes "Build a customer feedback portal"
And Kenji indicates he has not validated the problem space
Then the wizard recommends starting at DISCOVER wave
And the wizard shows rationale "Need to validate the problem space first"
When Kenji confirms
Then the wizard launches "/nw:discover" with project ID "customer-feedback-portal"
```

#### Scenario 3: Vague description triggers follow-up questions
```gherkin
Given Priya Sharma types "/nw:new"
When Priya describes "Make things better"
Then the wizard does not recommend a wave
And the wizard asks what system is being improved
And the wizard asks what problem is being solved
And the wizard asks who benefits from the change
And the wizard provides an example description
```

#### Scenario 4: Name conflict offers resolution options
```gherkin
Given Tomoko Hayashi has existing artifacts at docs/feature/rate-limiting/
When Tomoko types "/nw:new"
And Tomoko describes "Add rate limiting to the payment service"
Then the wizard detects a name conflict with project "rate-limiting"
And the wizard offers to continue that project, start fresh, or archive and restart
```

#### Scenario 5: Existing requirements detected, starts at DESIGN
```gherkin
Given Marcus Chen has complete DISCUSS artifacts at docs/feature/auth-upgrade/discuss/
  Including requirements.md and user-stories.md
When Marcus types "/nw:new"
And Marcus describes "Upgrade authentication to OAuth2"
Then the wizard detects existing DISCUSS artifacts for "auth-upgrade"
And the wizard recommends starting at DESIGN wave
When Marcus confirms
Then the wizard launches "/nw:design" with project ID "auth-upgrade"
```

### Acceptance Criteria
- [ ] User can type `/nw:new` and describe a feature in plain language
- [ ] Wizard asks 2-3 clarifying questions (new/existing, requirements readiness)
- [ ] Wizard auto-detects greenfield vs. brownfield from docs/feature/ presence
- [ ] Wizard classifies feature type (user-facing, backend, infrastructure, cross-cutting)
- [ ] Wizard recommends a starting wave with clear rationale shown to the user
- [ ] Wizard derives kebab-case project ID from the feature description
- [ ] Wizard detects and handles project name conflicts
- [ ] Wizard launches the recommended wave command with correct configuration
- [ ] Vague descriptions trigger follow-up questions, not a wrong-guess launch

### Technical Notes
- Command file: `nWave/tasks/nw/new.md` (new task file following existing conventions)
- Must follow the same frontmatter format as other task files (description, argument-hint)
- The wizard is conversational -- it runs as the main Claude instance (no subagent delegation for the wizard itself)
- Project ID derivation should match the existing logic in deliver.md (strip prefixes, remove stop words, kebab-case, max 5 words)
- Depends on: file system access to scan `docs/feature/` directories

---

## US-002: Resume a Feature by Detecting Current Wave Progress

### Problem (The Pain)
Elena Voronova is a full-stack developer who was designing the architecture for a notification service yesterday. Today she opens Claude Code and cannot remember whether she finished DESIGN or needs to start DISTILL. She finds it frustrating to manually check `docs/feature/notification-service/` for which artifacts exist and cross-reference them against the wave pipeline to figure out her next step. She ends up running `/nw:design` again, only to have Morgan tell her the architecture is already complete.

### Who (The User)
- Developer returning to a feature after hours or days away
- Working in Claude Code, lost context on current pipeline position
- Motivated to resume quickly, not to audit artifact directories manually

### Solution (What We Build)
A `/nw:continue` command that scans `docs/feature/` for project directories, checks which wave artifacts exist, displays a progress summary (which waves are complete, in progress, or not started), and launches the next wave command -- so the user picks up exactly where they left off with zero manual artifact inspection.

### Domain Examples

#### Example 1: Single project, DISCUSS complete, resume at DESIGN (Happy Path)
Elena Voronova types `/nw:continue`. The wizard scans `docs/feature/` and finds one project: `notification-service`. It checks artifact presence: `discuss/requirements.md` and `discuss/user-stories.md` exist (DISCUSS complete), no `design/` directory (DESIGN not started). It shows a progress bar with DISCUSS checked and DESIGN as the recommended next wave. Elena confirms and the wizard launches `/nw:design notification-service`.

#### Example 2: DELIVER wave partially complete, resume from last step
Rajesh Patel types `/nw:continue`. The wizard finds project `rate-limiting` with all waves through DISTILL complete and DELIVER in progress. It reads `execution-log.yaml` (steps 01-01 through 02-01 are COMMIT/PASS) and `.develop-progress.json` (last failure at step 02-02). It shows "DELIVER in progress: Steps 01-01 through 02-01 complete, next: 02-02" and launches `/nw:deliver "rate-limiting"` which auto-resumes from step 02-02.

#### Example 3: Multiple projects, user selects one
Wei Zhang types `/nw:continue`. The wizard finds two projects: `rate-limiting` (last modified 2026-02-20, at DESIGN wave) and `user-notifications` (last modified 2026-02-18, at DISCUSS wave). It lists them ordered by recency and asks Wei to pick. Wei selects `rate-limiting` and the wizard shows DESIGN as the next wave.

#### Example 4: No projects found (Error Path)
Fatima Al-Rashid types `/nw:continue` on a fresh repo with no `docs/feature/` directory. The wizard shows "No active projects found" and suggests `/nw:new` to start a new feature.

#### Example 5: Skipped waves detected (Error Path)
Carlos Mendez has a project `payment-gateway` with DISCUSS artifacts and partial DELIVER execution but no DESIGN or DISTILL artifacts. The wizard warns about the gap and offers options: fill from DESIGN, continue DELIVER as-is, or show all artifacts for manual review.

### UAT Scenarios (BDD)

#### Scenario 1: Single project resumes at next wave
```gherkin
Given Elena Voronova has project "notification-service" with complete DISCUSS artifacts
  And no DESIGN artifacts exist for "notification-service"
When Elena types "/nw:continue"
Then the wizard shows DISCUSS as complete and DESIGN as "not started"
And recommends resuming at DESIGN wave
When Elena confirms
Then the wizard launches "/nw:design" with argument "notification-service"
```

#### Scenario 2: DELIVER wave resumes from last completed step
```gherkin
Given Rajesh Patel has project "rate-limiting" with all waves through DISTILL complete
  And execution-log.yaml shows steps 01-01 through 02-01 as COMMIT/PASS
  And .develop-progress.json records last failure at step 02-02
When Rajesh types "/nw:continue"
Then the wizard shows DELIVER as "in progress" with next step 02-02
When Rajesh confirms
Then the wizard launches "/nw:deliver" with argument "rate-limiting"
```

#### Scenario 3: Multiple projects listed by recency
```gherkin
Given Wei Zhang has projects "rate-limiting" (modified 2026-02-20) and "user-notifications" (modified 2026-02-18)
When Wei types "/nw:continue"
Then the wizard lists "rate-limiting" first and "user-notifications" second
And asks Wei to select a project
When Wei selects "1"
Then the wizard shows progress for "rate-limiting"
```

#### Scenario 4: No projects found suggests /nw:new
```gherkin
Given Fatima Al-Rashid has no directories under docs/feature/
When Fatima types "/nw:continue"
Then the wizard shows "No active projects found under docs/feature/"
And suggests running "/nw:new" to start a new feature
```

#### Scenario 5: Non-adjacent wave artifacts trigger warning
```gherkin
Given Carlos Mendez has project "payment-gateway" with DISCUSS complete and partial DELIVER
  But no DESIGN or DISTILL artifacts
When Carlos types "/nw:continue"
Then the wizard warns about skipped waves DESIGN and DISTILL
And offers to resume from DESIGN, continue DELIVER, or show artifacts
```

#### Scenario 6: Corrupted artifact triggers re-run recommendation
```gherkin
Given Li Wei has project "search-index"
  And docs/feature/search-index/discuss/requirements.md exists but is empty (0 bytes)
When Li types "/nw:continue"
Then the wizard flags requirements.md as empty
And recommends re-running DISCUSS wave
```

### Acceptance Criteria
- [ ] User can type `/nw:continue` to scan for active projects
- [ ] Wizard scans `docs/feature/` directories and detects wave completion by artifact presence
- [ ] Wizard displays a progress summary showing each wave's status (complete, in progress, not started)
- [ ] For single projects, wizard recommends the next wave automatically
- [ ] For multiple projects, wizard lists them ordered by last modification and asks user to select
- [ ] For DELIVER wave in progress, wizard shows step-level progress from execution-log.yaml
- [ ] When no projects exist, wizard suggests `/nw:new`
- [ ] Wizard warns when wave artifacts are non-adjacent (skipped waves)
- [ ] Wizard detects empty or corrupted key artifacts and recommends re-running that wave

### Technical Notes
- Command file: `nWave/tasks/nw/continue.md` (new task file)
- Wave detection relies on specific artifact file paths (see journey YAML for the full mapping)
- DELIVER resume depends on existing logic: `.develop-progress.json` for step resume, `execution-log.yaml` for completion status
- "Last modified" for project ordering uses the most recent file modification timestamp under that project's `docs/feature/{id}/` tree
- The wizard runs as the main Claude instance (no subagent for the wizard itself)
- Depends on: file system access, existing wave artifact conventions across all 6 waves

---

## US-003: Derive Project ID from Natural Language Description

### Problem (The Pain)
Sofia Reyes describes her feature as "Add rate limiting to the API gateway" during the `/nw:new` wizard. The wizard needs to derive a consistent project ID (`rate-limiting`) that will be used as the directory name under `docs/feature/` and passed to every subsequent wave command. If this derivation is inconsistent or produces IDs that are too long, too short, or conflict with existing projects, the entire downstream pipeline breaks.

### Who (The User)
- Developer interacting with /nw:new wizard
- Provides natural language descriptions, not identifiers
- Expects the derived ID to be sensible without having to think about naming conventions

### Solution (What We Build)
Consistent project ID derivation logic that strips common prefixes ("implement", "add", "create", "build"), removes stop words, converts to kebab-case, and limits to 5 words. The derived ID is shown to the user for confirmation before any wave launches.

### Domain Examples

#### Example 1: Standard derivation (Happy Path)
Sofia describes "Add rate limiting to the API gateway." The wizard strips "Add", removes stop word "to the", and derives `rate-limiting-api-gateway`. It shows this to Sofia who confirms.

#### Example 2: Short description
Kenji describes "OAuth2 upgrade." The wizard derives `oauth2-upgrade` directly. No stripping needed.

#### Example 3: Long description truncated
Priya describes "Implement a real-time notification system with WebSocket support for mobile and desktop clients." The wizard strips "Implement a", removes stop words, and truncates to 5 words: `real-time-notification-system-websocket`. It shows this to Priya who adjusts to `realtime-notifications`.

### UAT Scenarios (BDD)

#### Scenario 1: Standard prefix stripping and kebab-case
```gherkin
Given Sofia describes "Add rate limiting to the API gateway"
When the wizard derives a project ID
Then the project ID is "rate-limiting-api-gateway"
And the wizard shows this ID to Sofia for confirmation
```

#### Scenario 2: Short description passes through
```gherkin
Given Kenji describes "OAuth2 upgrade"
When the wizard derives a project ID
Then the project ID is "oauth2-upgrade"
```

#### Scenario 3: Long description truncated to 5 words
```gherkin
Given Priya describes "Implement a real-time notification system with WebSocket support for mobile and desktop clients"
When the wizard derives a project ID
Then the project ID has at most 5 hyphenated segments
And the wizard shows the truncated ID for user confirmation
```

#### Scenario 4: User overrides derived ID
```gherkin
Given the wizard derives project ID "real-time-notification-system-websocket"
When Priya says she prefers "realtime-notifications"
Then the wizard uses "realtime-notifications" as the project ID
```

### Acceptance Criteria
- [ ] Wizard strips common prefixes: "implement", "add", "create", "build"
- [ ] Wizard removes English stop words ("a", "the", "to", "for", "with", "and")
- [ ] Wizard converts to kebab-case
- [ ] Wizard limits project ID to 5 hyphenated segments
- [ ] Wizard shows derived ID to user for confirmation before proceeding
- [ ] User can override the derived ID with their own choice

### Technical Notes
- Must match the existing derivation logic in `deliver.md` line: "Derive project-id: strip common prefixes (implement, add, create), remove stop words, kebab-case, max 5 words"
- This logic is shared between `/nw:new` and `/nw:deliver` -- should be described consistently in both task files
- Depends on: nothing (pure string transformation)

---

## Dependency Map

```
US-003 (Project ID derivation)
  |
  v
US-001 (/nw:new wizard) -----> US-002 (/nw:continue scanner)
  |                               |
  | uses project_id               | reads docs/feature/{project_id}/
  | launches wave commands        | reads execution-log.yaml
  v                               v
Existing wave commands:         Existing DELIVER resume logic:
/nw:discover                    .develop-progress.json
/nw:discuss                     execution-log.yaml
/nw:design
/nw:devops
/nw:distill
/nw:deliver
```

---

## US-004: Fast-Forward Through Remaining Waves

### Problem (The Pain)
Marcus Chen has clear requirements for his OAuth2 upgrade feature. He knows exactly what he wants. But nWave's step-by-step wave approach forces him to stop after each wave, review artifacts, and manually launch the next command. For well-understood features where the scope is clear, this ceremony is friction — he just wants to get to working code.

### Who (The User)
- Experienced developer with clear, well-defined requirements
- Working on brownfield features where the scope is obvious
- Wants to move fast without reviewing intermediate artifacts

### Solution (What We Build)
A `/nw:ff` (fast-forward) command that chains remaining waves end-to-end. It detects current progress (like `/nw:continue`), then runs each subsequent wave automatically — DISCUSS → DESIGN → DISTILL → DELIVER — without stopping for review between waves. The user confirms once at the start, then the pipeline runs to completion.

### Domain Examples

#### Example 1: Fast-forward from scratch (Happy Path)
Marcus types `/nw:ff "Upgrade authentication to OAuth2"`. The wizard detects no prior artifacts, derives project ID `oauth2-upgrade`, and shows the plan: "Will run DISCUSS → DESIGN → DISTILL → DELIVER without stopping." Marcus confirms. Each wave runs in sequence, passing artifacts to the next.

#### Example 2: Fast-forward from mid-pipeline
Elena has completed DISCUSS for `notification-service`. She types `/nw:ff`. The wizard detects DISCUSS is complete and shows: "Will run DESIGN → DISTILL → DELIVER for notification-service." Elena confirms and the remaining waves execute.

#### Example 3: Fast-forward with wave selection
Rajesh types `/nw:ff --from=distill "rate-limiting"`. He already has design artifacts from a manual review and wants to skip to DISTILL → DELIVER. The wizard validates that DESIGN artifacts exist and proceeds from DISTILL.

#### Example 4: Wave failure mid-pipeline (Error Path)
Sofia fast-forwards `api-gateway`. DISCUSS succeeds, DESIGN succeeds, but DISTILL fails (acceptance designer cannot parse the architecture). The pipeline stops, shows the error, and suggests resuming with `/nw:continue` after fixing the issue.

### UAT Scenarios (BDD)

#### Scenario 1: Full fast-forward from scratch
```gherkin
Given Marcus has no prior nWave artifacts under docs/feature/
When Marcus types "/nw:ff" with description "Upgrade authentication to OAuth2"
Then the wizard shows the planned wave sequence: DISCUSS → DESIGN → DISTILL → DELIVER
And asks for confirmation to proceed
When Marcus confirms
Then each wave executes in sequence without stopping for review
And artifacts from each wave are passed to the next
```

#### Scenario 2: Fast-forward from mid-pipeline
```gherkin
Given Elena has complete DISCUSS artifacts for "notification-service"
  And no DESIGN artifacts exist
When Elena types "/nw:ff"
Then the wizard detects DISCUSS is complete
And shows planned sequence: DESIGN → DISTILL → DELIVER
When Elena confirms
Then DESIGN executes followed by DISTILL followed by DELIVER
```

#### Scenario 3: Explicit --from flag
```gherkin
Given Rajesh has complete DESIGN artifacts for "rate-limiting"
When Rajesh types "/nw:ff --from=distill"
Then the wizard validates DESIGN artifacts exist
And shows planned sequence: DISTILL → DELIVER
When Rajesh confirms
Then DISTILL executes followed by DELIVER
```

#### Scenario 4: Wave failure stops pipeline
```gherkin
Given Sofia is fast-forwarding "api-gateway"
  And DISCUSS completes successfully
  And DESIGN completes successfully
When DISTILL fails with an error
Then the pipeline stops at DISTILL
And the wizard shows the error
And suggests "/nw:continue" to resume after fixing the issue
```

### Acceptance Criteria
- [ ] User can type `/nw:ff` with an optional feature description to fast-forward all remaining waves
- [ ] Wizard detects current progress (reusing `/nw:continue` detection logic)
- [ ] Wizard shows the planned wave sequence before execution and asks for one-time confirmation
- [ ] Each wave executes in sequence, passing artifacts to the next wave automatically
- [ ] Optional `--from={wave}` flag allows starting from a specific wave (validates prerequisites exist)
- [ ] If a wave fails mid-pipeline, execution stops with a clear error and suggests `/nw:continue` to resume
- [ ] Fast-forward skips DISCOVER wave by default (opt-in with `--from=discover`)

### Technical Notes
- Command file: `nWave/tasks/nw/ff.md` (new task file)
- Reuses wave detection logic from `/nw:continue`
- Reuses project ID derivation from US-003 when a description is provided
- Runs as main Claude instance — dispatches each wave via the Task tool to subagents
- Must handle wave handoff: each wave's output directory becomes the next wave's input
- DISCOVER is skipped by default because it requires interactive customer interview data that cannot be auto-generated

---

## Dependency Map

```
US-003 (Project ID derivation)
  |
  v
US-001 (/nw:new wizard) -----> US-002 (/nw:continue scanner)
  |                               |
  | uses project_id               | reads docs/feature/{project_id}/
  | launches wave commands        | reads execution-log.yaml
  v                               v
Existing wave commands:         US-004 (/nw:ff fast-forward)
/nw:discover                      |
/nw:discuss                       | reuses US-002 detection logic
/nw:design                        | reuses US-003 ID derivation
/nw:devops                        | chains wave commands sequentially
/nw:distill                       v
/nw:deliver                     Existing wave commands
```

All four stories can be implemented in parallel. US-003 is a subset of US-001 but split out because the ID derivation logic is a discrete, independently testable behavior shared across commands. US-004 reuses detection logic from US-002 and ID derivation from US-003.
