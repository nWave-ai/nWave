# Tutorial: Your First Feature

Learn nWave by building a complete feature end-to-end.

> **Note**: This tutorial covers a brownfield feature (adding to an existing project). If you're starting a **new product** or need to **explore multiple approaches**, consider running `/nw-discover` and `/nw-diverge` first. See the [DIVERGE Wave Guide](../diverge-wave-guide/).

**Prerequisites**:
- **Platform**: Linux, macOS, or Windows (WSL2 required)
- nWave installed: `pipx install nwave-ai && nwave-ai install` (in terminal, not Claude Code)
- Claude Code reopened after install
- A Python project with pytest
- Basic TDD familiarity

> **Stuck or unsure about nWave?** Type `/nw-buddy` at any point to ask the concierge agent about methodology, commands, or next steps.

---

## What You'll Do

You'll build a "user login" feature through four commands. Each command launches a specialized AI agent that produces artifacts for you to review before continuing.

```text
/nw-discuss  →  /nw-design  →  /nw-distill  →  /nw-deliver
Requirements    Architecture    Acceptance      TDD
                                Tests           Implementation
```

> **Full wave sequence**: nWave has 7 waves: DISCOVER, DIVERGE, DISCUSS, DESIGN, DEVOPS, DISTILL, DELIVER. This tutorial uses the 4 most common ones for brownfield features. See the [DIVERGE Wave Guide](../diverge-wave-guide/) for design exploration and [Tutorial 4](../tutorial-discovery/) for product discovery.

At every step, the agent generates — you review and approve.

---

## Step 1: Gather Requirements

Start by telling nWave what you want to build.

```
/nw-discuss "user login with email and password"
```

The `@product-owner` agent will ask you clarifying questions:
- Who are the users?
- What happens on invalid credentials?
- Are there rate limits?

Answer in plain language. The agent produces user stories and requirements at:

```
docs/feature/user-login/discuss/user-stories.md
```

> **SSOT model**: Product-level documents (journeys, architecture) are in `docs/product/`. Feature-specific artifacts (user stories, wave decisions) are in `docs/feature/{feature-id}/discuss/`.

**Your checkpoint**: Open the user stories file. Check that it captures what you want. Edit anything that's wrong. The agent works for you -- not the other way around.

---

## Step 2: Design the Architecture

With requirements in hand, design how the feature will be built.

```
/nw-design
```

The command asks two questions before it starts:

1. **Design scope**: system (infrastructure), domain (DDD/bounded contexts), or application (component boundaries). For most features, pick **application**.
2. **Interaction mode**: "Guide me" (collaborative Q&A) or "Propose" (autonomous analysis with trade-offs). Pick whichever suits your style.

Based on your scope choice, `/nw-design` routes to the right specialist:

| Scope | Architect | Focus |
|-------|-----------|-------|
| System / infrastructure | Titan (`@system-designer`) | Scalability, caching, load balancing, message queues |
| Domain / bounded contexts | Hera (`@ddd-architect`) | DDD, aggregates, Event Modeling, event sourcing |
| Application / components | Morgan (`@solution-architect`) | Component boundaries, hexagonal architecture, ADRs |

For a "user login" feature, **application** scope is the right choice. Morgan reads your requirements and produces:
- An architecture document with component boundaries
- Architecture Decision Records (ADRs) for key choices
- C4 diagrams (Mermaid) showing how pieces connect

Output lands in `docs/product/architecture/` (SSOT) and `docs/feature/user-login/design/` (feature delta).

**Your checkpoint**: Review the architecture. Does the component structure make sense? Are the technology choices appropriate? Push back on anything that feels wrong.

---

## Step 3: Define Acceptance Tests

Before writing any code, define what "done" looks like.

```
/nw-distill "user-login"
```

The `@acceptance-designer` agent creates Given-When-Then scenarios based on your requirements:

```python
# tests/acceptance/test_us001_user_login.py

def test_scenario_001_valid_credentials():
    """Given a registered user
    When they submit valid email and password
    Then they receive an authentication token"""

def test_scenario_002_invalid_password():
    """Given a registered user
    When they submit an incorrect password
    Then they receive an authentication error"""

def test_scenario_003_nonexistent_user():
    """Given an unregistered email
    When they attempt to login
    Then they receive an authentication error"""
```

These tests will fail — that's the point. They define the target.

**Your checkpoint**: Read each scenario. Do they cover the important cases? Missing an edge case? Ask the agent to add it.

---

## Step 4: Deliver with TDD

Now build the feature. This single command runs the full inner loop.

```
/nw-deliver
```

Here's what happens automatically:

1. **Roadmap**: `@solution-architect` creates one step per acceptance test scenario
2. **Execute**: `@software-crafter` makes each test pass using Outside-In TDD (RED → GREEN)
3. **Refactor**: Code is cleaned up after each green test
4. **Review**: `@software-crafter-reviewer` checks code quality
5. **Mutation Test**: Validates your test suite catches real bugs
6. **Finalize**: Archives the feature and cleans up workflow files

Each acceptance test becomes one TDD cycle. Three scenarios = three cycles. When it finishes, all acceptance tests pass.

**Your checkpoint**: Run the tests yourself to confirm:

```bash
pytest tests/acceptance/test_us001_user_login.py -v
```

---

## What Just Happened

Four commands. Four human checkpoints. One working feature.

```text
You typed          Agent produced              You reviewed
─────────          ──────────────              ────────────
/nw-discuss        Requirements doc            ✓ Scope correct?
/nw-design         Architecture + ADRs         ✓ Design sound?
/nw-distill        Acceptance test scenarios    ✓ Coverage complete?
/nw-deliver        Working implementation       ✓ Tests pass?
```

Your feature artifacts live in `docs/feature/user-login/` (feature deltas) and `docs/product/` (SSOT) -- requirements, architecture, and execution history are all traceable.

---

## Next Steps

- **Other workflows**: See [Jobs To Be Done Guide](../jobs-to-be-done-guide/) for brownfield, bug fix, and refactoring patterns
- **Manual control**: Run each DELIVER step individually instead of using the automated orchestration
- **Peer review**: Add quality gates with reviewer agents — see [How to Invoke Reviewers](../invoke-reviewer-agents/)
- **All commands**: See [nWave Commands Reference](../../reference/commands/index.md)

