---
name: leanux-methodology
description: LeanUX backlog management methodology - user story template, story sizing, story states, task types, Definition of Ready/Done, anti-pattern detection and remediation
---

# LeanUX Backlog Management Methodology

"A backlog is not a todo list. It's a collection of validated hypotheses waiting to become working software."

## Story States

| State | Meaning | Entry Criteria |
|-------|---------|----------------|
| Draft | Idea captured, not validated | Has problem statement |
| Ready | Validated, has UAT, ready to build | All DoR items complete |
| In Progress | Actively being built | UAT test written (RED) |
| In Review | Code complete, awaiting review | All tests green |
| Done | Merged, deployed, validated | UAT passes in production |
| Blocked | Cannot proceed | Blocker documented |

## Story Sizing Criteria

### Right-Sized
- Can be completed in 1-3 days
- Has 3-7 UAT scenarios
- Delivers demonstrable value
- Can be explained in 2 minutes

### Oversized Indicators
- More than 7 UAT scenarios
- More than 3 days estimated effort
- Multiple distinct user outcomes
- Cannot demonstrate in a single session

### Splitting Strategy
Split by user outcome, not by technical layer. Each resulting story delivers independently demonstrable value.

Example: "User Management" (20 scenarios) splits into:
- "Quick Login" (5 scenarios) -- returning customer on trusted device
- "New Registration" (4 scenarios) -- first-time customer sign-up
- "Password Recovery" (3 scenarios) -- customer who forgot credentials
- "Profile Settings" (4 scenarios) -- customer updating preferences

## Definition of Ready (DoR) - Hard Gate

Stories pass ALL 8 items before proceeding to DESIGN wave.

### Checklist with Pass/Fail Examples

**1. Problem statement clear and in domain language**
- Pass: "Maria wastes 30 seconds typing credentials on every visit"
- Fail: "Users need authentication"

**2. User/persona identified with specific characteristics**
- Pass: "Returning customer (2+ orders) on trusted personal device"
- Fail: "User" or "Customer"

**3. At least 3 domain examples with real data**
- Pass: "Maria on her MacBook, last login 5 days ago, goes directly to dashboard"
- Fail: "User logs in successfully"

**4. UAT scenarios in Given/When/Then (3-7 scenarios)**
- Pass: "Given Maria authenticated 5 days ago on 'MacBook-Home'..."
- Fail: "Test login functionality"

**5. Acceptance criteria derived from UAT**
- Pass: "Sessions older than 30 days require re-authentication"
- Fail: "System should work correctly"

**6. Story right-sized (1-3 days, 3-7 scenarios)**
- Pass: "2 days effort, 5 scenarios, single demo-able feature"
- Fail: "Epic with 20 scenarios"

**7. Technical notes identify constraints**
- Pass: "Requires JWT token storage, GDPR cookie consent"
- Fail: "No technical considerations"

**8. Dependencies resolved or tracked**
- Pass: "Depends on US-041 (completed) and Auth service API (available)"
- Fail: "Unspecified external dependencies"

### Validation Output Format

```markdown
## Definition of Ready Validation

**Story**: {story-id}

| DoR Item | Status | Evidence/Issue |
|----------|--------|----------------|
| Problem statement clear | PASS/FAIL | {evidence or issue} |
| User/persona identified | PASS/FAIL | {evidence or issue} |
| 3+ domain examples | PASS/FAIL | {evidence or issue} |
| UAT scenarios (3-7) | PASS/FAIL | {evidence or issue} |
| AC derived from UAT | PASS/FAIL | {evidence or issue} |
| Right-sized | PASS/FAIL | {evidence or issue} |
| Technical notes | PASS/FAIL | {evidence or issue} |
| Dependencies tracked | PASS/FAIL | {evidence or issue} |

**DoR Status**: PASSED / BLOCKED
```

### Failure Recovery
When DoR fails:
1. Display specific failures with remediation guidance
2. Do not proceed to peer review or handoff
3. Return to user with action items
4. Re-validate after fixes applied

## Definition of Done (DoD) - Completion Criteria

DoD validation is owned by acceptance-designer during DISTILL->DELIVER transition. Product-owner defines the checklist, acceptance-designer enforces it.

Checklist:
- All UAT scenarios pass (green)
- All supporting tests pass (unit, integration, component)
- Code refactored, no obvious debt
- Code reviewed and approved
- Merged to main branch
- Deployed to staging/production
- Story can be demoed to user

## Anti-Pattern Detection and Remediation

### Implement-X
- Signal: Task starts with "Implement X" or "Add X"
- Problem: No user context, technical focus, vague completion
- Bad: "Implement user authentication"
- Good: "Returning Customer Quick Login -- Maria wastes 30 seconds..."
- Fix: Start with user pain point, rewrite as problem statement

### Generic Data
- Signal: Examples use "user123", "test@test.com"
- Problem: Lacks real-world context, harder to validate
- Bad: "Given user123 logs in with password123"
- Good: "Given Maria Santos (maria.santos@email.com) on her MacBook"
- Fix: Replace all generic data with real names and realistic values

### Technical Acceptance Criteria
- Signal: AC describes implementation ("Use JWT tokens")
- Problem: Prescribes solution, not testable outcome
- Bad: "Use JWT tokens for session management"
- Good: "Session persists for 30 days on trusted device"
- Fix: Focus on observable user outcome, move tech choices to DESIGN

### Oversized Stories
- Signal: Story has >7 scenarios or >3 days effort
- Problem: Too large to track, deliver, or demo meaningfully
- Bad: "Complete user management (20 scenarios)"
- Good: "Quick Login (5 scenarios), Password Reset (4 scenarios)"
- Fix: Split into focused stories by user outcome

### No Examples
- Signal: Abstract requirements without concrete examples
- Problem: Ambiguous, untestable, different interpretations
- Bad: "Users should be able to manage their settings"
- Good: "Maria changes notification frequency from daily to weekly"
- Fix: Add 3+ concrete narratives with real data

### Tests After Code
- Signal: Tests written after implementation
- Problem: Technical debt, test coverage gaps
- Fix: UAT scenarios defined in DISCUSS wave, tests written RED first in DELIVER wave

## UAT-First Development Flow

The flow from Ready story to Done story follows double-loop TDD:

1. **Write UAT test from scenario**: Translate first Gherkin scenario to executable test. Run -> RED (correct).
2. **Build outside-in**: What does UAT need? Integration -> RED -> code -> GREEN. What does integration need? Unit -> RED -> code -> GREEN.
3. **Refactor**: All tests green, safe to refactor.
4. **Next scenario**: Repeat for each UAT scenario. All scenarios green -> Story is DONE.

## Story Prioritization

Use these techniques to order stories in the backlog when multiple stories compete for attention.

### MoSCoW Classification

| Category | Meaning | Guideline |
|----------|---------|-----------|
| Must Have | Required for minimum viable product | Without this, the release has no value |
| Should Have | Important for full product value | Significant value, but workaround exists |
| Could Have | Nice-to-have for enhanced experience | Desirable if time/budget allows |
| Won't Have | Deferred to future releases | Acknowledged, explicitly out of scope |

Assign MoSCoW during Phase 2 (CRAFT) when multiple stories emerge from the same requirements conversation.

### Value/Effort Matrix

Plot stories on two axes to identify execution order:

| | Low Effort | High Effort |
|---|---|---|
| **High Value** | Quick wins -- do first | Strategic investments -- plan carefully |
| **Low Value** | Fill-ins -- do if time allows | Eliminate or defer |

Quick wins build momentum and stakeholder confidence. Strategic investments need baseline measurement and roadmap planning (see `jtbd-workflow-selection` skill for workflow routing).

## Risk Identification Checklist

During Phase 4 (HANDOFF), include a brief risk assessment in the handoff package. Categorize identified risks:

**Business Risks**: market changes, regulatory changes, stakeholder availability, budget/timeline constraints
**Technical Risks**: integration complexity, technology uncertainty, data migration, performance/security unknowns
**Project Risks**: resource availability, scope creep potential, communication challenges, testing coverage gaps

For each identified risk, note: probability (low/medium/high), impact (low/medium/high), and mitigation approach (avoid, mitigate, transfer, or accept). Detailed risk management belongs to downstream waves -- the product-owner surfaces risks, does not manage them.

## Wave Handoff Package

When handing off to DESIGN wave (solution-architect), include:
- Structured requirements document with business context
- User stories with detailed acceptance criteria
- Stakeholder analysis and engagement plan
- Business rules and domain model
- Risk assessment with categorized risks (see checklist above)
- Non-functional requirements and quality attributes
- DoR validation results (all PASSED)
- Peer review approval
