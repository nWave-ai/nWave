---
name: nw-persona-jtbd-analysis
description: Structured persona creation and JTBD analysis methodology - persona templates, ODI job step tables, pain point mapping, success metric quantification, and multi-persona segmentation
user-invocable: false
disable-model-invocation: true
---

# Persona and JTBD Analysis

Use during Phase 1 (GATHER) when the user lacks clear personas or the "Who" section needs rigorous definition. Provides structured alternative to ad-hoc persona descriptions.

## Persona Template

For each user type, build a complete persona:

```markdown
## Persona: {Name}

**Who**: {Role description -- one sentence capturing relationship to product}
**Demographics**:
- {Characteristic 1: e.g., technical proficiency level}
- {Characteristic 2: e.g., frequency of interaction}
- {Characteristic 3: e.g., environment/context of use}
- {Characteristic 4: e.g., primary motivation}

**Jobs-to-be-Done**: (see Job Step Table below)

**Pain Points**:
- {Pain 1} -- maps to Job Step: {step name}
- {Pain 2} -- maps to Job Step: {step name}

**Success Metrics**:
- {Quantified outcome 1: e.g., "Task completed in < 2 minutes"}
- {Quantified outcome 2: e.g., "Zero manual configuration steps"}
```

## Job Step Table

Each persona has job steps describing what they accomplish. Steps follow ODI format.

| Job Step | Goal | Desired Outcome |
|----------|------|-----------------|
| {Verb} | {What the user wants to achieve} | Minimize {metric} of {undesirable state} |

### Rules for Job Steps

- Job Steps are always **verbs**: Discover, Validate, Install, Configure, Monitor, Recover
- Goals describe what the user **wants**, not what the system does
- Desired Outcomes use ODI format: "Minimize [time/effort/risk/likelihood] of [undesirable state]"
- Each step maps to a workflow point where value is created or destroyed

### Example Job Step Table

| Job Step | Goal | Desired Outcome |
|----------|------|-----------------|
| Discover | Find the right tool for the task | Minimize time to evaluate fit |
| Install | Get the tool running locally | Minimize steps to working state |
| Configure | Adapt to local environment | Minimize likelihood of misconfiguration |
| Verify | Confirm correct installation | Minimize uncertainty about readiness |
| Start | Begin productive work | Minimize time from install to first output |

## Pain Point Mapping

Every pain point maps to a specific job step. Pain points without a corresponding step indicate either a missing step or irrelevant pain point.

```
Pain Point: "I don't know if the tool supports my OS"
  -> Job Step: Discover
  -> Desired Outcome: Minimize uncertainty about compatibility

Pain Point: "Installation fails silently with no error message"
  -> Job Step: Install
  -> Desired Outcome: Minimize time to diagnose installation failures
```

Prioritize: pain points on high-frequency job steps deserve attention first.

## Success Metric Quantification

Every success metric needs a number or threshold. Qualitative metrics ("easy to use") are not actionable.

| Qualitative | Quantified |
|-------------|-----------|
| "Easy to install" | "Install completed in < 2 minutes with zero manual steps" |
| "Fast startup" | "First productive output within 30 seconds of launch" |
| "Reliable" | "Zero silent failures; all errors produce actionable messages" |
| "Intuitive" | "New user completes core task without reading documentation" |

## Multi-Persona Segmentation

Different users have fundamentally different jobs even when using the same product. Segment by **relationship** to the product.

Common axes: **Frequency** (first-time vs returning vs power user) | **Role** (end user vs admin vs developer) | **Context** (individual vs team vs CI/CD) | **Motivation** (exploration vs production vs evaluation)

### Example: Same Product, Different Jobs

| Persona | Primary Job | Key Difference |
|---------|-------------|----------------|
| Explorer | Evaluate the tool quickly | Needs fast time-to-value, minimal commitment |
| Returner | Resume work after absence | Needs state preservation, quick re-orientation |
| Deployer | Install for a team | Needs configuration management, multi-user setup |
| Automator | Integrate into CI/CD pipeline | Needs scriptability, headless operation, exit codes |

Each persona gets their own Job Step table because workflows differ. Do not merge personas -- JTBD analysis value comes from surfacing differences.

## Integration with Story Crafting

After completing persona analysis, feed results into LeanUX user story template:

1. Persona **Who** -> populated from persona template
2. Persona **Pain Points** -> inform story Problem section
3. Job Step **Desired Outcomes** -> inform AC (ODI outcomes translate to testable criteria)
4. **Success Metrics** -> inform NFR requirements in handoff package

Cross-reference: use `bdd-requirements` skill for Example Mapping once personas established. Use `jtbd-workflow-selection` skill to determine workflow for resulting stories.
