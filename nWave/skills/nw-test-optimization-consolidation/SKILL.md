---
name: nw-test-optimization-consolidation
description: Coverage-preserving consolidation patterns applied in order - parametrize-collapse, dict-iteration, fixture-scope, xdist-group, migration-collapse lifecycle, cross-tier dedup, single-lifecycle consolidation, state-delta cross-ref
user-invocable: false
disable-model-invocation: true
---

# Consolidation Patterns (KNOWLEDGE)

Native project conventions govern every pattern below. Python decorators,
fixture scopes and plugin commands illustrate Python bindings only; use the
actual native runner/build graph and sufficient incumbent helpers under
`nw-test-design-mandates`. Do not install pytest/xdist/randomly or add `.py`
files to apply consolidation in another stack. Preserve distinct consumer
observations, not test counts, source wording or hash pins.

**Kind**: KNOWLEDGE (reference). **One trigger**: "I have redundant tests — how do I collapse them without losing coverage" — consulted when behavior mapping shows two tests observing the same outcome, or the paradigm-match rule routes here. Composed by `nw-test-optimization`.

**Write scope**: apply these edits only to test files the dispatch declares as the oracle set under revision. A role reusing a complete oracle read-only (GREEN_TO_GREEN) or reviewing it reports consolidation candidates to their owner instead of editing. The release-window deadlines below bind the project's test-optimization workflow, not a single role turn.

Apply in this order. Each preserves coverage.

## 3.1 Parametrize Collapse

When N tests differ only by input value with the same assertion shape, collapse to one parametrized test. Failure granularity preserved by parameter ID.

## 3.2 Dict Iteration Collapse

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

## 3.3 Fixture Scope Promotion

Read-only fixtures used by N tests can promote to `module` or `session` scope when independence is preserved (no shared mutable state). Speeds up wall time without changing behavior coverage.

```python
@pytest.fixture(scope="module")  # was "function"
def loaded_skill_index():
    return SkillIndex.load_from(SKILLS_DIR)
```

Audit: tests using the fixture must not mutate it. If any test mutates, scope cannot promote.

## 3.4 xdist_group Tagging

When same-file tests benefit from a shared expensive fixture, add `@pytest.mark.xdist_group("name")` so the scheduler keeps them on the same worker. Fixture setup runs once per worker instead of once per test.

```python
@pytest.mark.xdist_group("expensive_http_server")
class TestRemoteVersionService:
    # All methods share the HTTP server fixture, scheduled to one worker
    ...
```

## 3.5 Migration-Collapse Lifecycle

Regression nets from one-time migrations (rename, move, restructure) MUST collapse within **1 stable release after migration completion**. Definition of "stable release":

- 1 release with the migration code green in CI for at least 7 days
- No follow-up bug reports referencing the migration during that window

After stabilization:
- Replace per-item parametrized tests with 1 single-iteration test reporting all violations at once
- Keep failure messages informative (set difference, dict diff)
- Document the collapse in commit body: `refactor(tests): collapse {migration} regression net (315 → 3) — stable since {date}`

## 3.6 Cross-Tier Deduplication

If `tests/<file>.py` and `tests/<subdir>/<file>.py` are byte-identical (md5-equal), delete the less canonical one. Canonical = the tier-correct location (unit under `unit/`, integration under `integration/`).

If two files are not byte-identical but assert the same handler/service through overlapping intent, merge into the canonical tier and delete the other.

## 3.7 Single-Lifecycle Consolidation

When N tests share an expensive setup/teardown lifecycle (subprocess install, container start, filesystem fixture build) AND each test asserts a distinct contract on the same post-setup state, collapse to **one lifecycle, N assertions** instead of N lifecycles × 1 assertion.

```python
# BEFORE — 24 tests × ~6s lifecycle each = 152s wall-clock
class TestTutorialSetupScripts:
    def setup_method(self):
        self.workspace = build_tutorial_workspace()  # expensive
        run_setup_script(self.workspace)
    def test_creates_project_dir(self): assert (self.workspace / "project").is_dir()
    def test_creates_config_file(self): assert (self.workspace / ".nwave/config.json").exists()
    # ... 22 more independent assertions ...

# AFTER — 1 lifecycle, 24 assertions = 63s wall-clock (2.4× faster)
@pytest.fixture(scope="class")
def tutorial_workspace():
    workspace = build_tutorial_workspace()
    run_setup_script(workspace)
    return workspace

class TestTutorialSetupScripts:
    def test_creates_project_dir(self, tutorial_workspace):
        assert (tutorial_workspace / "project").is_dir()
    def test_creates_config_file(self, tutorial_workspace):
        assert (tutorial_workspace / ".nwave/config.json").exists()
    # ... 22 more, all reading the same workspace ...
```

**Empirical anchor**: `tests/build/acceptance/test_tutorial_setup_scripts.py` (commit `defc07f0d`, 2026-05-18): 152.81s → 62.87s, 2.4× faster, -90s.

**Pre-conditions** (HARD GATES):
- Setup is **read-only** for the assertions — no test mutates shared state. If even one test mutates, scope cannot promote (audit per §3.3).
- Failure granularity preserved: each assertion identifies WHAT failed (file/property/contract), not just "setup failed".
- Tests remain **order-independent** — use the project's native isolated/reordered execution capability to expose hidden coupling; pytest-randomly is only an optional Python binding, not a universal prerequisite.

**Anti-pattern**: do NOT collapse when assertions verify **steps of a state-transition sequence** (run A → assert, mutate B → assert, mutate C → assert). That is state-delta paradigm territory (§3.8), not single-lifecycle.

## 3.8 State-Delta Paradigm (cross-ref)

For tests that mutate user-observable state (installer, uninstaller, sync, hooks, settings.json — ~28% of suite), use the **state-delta paradigm** instead of per-assertion lifecycle: capture initial state once, apply operation, assert the delta (added/removed/modified) as a single matcher.

Honest gain: 13% compression / 17% wall-clock on the addressable subset (Ale 2026-05-05 revision). NOT universal — pure-function/AST/schema tests retain standard assertions (3-5× ceremony for zero gain otherwise).

See `nw-tdd-methodology-paradigm` for public-state/transition observation and `nw-test-design-mandates` for native conventions; no optional missing skill or private-memory lookup is required.
