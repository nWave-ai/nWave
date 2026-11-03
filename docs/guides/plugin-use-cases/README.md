# nWave Plugin — Use Cases

Four practical use cases demonstrating nWave's core workflows. Each includes the prompt, what happens step by step, and expected output. The prompts are what you say to your assistant; it loads the skills and runs the `nwdes` route — see [For your assistant](../README.md#for-your-assistant).

---

## 1. Outside-In ATDD: Build a Feature with TDD Enforcement

**Prompt:**

```
/nw-deliver "Add password reset with email verification"
```

**What happens:**

1. **Design** — the architect names the observable values, owned targets and
   verification obligations, and records them through its `nwdes design` verbs
   (draft, then `nwdes design close`); nwdes assigns the identities and
   renders the briefs itself.

2. **Acceptance** — the acceptance designer supplies the executable oracle: it
   records one row per scenario with `nwdes acceptance row add` and publishes
   with `nwdes acceptance close`. The host runs the slice's declared commands
   and observes RED before implementation.

3. **Implementation** — the crafter changes the declared mutable targets.
   The host runs the slice's verification commands and retains their results.
   nwdes is a deterministic builder, not a phase-enforcement engine.

4. **Independent assessment** — reviewers and the examiner assess the actual
   evidence. A rendered document or a successful close does not establish that
   the delivered behavior is correct.

**Expected output:**

The feature's handoff, rendered briefs, oracle and execution receipts accompany
the implementation. Use `nwdes document` for reading views; use the host's
recorded command results, independent review and examination for delivery evidence.

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
