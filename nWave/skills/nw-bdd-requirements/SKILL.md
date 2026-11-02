---
name: nw-bdd-requirements
description: BDD requirements discovery methodology - Example Mapping, Three Amigos, conversational patterns, Given-When-Then translation, and collaborative specification
user-invocable: false
disable-model-invocation: true
---

# BDD Requirements Discovery

"If you're not having conversations, you're not doing BDD." -- Liz Keogh

BDD discovers "what we don't know we don't know" through collaborative exploration with concrete examples, not tools or formats.

## Facilitate product understanding

The PO owns DISCUSS, not merely story decomposition. Start from one actor,
concrete situation and intended benefit. Ask one consequential question or a
small related group; reflect the answer in the actor's language and invite
correction. Use existing answers instead of repeating discovery. Make alternatives
and their consequences clear without leading the human toward your preferred
formal property. Offer an example when abstraction prevents understanding.

Separate confirmed decisions, proposals, assumptions and open questions. Silence
is not agreement; a repeated answer supports those examples, not general model
fidelity. Honor interactive, final-review or explicitly delegated work. A delegated
PO relays questions through its host; it does not pretend to have interviewed a
person. Stop exploring when remaining questions do not change the current scope,
observable behavior or material trade-off; retain relevant unknowns visibly.

### Natural questions that can reveal properties

Use only questions relevant to the operation and current uncertainty. These are
candidate distinctions, not a completeness theorem or a compulsory checklist.
Do not name the algebra to the human unless it helps them.

| Ask in the domain | Distinction for downstream design |
|---|---|
| If the person submits twice, what should happen? | Repetition / idempotence |
| If these actions arrive in the opposite order, what changes? | Order dependence / commutativity |
| Can they undo it, and until when? | Reversibility / terminal state |
| When this amount is moved or split, what total must stay the same? | Conservation |
| Can both of these be true at once? | Mutual exclusion |
| If it stops halfway, what does the person see and what can they do? | Failure / recovery / compensation |
| Could doing this leave them with no safe next action? | Progress / non-trapping |

Accept answers such as “order matters” or “we have not decided”. Select operation
pairs that share a resource or rule; do not enumerate every mathematical pairing.
Record the answer and conditions before deriving a law. Examples remain product
choices; the architect determines the appropriate types, laws and proof bounds.

### Visual exploration and human view

For a changed human interface, offer a proportionate sketch, wireframe or navigable
prototype. Explain the uncertainty it resolves; reuse existing components and
honor a declined offer. The host can select `nw-ux-designer` and a bounded
`nw-spike`; distinguish simulated behavior from real integration. Discuss relevant
loading, empty, error, permission and recovery states, without inventing a quota
of scenarios. Record what feedback changed, not just that a prototype exists.

Use the brief's nwdes HTML view as the shared reading surface.
Put intent, journey, examples, decisions and open questions before formal detail.
Ask the human to explain or challenge a concrete consequence when understanding
is uncertain; do not turn comprehension checks into an examination or approval
ceremony. The renderer cannot repair unclear semantic input.

## The Three Amigos

Three perspectives revealing each other's blindspots:

1. **Problem Owner** (PO, BA, Domain Expert): business need | acceptance criteria | domain knowledge
2. **Problem Solver** (Developer, Engineer): technical constraints | implementation complexity | technical edge cases
3. **Skeptic** (Tester, QA): failure modes | edge cases and boundaries | challenge assumptions

### Session Structure (25-minute timebox)

1. Read user story aloud (2 min) -- shared context
2. Identify acceptance criteria/rules (8 min) -- "what must be true for done?"
3. Explore examples per rule (12 min) -- concrete scenarios, edge cases
4. Capture questions (ongoing) -- unknowns on red cards
5. Review and summarize (3 min) -- shared understanding check

If unmappable in 25 min: too large (split) | too uncertain (spike) | team needs practice.

## Example Mapping

### Four Card Types

- Yellow: User Story (1 per session) | Blue: Business Rules/AC | Green: Concrete Examples | Red: Questions/Unknowns (blockers)

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

Use when: story entering sprint | multiple edge cases | team uncertain about scope | cross-functional clarification needed.
Skip when: trivial well-understood story | pure technical refactoring with no behavior change | strong shared understanding already.

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

Abstract rules hide assumptions. Concrete examples force decisions.

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
- **Given** = context (preconditions, system state)
- **When** = event/action (user action, system trigger)
- **Then** = outcome (observable results, state changes)

### Scenario Titles: Business Outcomes Only

Scenario titles describe WHAT the user achieves, never HOW the system implements it.

| BAD (implementation) | GOOD (business outcome) |
|---|---|
| FileWatcher triggers TreeView refresh | Dashboard updates in real-time |
| Observer writes state.json on event | Wave progress is captured when a phase completes |
| Debounce prevents rapid writes | Rapid progress changes render smoothly |
| Atomic write prevents partial reads | Dashboard always sees consistent data |

**Rule**: If the title contains a class name, method name, file name, or protocol detail, rewrite it as the user-observable outcome.

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

### Choose examples that distinguish the rule
Use a typical case and add boundary or failure cases when they expose relevant
uncertainty. There is no fixed count per rule.

## Business Outcome Focus: Five Whys

Apply Five Whys to connect stories to business value:

```
Story: "Add CSV export for reports"
Why? "Users can export data"
Why? "Analyze in Excel"
Why? "No pivot tables in our app"
Why? "Need to slice data by dimensions"
Why? "Identify trends for business decisions"

Real need: better analytical capabilities, not CSV export
```

Focus on behaviors contributing to business results. Challenge features lacking clear business value.

## Acceptance Criteria Style

Traditional (implementation-focused) -- avoid:
- "API endpoint accepts POST requests" | "Response returns JSON with 201 status"

BDD-style (outcome-focused) -- use:
- "Customer can submit order even when offline" | "Order confirmed within 2 seconds" | "Customer receives email confirmation"

Shift from "system does X" to "user achieves Y."

## Confirmation Bias Defense

### Technique 1: Reverse Assumptions
Assumption: "Users fill out the form correctly."
Reverse: empty form | garbage data | 50,000 characters | 100 submissions in 10 seconds.

### Technique 2: Evil User Persona
"Malicious Mike" tries SQL injection, URL manipulation, unauthorized access. "Careless Cathy" never reads instructions, clicks back mid-process, refreshes constantly.

### Technique 3: Challenge the example
Consider a boundary, unusual valid case or failure when it can change the rule.
Choose the smallest contrasting example; do not require every category per rule.

## Red Card Management

Red cards are unresolved questions. Identify which prevent the current value
from being understood and which can be deferred explicitly. Never silently turn
an open question into a requirement; do not block unrelated understood work.

Resolution process:
1. Capture during session | 2. Assign owner (usually BA/PO) | 3. Set deadline (before dev starts) | 4. Follow-up session if answer reveals new complexity

Good red cards: "Character limit for product descriptions?" | "PDFs or only images?" | "What happens to orders if payment gateway is down?"

## Requirements Document Structure

BDD hierarchy:

```
Business Capability (Epic)
  +-- Feature (Theme)
      +-- User Story
          +-- Acceptance Criteria (Rules)
              +-- Scenarios (Examples)
```

Each level includes: business value | user context | concrete examples | Given-When-Then scenarios | tracked questions with resolution status.

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

Output: 2-3 stories mapped | 10-15 scenarios drafted | red cards assigned.

## Example Mapping Anti-Patterns

1. **No examples, just rules**: Blue cards without green cards. Rules are abstract. Force concrete examples for each rule.
2. **Too many rules (story too big)**: >5-6 blue cards means split needed.
3. **Implementation details in examples**: "POST to /api/users with JSON" instead of "I register with email." Describe user-observable behavior.
4. **Ignoring red cards**: Proceeding with unresolved questions leads to rework.

## User Story Mapping

Decompose epics into stories by tracing the complete user workflow.

### Process

1. **Map workflow end-to-end**: Walk complete user journey from trigger to outcome. Each step becomes a column.
2. **Identify touchpoints**: List system interactions, decisions, and information needs at each step.
3. **Break into stories**: Group touchpoints into coherent user stories delivering demonstrable slices.
4. **Prioritize by value**: Top row = minimum viable workflow (walking skeleton). Lower rows = enhancements.

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

Story mapping complements Example Mapping: use story mapping to identify WHICH stories, then Example Mapping to explore EACH story in depth.

## Requirements Completeness Check

Consider functional behavior, quality attributes and business rules when
relevant to the current outcome. No fixed category quota or phase is required.

### Functional Requirements
- Business capabilities and features | User interactions and system responses
- Data processing and transformation rules | Integration and interface requirements
- Validation: testable through acceptance tests | traceable to business objectives | complete and unambiguous

### Non-Functional Requirements (NFRs)
- Performance: response time, throughput, scalability | Security: authentication, authorization, data protection
- Usability: user experience, accessibility | Reliability: availability, fault tolerance, recovery
- Validation: quantifiable metrics and thresholds | testable through automated validation

### Business Rules
- Business policy enforcement | Data validation and integrity rules
- Workflow and process constraints | Compliance and regulatory requirements
- Validation: clear rule specification with examples | exception handling defined | rule precedence documented

Flag a missing category only when an identified product risk requires it.
Do not invent NFR thresholds or policies to fill a template.

## Domain Language Discovery

Formalize the ubiquitous language process. Domain language primacy (Core Principle 4) requires deliberate discovery.

### Phase 1: Discovery
- Identify domain-specific terminology through stakeholder conversations
- Document existing business language and definitions | Capture synonyms and variations
- Flag ambiguous terms requiring clarification

### Phase 2: Definition
- Collaborate with domain experts for precise definitions | Resolve terminology conflicts
- Create glossary with examples per term | Validate definitions with all stakeholder groups

### Phase 3: Adoption
- Integrate ubiquitous language into all requirements artifacts
- Use agreed terms consistently in stories, AC, and scenarios
- Include glossary in handoff package for downstream waves (DESIGN, DISTILL)

Terms discovered here feed directly into BDD scenarios -- Given/When/Then uses the ubiquitous language, ensuring zero translation loss.
