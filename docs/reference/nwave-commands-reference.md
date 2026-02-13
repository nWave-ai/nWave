# nWave Commands Reference

**Version**: 1.6.0
**Date**: 2026-01-24
**Status**: Production Ready

Quick reference for all nWave commands, agents, and file locations.

**Related Docs**:
- [Jobs To Be Done Guide](../guides/jobs-to-be-done-guide.md) (explanation)
- [How to Invoke Reviewers](../guides/how-to-invoke-reviewers.md) (how-to)
- [How To: Execute DEVELOP Wave with Step-to-Scenario Mapping](../guides/how-to-develop-wave-step-scenario-mapping.md) (how-to)
- [Outside-In TDD: Step-to-Scenario Mapping Principle](../principles/outside-in-tdd-step-mapping.md) (explanation)
- [Step Template: mapped_scenario Field Reference](./step-template-mapped-scenario-field.md) (reference)

---

## Discovery Phase Commands

| Command | Agent | Purpose |
|---------|-------|---------|
| `/nw:start` | product-owner | Initialize nWave workflow with project brief |
| `/nw:discuss` | product-owner | Requirements gathering and business analysis |
| `/nw:design` | solution-architect | Architecture design with technology selection |
| `/nw:distill` | acceptance-designer | Acceptance test creation (Given-When-Then) |

---

## Execution Loop Commands

| Command | Agent | Purpose |
|---------|-------|---------|
| `/nw:baseline` | researcher | Establish measurement baseline (BLOCKS roadmap) |
| `/nw:roadmap` | solution-architect | Create comprehensive planning document (reads acceptance tests for scenario mapping) |
| `/nw:split` | software-crafter | Generate atomic task files from roadmap (enforces 1:1 step-to-scenario mapping) |
| `/nw:execute` | varies | Execute atomic task with state tracking |
| `/nw:review` | *-reviewer | Expert critique and quality assurance |
| `/nw:finalize` | devop | Archive project and clean up workflow |
| `/nw:deliver` | devop | Production readiness validation |

---

## Cross-Wave Specialist Commands

| Command | Agent | Purpose |
|---------|-------|---------|
| `/nw:research` | researcher | Evidence-driven research with source verification |
| `/nw:document` | researcher + documentarist | DIVIO-compliant documentation with Layer 4 peer review |
| `/nw:root-why` | troubleshooter | Toyota 5 Whys root cause analysis |
| `/nw:mikado` | software-crafter | Complex refactoring roadmaps (Mikado Method) |
| `/nw:refactor` | software-crafter | Systematic code refactoring (Level 1-6) |
| `/nw:mutation-test` | software-crafter | Layer 5 mutation testing for test suite effectiveness |
| `/nw:develop` | software-crafter | Outside-In TDD implementation |
| `/nw:diagram` | visual-architect | Architecture diagram lifecycle management |

---

## Utility Commands

| Command | Agent | Purpose |
|---------|-------|---------|
| `/nw:git` | devop | Git workflow operations (commit, branch, merge) |
| `/nw:forge` | agent-builder | Create new agents from templates |

---

## Agent Selection Guide

### Core Wave Agents

| Agent | Use For |
|-------|---------|
| `@product-owner` | Requirements, business analysis, stakeholder alignment |
| `@solution-architect` | Architecture design, technology selection, planning |
| `@acceptance-designer` | BDD scenarios, acceptance tests, test completeness |
| `@software-crafter` | Implementation, TDD, refactoring, code quality |
| `@devop` | Deployment, operations, lifecycle management, git workflow |

### Cross-Wave Specialist Agents

| Agent | Use For |
|-------|---------|
| `@researcher` | Information gathering, evidence collection, analysis |
| `@troubleshooter` | Root cause analysis, failure investigation (Toyota 5 Whys) |
| `@visual-architect` | Architecture diagrams, visual documentation |
| `@data-engineer` | Database systems, data pipelines, query optimization, data governance |
| `@product-discoverer` | Evidence-based product discovery and validation |
| `@agent-builder` | Create and validate new specialized agents |
| `@illustrator` | Visual 2D diagrams, design artifacts, workflow visualizations |
| `@documentarist` | DIVIO-compliant documentation quality assurance |

### Utility Agents

| Agent | Use For |
|-------|---------|
| `@agent-builder` | Create new agents using validated patterns and templates |

### Reviewer Agents (Cost-Optimized)

Every agent has a corresponding `*-reviewer` variant using the Haiku model:

| Reviewer | Reviews |
|----------|---------|
| `@software-crafter-reviewer` | Code quality |
| `@solution-architect-reviewer` | Architecture |
| `@product-owner-reviewer` | Requirements |
| `@acceptance-designer-reviewer` | Test completeness |
| `@devop-reviewer` | Deployment readiness |
| `@researcher-reviewer` | Research quality |
| `@troubleshooter-reviewer` | RCA quality |

**Note**: `/nw:review` automatically routes to the reviewer variant.

---

## File Locations

| Artifact | Location |
|----------|----------|
| Research | `docs/research/{category}/{topic}.md` |
| Skills | `nWave/skills/{agent}/{topic}.md` |
| Baseline | `docs/workflow/{project-id}/baseline.yaml` |
| Roadmap | `docs/workflow/{project-id}/roadmap.yaml` |
| Tasks | `docs/workflow/{project-id}/steps/*.json` |
| Reviews | Embedded in task files |
| Architecture | `docs/architecture/` |
| Architecture Diagrams | `docs/architecture/diagrams/` |
| Requirements | `docs/requirements/` |
| Agents | `nWave/agents/` |

---

## Quick Job Reference Matrix

| Job | You Know What? | Sequence |
|-----|---------------|----------|
| **Greenfield** | No | [research] -> discuss -> design -> [diagram] -> distill -> baseline -> roadmap -> split -> execute -> review |
| **Brownfield** | Yes | [research] -> baseline -> roadmap -> split -> execute -> review |
| **Refactoring** | Partially | [research] -> baseline -> mikado/roadmap -> split -> execute -> review |
| **Bug Fix** | Yes (symptom) | [research] -> root-why -> develop -> deliver |
| **Research** | No | research -> (output informs next job) |

*Items in `[brackets]` are optional.*

---

## Command Parameters

### Common Flags

| Flag | Description | Commands |
|------|-------------|----------|
| `--architecture=<type>` | hexagonal, layered, microservices | design |
| `--format=<type>` | mermaid, plantuml, c4 | diagram |
| `--level=<type>` | context, container, component | diagram |
| `--embed-for=<agent>` | Target agent for knowledge | research |

### Command Syntax Examples

```bash
# Start new project
/nw:start "Project name"

# Requirements gathering
/nw:discuss "feature requirements"

# Architecture design
/nw:design --architecture=hexagonal

# Create diagram
/nw:diagram --format=mermaid --level=container

# Baseline before roadmap
/nw:baseline "goal description"

# Create roadmap
/nw:roadmap @solution-architect "goal description"

# Split into tasks
/nw:split @devop "project-id"

# Execute task
/nw:execute @software-crafter "path/to/step.json"

# Review task
/nw:review @software-crafter task "path/to/step.json"

# Research with embedding
/nw:research "topic" --embed-for=solution-architect

# Create DIVIO-compliant documentation
/nw:document "Getting Started Guide" --type=tutorial
/nw:document "API Reference" --type=reference --research-depth=comprehensive

# Mutation testing (Layer 5)
/nw:mutation-test --scope=module --operators=arithmetic,logic

# Root cause analysis
/nw:root-why "problem description"

# Git operations
/nw:git commit
/nw:git branch "feature/name"
/nw:git push
```

---

## DEVELOP Wave: Step-to-Scenario Mapping Constraint

**Applies to**: `/nw:roadmap`, `/nw:split`, `/nw:execute` when creating feature steps.

### The Rule

**1 Acceptance Test Scenario = 1 Roadmap Step = 1 TDD Cycle**

This is a hard constraint for Outside-In TDD, not a suggestion.

```
Acceptance Tests (from DISTILL):          Roadmap Steps (from solution-architect):
├─ test_scenario_001_execute              ├─ 01-01: Make scenario_001 pass
├─ test_scenario_002_ad_hoc                ├─ 01-02: Make scenario_002 pass
├─ test_scenario_003_research              ├─ 01-03: Make scenario_003 pass
└─ test_scenario_004_develop               └─ 01-04: Make scenario_004 pass

VALIDATION: num_roadmap_steps == num_acceptance_scenarios ✅ REQUIRED
```

### Why It Matters

- **Preserves TDD discipline**: Each step has clear RED → GREEN progression
- **Enables traceability**: Scenario → Step → Commit (business requirement to code)
- **Prevents architectural thinking in DEVELOP**: Focus on behavioral implementation, not technical layers
- **Maintains test granularity**: Can't batch multiple features into one step

### For solution-architect (/nw:roadmap)

**BEFORE creating roadmap**:
1. Read acceptance test file: `tests/acceptance/test_us00X_*.py`
2. Count scenarios: `grep 'def test_' | wc -l`
3. Create exactly N steps for N scenarios
4. Each step must map to one scenario

**Each roadmap step must include**:
```yaml
- step_id: "01-01"
  acceptance_test_scenario: "test_scenario_001_execute_command"
  acceptance_test_file: "tests/acceptance/test_us001_*.py"
  description: "Make test_scenario_001 pass (RED → GREEN)"
```

### For software-crafter (/nw:split)

**Before generating step files**:
1. Count roadmap steps
2. Count acceptance test scenarios
3. **ENFORCE**: `assert num_steps == num_acceptance_scenarios`

If mismatch detected, the split command FAILS with error message directing to [principle documentation](../principles/outside-in-tdd-step-mapping.md).

### Exceptions: Infrastructure & Refactoring Steps

Steps that don't map to acceptance tests CAN exist, but only as:
- **Infrastructure steps**: Database migrations, environment setup (type: `infrastructure`)
- **Refactoring steps**: Code improvement without behavior change (type: `refactoring`)

These steps have NO acceptance test scenario and do NOT count toward the 1:1 mapping validation.

### Related Documentation

- **Detailed Principle**: [Outside-In TDD: Step-to-Scenario Mapping Principle](../principles/outside-in-tdd-step-mapping.md)
- **How-to Guide**: [How To: Execute DEVELOP Wave](../guides/how-to-develop-wave-step-scenario-mapping.md)
- **Template Reference**: [Step Template: mapped_scenario Field](./step-template-mapped-scenario-field.md)
- **Agent Spec**: [solution-architect - Step-to-Scenario Mapping core principle](../../nWave/agents/solution-architect.md)

---

**Last Updated**: 2026-01-24
**Type**: Reference
**Purity**: 98%+
