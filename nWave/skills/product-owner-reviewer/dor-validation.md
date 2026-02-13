---
name: dor-validation
description: Definition of Ready checklist criteria, antipattern detection patterns, UAT quality rules, and domain language enforcement for product owner review
---

# DoR Validation and Antipattern Detection

## Definition of Ready Checklist (8 Items - Hard Gate)

All items must PASS with evidence for approval. Each FAIL blocks handoff.

### Item 1: Problem Statement Clear and Validated
Criteria: written in domain language (not technical), describes real user pain, specific enough to be testable.
Pass: "Maria wastes 30 seconds typing credentials on every visit"
Fail: "Users need authentication", "Implement login feature", "System requires auth module"

### Item 2: User/Persona Identified with Specific Characteristics
Criteria: real name used, specific role, clear context.
Pass: "Maria Santos, returning customer (2+ previous orders), using trusted MacBook"
Fail: "User", "Customer", "End user", "Authenticated user"

### Item 3: At Least 3 Domain Examples with Real Data
Criteria: minimum 3 examples, real names (not user123), real values (30 days, not "some time"), different scenarios (happy path, edge case, error).
Pass: "Example 1: Maria on MacBook, 5 days since login, goes to dashboard"
Fail: "User logs in successfully", "Test with valid credentials", "user123 authenticates"

### Item 4: UAT Scenarios Cover Happy Path + Key Edge Cases
Criteria: Given/When/Then format, 3-7 scenarios, real data in scenarios, covers happy path AND edge cases.
Pass: "Given Maria authenticated on 'MacBook-Home' 5 days ago..."
Fail: "Test login works", "Given a user When they login Then success"

### Item 5: Acceptance Criteria Derived from UAT
Criteria: checkable (checkbox format), traceable to UAT scenario, outcome-focused (not implementation).
Pass: "Sessions older than 30 days require re-authentication"
Fail: "Use JWT tokens", "System should work correctly", "Implement auth"

### Item 6: Story Right-Sized (1-3 Days, 3-7 Scenarios)
Criteria: effort estimate provided, scenario count in range, single demonstrable outcome.
Pass indicators: 2 days estimated effort, 5 UAT scenarios, can be demoed in single session.
Fail indicators: >7 scenarios, >3 days effort, multiple distinct user outcomes.

### Item 7: Technical Notes Identify Constraints
Criteria: dependencies listed, risks identified, architectural considerations noted.
Pass: "Requires JWT token storage, GDPR cookie consent integration"
Fail: no technical notes section present.

### Item 8: Dependencies Resolved or Tracked
Criteria: blocking dependencies identified, resolution status clear, escalation path if blocked.
Pass: "Depends on US-041 (completed) and Auth service API (available)"
Fail: "Needs some API - TBD"

---

## Antipattern Detection (8 Patterns)

### 1. Implement-X (Severity: critical)
Signal: task starts with "Implement", "Add", "Create", "Build", "Develop".
Detection regex: `^(Implement|Add|Create|Build|Develop)\s`
Fix: rewrite as problem statement from user pain.

### 2. Generic Data (Severity: high)
Signal: examples use user123, test@test.com, foo, bar, lorem, placeholder.
Detection patterns: `user[0-9]+`, `test@`, `example@`, `foo`, `bar`, `lorem`, `placeholder`
Fix: use real names -- Maria Santos, maria.santos@email.com.

### 3. Technical Acceptance Criteria (Severity: high)
Signal: AC describes implementation not outcome.
Detection patterns: "Use JWT", "Implement using", "Database should", "API must return", "Backend needs"
Fix: focus on outcome -- "Session persists for 30 days."

### 4. Giant Stories (Severity: critical)
Signal: >7 scenarios or >3 days effort or multiple distinct user outcomes.
Fix: split into focused stories by user outcome.

### 5. No Examples (Severity: critical)
Signal: no "Example" section, less than 3 examples, or examples are abstract.
Fix: add 3+ examples with real names and data.

### 6. Tests After Code (Severity: high)
Signal: "Tests to be added", "Will write tests later", "Tests TBD"
Fix: UAT first, always RED first.

### 7. Vague Persona (Severity: high)
Signal: "User", "Customer", "End user", "the user", "users" as persona.
Fix: use specific persona -- "Maria Santos, returning customer (2+ orders)."

### 8. Missing Edge Cases (Severity: medium)
Signal: all scenarios are success scenarios, no error handling, no boundary conditions.
Fix: add edge cases -- expired session, invalid device, concurrent login.

---

## UAT Scenario Quality Checks

### Format Compliance
Required: Given/When/Then structure with complete sentences.
Fail: "Test login", "Given user When login Then success"

### Real Data Usage
Required: real names, real values, real scenarios.
Fail: "Given user123", "When X happens", "Then Y occurs"

### Coverage
Required types: happy path (at least 1), edge case (at least 1), error scenario (at least 1).
Range: minimum 3, maximum 7 scenarios.

---

## Domain Language Checks

### Technical Jargon Detection
Flag in user-facing sections: JWT, API, database, backend, frontend, microservice, REST, HTTP, JSON, SQL.
Exception: Technical Notes section (allowed).
Fix: use domain language -- "session token" becomes "remember me."

### Generic Language Detection
Flag: "the system", "the application", "the software", "functionality", "feature."
Fix: use specific names -- "the login page" becomes "the welcome screen."
