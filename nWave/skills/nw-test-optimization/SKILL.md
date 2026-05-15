---
name: nw-test-optimization
description: Methodology for minimizing test count while maximizing behavioral coverage - behavior definition, anti-pattern catalog, consolidation patterns, stopping criterion, coverage-preserving validation
user-invocable: false
disable-model-invocation: true
---

# Test Optimization Methodology

## Mission

> Minimize tests, maximize value, reduce feedback time, maintain quality.
> (Ale, 2026-04-28: "Bisogna minimizzare i test, massimizzare il valore per ridurre il tempo di feedback, mantenendo la qualità.")

This skill operationalizes that mission. Apply during DELIVER COMMIT, scheduled audits, or `/nw-optimize-tests` invocations.

## 1. Behavior Definition (the loose joint, closed)

The phrase "distinct behavior" in the test budget formula `max_unit_tests = 2 × distinct_behaviors` is the loose joint that lets test counts inflate. Close it with these rules.

### 1.1 What IS a behavior

A behavior is an **observable outcome via a port** (driving or driven):

- A return value from a driving-port call given specific inputs
- A state change visible through a driving-port query after an action
- A side effect at a driven-port boundary (call sequence + payload)
- An exception raised from a driving port
- A business invariant that holds across a class of inputs

### 1.2 What is NOT a behavior

- Phrase presence in markdown — that is one **document contract**, not one behavior per phrase
- AST shape (try/except wrapping, decorator presence, import order) — that is source structure, not runtime behavior
- Type system facts (subclass relations, attribute presence) — Python language guarantees, not domain behaviors
- Internal data shape (dataclass field assignment, dict structure) — language guarantees
- Internal method calls (mock.assert_called_with) — implementation, not outcome
- Source-shape compliance — runtime behavior on each supported environment IS the behavior, not the source it was compiled from

### 1.3 Counting rules — concrete cases

| Surface | Behaviors |
|---------|-----------|
| Markdown skill with required phrases | 1 (the file conforms to the contract) |
| 5 skill files × 30 required phrases each | 5 (one per file), NOT 150 |
| Function with N input variations, same assertion shape | 1 (parametrize the variations) |
| Function with N error types, distinct messages and paths | N |
| Adapter that calls a driven port with ordered payload | 1 per call site, asserted once |
| Pure dataclass storing fields | 0 (Python guarantees this) |
| ABC with 5 abstract methods | 0 (Python guarantees abstract enforcement) |

### 1.4 Re-derivation procedure

Before counting tests in a target scope:

1. List the driving ports the scope exposes
2. For each driving port, list the observable outcomes it produces (return values, state, side effects, exceptions)
3. Collapse outcomes that vary only by input value into one parametrized behavior
4. Count the result. That number × 2 = budget.

If your count exceeds 2× behaviors, you have either testing theater or genuinely high behavioral surface — investigate which before adding mass.

## 2. Banned Anti-Patterns

Each pattern below is an automatic block at review. Counter-example shows the right test.

### 2.1 Language-Guarantee Tests

Tests that assert what the language already guarantees.

```python
# BANNED — Python @abstractmethod already enforces this at instantiation
def test_config_port_interface_defines_required_methods():
    assert issubclass(ConfigPort, ABC)
    assert hasattr(ConfigPort, "get_timeout_threshold_default")

# CORRECT — test runtime behavior of a concrete adapter
def test_config_adapter_returns_default_when_unset():
    adapter = EnvironmentConfigAdapter(env={})
    assert adapter.get_timeout_threshold_default() == DEFAULT_THRESHOLD
```

### 2.2 AST-Shape Tests

Tests that parse source and assert structural shape.

```python
# BANNED — tests source structure, not runtime behavior
def test_no_bare_typing_self_import():
    src = Path("src/des/domain/value_objects.py").read_text()
    tree = ast.parse(src)
    # ... assert try/except wraps the import ...

# CORRECT — test runtime behavior on each supported version (matrix in CI)
def test_value_objects_import_succeeds_on_python_310():
    # Run pytest under Python 3.10 in CI matrix
    from des.domain.value_objects import OrderId
    assert OrderId("abc").value == "abc"
```

Source compliance is a CI matrix concern, not a unit test.

### 2.3 Trivial Dataclass-Storage Tests

```python
# BANNED — Python @dataclass guarantees field assignment
def test_turn_limit_config_stores_limits_by_task_type():
    config = TurnLimitConfig(quick=20, deep=60)
    assert config.quick == 20
    assert config.deep == 60

# CORRECT — test the behavior that uses the config
def test_turn_counter_aborts_quick_task_at_limit():
    counter = TurnCounter(TurnLimitConfig(quick=20, deep=60))
    for _ in range(20):
        counter.increment("quick")
    assert counter.is_exhausted("quick")
```

If the dataclass has invariants (validation, derived fields), those ARE behaviors — test them.

### 2.4 Mock-Asserting-Mock

```python
# BANNED — mock returns what you told it to; you are testing unittest.mock
def test_repository_returns_user():
    mock_repo = Mock()
    mock_repo.get.return_value = User(name="Alice")
    result = mock_repo.get(1)
    assert result.name == "Alice"

# CORRECT — test the application service that uses the repository
def test_user_service_returns_active_user():
    repo = InMemoryUserRepository(users=[User(id=1, name="Alice", active=True)])
    service = UserService(repo)
    assert service.get_active(1).name == "Alice"
```

### 2.5 Parametrize-Inflation

One contract becomes N tests by parametrizing every variant.

```python
# BANNED — 150 tests for "the markdown contains required phrases"
@pytest.mark.parametrize("phrase", PHRASES_30)
@pytest.mark.parametrize("skill_dir", SKILLS_5)
def test_skill_contains_phrase(skill_dir, phrase):
    md = (skill_dir / "SKILL.md").read_text()
    assert phrase in md  # 30 × 5 = 150 test cases

# CORRECT — 1 test per file, asserts the contract once
@pytest.mark.parametrize("skill_dir", SKILLS_5)
def test_skill_contains_required_phrases(skill_dir):
    md = (skill_dir / "SKILL.md").read_text()
    missing = [p for p in REQUIRED_PHRASES if p not in md]
    assert missing == [], f"{skill_dir.name} missing: {missing}"
```

Failure granularity is preserved: the assertion message names the missing phrases. Test count drops 30×.

### 2.6 Migration Regression Nets That Never Collapse

A migration produces a regression net (e.g. "every old skill name now exists at new location"). After 1 stable release with the migration green, the net MUST collapse to a single iteration.

```python
# BANNED after migration is stable — 315 tests asserting filesystem invariants
@pytest.mark.parametrize("skill_name", SKILL_NAMES_149)
def test_skill_directory_exists(skill_name):
    assert (SKILLS_DIR / f"nw-{skill_name}").is_dir()

# CORRECT post-stabilization — 1 test, single iteration
def test_all_canonical_skills_present():
    expected = set(load_canonical_skill_names())
    actual = {p.name.removeprefix("nw-") for p in SKILLS_DIR.glob("nw-*")}
    missing = expected - actual
    assert not missing, f"Missing skills: {sorted(missing)}"
```

## 3. Consolidation Patterns

Apply in this order. Each preserves coverage.

### 3.1 Parametrize Collapse

When N tests differ only by input value with the same assertion shape, collapse to one parametrized test. Failure granularity preserved by parameter ID.

### 3.2 Dict Iteration Collapse

When N parametrized tests assert independent membership/equality, collapse to one test iterating a dict and reporting all violations at once.

```python
# BEFORE — 12 tests
@pytest.mark.parametrize("event,handler", [("RED", h1), ("GREEN", h2), ...])
def test_event_routes_to_handler(event, handler):
    assert ROUTING[event] is handler

# AFTER — 1 test, all violations reported
def test_event_routing_table_complete_and_correct():
    expected = {"RED": h1, "GREEN": h2, "COMMIT": h3, ...}
    assert ROUTING == expected
```

### 3.3 Fixture Scope Promotion

Read-only fixtures used by N tests can promote to `module` or `session` scope when independence is preserved (no shared mutable state). Speeds up wall time without changing behavior coverage.

```python
@pytest.fixture(scope="module")  # was "function"
def loaded_skill_index():
    return SkillIndex.load_from(SKILLS_DIR)
```

Audit: tests using the fixture must not mutate it. If any test mutates, scope cannot promote.

### 3.4 xdist_group Tagging

When same-file tests benefit from a shared expensive fixture, add `@pytest.mark.xdist_group("name")` so the scheduler keeps them on the same worker. Fixture setup runs once per worker instead of once per test.

```python
@pytest.mark.xdist_group("update_check_http_server")
class TestUpdateCheckService:
    # All methods share the HTTP server fixture, scheduled to one worker
    ...
```

### 3.5 Migration-Collapse Lifecycle

Regression nets from one-time migrations (rename, move, restructure) MUST collapse within **1 stable release after migration completion**. Definition of "stable release":

- 1 release with the migration code green in CI for at least 7 days
- No follow-up bug reports referencing the migration during that window

After stabilization:
- Replace per-item parametrized tests with 1 single-iteration test reporting all violations at once
- Keep failure messages informative (set difference, dict diff)
- Document the collapse in commit body: `refactor(tests): collapse {migration} regression net (315 → 3) — stable since {date}`

### 3.6 Cross-Tier Deduplication

If `tests/<file>.py` and `tests/<subdir>/<file>.py` are byte-identical (md5-equal), delete the less canonical one. Canonical = the tier-correct location (unit under `unit/`, integration under `integration/`).

If two files are not byte-identical but assert the same handler/service through overlapping intent, merge into the canonical tier and delete the other.

## 4. Stopping Criterion Procedure

Apply when planning unit-test authoring inside RED (3-phase canon, ADR-025) or RED_UNIT (legacy 5-phase), at GREEN, and at COMMIT. Reviewer enforces at review.

1. **Count behaviors** — list distinct port-level behaviors in the AC. Use the rules in Section 1.
2. **Compute budget** — `budget = 2 × behavior_count`. Document in commit body: `Test budget: N behaviors × 2 = M unit tests`.
3. **Compare to actual** — count parametrized tests as 1, count parametrize cases as the parameter id contributes. Group dict-iteration assertions as 1.
4. **Below budget** — proceed.
5. **Above budget** — trigger consolidation (Section 3). If consolidation reduces below budget, proceed.
6. **Still above after consolidation** — two paths:
   - Justify in commit body: cite the specific behaviors that genuinely require N tests and the consolidation patterns already applied
   - Or redesign the abstraction: high test count often signals the unit under test owns too many responsibilities
7. **Reviewer enforcement** — counts independently. Budget exceeded without justification or applied pattern citation = block.

## 5. Coverage-Preserving Validation

Before declaring an optimization done, prove no behavior was lost.

### 5.1 Baseline before optimization

```bash
pipenv run pytest <scope> -p no:randomly --tb=no -q | tail -3
# Record: passed count, failed count
pipenv run pytest <scope> --cov=<package> --cov-report=term-missing -p no:randomly | tail -20
# Record: coverage %, missing lines
```

### 5.2 Apply optimization

Apply consolidation patterns. Stage changes file-by-file (`git add path/to/file`).

### 5.3 Validate after optimization

```bash
pipenv run pytest <scope> -p no:randomly --tb=short
# Required: passed count >= baseline (consolidation reduces test count, not pass count semantics)
pipenv run pytest <scope> --cov=<package> -p no:randomly | tail -5
# Required: coverage % >= baseline
```

Acceptable outcomes:
- Test count drops, pass count drops by the consolidation delta, coverage % unchanged or higher
- Test count drops, pass count drops, coverage % drops by less than 0.5% AND the missing lines are demonstrably language-guarantee tests (Section 2.1) — document in commit body

Block conditions:
- Coverage drops by >= 0.5% without explicit justification
- Any test that was green pre-optimization is now red
- Any production file appears in git diff (optimizer never modifies production)

### 5.4 Optional mutation validation

For high-confidence optimizations on critical scopes:

```bash
pipenv run mutmut run --paths-to-mutate <scope>
```

Kill rate before optimization vs after must not regress. Loaded only when invoking nw-mutation-test skill.

## 6. Scope Selection Heuristics

When invoked without a specific scope, prioritize by leverage:

| Indicator | Priority | Pattern |
|-----------|----------|---------|
| Byte-identical file pairs (md5-equal) | P0 | Cross-Tier Deduplication |
| Single file with > 200 collected tests | P0 | Investigate parametrize-inflation, migration nets |
| Tests/function ratio > 4 in a module | P1 | Behavior re-counting, anti-pattern scan |
| Files matching `*_typing_compat`, `*_interface_*`, `*_abc_*` | P1 | Language-guarantee scan |
| AST-import test files | P1 | Replace with CI matrix |
| Files older than 6 months touching migration paths | P2 | Migration-collapse lifecycle check |

Use `git log --diff-filter=A --name-only` for migration-net dating, `find tests/ -name '*.py' -exec wc -l {} + | sort -rn` for fat files.

## 7. What This Methodology Does NOT Cover

- Test infrastructure (fixtures, conftest, plugins) — that is platform-architect or troubleshooter scope
- Production code refactoring — `/nw-refactor` and the crafter scope
- New test authoring — crafter scope (DELIVER wave)
- Adapter integration tests — different rules apply (real I/O, no parametrize-collapse there); see hexagonal-testing skill

## 8. Cross-References

- `nw-tdd-methodology` — Mandate 1 (Observable Behavioral Outcomes), Mandate 5 (Parametrize Input Variations)
- `nw-tdd-review-enforcement` — reviewer block conditions
- `nw-mutation-test` — coverage-preserving validation via mutation kill rate
- `nw-test-refactoring-catalog` — refactoring patterns for test code structure
- `docs/analysis/investigation-overtesting-hypothesis-2026-04-28.md` — empirical evidence (~580 removable tests, 18% of unit suite, the gap is enforcement decay + loose behavior definition)
