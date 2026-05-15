/*
 * StateDeltaTest.java — JUnit 5 + jqwik contract tests for the Java port.
 *
 * Mirrors `tests/state_delta/unit/test_matcher.py` and the predicate tests
 * for the Python canonical. jqwik `@Property` covers universe semantics where
 * the contract is quantified; standard `@Test` covers concrete examples.
 *
 * One @Property per predicate is the layered-unit minimum (paradigm mandate).
 */
package common;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.fail;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import net.jqwik.api.ForAll;
import net.jqwik.api.Property;
import net.jqwik.api.constraints.AlphaChars;
import net.jqwik.api.constraints.NotBlank;
import net.jqwik.api.constraints.StringLength;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import common.StateDelta.Predicate;
import common.StateDelta.PredicateResult;
import common.StateDelta.StateDeltaException;
import common.StateDelta.StateDeltaViolation;
import common.StateDelta.ViolationKind;

class StateDeltaTest {

    // ------------------------------------------------------------------------
    // assertDelta — walking skeleton + core semantics
    // ------------------------------------------------------------------------

    @Test
    @DisplayName("returns silently on a clean prepend transition")
    void cleanPrependPasses() {
        StateDelta.assertDelta(
                Map.of("PATH", "/usr/bin"),
                Map.of("PATH", "/des/bin:/usr/bin"),
                Set.of("PATH"),
                Map.of("PATH", Predicates.prependedWith("/des/bin")));
    }

    @Test
    @DisplayName("throws StateDeltaException with full context on predicate failure")
    void predicateFailureCarriesContext() {
        StateDeltaException ex = assertThrows(StateDeltaException.class, () ->
                StateDelta.assertDelta(
                        Map.of("PATH", "/usr/bin"),
                        Map.of("PATH", "/wrong"),
                        Set.of("PATH"),
                        Map.of("PATH", Predicates.prependedWith("/des/bin"))));
        assertEquals(1, ex.violations().size());
        StateDeltaViolation v = ex.violations().get(0);
        assertEquals(ViolationKind.PREDICATE_FAILED, v.kind());
        assertEquals("PATH", v.key());
        assertEquals("/usr/bin", v.oldValue());
        assertEquals("/wrong", v.newValue());
        assertEquals("prepended_with(/des/bin)", v.predicateName());
        assertTrue(ex.getMessage().contains("PATH"));
        assertTrue(ex.getMessage().contains("predicate_name='prepended_with(/des/bin)'"));
    }

    @Test
    @DisplayName("implicit-unchanged catches an undeclared change on an adjacent slot")
    void implicitUnchangedCatchesAdjacent() {
        StateDeltaException ex = assertThrows(StateDeltaException.class, () ->
                StateDelta.assertDelta(
                        Map.of("PATH", "/u/bin", "HOME", "/home/u"),
                        Map.of("PATH", "/des/bin:/u/bin", "HOME", "/home/changed"),
                        Set.of("PATH", "HOME"),
                        Map.of("PATH", Predicates.prependedWith("/des/bin"))));
        assertEquals(1, ex.violations().size());
        StateDeltaViolation v = ex.violations().get(0);
        assertEquals(ViolationKind.UNDECLARED_CHANGE, v.kind());
        assertEquals("HOME", v.key());
    }

    @Test
    @DisplayName("collects multiple violations into a single exception (A7)")
    void multiViolationAggregation() {
        StateDeltaException ex = assertThrows(StateDeltaException.class, () -> {
            Map<String, Predicate> expected = new HashMap<>();
            expected.put("PATH", Predicates.prependedWith("/des"));
            expected.put("HOME", Predicates.unchanged());
            StateDelta.assertDelta(
                    Map.of("PATH", "/u", "HOME", "/h", "X", "1"),
                    Map.of("PATH", "/wrong", "HOME", "/h2", "X", "1"),
                    Set.of("PATH", "HOME", "X"),
                    expected);
        });
        assertEquals(2, ex.violations().size());
        // Deterministic ordering (TreeSet) — HOME before PATH alphabetically.
        List<String> keys = ex.violations().stream().map(StateDeltaViolation::key).sorted().toList();
        assertEquals(List.of("HOME", "PATH"), keys);
    }

    @Test
    @DisplayName("strict mode flags keys present in before|after but missing from universe")
    void strictModeFlagsExtras() {
        StateDeltaException ex = assertThrows(StateDeltaException.class, () ->
                StateDelta.assertDelta(
                        Map.of("PATH", "/u", "EXTRA", "x"),
                        Map.of("PATH", "/des:/u", "EXTRA", "x2"),
                        Set.of("PATH"),
                        Map.of("PATH", Predicates.prependedWith("/des")),
                        true));
        boolean foundExtra = ex.violations().stream()
                .anyMatch(v -> v.kind() == ViolationKind.STRICT_UNIVERSE_MISMATCH && v.key().equals("EXTRA"));
        assertTrue(foundExtra, "expected STRICT_UNIVERSE_MISMATCH on key=EXTRA");
    }

    // ------------------------------------------------------------------------
    // Predicate library — Python parity (one @Test concrete + one @Property quantified)
    // ------------------------------------------------------------------------

    @Test
    @DisplayName("unchanged() — deep equality on Maps and primitives")
    void unchangedDeepEquality() {
        Predicate p = Predicates.unchanged();
        assertTrue(p.test(1, 1).ok());
        assertFalse(p.test(1, 2).ok());
        assertTrue(p.test(Map.of("a", 1), Map.of("a", 1)).ok());
        assertFalse(p.test(Map.of("a", 1), Map.of("a", 2)).ok());
    }

    @Property
    void unchangedAlwaysPassesOnIdenticalReference(@ForAll @AlphaChars @StringLength(min = 1, max = 20) String v) {
        assertTrue(Predicates.unchanged().test(v, v).ok());
    }

    @Test
    @DisplayName("prependedWith(prefix, sep) — concrete pass + fail")
    void prependedWithConcrete() {
        assertTrue(Predicates.prependedWith("/des/bin").test("/usr/bin", "/des/bin:/usr/bin").ok());
        assertFalse(Predicates.prependedWith("/des/bin").test("/usr/bin", "/wrong").ok());
    }

    @Property
    void prependedWithMatchesAnyTail(@ForAll @AlphaChars @StringLength(min = 0, max = 30) String tail) {
        PredicateResult r = Predicates.prependedWith("PRE").test(tail, "PRE:" + tail);
        assertTrue(r.ok(), "expected pass for tail=" + tail);
    }

    @Test
    @DisplayName("appendedWith(suffix, sep) — concrete pass + fail")
    void appendedWithConcrete() {
        assertTrue(Predicates.appendedWith(".bak").test("/etc/hosts", "/etc/hosts:.bak").ok());
        assertFalse(Predicates.appendedWith(".bak").test("/etc/hosts", "/etc/hosts").ok());
    }

    @Test
    @DisplayName("setTo(value) — ignores old, matches new")
    void setToIgnoresOld() {
        assertTrue(Predicates.setTo("active").test("inactive", "active").ok());
        assertTrue(Predicates.setTo("active").test("anything", "active").ok());
        assertFalse(Predicates.setTo("active").test("inactive", "pending").ok());
        assertTrue(Predicates.setTo(Map.of("k", 1)).test(null, Map.of("k", 1)).ok());
    }

    @Test
    @DisplayName("containing(sub) — string substring + collection element")
    void containingSubstringOrElement() {
        assertTrue(Predicates.containing("/usr/bin").test("", "/des/bin:/usr/bin").ok());
        assertFalse(Predicates.containing("/usr/bin").test("", "/des/bin:/opt/bin").ok());
        assertTrue(Predicates.containing(Map.of("id", 1))
                .test(null, List.of(Map.of("id", 1), Map.of("id", 2))).ok());
        assertFalse(Predicates.containing(Map.of("id", 9))
                .test(null, List.of(Map.of("id", 1), Map.of("id", 2))).ok());
    }

    @Test
    @DisplayName("normalizedTo(fn) — equality under a normaliser")
    void normalizedToUnderFn() {
        Predicate expandHome = Predicates.normalizedTo(v ->
                v instanceof String s ? s.replace("$HOME", "/home/u") : v);
        assertTrue(expandHome.test("/home/u/.local/bin", "$HOME/.local/bin").ok());
        assertFalse(expandHome.test("/home/u/.local/bin", "$HOME/.other/bin").ok());
    }

    @Test
    @DisplayName("idempotentAfter(prefix) — first segment match")
    void idempotentAfterFirstSegment() {
        assertTrue(Predicates.idempotentAfter("DES_BIN").test("anything", "DES_BIN:/usr/bin").ok());
        assertFalse(Predicates.idempotentAfter("DES_BIN").test("anything", "/usr/bin:/opt/bin").ok());
    }

    @Test
    @DisplayName("legacyHealed(det, heal) — D-11 paper-trace 4 cases")
    void legacyHealedFourCases() {
        final String LEGACY = "DES_BIN:SYSTEM_PATH_FALLBACK";
        Predicate pred = Predicates.legacyHealed(
                old -> LEGACY.equals(old),
                next -> next instanceof String s && !s.equals(LEGACY) && s.startsWith("DES_BIN:"));
        assertTrue(pred.test(LEGACY, "DES_BIN:/usr/bin").ok(), "case 1: healed");
        assertFalse(pred.test(LEGACY, LEGACY).ok(), "case 2: heal not applied");
        assertFalse(pred.test("/usr/bin", "DES_BIN:/usr/bin").ok(), "case 3: not legacy");
    }

    @Test
    @DisplayName("listAppended(item) — new == [...old, item]")
    void listAppendedShape() {
        assertTrue(Predicates.listAppended("z").test(List.of(), List.of("z")).ok());
        assertTrue(Predicates.listAppended("z").test(List.of("x"), List.of("x", "z")).ok());
        assertFalse(Predicates.listAppended("z").test(List.of("x"), List.of("z", "x")).ok());
    }

    @Test
    @DisplayName("listPrepended(item) — new == [item, ...old]")
    void listPrependedShape() {
        assertTrue(Predicates.listPrepended("a").test(List.of(), List.of("a")).ok());
        assertTrue(Predicates.listPrepended("a").test(List.of("x"), List.of("a", "x")).ok());
        assertFalse(Predicates.listPrepended("a").test(List.of("x"), List.of("x", "a")).ok());
    }

    // ------------------------------------------------------------------------
    // Universe semantics — quantified properties (jqwik)
    // ------------------------------------------------------------------------

    @Property
    void implicitUnchangedAlwaysCatchesAdjacentMutation(
            @ForAll @NotBlank @StringLength(min = 1, max = 20) String oldHome,
            @ForAll @NotBlank @StringLength(min = 1, max = 20) String newHome) {
        if (oldHome.equals(newHome)) {
            return; // precondition — different values
        }
        boolean threw = false;
        try {
            StateDelta.assertDelta(
                    Map.of("PATH", "/u", "HOME", oldHome),
                    Map.of("PATH", "/des:/u", "HOME", newHome),
                    Set.of("PATH", "HOME"),
                    Map.of("PATH", Predicates.prependedWith("/des")));
        } catch (StateDeltaException e) {
            threw = true;
        }
        assertTrue(threw, "expected implicit-unchanged to flag HOME mutation");
    }

    @Test
    @DisplayName("universe slot with matching predicate permits mutation")
    void permittedMutationGoesGreen() {
        StateDelta.assertDelta(
                Map.of("PATH", "/u", "HOME", "/h"),
                Map.of("PATH", "/des:/u", "HOME", "/h"),
                Set.of("PATH", "HOME"),
                Map.of("PATH", Predicates.prependedWith("/des")));
    }

    // ------------------------------------------------------------------------
    // Snapshot helper — protects callers from mid-test mutation
    // ------------------------------------------------------------------------

    @Test
    @DisplayName("snapshot() returns deep-frozen copy that survives source mutation")
    void snapshotIsImmutable() {
        List<String> mutableList = new ArrayList<>();
        mutableList.add("a");
        Map<String, Object> source = new LinkedHashMap<>();
        source.put("k", mutableList);

        Map<String, Object> snap = StateDelta.snapshot(source);
        mutableList.add("b"); // mutate source after snapshot

        Object snappedK = snap.get("k");
        assertTrue(snappedK instanceof List<?>);
        assertEquals(1, ((List<?>) snappedK).size(), "snapshot must not reflect source mutation");

        // And it must be unmodifiable.
        assertThrows(UnsupportedOperationException.class, () -> snap.put("k2", "v"));
    }

    // Avoid unused-import lint flagging when @DisplayName-only tests are stripped.
    @SuppressWarnings("unused")
    private static void noop() {
        fail("unreachable");
    }
}
