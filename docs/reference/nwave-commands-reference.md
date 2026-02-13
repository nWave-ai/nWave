# nWave Commands Reference

**Version**: 2.0.0
**Date**: 2026-02-13
**Status**: Production Ready

Quick reference for all nWave commands, agents, and file locations.

**Related Docs**:
- [Jobs To Be Done Guide](../guides/jobs-to-be-done-guide.md) (explanation)
- [How to Invoke Reviewers](../guides/invoke-reviewer-agents.md) (how-to)
- [How To: Execute DELIVER Wave with Step-to-Scenario Mapping](../guides/how-to-deliver-wave-step-scenario-mapping.md) (how-to)
- [Step Template: mapped_scenario Field Reference](./step-template-mapped-scenario-field.md) (reference)

---

## Discovery Phase Commands

| Command | Agent | Purpose |
|---------|-------|---------|
| `/nw:discover` | product-discoverer | Evidence-based product discovery and market validation |
| `/nw:discuss` | product-owner | Requirements gathering and business analysis |
| `/nw:design` | solution-architect | Architecture design with technology selection |
| `/nw:devops` | platform-architect | Platform readiness, CI/CD, infrastructure |
| `/nw:distill` | acceptance-designer | Acceptance test creation (Given-When-Then) |

---

## Execution Commands

| Command | Agent | Purpose |
|---------|-------|---------|
| `/nw:execute` | varies | Execute atomic task with state tracking |
| `/nw:refactor` | software-crafter | Systematic code refactoring (Level 1-6) |
| `/nw:review` | *-reviewer | Expert critique and quality assurance |
| `/nw:finalize` | platform-architect | Archive project and clean up workflow |

---

## Cross-Wave Specialist Commands

| Command | Agent | Purpose |
|---------|-------|---------|
| `/nw:research` | researcher | Evidence-driven research with source verification |
| `/nw:document` | researcher + documentarist | DIVIO-compliant documentation with Layer 4 peer review |
| `/nw:root-why` | troubleshooter | Toyota 5 Whys root cause analysis |
| `/nw:mikado` | software-crafter | Complex refactoring roadmaps (Mikado Method) |
| `/nw:mutation-test` | software-crafter | Layer 5 mutation testing for test suite effectiveness |
| `/nw:diagram` | solution-architect | Architecture diagram lifecycle management |

---

## Utility Commands

| Command | Agent | Purpose |
|---------|-------|---------|
| `/nw:forge` | agent-builder | Create new agents from templates |

---

## Agent Selection Guide

### Core Wave Agents

| Agent | Use For |
|-------|---------|
| `@product-discoverer` | Evidence-based product discovery and market validation |
| `@product-owner` | Requirements, business analysis, stakeholder alignment |
| `@solution-architect` | Architecture design, technology selection, planning |
| `@platform-architect` | Deployment, CI/CD, infrastructure, lifecycle management |
| `@acceptance-designer` | BDD scenarios, acceptance tests, test completeness |
| `@software-crafter` | Implementation, TDD, refactoring, code quality |

### Cross-Wave Specialist Agents

| Agent | Use For |
|-------|---------|
| `@researcher` | Information gathering, evidence collection, analysis |
| `@troubleshooter` | Root cause analysis, failure investigation (Toyota 5 Whys) |
| `@data-engineer` | Database systems, data pipelines, query optimization, data governance |
| `@documentarist` | DIVIO-compliant documentation quality assurance |
| `@agent-builder` | Create and validate new specialized agents |

### Reviewer Agents (Cost-Optimized)

Every agent has a corresponding `*-reviewer` variant using the Haiku model:

| Reviewer | Reviews |
|----------|---------|
| `@software-crafter-reviewer` | Code quality |
| `@solution-architect-reviewer` | Architecture |
| `@product-owner-reviewer` | Requirements |
| `@acceptance-designer-reviewer` | Test completeness |
| `@platform-architect-reviewer` | Deployment readiness |
| `@researcher-reviewer` | Research quality |
| `@troubleshooter-reviewer` | RCA quality |
| `@data-engineer-reviewer` | Data architecture quality |
| `@documentarist-reviewer` | Documentation quality |
| `@product-discoverer-reviewer` | Discovery quality |
| `@agent-builder-reviewer` | Agent design quality |

**Note**: `/nw:review` automatically routes to the reviewer variant.

---

## File Locations

| Artifact | Location |
|----------|----------|
| Feature Docs | `docs/feature/{feature-name}/{wave}/` |
| Research | `docs/research/{category}/{topic}.md` |
| Roadmap | `docs/feature/{feature-name}/roadmap.yaml` |
| Execution Log | `docs/feature/{feature-name}/execution-log.yaml` |
| Reviews | Embedded in execution log |

---

## Quick Job Reference Matrix

| Job | You Know What? | Sequence |
|-----|---------------|----------|
| **Greenfield** | No | [discover] → discuss → design → devops → distill → deliver |
| **Brownfield** | Yes | [research] → deliver |
| **Refactoring** | Partially | [research] → mikado → deliver |
| **Bug Fix** | Yes (symptom) | [research] → root-why → execute → review |
| **Research** | No | research → (output informs next job) |

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
# Requirements gathering
/nw:discuss "feature requirements"

# Architecture design
/nw:design --architecture=hexagonal

# Platform readiness
/nw:devops

# Create diagram
/nw:diagram --format=mermaid --level=container

# Execute task
/nw:execute @software-crafter "implement login endpoint"

# Refactor after execute
/nw:refactor --target="ServiceName" --level=3

# Review task
/nw:review @software-crafter task "implement login endpoint"

# Research with embedding
/nw:research "topic" --embed-for=solution-architect

# Create DIVIO-compliant documentation
/nw:document "Getting Started Guide" --type=tutorial
/nw:document "API Reference" --type=reference --research-depth=comprehensive

# Mutation testing (Layer 5)
/nw:mutation-test --scope=module --operators=arithmetic,logic

# Root cause analysis
/nw:root-why "problem description"
```

---

## DELIVER Wave: Step-to-Scenario Mapping Constraint

**Applies to**: `/nw:deliver` and `/nw:execute` when creating feature steps.

### The Rule

**1 Acceptance Test Scenario = 1 Roadmap Step = 1 TDD Cycle**

This is a hard constraint for Outside-In TDD, not a suggestion.

```
Acceptance Tests (from DISTILL):          Roadmap Steps (from solution-architect):
├─ test_scenario_001_execute              ├─ 01-01: Make scenario_001 pass
├─ test_scenario_002_ad_hoc               ├─ 01-02: Make scenario_002 pass
├─ test_scenario_003_research             ├─ 01-03: Make scenario_003 pass
└─ test_scenario_004_deliver              └─ 01-04: Make scenario_004 pass

VALIDATION: num_roadmap_steps == num_acceptance_scenarios ✅ REQUIRED
```

### Why It Matters

- **Preserves TDD discipline**: Each step has clear RED → GREEN progression
- **Enables traceability**: Scenario → Step → Commit (business requirement to code)
- **Prevents architectural thinking in DELIVER**: Focus on behavioral implementation, not technical layers
- **Maintains test granularity**: Can't batch multiple features into one step

### For solution-architect (within /nw:deliver)

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

### Exceptions: Infrastructure & Refactoring Steps

Steps that don't map to acceptance tests CAN exist, but only as:
- **Infrastructure steps**: Database migrations, environment setup (type: `infrastructure`)
- **Refactoring steps**: Code improvement without behavior change (type: `refactoring`)

These steps have NO acceptance test scenario and do NOT count toward the 1:1 mapping validation.

### Related Documentation

- **How-to Guide**: [How To: Execute DELIVER Wave](../guides/how-to-deliver-wave-step-scenario-mapping.md)
- **Template Reference**: [Step Template: mapped_scenario Field](./step-template-mapped-scenario-field.md)

---

**Last Updated**: 2026-02-13
**Type**: Reference
**Purity**: 98%+
