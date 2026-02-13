---
name: persona-jtbd-analysis
description: Structured persona creation and JTBD analysis methodology - persona templates, ODI job step tables, pain point mapping, success metric quantification, and multi-persona segmentation
---

# Persona and JTBD Analysis

Use this skill during Phase 1 (GATHER) when the user does not yet have clear personas or when the "Who" section of stories needs rigorous definition. Provides a structured alternative to ad-hoc persona descriptions.

## Persona Template

For each user type, build a complete persona using this structure:

```markdown
## Persona: {Name}

**Who**: {Role description -- one sentence capturing their relationship to the product}
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

Each persona has a table of job steps describing what they are trying to accomplish. Job steps follow ODI format.

| Job Step | Goal | Desired Outcome |
|----------|------|-----------------|
| {Verb} | {What the user wants to achieve} | Minimize {metric} of {undesirable state} |

### Rules for Job Steps

- Job Steps are always **verbs**: Discover, Validate, Install, Configure, Monitor, Recover
- Goals describe what the user **wants**, not what the system does
- Desired Outcomes use ODI format: "Minimize [time/effort/risk/likelihood] of [undesirable state]"
- Each step maps to a point in the user's workflow where value is created or destroyed

### Example Job Step Table

| Job Step | Goal | Desired Outcome |
|----------|------|-----------------|
| Discover | Find the right tool for the task | Minimize time to evaluate fit |
| Install | Get the tool running locally | Minimize steps to working state |
| Configure | Adapt to local environment | Minimize likelihood of misconfiguration |
| Verify | Confirm correct installation | Minimize uncertainty about readiness |
| Start | Begin productive work | Minimize time from install to first output |

## Pain Point Mapping

Every pain point maps back to a specific job step. Pain points without a corresponding job step indicate either a missing step or an irrelevant pain point.

```
Pain Point: "I don't know if the tool supports my OS"
  -> Job Step: Discover
  -> Desired Outcome: Minimize uncertainty about compatibility

Pain Point: "Installation fails silently with no error message"
  -> Job Step: Install
  -> Desired Outcome: Minimize time to diagnose installation failures
```

Use this mapping to prioritize: pain points on high-frequency job steps deserve attention first.

## Success Metric Quantification

Every success metric needs a number or threshold. Qualitative metrics ("easy to use") are not actionable.

| Qualitative | Quantified |
|-------------|-----------|
| "Easy to install" | "Install completed in < 2 minutes with zero manual steps" |
| "Fast startup" | "First productive output within 30 seconds of launch" |
| "Reliable" | "Zero silent failures; all errors produce actionable messages" |
| "Intuitive" | "New user completes core task without reading documentation" |

## Multi-Persona Segmentation

Different users have fundamentally different jobs even when using the same product. Segment personas by their **relationship** to the product.

Common segmentation axes:
- **Frequency**: First-time vs. returning vs. power user
- **Role**: End user vs. administrator vs. developer
- **Context**: Individual use vs. team deployment vs. CI/CD automation
- **Motivation**: Exploration vs. production use vs. evaluation

### Example: Same Product, Different Jobs

| Persona | Primary Job | Key Difference |
|---------|-------------|----------------|
| Explorer | Evaluate the tool quickly | Needs fast time-to-value, minimal commitment |
| Returner | Resume work after an absence | Needs state preservation, quick re-orientation |
| Deployer | Install for a team | Needs configuration management, multi-user setup |
| Automator | Integrate into CI/CD pipeline | Needs scriptability, headless operation, exit codes |

Each persona gets their own Job Step table because their workflows differ. Do not merge personas -- the value of JTBD analysis comes from surfacing these differences.

## Integration with Story Crafting

After completing persona analysis, feed results into the LeanUX user story template:

1. Persona **Who** section -> populated from the persona template
2. Persona **Pain Points** -> inform the story Problem section
3. Job Step **Desired Outcomes** -> inform Acceptance Criteria (ODI outcomes translate to testable criteria)
4. **Success Metrics** -> inform NFR requirements in handoff package

Cross-reference: use the `bdd-requirements` skill for Example Mapping once personas are established. Use the `jtbd-workflow-selection` skill to determine which workflow the resulting stories enter.
