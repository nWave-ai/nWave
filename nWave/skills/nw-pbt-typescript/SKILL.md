---
name: nw-pbt-typescript
agent: nw-functional-software-crafter
description: TypeScript/JavaScript property-based testing with fast-check framework and arbitraries
user-invocable: false
---

# PBT TypeScript -- fast-check

## Framework Selection

**fast-check** is the dominant PBT framework for TypeScript/JavaScript. No serious competitors.

- 8+ years mature, very actively maintained
- First-class TypeScript types
- Zero runtime dependencies
- Used by jest, jasmine, fp-ts, ramda, js-yaml

## Quick Start

```typescript
import fc from 'fast-check';

test('sort is idempotent', () => {
  fc.assert(
    fc.property(fc.array(fc.integer()), (arr) => {
      const sorted = [...arr].sort((a, b) => a - b);
      const twice = [...sorted].sort((a, b) => a - b);
      expect(sorted).toEqual(twice);
    }),
    { numRuns: 1000 }
  );
});
```

## Generator (Arbitrary) Cheat Sheet

### Primitives
```typescript
fc.integer()                          // any safe integer
fc.integer({ min: 0, max: 99 })
fc.nat()                              // non-negative integer
fc.float()
fc.double()
fc.string()
fc.string({ minLength: 1, maxLength: 50 })
fc.boolean()
fc.constant(null)
fc.constantFrom(1, 2, 3)             // pick from values
```

### Collections
```typescript
fc.array(fc.integer())
fc.array(fc.integer(), { minLength: 1, maxLength: 10 })
fc.set(fc.integer())
fc.dictionary(fc.string(), fc.integer())
fc.tuple(fc.integer(), fc.string())
```

### Combinators
```typescript
fc.oneof(fc.integer(), fc.string())   // union
fc.option(fc.integer())               // T | null

// Map
fc.integer().map(n => n * 2)          // even integers

// Filter
fc.integer().filter(n => n > 0)
// Prefer: fc.integer({ min: 1 })

// Chain (dependent generation)
fc.array(fc.integer(), { minLength: 1 }).chain(
  arr => fc.tuple(fc.constant(arr), fc.integer({ min: 0, max: arr.length - 1 }))
)

// Record
fc.record({
  name: fc.string({ minLength: 1 }),
  age: fc.integer({ min: 0, max: 150 }),
  active: fc.boolean(),
})

// Frequency (weighted)
fc.frequency(
  { weight: 80, arbitrary: fc.char() },
  { weight: 10, arbitrary: fc.constant(' ') },
  { weight: 1,  arbitrary: fc.constantFrom('.', '-') }
)
```

### Recursive
```typescript
const jsonArb = fc.letrec(tie => ({
  value: fc.oneof(
    fc.constant(null), fc.boolean(), fc.integer(), fc.string(),
    fc.array(tie('value')), fc.dictionary(fc.string(), tie('value'))
  ),
})).value;
```

## Stateful Testing (Model-Based)

```typescript
import fc from 'fast-check';

type Model = { items: Map<string, number> };

class PutCommand implements fc.Command<Model, MyStore> {
  constructor(readonly key: string, readonly value: number) {}
  check = (m: Readonly<Model>) => true;
  run(m: Model, r: MyStore): void {
    r.put(this.key, this.value);
    m.items.set(this.key, this.value);
  }
  toString = () => `put(${this.key}, ${this.value})`;
}

class GetCommand implements fc.Command<Model, MyStore> {
  constructor(readonly key: string) {}
  check(m: Readonly<Model>): boolean {
    return m.items.has(this.key);  // precondition
  }
  run(m: Model, r: MyStore): void {
    expect(r.get(this.key)).toBe(m.items.get(this.key));
  }
  toString = () => `get(${this.key})`;
}

const allCommands = [
  fc.tuple(fc.string(), fc.integer()).map(([k, v]) => new PutCommand(k, v)),
  fc.string().map(k => new GetCommand(k)),
];

test('store matches model', () => {
  fc.assert(
    fc.property(fc.commands(allCommands), (cmds) => {
      const setup = () => ({
        model: { items: new Map() },
        real: new MyStore(),
      });
      fc.modelRun(setup, cmds);
    })
  );
});
```

### Race Condition Testing

```typescript
fc.assert(
  fc.property(fc.scheduler(), fc.commands(allCommands), async (s, cmds) => {
    const setup = () => ({
      model: { items: new Map() },
      real: new MyStore(s),  // system must use scheduler for async ops
    });
    await fc.scheduledModelRun(setup, cmds);
  })
);
```

Scheduler controls promise resolution order, enabling deterministic exploration of async interleavings.

## Test Runner Integration

```typescript
// Jest -- works out of the box
// Vitest -- works out of the box

// With @fast-check/jest (enhanced integration)
import { test } from '@fast-check/jest';
test.prop([fc.integer(), fc.integer()])('commutative addition', (a, b) => {
  expect(a + b).toBe(b + a);
});

// With @fast-check/vitest
import { test } from '@fast-check/vitest';
test.prop([fc.string()])('string length non-negative', (s) => {
  expect(s.length).toBeGreaterThanOrEqual(0);
});

// Replay failing tests
fc.assert(
  fc.property(fc.integer(), (n) => { /* ... */ }),
  { seed: 1234567890, path: '4:1:0' }  // from failure output
);
```

## Unique Features

- **Race condition detection**: `fc.scheduler()` controls async interleaving -- unique outside Erlang
- **Replay**: Seed + path for deterministic reproduction
- **Bias mode**: Automatically tests edge cases (0, -1, MAX_INT, empty) more often
- **Verbose mode**: Shows all generated values and shrink steps
- **Integrated shrinking**: Automatic via shrink trees, composes with generators
- **Size parameter**: `{ size: '+1' }` controls generation complexity growth
