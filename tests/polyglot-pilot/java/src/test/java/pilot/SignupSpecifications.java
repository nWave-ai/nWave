/*
 * SignupSpecifications.java — step-method companion class for the polyglot pilot.
 *
 * Generated from FeatureSpecifications.java.template. Module-scope fixture
 * is established by given_* (NOT @BeforeEach) so JUnit's collection mechanism
 * is decoupled from this non-test-class file.
 */
package pilot;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

import common.Predicates;
import common.StateDelta;

public final class SignupSpecifications {

    private SignupSpecifications() {
        // Static utility — no instances.
    }

    // ------------------------------------------------------------------------
    // Test fixture
    // ------------------------------------------------------------------------

    private static ProductionApp app;
    private static Map<String, Object> stateBefore;

    private static final Set<String> SIGNUP_UNIVERSE =
            Set.of("registry.users", "audit.events");

    // ------------------------------------------------------------------------
    // Step methods
    // ------------------------------------------------------------------------

    public static void given_aFreshSignupRegistry() {
        app = new ProductionApp();
        stateBefore = app.captureUniverse(SIGNUP_UNIVERSE);
    }

    public static void when_userSignsUpWithEmail(String email) {
        app.signup(email);
    }

    public static void then_userIsAddedToRegistryAndAuditedOnce(String email) {
        String normalized = email.trim().toLowerCase();
        Map<String, Object> stateAfter = app.captureUniverse(SIGNUP_UNIVERSE);

        Map<String, StateDelta.Predicate> expected = new LinkedHashMap<>();
        expected.put("registry.users", Predicates.listAppended(Map.of("email", normalized)));
        expected.put("audit.events", Predicates.listAppended(
                Map.of("type", "UserSignedUp", "email", normalized)));

        StateDelta.assertDelta(stateBefore, stateAfter, SIGNUP_UNIVERSE, expected);
    }

    public static void when_userAttemptsDuplicateSignup(String email) {
        // Re-baseline so the next then_ measures the duplicate's delta only.
        stateBefore = app.captureUniverse(SIGNUP_UNIVERSE);
        try {
            app.signup(email);
        } catch (RuntimeException expected) {
            // Expected — duplicate rejection. then_ asserts the observable zero-delta.
        }
    }

    public static void then_secondSignupIsRejectedAndStateIsUnchanged() {
        Map<String, Object> stateAfter = app.captureUniverse(SIGNUP_UNIVERSE);
        Map<String, StateDelta.Predicate> expected = new LinkedHashMap<>();
        expected.put("registry.users", Predicates.unchanged());
        expected.put("audit.events", Predicates.unchanged());
        StateDelta.assertDelta(stateBefore, stateAfter, SIGNUP_UNIVERSE, expected);
    }
}
