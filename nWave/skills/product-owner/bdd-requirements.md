---
name: bdd-requirements
description: BDD requirements discovery methodology - Example Mapping, Three Amigos, conversational patterns, Given-When-Then translation, and collaborative specification
---

# BDD Requirements Discovery

"If you're not having conversations, you're not doing BDD." -- Liz Keogh

BDD is about discovering "what we don't know we don't know" through collaborative exploration with concrete examples, not about tools or formats.

## The Three Amigos

Three core perspectives that reveal each other's blindspots:

1. **Problem Owner** (Product Owner, BA, Domain Expert): understands business need, defines acceptance criteria, provides domain knowledge
2. **Problem Solver** (Developer, Engineer): understands technical constraints, identifies implementation complexity, reveals technical edge cases
3. **Skeptic** (Tester, QA): thinks about what could go wrong, identifies edge cases and boundaries, challenges assumptions

### Session Structure (25-minute timebox)

1. Read user story aloud (2 min) -- establish shared context
2. Identify acceptance criteria / rules (8 min) -- "what must be true for done?"
3. Explore examples for each rule (12 min) -- concrete scenarios, edge cases
4. Capture questions (ongoing) -- unknowns on red cards
5. Review and summarize (3 min) -- shared understanding check

If a story cannot be mapped in 25 minutes, it is either too large (split), too uncertain (spike), or the team needs practice.

## Example Mapping

### Four Card Types

- Yellow: User Story (1 per session)
- Blue: Business Rules / Acceptance Criteria
- Green: Concrete Examples illustrating rules
- Red: Questions / Unknowns (blockers)

### Visual Layout

```
[Yellow] User Story: Transfer money between accounts
  |
  +-- [Blue] Rule: Amount must not exceed source balance
  |     +-- [Green] $500 balance, transfer $400 -> succeeds
  |     +-- [Green] $500 balance, transfer $500 -> succeeds (boundary)
  |     +-- [Green] $500 balance, transfer $501 -> fails
  |     +-- [Red] What happens if balance changes during transfer?
  |
  +-- [Blue] Rule: Both accounts belong to same customer
  |     +-- [Green] Transfer between checking and savings -> succeeds
  |     +-- [Green] Transfer to friend's account -> requires different flow
  |
  +-- [Blue] Rule: Transfer creates transaction records
        +-- [Green] $100 transfer -> 2 transactions (debit + credit)
        +-- [Red] What timezone for timestamps?
```

### When to Use Example Mapping

Use when: story about to enter sprint, has multiple edge cases, team uncertain about scope, cross-functional clarification needed.
Skip when: story is trivial and well-understood, pure technical refactoring with no behavior change, team already has strong shared understanding.

## Conversational Patterns

### Pattern 1: Context Questioning

Template: "Is there any other context which, when this event happens, will produce a different outcome?"

Purpose: discover edge cases and alternative scenarios.

```
BA: "When a customer submits an order, the order is confirmed."
Tester: "Is there context that produces a different outcome?"
Developer: "What if the item is out of stock?"
BA: "Then the order goes to backorder status."
Tester: "What if payment is declined?"
BA: "Then the order is pending payment."
```

Result: three rules discovered from one statement.

### Pattern 2: Outcome Questioning

Template: "Given this context, when this event happens, is there another outcome that's important?"

```
BA: "When admin deletes a user account, the account is deleted."
Tester: "Is there another important outcome?"
Developer: "Audit log entry for the deletion."
BA: "Email notification to the user."
Tester: "GDPR -- delete all personal data."
Developer: "What about resources owned by the user?"
```

Result: one simple statement revealed five important outcomes.

### Pattern 3: Concrete Examples

Template: "Can you give me a concrete example?"

Purpose: abstract rules hide assumptions. Concrete examples force decisions.

```
BA: "User can search products by category."
Developer: "Concrete example?"
BA: "User selects 'Electronics' category."
Tester: "What if Electronics has 10,000 products?"
BA: "We paginate. Show 20 per page."
Developer: "Default sort order?"
BA: "I need to ask stakeholders."
[Red card: "Default sort order for category browsing?"]
```

## From Examples to Given-When-Then

### Translation Rules
- **Given** = context from example (preconditions, system state)
- **When** = event/action from example (user action, system trigger)
- **Then** = outcome from example (observable results, state changes)

### Example Translation

Example card: "Balance $500, transfer $300 -> succeeds"

```gherkin
Scenario: Successful transfer with sufficient balance
  Given my checking account balance is $500.00
  And my savings account balance is $100.00
  When I transfer $300.00 from checking to savings
  Then my checking balance is $200.00
  And my savings balance is $400.00
  And I receive a confirmation message
```

### For Each Rule, Create 2-3 Examples
1. Typical/happy path example
2. Boundary condition example
3. Error/alternative path example

## Business Outcome Focus: Five Whys

Apply Five Whys to ensure stories connect to business value:

```
Story: "Add CSV export for reports"
Why? "Users can export data"
Why? "Analyze in Excel"
Why? "No pivot tables in our app"
Why? "Need to slice data by dimensions"
Why? "Identify trends for business decisions"

Real need: better analytical capabilities, not CSV export
```

Focus on behaviors that directly contribute to business results. Challenge features that lack clear business value.

## Acceptance Criteria Style

Traditional (implementation-focused) -- avoid:
- "API endpoint accepts POST requests"
- "Response returns JSON with 201 status"

BDD-style (outcome-focused) -- use this:
- "Customer can submit order even when offline"
- "Order confirmed within 2 seconds"
- "Customer receives email confirmation"

Shift from "system does X" to "user achieves Y."

## Confirmation Bias Defense

### Technique 1: Reverse Assumptions
Assumption: "Users fill out the form correctly."
Reverse: empty form, garbage data, 50,000 characters, 100 submissions in 10 seconds.

### Technique 2: Evil User Persona
Create "Malicious Mike" and "Careless Cathy" personas. Mike tries SQL injection, URL manipulation, unauthorized access. Cathy never reads instructions, clicks back mid-process, refreshes constantly.

### Technique 3: Force Example Diversity
For each rule, require examples from three categories:
1. Happy path (typical success)
2. Edge case (boundary, unusual but valid)
3. Error case (invalid, failure condition)

Forcing diversity prevents echo chamber thinking.

## Red Card Management

Red cards are blockers. Never proceed to development with unresolved questions.

Resolution process:
1. Capture question during session
2. Assign owner (usually BA or Product Owner)
3. Set deadline (before development starts)
4. Follow-up session if answer reveals new complexity

Good red cards:
- "What's the character limit for product descriptions?"
- "Can users upload PDFs or only images?"
- "What happens to orders if payment gateway is down?"

## Requirements Document Structure

BDD hierarchy for documentation:

```
Business Capability (Epic)
  +-- Feature (Theme)
      +-- User Story
          +-- Acceptance Criteria (Rules)
              +-- Scenarios (Examples)
```

Each level includes: business value, user context, concrete examples, Given-When-Then scenarios, and tracked questions with resolution status.

## Bridging Business and Technical Perspectives

Same scenario, understood differently by each role:

```gherkin
Scenario: High-value customer receives priority support
  Given I am a customer with "Platinum" membership
  And I submit a support ticket with priority "urgent"
  When the support team reviews new tickets
  Then my ticket appears at the top of the queue
  And I receive automated acknowledgment within 1 minute
```

- Executive sees: "Platinum customers get priority" (business rule)
- Customer sees: "My urgent issues get fast response" (user benefit)
- Developer sees: "Filter by membership tier and priority" (implementation)
- Tester sees: "Verify queue ordering and SLA compliance" (test case)

Same scenario, multiple valid interpretations, zero translation loss.

## Discovery Workshop Format (90 minutes)

Participants: 6-8 people (PO, BA as facilitator, 2-3 developers, 1-2 testers, optional SME).

1. Context Setting (10 min) -- business problem, success criteria
2. Story Writing (15 min) -- brainstorm, write on yellow cards, prioritize
3. Example Mapping Round 1 (25 min) -- top priority story
4. Break (5 min)
5. Example Mapping Round 2 (25 min) -- second priority story
6. Review and Next Steps (10 min) -- summarize, assign red cards, schedule follow-up

Output: 2-3 stories mapped, 10-15 scenarios drafted, red cards assigned.

## Example Mapping Anti-Patterns

1. **No examples, just rules**: Blue cards without green cards underneath. Rules are abstract. Force concrete examples for each rule.
2. **Too many rules (story too big)**: More than 5-6 blue cards means story needs splitting.
3. **Implementation details in examples**: "POST to /api/users with JSON" instead of "I register with email." Describe user-observable behavior.
4. **Ignoring red cards**: Proceeding to development with unresolved questions leads to rework.

## User Story Mapping

Use story mapping to decompose epics into stories by tracing the complete user workflow.

### Process

1. **Map the workflow end-to-end**: Walk through the user's complete journey from trigger to outcome. Each step becomes a column.
2. **Identify touchpoints**: At each step, list system interactions, decisions, and information needs.
3. **Break into stories**: Group touchpoints into coherent user stories. Each story delivers a demonstrable slice of the workflow.
4. **Prioritize by value**: Arrange stories top-to-bottom within each column. Top row = minimum viable workflow (walking skeleton). Lower rows = enhancements.

### Visual Layout

```
Workflow:  [Discover] --> [Evaluate] --> [Purchase] --> [Receive]
             |              |              |              |
Row 1:     Search by     View details   Add to cart    Track order
           keyword        + price        + checkout     status
             |              |              |              |
Row 2:     Filter by     Compare        Apply          Delivery
           category       products       coupon         notifications
             |              |
Row 3:     Save search   Read reviews
```

Row 1 = MVP release. Row 2 = second release. Row 3 = future.

Story mapping complements Example Mapping: use story mapping first to identify WHICH stories to write, then Example Mapping to explore EACH story in depth.

## Requirements Completeness Check

During Phase 1 (GATHER), verify all three requirement types are captured. Stories that cover only functional requirements produce incomplete handoff packages.

### Functional Requirements
- Specific business capabilities and features
- User interactions and system responses
- Data processing and transformation rules
- Integration and interface requirements
- Validation: testable through acceptance tests, traceable to business objectives, complete and unambiguous

### Non-Functional Requirements (NFRs)
- Performance: response time, throughput, scalability
- Security: authentication, authorization, data protection
- Usability: user experience, accessibility
- Reliability: availability, fault tolerance, recovery
- Validation: quantifiable metrics and thresholds, testable through automated validation

### Business Rules
- Business policy enforcement requirements
- Data validation and integrity rules
- Workflow and process constraints
- Compliance and regulatory requirements
- Validation: clear rule specification with examples, exception handling defined, rule precedence documented

For each story, ask: "Have we captured the functional behavior, the quality attributes (NFRs), and the business constraints?" Missing any category is a completeness gap flagged during review (see `review-dimensions` skill, Dimension 2).

## Domain Language Discovery

Formalize the ubiquitous language process. Domain language primacy (Core Principle 4) requires deliberate discovery, not just passive adoption.

### Phase 1: Discovery
- Identify domain-specific terminology through stakeholder conversations
- Document existing business language and definitions
- Capture synonyms and variations in usage
- Flag ambiguous terms requiring clarification

### Phase 2: Definition
- Collaborate with domain experts to establish precise definitions
- Resolve terminology conflicts and inconsistencies
- Create a glossary with examples for each term
- Validate definitions with all stakeholder groups

### Phase 3: Adoption
- Integrate ubiquitous language into all requirements artifacts
- Use agreed terms consistently in user stories, acceptance criteria, and scenarios
- Ensure handoff package includes the glossary for downstream waves (DESIGN, DISTILL)

Terms discovered here feed directly into BDD scenarios -- Given/When/Then statements use the ubiquitous language, ensuring zero translation loss between business and technical perspectives.
