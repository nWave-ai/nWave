---
name: nw-dor-validation
description: "Validates Definition of Ready with checklist criteria, antipattern detection, and domain language enforcement. Use when reviewing story readiness, checking handoff quality, or auditing acceptance criteria."
user-invocable: false
disable-model-invocation: true
---

# DoR Validation and Antipattern Detection

## Definition of Ready Checklist (8 Items - Hard Gate)

All items must PASS with evidence. Each FAIL blocks handoff.

### Item 1: Problem Statement Clear and Validated
Domain language (not technical), describes real user pain, testable.
Pass: "Maria wastes 30 seconds typing credentials on every visit"
Fail: "Users need authentication" | "Implement login feature"

### Item 2: User/Persona with Specific Characteristics
Real name, specific role, clear context.
Pass: "Maria Santos, returning customer (2+ orders), using trusted MacBook"
Fail: "User" | "Customer" | "End user" | "Authenticated user"

### Item 3: At Least 3 Domain Examples with Real Data
Min 3 examples, real names (not user123), real values, different scenarios (happy/edge/error).
Pass: "Example 1: Maria on MacBook, 5 days since login, goes to dashboard"
Fail: "User logs in successfully" | "Test with valid credentials"

### Item 4: UAT Scenarios Cover Happy Path + Edge Cases
Given/When/Then format, 3-7 scenarios, real data, covers happy + edge.
Pass: "Given Maria authenticated on 'MacBook-Home' 5 days ago..."
Fail: "Test login works" | "Given a user When they login Then success"

### Item 5: Acceptance Criteria Derived from UAT
Checkable (checkbox), traceable to UAT, outcome-focused (not implementation).
Pass: "Sessions older than 30 days require re-authentication"
Fail: "Use JWT tokens" | "System should work correctly"

### Item 6: Story Right-Sized (1-3 Days, 3-7 Scenarios)
Effort estimate provided, scenario count in range, single demonstrable outcome.
Pass: 2 days, 5 UAT scenarios, demoed in single session
Fail: >7 scenarios | >3 days | multiple distinct outcomes

### Item 7: Technical Notes Identify Constraints
Dependencies listed, risks identified, architectural considerations noted.
Pass: "Requires JWT token storage, GDPR cookie consent integration"
Fail: no technical notes section

### Item 8: Dependencies Resolved or Tracked
Blocking deps identified, resolution status clear, escalation path.
Pass: "Depends on US-041 (completed) and Auth service API (available)"
Fail: "Needs some API - TBD"

---

## Antipattern Detection (8 Patterns)

### 1. Implement-X (critical)
Signal: starts with "Implement", "Add", "Create", "Build", "Develop"
Detection: `^(Implement|Add|Create|Build|Develop)\s` | Fix: rewrite as user pain

### 2. Generic Data (high)
Signal: user123, test@test.com, foo, bar, lorem, placeholder
Detection: `user[0-9]+`, `test@`, `example@`, `foo`, `bar` | Fix: real names -- Maria Santos

### 3. Technical AC (high)
Signal: AC describes implementation not outcome
Detection: "Use JWT", "Implement using", "Database should", "API must return"
Fix: outcome focus -- "Session persists for 30 days"

### 4. Giant Stories (critical)
Signal: >7 scenarios | >3 days | multiple distinct outcomes | Fix: split by user outcome

### 5. No Examples (critical)
Signal: no "Example" section | <3 examples | abstract examples | Fix: add 3+ with real data

### 6. Tests After Code (high)
Signal: "Tests to be added", "Will write tests later", "Tests TBD" | Fix: UAT first, RED first

### 7. Vague Persona (high)
Signal: "User", "Customer", "End user" as persona | Fix: "Maria Santos, returning customer (2+ orders)"

### 8. Missing Edge Cases (medium)
Signal: all success scenarios, no errors, no boundaries | Fix: add expired session, invalid device, etc.

---

## UAT Scenario Quality Checks

**Format**: Given/When/Then with complete sentences. Fail: "Test login", "Given user When login Then success"
**Real Data**: real names, values, scenarios. Fail: "Given user123", "When X happens"
**Coverage**: min 1 happy path + 1 edge + 1 error. Range: 3-7 scenarios.

---

## Domain Language Checks

**Technical Jargon**: flag in user-facing sections: JWT, API, database, backend, frontend, microservice, REST, HTTP, JSON, SQL. Exception: Technical Notes section. Fix: "session token" -> "remember me"

**Generic Language**: flag "the system", "the application", "functionality", "feature". Fix: use specific names -- "the login page" -> "the welcome screen"
