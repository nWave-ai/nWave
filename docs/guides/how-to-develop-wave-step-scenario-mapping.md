# How To: Execute DEVELOP Wave with Step-to-Scenario Mapping

**Document Type**: How-to Guide
**Last Updated**: 2026-01-24
**Related**: [Outside-In TDD: Step-to-Scenario Mapping Principle](../reference/step-template-mapped-scenario-field.md)

## Goal

Successfully execute a DEVELOP wave where each roadmap step implements exactly one acceptance test scenario following Outside-In TDD discipline.

## Before You Start

You will need:
- A completed acceptance test file with scenarios (from DISTILL wave)
- The nWave framework installed via `pipx install nwave-ai && nwave-ai install`
- A project with user story identification (e.g., `us001`, `us002`)

## Step 1: Count Your Acceptance Test Scenarios

First, determine how many acceptance test scenarios exist in your feature.

**Location**: `tests/acceptance/test_us00X_*.py`

**Command**:
```bash
grep 'def test_' tests/acceptance/test_us001_*.py | wc -l
```

**Expected Output**:
```
4
```

This tells you that you need exactly **4 steps** in your roadmap (one per scenario).

## Step 2: Verify the Step-to-Scenario Mapping Principle

Before proceeding, review the mapping rule:

**The Rule**: `num_roadmap_steps == num_acceptance_scenarios`

**Example**:
- 4 acceptance test scenarios = 4 roadmap steps = 4 step files (01-01, 01-02, 01-03, 01-04)
- Each step makes exactly 1 scenario pass (RED → GREEN)

## Step 3: Create a Measurement Baseline

Initialize the DEVELOP wave with quantitative baseline data (this is mandatory).

**Command**:
```
/nw:baseline "{project_id}" "{feature_description}"
```

**Example**:
```
/nw:baseline "des" "Add DES validation markers to commands"
```

**Output Location**: `docs/feature/{project_id}/baseline.yaml`

**Deliverables**:
- Current state metrics (performance, complexity, coverage)
- Measurement methodology documentation
- Target improvement thresholds

## Step 4: Create the Roadmap with Scenario Mapping

Create a comprehensive roadmap where each step explicitly maps to one acceptance scenario.

**Command**:
```
/nw:roadmap "{project_id}" "{feature_description}"
```

**Pre-Check** (Agent will verify this):
1. Agent reads acceptance tests: `tests/acceptance/test_us00X_*.py`
2. Agent counts scenarios and creates N steps for N scenarios
3. Agent flags if count mismatch is detected

**Roadmap Structure**:
```yaml
steps:
  - step_id: "01-01"
    name: "Make test_execute_command_includes_des_validation_marker pass"
    acceptance_test_scenario: "test_scenario_001_execute_command"
    acceptance_test_file: "tests/acceptance/test_us001_*.py"
    description: "Implement code to make test_scenario_001 pass (RED → GREEN)"

  - step_id: "01-02"
    name: "Make test_ad_hoc_task_bypasses_des_validation pass"
    acceptance_test_scenario: "test_scenario_002_ad_hoc_task"
    acceptance_test_file: "tests/acceptance/test_us001_*.py"
    description: "Implement code to make test_scenario_002 pass (RED → GREEN)"

  # ... continue for each scenario
```

**Critical Fields** (Must include):
- `acceptance_test_scenario`: Maps to exact test function name
- `acceptance_test_file`: Points to the feature acceptance test file
- `description`: Explicitly states "Make test_X pass (RED → GREEN)"

**Output Location**: `docs/feature/{project_id}/roadmap.yaml`

## Step 5: Split Roadmap into Atomic Step Files

Generate individual step files that will be executed in sequence.

**Command**:
```
/nw:split "{project_id}" "{feature_description}"
```

**Validation** (Agent will verify):
- `assert num_steps == num_acceptance_scenarios`
- Each step file contains exactly one acceptance test scenario reference
- Each step maps to roadmap via `step_id`

**Step File Template**:
```json
{
  "task_specification": {
    "task_id": "01-01",
    "acceptance_test_scenario": "test_scenario_001_execute_command",
    "acceptance_test_file": "tests/acceptance/test_us001_*.py",
    "description": "Make test_scenario_001 pass (RED → GREEN)",
    "phase_2_acceptance_test_command": "pytest tests/acceptance/test_us001_*.py::test_scenario_001_* -v"
  }
}
```

**Output Location**: `docs/feature/{project_id}/steps/01-01.json` through `01-0N.json`

## Step 6: Execute Each Step with RED → GREEN Discipline

Execute steps sequentially, with each step focusing on a single acceptance scenario.

**Command** (execute each step):
```
/nw:execute "{project_id}" "01-01"
/nw:execute "{project_id}" "01-02"
/nw:execute "{project_id}" "01-03"
/nw:execute "{project_id}" "01-04"
```

**For Each Step**:

### Phase 2: Acceptance Test (RED)
Run only the mapped scenario:
```bash
pytest tests/acceptance/test_us001_*.py::test_scenario_001_* -v
```
**Expected**: FAIL (RED state)

### Phase 6: Acceptance Test (GREEN)
Run the same scenario again after implementation:
```bash
pytest tests/acceptance/test_us001_*.py::test_scenario_001_* -v
```
**Expected**: PASS (GREEN state)

### Verify No Regression
Run all acceptance tests to ensure previous steps aren't broken:
```bash
pytest tests/acceptance/ -v
```
**Expected**: All previously passing tests still pass, new test now passes

## Step 7: Finalize the Wave

After all steps complete successfully, finalize the wave (archival and reporting).

**Command**:
```
/nw:finalize "{project_id}"
```

**Deliverables**:
- Wave completion report
- Metrics analysis (baseline vs. final state)
- Archival of step files

## Validation Checklist

Before declaring DEVELOP wave complete:

- [ ] Baseline created: `docs/feature/{project_id}/baseline.yaml` exists
- [ ] Roadmap created: `docs/feature/{project_id}/roadmap.yaml` exists
- [ ] Step count matches: `num_steps == num_acceptance_scenarios`
- [ ] Each step has `acceptance_test_scenario` field
- [ ] All step files created: `docs/feature/{project_id}/steps/01-01.json` through `01-0N.json`
- [ ] Each step executed: All 14 phases completed (PREPARE through COMMIT)
- [ ] All acceptance tests pass: `pytest tests/acceptance/ -v` = 100% pass
- [ ] No test regressions: Previously passing tests still pass
- [ ] Wave finalized: `docs/feature/{project_id}/` contains completion report

## Common Issues

### Issue: "Count Mismatch" Error
**Problem**: Roadmap has 11 steps but only 4 acceptance test scenarios.

**Solution**:
1. Verify the acceptance test file: `tests/acceptance/test_us001_*.py`
2. Count scenarios: `grep 'def test_' file.py | wc -l`
3. Reduce roadmap to match scenario count
4. Mark infrastructure steps as type `infrastructure` (not feature)

**Reference**: [Outside-In TDD: Step-to-Scenario Mapping Principle](../reference/step-template-mapped-scenario-field.md)

### Issue: Multiple Scenarios Pass in One Step
**Problem**: Step 01-01 makes tests 1, 2, and 3 pass instead of just test 1.

**Solution**:
- This violates Outside-In TDD discipline
- Split the implementation into separate steps
- Each step should make exactly 1 scenario pass
- Refactor to isolate concerns per scenario

### Issue: "Infrastructure Step" Exception
**Problem**: Need a step for database migration or environment setup (no acceptance test).

**Solution**:
1. Create step with type `infrastructure`
2. Leave `acceptance_test_scenario` empty
3. Document manual verification in step file
4. Do NOT count toward feature scenario mapping

## Related Documentation

- **Principle**: [Outside-In TDD: Step-to-Scenario Mapping](../reference/step-template-mapped-scenario-field.md) - Understand the discipline behind step-to-scenario mapping
- **Reference**: [Step Template Mapped Scenario Field](../reference/step-template-mapped-scenario-field.md) - Full schema specification for mapping fields
- **Reference**: [nWave Commands Reference](../reference/nwave-commands-reference.md) - Complete command specifications
- **Agent Specification**: See `~/.claude/agents/nw/solution-architect.md` for step generation details

---

**Document Owner**: AI-Craft Team
**Last Review**: 2026-01-24
**Next Review**: After DES US-002 completion
