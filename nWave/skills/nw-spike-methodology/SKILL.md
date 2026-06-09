---
name: nw-spike-methodology
description: Teaches agents how to run a timeboxed spike - throwaway code that validates one assumption before DESIGN
user-invocable: false
disable-model-invocation: true
---

# Spike Methodology

## What a Spike IS

Throwaway code that validates exactly one assumption. Max 1 hour. Binary outcome: works or doesn't work. Code is deleted after validation; only findings persist.

## What a Spike IS NOT

| Not This | Why |
|----------|-----|
| Prototype | Prototypes evolve into production code. Spikes are deleted. |
| MVP | MVPs ship to users. Spikes never leave the developer's machine. |
| Walking Skeleton | Skeletons wire end-to-end architecture. Spikes test one mechanism. |
| POC | POCs demonstrate feasibility to stakeholders. Spikes answer a developer question. |

## The 4 Questions

Every spike answers exactly these:

1. **Does the core mechanism work?** Can we parse the output? Call the API? Does the algorithm produce correct results?
2. **Does it meet the performance requirement?** Is it under the time/memory/throughput budget?
3. **What edge cases exist?** Empty input, malformed data, missing dependencies, concurrent access.
4. **What did we assume wrong?** The design said X, but reality is Y. Document the delta.

## When to Spike

- New mechanism never tried before in this codebase
- Performance requirement that cannot be validated by reasoning alone
- External integration (API, library, OS feature) with unknown behavior
- Algorithm where correctness is non-obvious

## When to Skip

- Pure refactoring (mechanism already proven)
- Bug fix (behavior already understood)
- Feature estimated at less than 1 day (spike overhead not justified)
- Mechanism already validated by a prior spike or existing code

## Rules

1. Max 1 hour wall clock. If it takes longer, the problem is bigger than expected. Stop and escalate.
2. No tests. No types. No error handling. No ports. No abstractions.
3. Code lives in `/tmp/spike_{feature_id}/` or a scratch directory. Never in `src/`.
4. One file preferred. Two files maximum.
5. Use `time.perf_counter()` for timing, not `time.time()`.
6. Print results to stdout. No logging frameworks.
7. After validation: delete the code, keep the findings.

## Spike Code Structure

```python
#!/usr/bin/env python3
"""SPIKE: {feature} -- {one-line question being validated}

Throwaway code. Not production. Will be deleted after validation.
"""
import time

# 1. Setup (minimal, no frameworks)
# ...

# 2. Core mechanism attempt
start = time.perf_counter()
# ... the thing you're testing ...
elapsed = time.perf_counter() - start

# 3. Print findings
print(f"Mechanism: {'WORKS' if success else 'FAILS'}")
print(f"Timing: {elapsed*1000:.1f}ms (budget: {budget}ms)")
print(f"Edge cases: {edge_cases}")
```

## Findings Output Format

Output goes to `docs/feature/{feature-id}/spike/findings.md`:

```markdown
# Spike Findings -- {feature-id}

## Verdict: WORKS / DOESN'T WORK

## Question tested
{the one assumption being validated}

## Core mechanism
- Tested: {what was tested}
- Result: {what happened}

## Timing
- {operation}: {time}ms
- Total: {time}ms (budget: {budget}ms) -- PASS / FAIL

## Edge cases discovered
1. {edge case}: {what happened}
2. {edge case}: {what happened}

## Design implications
- {assumption that was wrong}: {correct reality}
- {approach the spike validated or invalidated}

## Spike code
Deleted. Was at /tmp/spike_{feature_id}/
```

## Escalation

If the spike reveals the problem is fundamentally different from what was assumed:
1. Stop the spike
2. Write findings with verdict "DOESN'T WORK" or "BIGGER THAN EXPECTED"
3. Return to DISCUSS to re-scope the feature
4. The spike findings become input to the revised DISCUSS wave
