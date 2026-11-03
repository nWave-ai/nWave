# How To: Deliver a Slice with Scenario-to-Row Mapping

**Document Type**: How-to Guide
**Last Updated**: 2026-10-23
**Related**: Outside-In TDD: Scenario-to-Row Mapping Principle

**Audience.** The steps are run by the root assistant — the session you talk to: it executes the `nwdes` verbs and the test runs below. The person reads along, decides scope and trade-offs, and points the assistant at this guide — the sentence to paste is in [For your assistant](../README.md#for-your-assistant).

## Goal

Successfully deliver a slice through the nwdes route where each acceptance test scenario is recorded as exactly one acceptance row and observed RED, then GREEN, following Outside-In TDD discipline.

## Before You Start

You will need:
- A completed acceptance test file with scenarios (from the DISTILL wave or the acceptance designer)
- The nWave framework installed via `sh -c "$(curl -fsSL https://raw.githubusercontent.com/nWave-ai/nWave/main/scripts/install/install.sh)"`
- A feature created with `nwdes feature new`, so its `handoff.json` (`$H` below) exists
- The slice you are delivering (for example `S1`)

Run every nwdes command from the top level of the checkout. Roots default to cwd and the repository root, and the first add, set or remove creates the draft.

## Step 1: Count Your Acceptance Test Scenarios

First, determine how many acceptance test scenarios exist in your slice.

**Location**: `tests/acceptance/test_us00X_*.py`

**Command**:
```bash
grep 'def test_' tests/acceptance/test_us001_*.py | wc -l
```

**Expected Output**:
```
4
```

This tells you that the slice needs exactly **4 acceptance rows** (one per scenario).

## Step 2: Verify the Scenario-to-Row Mapping Principle

Before proceeding, review the mapping rule:

**The Rule**: `num_acceptance_rows == num_acceptance_scenarios`

**Example**:
- 4 acceptance test scenarios = 4 acceptance rows in the slice's `### S1` section of `acceptance.md`
- Each row names one test locator through `--test` and the promises it covers through `--covers`
- Each scenario goes RED → GREEN on its own declared command

## Step 3: Record the Acceptance Rows

Run `/nw-deliver` to route the Request. When the slice reaches its acceptance stage, give the acceptance designer the complete bundle that nwdes builds:

```bash
nwdes prompt --role nw-acceptance-designer --handoff "$H" --slice S1 --jev unauthorized
```

**Pre-Check** (the designer verifies this):
1. The designer reads the acceptance tests: `tests/acceptance/test_us00X_*.py`
2. It counts scenarios and records one row per scenario
3. It flags a count mismatch before closing

**Recording**: the designer records one row per scenario with `nwdes acceptance row add` and ends the draft with `nwdes acceptance close`.

```bash
nwdes acceptance row add --slice S1 \
  --stimulus 'The user runs the command' \
  --expected 'The command output is shown' \
  --user-result 'The user sees the result' \
  --disposition Tested \
  --test 'tests/acceptance/test_us001_x.py::test_scenario_001_execute_command'
```

**Critical Fields** (must include):
- `--test`: the exact test function locator for a Tested row
- `--covers`: the promise or design identities the scenario covers
- `--stimulus`, `--expected`, `--user-result`: the observation the scenario makes

**Output Location**: `docs/feature/{project_id}/handoff.json`, with the rendered `acceptance.md` beside it.

## Step 4: Verify the Rows

nwdes renders the rows into `acceptance.md`. Verify them before crafting.

**Validation**:
- `assert num_rows == num_acceptance_scenarios`
- Each Tested row references exactly one scenario locator
- Each row cites known identities in `--covers`; an unknown reference is refused as `DanglingReference`

## Step 5: Craft with RED → GREEN Discipline

The crafter implements the slice against the immutable oracle and records its files and commands with `nwdes craft`. The host runs the declared commands and observes the actual results.

```bash
nwdes prompt --role nw-software-crafter --handoff "$H" --slice S1 --jev unauthorized
```

**For Each Scenario**:

### Acceptance Test (RED)
Run only the mapped scenario:
```bash
pytest tests/acceptance/test_us001_*.py::test_scenario_001_* -v
```
**Expected**: FAIL (RED state)

### Acceptance Test (GREEN)
Run the same scenario again after implementation:
```bash
pytest tests/acceptance/test_us001_*.py::test_scenario_001_* -v
```
**Expected**: PASS (GREEN state)

### Verify No Regression
Run all acceptance tests to ensure earlier scenarios aren't broken:
```bash
pytest tests/acceptance/ -v
```
**Expected**: All previously passing tests still pass, new test now passes

## Step 6: Review, Examine and Integrate

After every slice is GREEN, run one review and one examination of the whole candidate, then integrate.

**Command**:
```bash
nwdes lane compose --feature "{project_id}"
nwdes lane integrate --feature "{project_id}" --expected "$EXPECTED" --candidate "$CANDIDATE"
```

**Deliverables**:
- Accepted whole-candidate review and examiner verdicts
- Craft and review run records under `docs/feature/{project_id}/runs/`
- Trunk fast-forwarded to the candidate and the lane removed

See [Deliver a feature with nwdes](../nwdes/deliver-feature.md) for the complete route, including the lane-free variant.

## Validation Checklist

Before declaring the delivery complete:

- [ ] Handoff recorded: `docs/feature/{project_id}/handoff.json` exists
- [ ] Row count matches: `num_rows == num_acceptance_scenarios`
- [ ] Each Tested row has a `--test` locator
- [ ] Each scenario observed RED, then GREEN, with its declared command
- [ ] All acceptance tests pass: `pytest tests/acceptance/ -v` = 100% pass
- [ ] No test regressions: Previously passing tests still pass
- [ ] Craft run closed accepted for every slice
- [ ] Whole-candidate review and examiner verdicts accepted
- [ ] Candidate integrated with `nwdes lane integrate`

## Common Issues

### Issue: "Count Mismatch"
**Problem**: The slice has 11 acceptance rows but only 4 acceptance test scenarios.

**Solution**:
1. Verify the acceptance test file: `tests/acceptance/test_us001_*.py`
2. Count scenarios: `grep 'def test_' file.py | wc -l`
3. Remove surplus rows with `nwdes acceptance row remove`, or revise published rows with `nwdes acceptance open --from-current`
4. Record a requirement with no scenario as a `NotTested` row (see below)

**Reference**: See the Scenario-to-Row Mapping sections above

### Issue: Multiple Scenarios Pass in One Change
**Problem**: Implementing for scenario 1 also makes tests 2 and 3 pass.

**Solution**:
- This violates Outside-In TDD discipline
- Split the implementation so each scenario is observed RED before its own implementation
- Each scenario should be observed going from RED to GREEN on its own
- Refactor to isolate concerns per scenario

### Issue: "Infrastructure" Requirement Without a Scenario
**Problem**: Need a database migration or environment setup (no acceptance test).

**Solution**:
1. Record a row with `--disposition NotTested`
2. Give its `--reason` and its `--owner`
3. Document manual verification in that reason
4. Do NOT count it toward the scenario mapping

## Related Documentation

- **Principle**: Outside-In TDD: Scenario-to-Row Mapping - See the sections above for the discipline behind scenario-to-row mapping
- **Route**: [Deliver a feature with nwdes](../nwdes/deliver-feature.md) - The complete nwdes route
- **Reference**: [nWave Commands Reference](../../reference/commands/index.md) - Complete command specifications
- **Agent Specification**: See `~/.claude/agents/nw/nw-acceptance-designer.md` for acceptance row recording details

---

**Document Owner**: nWave Team
**Last Review**: 2026-10-23
**Next Review**: When the scenario-mapping contract changes
