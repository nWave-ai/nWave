---
name: nw-tdd-methodology-paradigm
description: "Native contract-driven unit and acceptance testing: generative broad laws, finite examples, public-state preservation and real-boundary evidence."
user-invocable: false
disable-model-invocation: true
---

# Test-Writing Paradigm — Property-Based + State-Delta

**Trigger**: writing a unit or acceptance test — deciding native generation versus finite examples and public-state preservation observations.

## Native, contract-driven test paradigm

The language/build discovery authority is `nw-test-design-mandates`' language
convention frame. Its layered-mechanics module owns observation treatment;
`nw-property-based-testing` owns non-vacuous generation and shrinking.
Apply those rules rather than imposing a second methodology.

| Contract | Test treatment |
|---|---|
| Broad input, state or sequence law | Native generative property with independent oracle, constructive branch coverage and reproducible shrinking/replay |
| Closed finite domain or singular observation | Native parameterized examples or exhaustive finite check |
| Mutation of public state | Observe promised changes and adjacent preservation, using sufficient native assertions/helpers |
| Real storage, protocol, crash or race | Targeted real-boundary integration; synchronized checkpoints where ordering matters |
| Feature journey | Identifiable end-to-end business walkthrough through production composition, retaining distinct failure observations |

PBT does not require Hypothesis, a fixed number of generated examples, Gherkin,
an nWave matcher, or a copied helper library. Reuse incumbent native facilities.
Examples are not banned or a fallback needing a bypass comment. Conversely,
finite examples cannot silently discharge a promised broad law.

Name the business stimulus, expected outcome and falsifier. Assert public
outcomes, state, types and required fields; exact formatting or ordering is
pinned only when the authority deliberately promises it. Equivalent JSON and
permitted extra fields remain valid. Do not assert incidental private layout
or mock call counts instead of the consumer's outcome.

Declared state-delta observations protect changed and preserved public state;
they need not reproduce Python function signatures or capture all internal
implementation state. Native records and assertions may express the same law.
A PBT model cannot replace real persistence, synchronized fault/race evidence
or the feature journey. Property quantity and predicted speed are not quality
evidence; measure distribution/transitions, counterexamples and replay instead.

### Empirical efficacy framework — debt-payoff curve (NOT instantaneous hit rate)

**Reframing (Ale 2026-05-05)**: paradigm efficacy is measured via the **debt-payoff curve over a surface's lifetime**, not via instantaneous hit rate snapshots.

#### Three stages

| Stage | Surface state | Expected hit rate | Meaning |
|---|---|---|---|
| **Stage 0** | New code, paradigm-from-day-zero | N/A — debt never accumulates | **Healthy by construction**. Tests catch hidden mutations as they emerge |
| **Stage 1** | Bug-prone, debt-accumulated, never-cured | 33–75% (state-delta migration) | **Debt-payoff phase**. High yield = years of single-property-asserts being unmasked |
| **Stage 2a** | Stage-1-completed surface, PBT amplification | ~0% by design | **Maintenance mode**. Debt is paid; PBT now catches in-flight regressions, not retroactive ones |
| **Stage 2b** | Bug-prone, never-migrated, PBT amplification | ~75% (per hardening empirical) | Same as Stage 1 — surface still has accumulated assumptions |

#### Empirical evidence (2026-05-05 pilot, 2 instances)

| Pilot | Stage | Surface | Hit rate | Source |
|---|---|---|---|---|
| Stage 1 state-delta migration | Stage 1 | installer plugin tests, never cured | 4/9 = 44% |
| Stage 2a PBT amplification | Stage 2a | plugin code post Stage 1 | 0/3 = 0% (post commit `29daeb102`) |

**Reading the data correctly**: the master 0% is NOT failure — it's confirmation that Stage 1 already extracted the debt. Stage 2a on a cured surface validates the surface stays healthy. Stage 2b on an uncured surface re-confirms paradigm yield on debt-accumulated code.

#### Implication for AI delegation (the deeper point)

Humans accumulate test debt (single-property-asserts, missed-universe-keys, post-state-only). Machines applying the paradigm **from day zero** (Stage 0) do NOT accumulate debt by construction. Therefore: **AI-written code under paradigm enforcement has lower debt-rate than human-written code**, given equivalent specification quality.

This is why paradigm-as-default for NEW unit tests (the mandate above) matters more than migration: migrations are one-time cleanup; the long-term value is **never accumulating debt to migrate**.

**The paradigm is the environment modification that lets machines build software with lower debt over time** (Ale 2026-05-05).

## Delta-First Test Paradigm (state-mutating code)

**Scope**: ~28% of the test suite (419 test files audited). Applies to installer-class, sync-class, and hook-registration code that mutates user-observable state. NOT universal. Pure-function tests, schema validators, and interaction tests retain standard assertion style.

### Trigger — apply delta-first when ALL of these hold

1. The test mutates user-observable state in **2 or more** distinct slots (e.g. filesystem path + config key + env setting).
2. OR the test implicitly asserts "preserve X" semantics — i.e., the correctness claim is partly about what did NOT change.
3. The code under test is in `scripts/install/`, `scripts/sync/`, or any hook-registration path.

### Bypass — do NOT apply delta-first when

- Pure-function tests with a single return value (no side effects).
- Single-property assertion (`assert result.returncode == 0`).
- `validate_prerequisites()` failure paths (returncode / boolean / exception only).
- Interaction tests (`mock.assert_called_with(...)`) — no universe to declare.
- AST / schema / YAML validators.
- Adding 3-5× ceremony for zero additional detection gain vs. a direct `assert`.

### Pattern

The following is a repository-specific Python illustration. It is not a required
API, directory or predicate set for another project; sufficient native assertions
and incumbent helpers satisfy the observation contract above.

```python
from nwave_ai.state_delta import (
    assert_state_delta,
    prepended_with,
    unchanged,
    set_to,
    containing,
)

def test_plugin_installs_hook(tmp_path):
    before = capture_state(tmp_path)   # snapshot before action

    plugin.install(context_for(tmp_path))

    after = capture_state(tmp_path)    # snapshot after action

    assert_state_delta(
        before,
        after,
        universe={
            "hooks.pre_tool_use",      # every slot that COULD change
            "hooks.post_tool_use",
            "config.rigor",
        },
        expected={
            "hooks.pre_tool_use": prepended_with("app_hook.py"),
            "hooks.post_tool_use": unchanged(),
            "config.rigor": set_to("standard"),
        },
        # implicit-unchanged: any universe slot NOT in expected must be identical
    )
```

Full API: `assert_state_delta(before, after, universe, expected, *, strict=False)`.

Available predicate factories: `prepended_with`, `appended_with`, `unchanged`, `set_to`, `containing`, `normalized_to`, `idempotent_after`, `legacy_healed`.

Import: `from nwave_ai.state_delta import assert_state_delta, <predicates>`.

### Empirical justification

Migration of 7 installer test files: **4/7 (57%) exposed previously-untracked mutations** that post-state-property assertions had missed.

Hidden mutations caught:
- `attribution.trailer` written silently (`test_attribution_plugin`) — post-state test only checked `returncode`.
- `content.full` transitioned `None → str` in an installer test — the old assertion never declared `content.full` in its universe.

### Reusable helpers that emerged from migration

- `_flatten_config(path)` — flattens a JSON/YAML config into dotted key paths.
- `_skill_filesystem_state(target_dir, track=)` — snapshots skills directory into slot dict.
- `_*_content_state(target_dir, name)` — snapshots a named agent/command content file.

### References

- Source: `nwave_ai/state_delta/matcher.py`
- Canonical migrated example: `tests/installer/unit/plugins/test_attribution_plugin.py`
- D-12 hard gate examples: `tests/state_delta/integration/test_pilot_bug48.py`
