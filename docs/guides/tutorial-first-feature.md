# Tutorial: Your First Feature with nWave

**Version**: 1.0.0
**Date**: 2026-02-13
**Status**: Production Ready

Build a feature from requirements to working code using the nWave 6-wave workflow.

**Prerequisites**:
- nWave installed (`pipx install nwave-ai && nwave-ai install`)
- Claude Code open in a Python project with pytest
- Basic familiarity with TDD concepts

---

## What You'll Do

You'll build a "user login" feature through four commands. Each command launches a specialized AI agent that produces artifacts for you to review before continuing.

```text
/nw:discuss  →  /nw:design  →  /nw:distill  →  /nw:deliver
Requirements    Architecture    Acceptance      TDD
                                Tests           Implementation
```

At every step, the agent generates — you review and approve.

---

## Step 1: Gather Requirements

Start by telling nWave what you want to build.

```
/nw:discuss "user login with email and password"
```

The `@product-owner` agent will ask you clarifying questions:
- Who are the users?
- What happens on invalid credentials?
- Are there rate limits?

Answer in plain language. The agent produces a requirements document at:

```
docs/feature/user-login/discuss/requirements.md
```

**Your checkpoint**: Open the requirements file. Check that it captures what you want. Edit anything that's wrong. The agent works for you — not the other way around.

---

## Step 2: Design the Architecture

With requirements in hand, design how the feature will be built.

```
/nw:design --architecture=hexagonal
```

The `@solution-architect` agent reads your requirements and produces:
- An architecture document with component boundaries
- Architecture Decision Records (ADRs) for key choices
- A component diagram showing how pieces connect

Output lands at:

```
docs/feature/user-login/design/architecture-design.md
```

**Your checkpoint**: Review the architecture. Does the component structure make sense? Are the technology choices appropriate? Push back on anything that feels wrong.

---

## Step 3: Define Acceptance Tests

Before writing any code, define what "done" looks like.

```
/nw:distill "user-login"
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
/nw:deliver
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
/nw:discuss        Requirements doc            ✓ Scope correct?
/nw:design         Architecture + ADRs         ✓ Design sound?
/nw:distill        Acceptance test scenarios    ✓ Coverage complete?
/nw:deliver        Working implementation       ✓ Tests pass?
```

Your feature artifacts live in `docs/feature/user-login/` — requirements, architecture, and execution history are all traceable.

---

## Next Steps

- **Other workflows**: See [Jobs To Be Done Guide](./jobs-to-be-done-guide.md) for brownfield, bug fix, and refactoring patterns
- **Manual control**: Run each DELIVER step individually instead of using the automated orchestration — see [README](../../README.md)
- **Peer review**: Add quality gates with reviewer agents — see [How to Invoke Reviewers](./invoke-reviewer-agents.md)
- **All commands**: See [nWave Commands Reference](../reference/nwave-commands-reference.md)

---

**Last Updated**: 2026-02-13
**Type**: Tutorial
