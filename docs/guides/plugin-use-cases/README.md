# nWave Plugin — Use Cases

Four practical use cases demonstrating nWave's core workflows. Each includes the prompt, what happens step by step, and expected output.

---

## 1. Outside-In ATDD: Build a Feature with TDD Enforcement

**Prompt:**

```
/nw-deliver "Add password reset with email verification"
```

**What happens:**

1. **Roadmap creation** — the solution architect agent analyzes the feature, decomposes it into ordered steps (e.g., `01-01 Add reset token generation`, `01-02 Add email sending adapter`, `02-01 Wire reset endpoint`), and produces a `roadmap.json` with acceptance criteria per step.

2. **Roadmap review** — a reviewer agent validates step sizing, dependency ordering, and acceptance criteria quality. Rejects if steps are too large or criteria reference private internals.

3. **TDD execution** — for each step, a software crafter agent runs the 5-phase TDD cycle:
   - **PREPARE** — loads methodology skills, sets up test fixtures
   - **RED_ACCEPTANCE** — writes a failing acceptance test that exercises the full path (driving port → domain → driven port)
   - **RED_UNIT** — writes failing unit tests through driving ports, respecting the test budget (`2 × distinct behaviors`)
   - **GREEN** — implements minimal code to pass all tests
   - **COMMIT** — stages and commits with conventional commit message and `Step-ID` trailer

4. **DES enforcement** — every Task invocation is monitored by the Deterministic Execution System. It validates DES markers are present, logs each TDD phase with UTC timestamps, and blocks commits with incomplete phases.

5. **Refactoring** — after all steps, an L1-L4 progressive refactoring pass cleans up the modified files.

6. **Adversarial review** — a reviewer agent checks the implementation for Testing Theater patterns (tautological tests, mock-dominated tests, assertion-free tests, etc.) and flags issues.

7. **Integrity verification** — DES verifies all steps have complete 5-phase audit trails.

**Expected output:**

```
docs/feature/password-reset-email-verification/
  roadmap.json           # Step decomposition with acceptance criteria
  execution-log.json     # DES audit trail (all phases, timestamps, outcomes)
```

Plus: committed, tested code with conventional commit messages per step, all tests green, reviewer approval logged.

---

## 2. LeanUX JTBD Analysis: Define Requirements with User Stories

**Prompt:**

```
/nw-discuss "User onboarding optimization"
```

**What happens:**

1. **Jobs-to-be-Done discovery** — the product owner agent conducts an interactive session to identify the core jobs users are trying to accomplish during onboarding. Asks probing questions: "What triggers onboarding?", "What does success look like?", "What frustrations exist today?"

2. **Emotional arc mapping** — maps the user's emotional journey through onboarding stages (sign-up → first action → aha moment → habit formation), identifying pain points and delight opportunities.

3. **User story creation** — produces structured user stories in standard format:
   ```
   As a [persona],
   I want to [action],
   So that [outcome].
   ```

4. **BDD acceptance criteria** — each story gets Given-When-Then acceptance criteria:
   ```
   Given a new user has completed sign-up
   When they reach the dashboard for the first time
   Then they see a guided walkthrough highlighting 3 key features
   ```

5. **Definition of Ready enforcement** — validates that every story meets the Definition of Ready checklist: clear persona, measurable outcome, testable acceptance criteria, no ambiguous requirements.

**Expected output:**

A structured requirements document with user stories, acceptance criteria in BDD format, emotional arc diagram, and a Definition of Ready checklist. Ready for handoff to `/nw-design` (architecture) and `/nw-distill` (test scenarios).

---

## 3. Advanced Research with Adversarial Review

**Prompt:**

```
/nw-research "Compare event sourcing vs CQRS for order processing"
```

**What happens:**

1. **Multi-source evidence gathering** — the researcher agent searches documentation, academic papers, and technical references across multiple sources. Gathers concrete data: performance characteristics, complexity trade-offs, operational overhead, team skill requirements.

2. **Cross-referencing** — validates claims across sources. If one source claims "event sourcing adds 30% latency," the researcher looks for corroborating or contradicting evidence from other sources.

3. **Structured analysis** — produces a research document with:
   - Executive summary
   - Detailed comparison matrix (consistency model, query complexity, storage, scalability, debugging)
   - Concrete pros/cons for each approach in the order processing context
   - Recommendations with evidence backing
   - Source citations

4. **Adversarial review** (optional follow-up with `/nw-review`):

   ```
   /nw-review @nw-researcher-reviewer research "docs/research/event-sourcing-vs-cqrs.md"
   ```

   A reviewer agent critiques the research for:
   - Confirmation bias (did the researcher only seek evidence for one approach?)
   - Missing perspectives (operational complexity? team learning curve?)
   - Unsupported claims (assertions without evidence?)
   - Anchoring bias (over-relying on the first source found?)

**Expected output:**

A cited research document in `docs/research/` with evidence-backed recommendations, structured comparison, and (after review) an adversarial critique highlighting blind spots and strengthening the analysis.

---

## 4. Meta-Agent Creation: Build a New Specialized Agent

**Prompt:**

```
/nw-forge "security-auditor"
```

**What happens:**

1. **ANALYZE** — the agent builder researches existing security audit tools, OWASP guidelines, and nWave's agent specification format. Identifies the gap: no existing agent covers security-specific code review (dependency vulnerabilities, secrets detection, OWASP Top 10 patterns).

2. **DESIGN** — designs the agent specification:
   - Name, description, and persona
   - Core principles (e.g., "flag, don't fix — auditor reports, crafter implements")
   - Tool access (Read, Grep, Glob, Bash for scanning)
   - Skills to create (OWASP patterns, dependency scanning, secrets detection)
   - Integration points with existing waves (fits as reviewer in DELIVER Phase 4)

3. **CREATE** — generates the agent definition file (`nw-security-auditor.md`) with:
   - YAML frontmatter (name, description, model, tools, skills, maxTurns)
   - Markdown body (~200-400 lines) with principles, workflow, examples, constraints
   - Skill files for domain knowledge

4. **VALIDATE** — validates the generated agent against nWave's agent quality standards:
   - Frontmatter schema compliance
   - Principle count and differentiation from defaults
   - Example coverage (at least 3 examples)
   - Constraint clarity (what the agent does NOT do)
   - Skill file structure

5. **REFINE** — addresses validation findings, tightens language, ensures the agent integrates cleanly with existing nWave commands.

**Expected output:**

```
nWave/agents/nw-security-auditor.md    # Agent specification
nWave/skills/security-auditor/         # Domain knowledge skills
  owasp-patterns.md
  dependency-scanning.md
  secrets-detection.md
```

A production-ready agent definition that can be invoked via `/nw-review @nw-security-auditor security` or integrated into the DELIVER wave.
