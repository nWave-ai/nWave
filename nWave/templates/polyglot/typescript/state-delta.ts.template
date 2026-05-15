/**
 * state-delta.ts — TypeScript port of nwave_ai.state_delta (Python canonical).
 *
 * Polyglot pilot (Epic 2B). Mirrors the contract of
 * `nwave_ai/state_delta/{matcher,predicates}.py`:
 *
 *   - Predicate signature: (old, new) => boolean
 *   - Universe = string[] (set semantics; duplicates ignored)
 *   - assertStateDelta collects ALL violations across the universe before
 *     throwing a single StateDeltaViolation aggregating them (multi-violation
 *     contract A7).
 *   - strict mode reports any key present in before|after but not in universe
 *     as a strict_universe_mismatch violation.
 *   - Implicit-unchanged: a key in universe but NOT in expected requires
 *     deep-equal between before[key] and after[key]; difference =>
 *     undeclared_change violation.
 *
 * Zero external dependencies — uses an inline structural deep-equal so this
 * file can be dropped into any TypeScript project without lodash et al.
 *
 * Source of truth: Python module at `nwave_ai/state_delta/`. Keep the contract
 * in sync; deviations are bugs.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type Universe = readonly string[];
export type StateSnapshot = Readonly<Record<string, unknown>>;

/** Result of a predicate evaluation. ok=true passes; ok=false records a violation. */
export type PredicateResult = { readonly ok: true } | { readonly ok: false; readonly reason: string };

/**
 * Predicate signature mirrors the Python contract: (old, new) -> boolean.
 *
 * The function form returns boolean for Python parity. The wrapper coerces it
 * to a PredicateResult internally so violation messages can include
 * predicate-specific reasons.
 */
export type Predicate = ((old: unknown, next: unknown) => boolean) & {
  readonly predicateName: string;
};

export type Expected = Readonly<Record<string, Predicate>>;

export type ViolationKind = "undeclared_change" | "predicate_failed" | "strict_universe_mismatch";

export interface Violation {
  readonly kind: ViolationKind;
  readonly key: string;
  readonly old: unknown;
  readonly next: unknown;
  readonly predicateName: string | null;
}

/** Thrown by assertStateDelta when one or more violations are detected. */
export class StateDeltaViolation extends Error {
  public readonly violations: ReadonlyArray<Violation>;

  constructor(violations: ReadonlyArray<Violation>) {
    super(StateDeltaViolation.format(violations));
    this.name = "StateDeltaViolation";
    this.violations = violations;
    // Restore prototype chain for `instanceof` to work across ES targets.
    Object.setPrototypeOf(this, StateDeltaViolation.prototype);
  }

  private static format(violations: ReadonlyArray<Violation>): string {
    const header = `assertStateDelta: ${violations.length} violation(s) detected:`;
    const lines = violations.map((v) => {
      let line = `  kind='${v.kind}' key='${v.key}' old=${JSON.stringify(v.old)} new=${JSON.stringify(v.next)}`;
      if (v.predicateName !== null) {
        line += ` predicate_name='${v.predicateName}'`;
      }
      return line;
    });
    return [header, ...lines].join("\n");
  }
}

// ---------------------------------------------------------------------------
// Deep equality (zero-dep, ~25 LOC)
// ---------------------------------------------------------------------------

/**
 * Structural deep equality for plain JSON-shaped values.
 *
 * Handles: primitives, arrays, plain objects, null/undefined. Does NOT special
 * case Map/Set/Date/RegExp — the universe contract treats state slots as
 * JSON-serializable. Out-of-scope inputs fall back to reference equality.
 */
export function deepEqual(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (a === null || b === null) return false;
  if (typeof a !== "object" || typeof b !== "object") return false;

  if (Array.isArray(a)) {
    if (!Array.isArray(b) || a.length !== b.length) return false;
    for (let i = 0; i < a.length; i++) {
      if (!deepEqual(a[i], b[i])) return false;
    }
    return true;
  }
  if (Array.isArray(b)) return false;

  const ao = a as Record<string, unknown>;
  const bo = b as Record<string, unknown>;
  const aKeys = Object.keys(ao);
  const bKeys = Object.keys(bo);
  if (aKeys.length !== bKeys.length) return false;
  for (const k of aKeys) {
    if (!Object.prototype.hasOwnProperty.call(bo, k)) return false;
    if (!deepEqual(ao[k], bo[k])) return false;
  }
  return true;
}

// ---------------------------------------------------------------------------
// Predicate factories — mirror nwave_ai/state_delta/predicates.py
// ---------------------------------------------------------------------------

function makePredicate(name: string, fn: (old: unknown, next: unknown) => boolean): Predicate {
  const pred = ((old: unknown, next: unknown) => fn(old, next)) as Predicate;
  Object.defineProperty(pred, "predicateName", { value: name, enumerable: true });
  return pred;
}

/** Passes when `old` equals `next` (deep equality). */
export function unchanged(): Predicate {
  return makePredicate("unchanged()", (old, next) => deepEqual(old, next));
}

/**
 * Passes when `next` is a string `prefix + sep + old`. Mirrors Python
 * `prepended_with(prefix, sep=":")` — for PATH-like string composition.
 *
 * For array-prepend semantics (next = [item, ...old]), use `arrayPrepended`.
 */
export function prependedWith(prefix: string, sep: string = ":"): Predicate {
  const expectedPrefix = prefix + sep;
  return makePredicate(`prepended_with(${prefix})`, (old, next) => {
    if (typeof old !== "string" || typeof next !== "string") return false;
    return next === expectedPrefix + old;
  });
}

/**
 * Passes when `next` is a string `old + sep + suffix`. Mirrors Python
 * `appended_with(suffix, sep=":")`.
 */
export function appendedWith(suffix: string, sep: string = ":"): Predicate {
  return makePredicate(`appended_with(${suffix})`, (old, next) => {
    if (typeof old !== "string" || typeof next !== "string") return false;
    return next === `${old}${sep}${suffix}`;
  });
}

/** Passes when `next` deep-equals `value` (old is ignored). */
export function setTo(value: unknown): Predicate {
  return makePredicate(`set_to(${JSON.stringify(value)})`, (_old, next) =>
    deepEqual(next, value),
  );
}

/**
 * Passes when `substring` is a substring of `next` (string), or when `next` is
 * an array that includes a deep-equal element to `substring`.
 */
export function containing(substring: unknown): Predicate {
  return makePredicate(`containing(${JSON.stringify(substring)})`, (_old, next) => {
    if (typeof next === "string" && typeof substring === "string") {
      return next.includes(substring);
    }
    if (Array.isArray(next)) {
      return next.some((el) => deepEqual(el, substring));
    }
    return false;
  });
}

/**
 * Passes when `normalizer(old)` deep-equals `normalizer(next)`. Used for
 * transformations that are equivalent under a normalisation function (e.g.
 * `$HOME` expansion, case folding).
 */
export function normalizedTo(normalizer: (value: unknown) => unknown): Predicate {
  return makePredicate("normalized_to(<normalizer>)", (old, next) =>
    deepEqual(normalizer(old), normalizer(next)),
  );
}

/**
 * Passes when `prefix` is already the first segment of `next` (split by `sep`).
 * Mirrors `idempotent_after` — used to assert a prepend-if-absent operation
 * left the slot untouched because the prefix was already present.
 */
export function idempotentAfter(prefix: string, sep: string = ":"): Predicate {
  return makePredicate(`idempotent_after(${prefix})`, (_old, next) => {
    if (typeof next !== "string") return false;
    return next.split(sep)[0] === prefix;
  });
}

/**
 * Passes when `detector(old)` AND `healedCheck(next)` are both true.
 * Mirrors `legacy_healed` — paper-trace pattern for migrating fabricated
 * legacy values to a healed shape.
 */
export function legacyHealed(
  detector: (old: unknown) => boolean,
  healedCheck: (next: unknown) => boolean,
): Predicate {
  return makePredicate("legacy_healed(<det>,<heal>)", (old, next) =>
    Boolean(detector(old) && healedCheck(next)),
  );
}

// ---------------------------------------------------------------------------
// Array-shaped helpers (TypeScript extension — beyond Python parity)
//
// The Python predicates `prepended_with`/`appended_with`/`containing` work on
// colon-separated strings (PATH-style). TypeScript callers more commonly hold
// arrays as state. These helpers cover that idiom without modifying the
// Python-parity functions above.
// ---------------------------------------------------------------------------

/** Passes when `next` is `[item, ...old]` (array prepend). */
export function arrayPrepended(item: unknown): Predicate {
  return makePredicate(`array_prepended(${JSON.stringify(item)})`, (old, next) => {
    if (!Array.isArray(old) || !Array.isArray(next)) return false;
    if (next.length !== old.length + 1) return false;
    if (!deepEqual(next[0], item)) return false;
    for (let i = 0; i < old.length; i++) {
      if (!deepEqual(next[i + 1], old[i])) return false;
    }
    return true;
  });
}

/** Passes when `next` is `[...old, item]` (array append). */
export function arrayAppended(item: unknown): Predicate {
  return makePredicate(`array_appended(${JSON.stringify(item)})`, (old, next) => {
    if (!Array.isArray(old) || !Array.isArray(next)) return false;
    if (next.length !== old.length + 1) return false;
    if (!deepEqual(next[next.length - 1], item)) return false;
    for (let i = 0; i < old.length; i++) {
      if (!deepEqual(next[i], old[i])) return false;
    }
    return true;
  });
}

// ---------------------------------------------------------------------------
// Driving function — assertStateDelta
// ---------------------------------------------------------------------------

export interface AssertStateDeltaArgs {
  readonly before: StateSnapshot;
  readonly after: StateSnapshot;
  readonly universe: Universe;
  readonly expected: Expected;
  /** When true, any key in before|after not in universe is a violation. */
  readonly strict?: boolean;
}

/**
 * Assert that state transitions satisfy the expected predicates.
 *
 * For each key in `universe`:
 *   - If the key has a predicate in `expected`, the predicate is called with
 *     `(before[key], after[key])`. A `false` return records a
 *     `predicate_failed` violation.
 *   - If the key is NOT in `expected`, `before[key]` must deep-equal
 *     `after[key]`. A difference records an `undeclared_change` violation
 *     (implicit-unchanged enforcement).
 *
 * Strict mode: any key present in `before` or `after` but not in `universe`
 * records a `strict_universe_mismatch` violation.
 *
 * All violations are collected across the full universe before a single
 * `StateDeltaViolation` is thrown (multi-violation contract A7).
 */
export function assertStateDelta(args: AssertStateDeltaArgs): void {
  const { before, after, universe, expected, strict = false } = args;
  const violations: Violation[] = [];

  // Universe-deduplication (mirrors Python `set` semantics).
  const universeSet = new Set(universe);

  if (strict) {
    const seen = new Set<string>([...Object.keys(before), ...Object.keys(after)]);
    const extras = [...seen].filter((k) => !universeSet.has(k)).sort();
    for (const key of extras) {
      violations.push({
        kind: "strict_universe_mismatch",
        key,
        old: before[key],
        next: after[key],
        predicateName: null,
      });
    }
  }

  for (const key of universeSet) {
    const oldValue = before[key];
    const newValue = after[key];
    const predicate = expected[key];

    if (predicate !== undefined) {
      let passed = false;
      try {
        passed = predicate(oldValue, newValue);
      } catch (_err) {
        passed = false;
      }
      if (!passed) {
        violations.push({
          kind: "predicate_failed",
          key,
          old: oldValue,
          next: newValue,
          predicateName: predicate.predicateName,
        });
      }
    } else if (!deepEqual(oldValue, newValue)) {
      // Implicit-unchanged enforcement.
      violations.push({
        kind: "undeclared_change",
        key,
        old: oldValue,
        next: newValue,
        predicateName: null,
      });
    }
  }

  if (violations.length > 0) {
    throw new StateDeltaViolation(violations);
  }
}

// NWAVE-POLYGLOT-TYPESCRIPT v1 — pilot template. Python canonical source of
// truth lives at `nwave_ai/state_delta/`. Updates to the Python contract must
// be ported here.
