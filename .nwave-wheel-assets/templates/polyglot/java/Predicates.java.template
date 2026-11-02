/*
 * Predicates.java — predicate factory mirroring nwave_ai.state_delta.predicates
 * (Python canonical). Static factory methods returning {@link StateDelta.Predicate}
 * instances with descriptive {@code predicateName()} values for violation
 * messages.
 *
 * Canonical 8 predicates (Python parity):
 *   unchanged          — old equals new (deep)
 *   prependedWith      — new == prefix + sep + old   (String composition, PATH-style)
 *   appendedWith       — new == old + sep + suffix
 *   setTo              — new equals value (old ignored)
 *   containing         — substring in new (String) or contains element (Collection)
 *   normalizedTo       — normalizer(old) equals normalizer(new)
 *   idempotentAfter    — first segment of new (split by sep) equals prefix
 *   legacyHealed       — detector(old) && healedCheck(new)  (D-11 paper-trace)
 *
 * Java-idiomatic helpers (extension beyond Python parity — covers the
 * collection-shaped state common in Java apps where Python uses colon-strings):
 *   listAppended       — new == [...old, item]
 *   listPrepended      — new == [item, ...old]
 *
 * Source of truth: Python module at `nwave_ai/state_delta/predicates.py`.
 */
package common;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.function.Function;

import common.StateDelta.Predicate;
import common.StateDelta.PredicateResult;

/** Static factory for the canonical 8 + 2 Java-idiomatic predicates. */
public final class Predicates {

    private Predicates() {
        // Static utility — no instances.
    }

    // ------------------------------------------------------------------------
    // 1. unchanged()
    // ------------------------------------------------------------------------

    /** Passes when {@code old} deep-equals {@code newValue}. */
    public static Predicate unchanged() {
        return named("unchanged()", (old, next) ->
                StateDelta.deepEquals(old, next)
                        ? PredicateResult.pass()
                        : PredicateResult.fail("values differ"));
    }

    // ------------------------------------------------------------------------
    // 2. prependedWith(prefix [, sep])
    // ------------------------------------------------------------------------

    /** Passes when {@code newValue} is a String equal to {@code prefix + ":" + old}. */
    public static Predicate prependedWith(String prefix) {
        return prependedWith(prefix, ":");
    }

    /** Passes when {@code newValue} is a String equal to {@code prefix + sep + old}. */
    public static Predicate prependedWith(String prefix, String sep) {
        String expectedPrefix = prefix + sep;
        return named("prepended_with(" + prefix + ")", (old, next) -> {
            if (!(old instanceof String oldStr) || !(next instanceof String newStr)) {
                return PredicateResult.fail("old/new not both Strings");
            }
            return newStr.equals(expectedPrefix + oldStr)
                    ? PredicateResult.pass()
                    : PredicateResult.fail("new != prefix+sep+old");
        });
    }

    // ------------------------------------------------------------------------
    // 3. appendedWith(suffix [, sep])
    // ------------------------------------------------------------------------

    /** Passes when {@code newValue} is a String equal to {@code old + ":" + suffix}. */
    public static Predicate appendedWith(String suffix) {
        return appendedWith(suffix, ":");
    }

    /** Passes when {@code newValue} is a String equal to {@code old + sep + suffix}. */
    public static Predicate appendedWith(String suffix, String sep) {
        return named("appended_with(" + suffix + ")", (old, next) -> {
            if (!(old instanceof String oldStr) || !(next instanceof String newStr)) {
                return PredicateResult.fail("old/new not both Strings");
            }
            return newStr.equals(oldStr + sep + suffix)
                    ? PredicateResult.pass()
                    : PredicateResult.fail("new != old+sep+suffix");
        });
    }

    // ------------------------------------------------------------------------
    // 4. setTo(value)
    // ------------------------------------------------------------------------

    /** Passes when {@code newValue} deep-equals {@code value}; {@code old} is ignored. */
    public static Predicate setTo(Object value) {
        return named("set_to(" + repr(value) + ")", (old, next) ->
                StateDelta.deepEquals(next, value)
                        ? PredicateResult.pass()
                        : PredicateResult.fail("new != value"));
    }

    // ------------------------------------------------------------------------
    // 5. containing(substring)
    // ------------------------------------------------------------------------

    /**
     * Passes when {@code substring} is a substring of {@code newValue} (String),
     * or when {@code newValue} is a {@link Collection} containing a deep-equal
     * element to {@code substring}.
     */
    public static Predicate containing(Object substring) {
        return named("containing(" + repr(substring) + ")", (old, next) -> {
            if (next instanceof String newStr && substring instanceof String s) {
                return newStr.contains(s)
                        ? PredicateResult.pass()
                        : PredicateResult.fail("substring not found");
            }
            if (next instanceof Collection<?> coll) {
                for (Object el : coll) {
                    if (StateDelta.deepEquals(el, substring)) {
                        return PredicateResult.pass();
                    }
                }
                return PredicateResult.fail("element not present in collection");
            }
            return PredicateResult.fail("new is neither String nor Collection");
        });
    }

    // ------------------------------------------------------------------------
    // 6. normalizedTo(normalizer)
    // ------------------------------------------------------------------------

    /** Passes when {@code normalizer.apply(old)} deep-equals {@code normalizer.apply(newValue)}. */
    public static Predicate normalizedTo(Function<Object, Object> normalizer) {
        return named("normalized_to(<normalizer>)", (old, next) ->
                StateDelta.deepEquals(normalizer.apply(old), normalizer.apply(next))
                        ? PredicateResult.pass()
                        : PredicateResult.fail("normalized values differ"));
    }

    // ------------------------------------------------------------------------
    // 7. idempotentAfter(prefix [, sep])
    // ------------------------------------------------------------------------

    /**
     * Passes when the first segment of {@code newValue} (split by {@code sep})
     * equals {@code prefix}. Used to assert prepend-if-absent idempotency.
     */
    public static Predicate idempotentAfter(String prefix) {
        return idempotentAfter(prefix, ":");
    }

    /** Same as {@link #idempotentAfter(String)} with explicit separator. */
    public static Predicate idempotentAfter(String prefix, String sep) {
        return named("idempotent_after(" + prefix + ")", (old, next) -> {
            if (!(next instanceof String newStr)) {
                return PredicateResult.fail("new is not a String");
            }
            String[] parts = newStr.split(java.util.regex.Pattern.quote(sep), 2);
            return parts.length > 0 && parts[0].equals(prefix)
                    ? PredicateResult.pass()
                    : PredicateResult.fail("first segment != prefix");
        });
    }

    // ------------------------------------------------------------------------
    // 8. legacyHealed(detector, healedCheck)
    // ------------------------------------------------------------------------

    /**
     * Passes iff {@code detector.apply(old)} AND {@code healedCheck.apply(newValue)}
     * are both true (D-11 paper-trace pattern).
     */
    public static Predicate legacyHealed(
            Function<Object, Boolean> detector,
            Function<Object, Boolean> healedCheck) {
        return named("legacy_healed(<det>,<heal>)", (old, next) -> {
            boolean detected = Boolean.TRUE.equals(detector.apply(old));
            boolean healed = Boolean.TRUE.equals(healedCheck.apply(next));
            if (detected && healed) {
                return PredicateResult.pass();
            }
            if (!detected) {
                return PredicateResult.fail("detector(old)=false — old is not a legacy value");
            }
            return PredicateResult.fail("healedCheck(new)=false — heal not applied");
        });
    }

    // ------------------------------------------------------------------------
    // Java-idiomatic List helpers (extension)
    // ------------------------------------------------------------------------

    /** Passes when {@code newValue} is a {@link List} equal to {@code [...old, item]}. */
    public static Predicate listAppended(Object item) {
        return named("list_appended(" + repr(item) + ")", (old, next) -> {
            if (!(old instanceof List<?> oldList) || !(next instanceof List<?> newList)) {
                return PredicateResult.fail("old/new not both Lists");
            }
            if (newList.size() != oldList.size() + 1) {
                return PredicateResult.fail("size mismatch (expected old+1)");
            }
            for (int i = 0; i < oldList.size(); i++) {
                if (!StateDelta.deepEquals(newList.get(i), oldList.get(i))) {
                    return PredicateResult.fail("prefix mismatch at index " + i);
                }
            }
            if (!StateDelta.deepEquals(newList.get(newList.size() - 1), item)) {
                return PredicateResult.fail("last element != item");
            }
            return PredicateResult.pass();
        });
    }

    /** Passes when {@code newValue} is a {@link List} equal to {@code [item, ...old]}. */
    public static Predicate listPrepended(Object item) {
        return named("list_prepended(" + repr(item) + ")", (old, next) -> {
            if (!(old instanceof List<?> oldList) || !(next instanceof List<?> newList)) {
                return PredicateResult.fail("old/new not both Lists");
            }
            if (newList.size() != oldList.size() + 1) {
                return PredicateResult.fail("size mismatch (expected old+1)");
            }
            if (!StateDelta.deepEquals(newList.get(0), item)) {
                return PredicateResult.fail("first element != item");
            }
            for (int i = 0; i < oldList.size(); i++) {
                if (!StateDelta.deepEquals(newList.get(i + 1), oldList.get(i))) {
                    return PredicateResult.fail("tail mismatch at index " + i);
                }
            }
            return PredicateResult.pass();
        });
    }

    // ------------------------------------------------------------------------
    // Internal: name-preserving Predicate wrapper
    // ------------------------------------------------------------------------

    private static Predicate named(String name, Predicate impl) {
        return new Predicate() {
            @Override
            public PredicateResult test(Object oldValue, Object newValue) {
                return impl.test(oldValue, newValue);
            }

            @Override
            public String predicateName() {
                return name;
            }

            @Override
            public String toString() {
                return name;
            }
        };
    }

    private static String repr(Object value) {
        if (value == null) return "null";
        if (value instanceof String s) return "\"" + s + "\"";
        return String.valueOf(value);
    }

    // Suppress "unused" warning on helper kept for symmetry with TS arrayPrepended/Appended
    @SuppressWarnings("unused")
    private static List<Object> copyOf(Collection<?> c) {
        return new ArrayList<>(c);
    }
}

// NWAVE-POLYGLOT-JAVA v1 — pilot template. Python canonical source of truth
// lives at `nwave_ai/state_delta/predicates.py`. Updates to the Python contract
// must be ported here.
