---
name: nw-pbt-python
agent: nw-functional-software-crafter
description: Python property-based testing with Hypothesis framework, strategies, and pytest integration
disable-model-invocation: true
---

# PBT Python -- Hypothesis

## Framework Selection

**Hypothesis** is the only serious choice for Python PBT. No competitive alternatives.

- 10+ years mature, very actively maintained
- Used by PyTorch, NumPy, pandas
- Seamless pytest integration (no plugin needed)

## Quick Start

```python
from hypothesis import given, assume, settings, HealthCheck
from hypothesis import strategies as st

@given(st.lists(st.integers()))
def test_sort_idempotent(xs):
    assert sorted(sorted(xs)) == sorted(xs)

# Run: pytest test_file.py
```

## Generator (Strategy) Cheat Sheet

### Primitives
```python
st.integers()                         # any int
st.integers(min_value=0, max_value=99) # bounded
st.floats()                           # includes NaN, inf
st.floats(allow_nan=False, allow_infinity=False)
st.text()                             # unicode strings
st.text(min_size=1, max_size=50)
st.binary()                           # bytes
st.booleans()
st.none()
```

### Collections
```python
st.lists(st.integers())
st.lists(st.integers(), min_size=1, max_size=10)
st.sets(st.integers())
st.frozensets(st.text())
st.dictionaries(st.text(), st.integers())
st.tuples(st.integers(), st.text())
```

### Combinators
```python
st.one_of(st.integers(), st.text())   # union
st.sampled_from([1, 2, 3])            # pick from list
st.just(42)                           # constant

# Map (transform)
st.integers().map(lambda x: x * 2)    # even integers

# Filter (use sparingly)
st.integers().filter(lambda x: x > 0)
# Prefer: st.integers(min_value=1)

# Composite (dependent generation)
@st.composite
def list_and_element(draw):
    xs = draw(st.lists(st.integers(), min_size=1))
    elem = draw(st.sampled_from(xs))
    return (xs, elem)
```

### Recursive
```python
json_values = st.recursive(
    st.none() | st.booleans() | st.integers() | st.text(),
    lambda children: st.lists(children) | st.dictionaries(st.text(), children),
    max_leaves=50
)
```

### Objects
```python
from dataclasses import dataclass

@dataclass
class User:
    name: str
    age: int

users = st.builds(User, name=st.text(min_size=1), age=st.integers(1, 120))
# Or: st.from_type(User) if type annotations are sufficient
```

## Stateful Testing

```python
from hypothesis.stateful import RuleBasedStateMachine, Bundle, rule, initialize, invariant, precondition, consumes

class MyStoreTest(RuleBasedStateMachine):
    keys = Bundle("keys")

    @initialize()
    def init(self):
        self.store = MyStore()
        self.model = {}

    @rule(target=keys, k=st.text(min_size=1))
    def create(self, k):
        return k  # deposited into keys bundle

    @rule(k=keys, v=st.integers())
    def put(self, k, v):
        self.store.put(k, v)
        self.model[k] = v

    @rule(k=keys)
    def get(self, k):
        if k in self.model:
            assert self.store.get(k) == self.model[k]

    @rule(k=consumes(keys))  # removes from bundle
    def delete(self, k):
        self.store.delete(k)
        self.model.pop(k, None)

    @invariant()
    def size_matches(self):
        assert self.store.size() == len(self.model)

TestMyStore = MyStoreTest.TestCase
TestMyStore.settings = settings(max_examples=100, stateful_step_count=50)
```

Limitation: No parallel/linearizability testing.

## Test Runner Integration

```python
# pytest -- just works, no plugin needed
# @given tests are regular pytest functions

# Settings profiles
from hypothesis import settings, Phase
settings.register_profile("ci", max_examples=1000)
settings.register_profile("dev", max_examples=50)
settings.load_profile("ci")  # or via HYPOTHESIS_PROFILE env var

# Suppress slow test warnings
@settings(suppress_health_check=[HealthCheck.too_slow])

# Deadline (max time per example)
@settings(deadline=500)  # 500ms

# Database of failing examples
# Hypothesis auto-saves failures to .hypothesis/
# Replays them on subsequent runs
```

## Unique Features

- **Ghostwriter**: `hypothesis write json.dumps` auto-generates PBT from type annotations
- **Coverage-guided**: Can use coverage info to guide exploration
- **Example database**: Persists failures across runs
- **Health checks**: Warns on slow strategies or excessive filtering
- **`assume()`**: Skip invalid inputs inside tests (like filter but inline)
- **`event()`/`target()`**: Distribution monitoring and coverage-guided feedback
- **Internal shrinking**: Fully automatic, works with `@st.composite` and monadic bind
