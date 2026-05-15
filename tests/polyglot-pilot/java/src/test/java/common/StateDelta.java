/*
 * StateDelta.java — Java port of nwave_ai.state_delta (Python canonical).
 *
 * Polyglot pilot (Epic 3 — Java). Mirrors the contract of
 * `nwave_ai/state_delta/{matcher,predicates}.py`:
 *
 *   - Predicate signature: (oldValue, newValue) -> PredicateResult
 *     (bool + optional reason; bool-only callers wrap via Predicates factories)
 *   - Universe = Set<String> (set semantics; duplicates ignored)
 *   - assertDelta collects ALL violations across the universe before
 *     throwing a single StateDeltaException aggregating them
 *     (multi-violation contract A7).
 *   - Implicit-unchanged: a key in universe but NOT in expected requires
 *     deep-equal between before.get(key) and after.get(key); difference =>
 *     undeclared_change violation.
 *   - Strict mode reports any key present in before|after but not in universe
 *     as a strict_universe_mismatch violation.
 *
 * Zero external dependencies — uses Objects.deepEquals + a recursive
 * Map/Collection comparator so this file can drop into any Java 17+ project
 * (no Guava, no Apache Commons).
 *
 * Source of truth: Python module at `nwave_ai/state_delta/`. Keep the contract
 * in sync; deviations are bugs.
 *
 * Java version: 17+ (records, switch expressions, sealed interfaces optional).
 */
package common;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.TreeSet;

/**
 * Driving entry point for state-delta assertions. Static utility class —
 * call {@link #assertDelta(Map, Map, Set, Map)} or the strict-mode overload.
 */
public final class StateDelta {

    private StateDelta() {
        // Static utility — no instances.
    }

    /**
     * Predicate over a (oldValue, newValue) pair. Returns a {@link PredicateResult}
     * carrying ok-flag + optional reason. Use the {@link Predicates} factory
     * for the canonical 8 predicates.
     */
    @FunctionalInterface
    public interface Predicate {
        PredicateResult test(Object oldValue, Object newValue);

        /**
         * Optional human-readable identifier (e.g. "prepended_with(/des/bin)").
         * Default mirrors {@code toString()}; factories override.
         */
        default String predicateName() {
            return toString();
        }
    }

    /** Result of a predicate evaluation. ok=true passes; ok=false records a violation. */
    public record PredicateResult(boolean ok, String reason) {
        public static PredicateResult pass() {
            return new PredicateResult(true, "");
        }

        public static PredicateResult fail(String reason) {
            return new PredicateResult(false, reason == null ? "" : reason);
        }
    }

    /** Categories of failure recorded by {@link #assertDelta}. */
    public enum ViolationKind {
        UNDECLARED_CHANGE,
        PREDICATE_FAILED,
        STRICT_UNIVERSE_MISMATCH;
    }

    /**
     * A single state-delta violation. Aggregated inside
     * {@link StateDeltaException}; printed in the exception message.
     */
    public record StateDeltaViolation(
            ViolationKind kind,
            String key,
            Object oldValue,
            Object newValue,
            String predicateName,
            String reason) {

        @Override
        public String toString() {
            StringBuilder sb = new StringBuilder();
            sb.append("  kind=").append(kind.name().toLowerCase())
              .append(" key='").append(key).append("'")
              .append(" old=").append(repr(oldValue))
              .append(" new=").append(repr(newValue));
            if (predicateName != null && !predicateName.isEmpty()) {
                sb.append(" predicate_name='").append(predicateName).append("'");
            }
            if (reason != null && !reason.isEmpty()) {
                sb.append(" reason='").append(reason).append("'");
            }
            return sb.toString();
        }

        private static String repr(Object value) {
            if (value == null) return "null";
            if (value instanceof String s) return "\"" + s + "\"";
            return String.valueOf(value);
        }
    }

    /**
     * Thrown by {@link #assertDelta} when one or more violations are detected.
     * Extends {@link AssertionError} so JUnit 5 treats it as a test failure
     * (not an "error") — matches the Python {@code AssertionError} contract.
     */
    public static final class StateDeltaException extends AssertionError {
        private static final long serialVersionUID = 1L;
        private final List<StateDeltaViolation> violations;

        public StateDeltaException(List<StateDeltaViolation> violations) {
            super(format(violations));
            this.violations = Collections.unmodifiableList(new ArrayList<>(violations));
        }

        public List<StateDeltaViolation> violations() {
            return violations;
        }

        private static String format(List<StateDeltaViolation> violations) {
            StringBuilder sb = new StringBuilder();
            sb.append("assertStateDelta: ").append(violations.size())
              .append(" violation(s) detected:");
            for (StateDeltaViolation v : violations) {
                sb.append("\n").append(v.toString());
            }
            return sb.toString();
        }
    }

    // ------------------------------------------------------------------------
    // Driving function — assertDelta
    // ------------------------------------------------------------------------

    /**
     * Assert that state transitions satisfy the expected predicates.
     *
     * For each key in {@code universe}:
     *   - If the key has a predicate in {@code expected}, the predicate is
     *     called with {@code (before.get(key), after.get(key))}. A
     *     non-{@code ok} result records a {@link ViolationKind#PREDICATE_FAILED}.
     *   - If the key is NOT in {@code expected}, {@code before.get(key)} must
     *     deep-equal {@code after.get(key)}. A difference records an
     *     {@link ViolationKind#UNDECLARED_CHANGE} (implicit-unchanged enforcement).
     *
     * All violations are collected across the full universe before a single
     * {@link StateDeltaException} is thrown (multi-violation contract A7).
     */
    public static void assertDelta(
            Map<String, Object> before,
            Map<String, Object> after,
            Set<String> universe,
            Map<String, Predicate> expected) {
        assertDelta(before, after, universe, expected, false);
    }

    /**
     * Strict-mode overload. When {@code strict==true}, any key present in
     * {@code before} or {@code after} but not in {@code universe} records a
     * {@link ViolationKind#STRICT_UNIVERSE_MISMATCH} violation.
     */
    public static void assertDelta(
            Map<String, Object> before,
            Map<String, Object> after,
            Set<String> universe,
            Map<String, Predicate> expected,
            boolean strict) {
        Objects.requireNonNull(before, "before");
        Objects.requireNonNull(after, "after");
        Objects.requireNonNull(universe, "universe");
        Objects.requireNonNull(expected, "expected");

        List<StateDeltaViolation> violations = new ArrayList<>();

        // Universe-deduplication (Set semantics already handles this, but a
        // copy guards against caller mutation mid-iteration).
        Set<String> universeSet = new HashSet<>(universe);

        if (strict) {
            Set<String> seen = new TreeSet<>();
            seen.addAll(before.keySet());
            seen.addAll(after.keySet());
            for (String key : seen) {
                if (!universeSet.contains(key)) {
                    violations.add(new StateDeltaViolation(
                            ViolationKind.STRICT_UNIVERSE_MISMATCH,
                            key,
                            before.get(key),
                            after.get(key),
                            null,
                            ""));
                }
            }
        }

        // Iterate universe in deterministic order — TreeSet gives sorted keys
        // so violation order is reproducible across JVMs/runs.
        Set<String> orderedUniverse = new TreeSet<>(universeSet);
        for (String key : orderedUniverse) {
            Object oldValue = before.get(key);
            Object newValue = after.get(key);
            Predicate predicate = expected.get(key);

            if (predicate != null) {
                PredicateResult result;
                try {
                    result = predicate.test(oldValue, newValue);
                } catch (RuntimeException e) {
                    result = PredicateResult.fail("predicate threw: " + e.getMessage());
                }
                if (!result.ok()) {
                    violations.add(new StateDeltaViolation(
                            ViolationKind.PREDICATE_FAILED,
                            key,
                            oldValue,
                            newValue,
                            predicate.predicateName(),
                            result.reason()));
                }
            } else if (!deepEquals(oldValue, newValue)) {
                violations.add(new StateDeltaViolation(
                        ViolationKind.UNDECLARED_CHANGE,
                        key,
                        oldValue,
                        newValue,
                        null,
                        ""));
            }
        }

        if (!violations.isEmpty()) {
            throw new StateDeltaException(violations);
        }
    }

    // ------------------------------------------------------------------------
    // Deep equality — recursive over Map / Collection / primitives + Objects.deepEquals fallback
    // ------------------------------------------------------------------------

    /**
     * Structural deep equality for JSON-shaped values: primitives, Strings,
     * {@link Map}s, {@link Collection}s, arrays. Falls back to
     * {@link Objects#deepEquals(Object, Object)} for anything else.
     *
     * <p>This is package-private so {@link Predicates} can reuse it.
     */
    static boolean deepEquals(Object a, Object b) {
        if (a == b) return true;
        if (a == null || b == null) return false;

        if (a instanceof Map<?, ?> am && b instanceof Map<?, ?> bm) {
            if (am.size() != bm.size()) return false;
            for (Map.Entry<?, ?> e : am.entrySet()) {
                if (!bm.containsKey(e.getKey())) return false;
                if (!deepEquals(e.getValue(), bm.get(e.getKey()))) return false;
            }
            return true;
        }
        if (a instanceof Map<?, ?> || b instanceof Map<?, ?>) return false;

        if (a instanceof Collection<?> ac && b instanceof Collection<?> bc) {
            if (ac.size() != bc.size()) return false;
            var ai = ac.iterator();
            var bi = bc.iterator();
            while (ai.hasNext()) {
                if (!deepEquals(ai.next(), bi.next())) return false;
            }
            return true;
        }
        if (a instanceof Collection<?> || b instanceof Collection<?>) return false;

        // Arrays + boxed primitives + Strings → Objects.deepEquals handles correctly.
        return Objects.deepEquals(a, b);
    }

    // ------------------------------------------------------------------------
    // Helpers — small builders for tests
    // ------------------------------------------------------------------------

    /**
     * Build a deep-frozen snapshot of the given key→value mapping. Snapshots
     * are immutable; subsequent mutation of source collections does not
     * affect the snapshot's view.
     */
    public static Map<String, Object> snapshot(Map<String, Object> source) {
        Map<String, Object> out = new LinkedHashMap<>();
        for (Map.Entry<String, Object> e : source.entrySet()) {
            out.put(e.getKey(), freeze(e.getValue()));
        }
        return Collections.unmodifiableMap(out);
    }

    private static Object freeze(Object value) {
        if (value == null) return null;
        if (value instanceof Map<?, ?> m) {
            Map<Object, Object> copy = new LinkedHashMap<>();
            for (Map.Entry<?, ?> e : m.entrySet()) {
                copy.put(e.getKey(), freeze(e.getValue()));
            }
            return Collections.unmodifiableMap(copy);
        }
        if (value instanceof List<?> l) {
            List<Object> copy = new ArrayList<>(l.size());
            for (Object item : l) {
                copy.add(freeze(item));
            }
            return Collections.unmodifiableList(copy);
        }
        if (value instanceof Collection<?> c) {
            List<Object> copy = new ArrayList<>(c.size());
            for (Object item : c) {
                copy.add(freeze(item));
            }
            return Collections.unmodifiableList(copy);
        }
        // Primitives, Strings, boxed numerics — already immutable.
        return value;
    }
}

// NWAVE-POLYGLOT-JAVA v1 — pilot template. Python canonical source of truth
// lives at `nwave_ai/state_delta/`. Updates to the Python contract must be
// ported here.
