/*
 * SignupScenarios.java — generated from FeatureScenarios.java.template
 * for the polyglot pilot toy feature.
 *
 * Pillars 1+2 — domain-language scenarios composed from step methods imported
 * statically from SignupSpecifications. JUnit 5 picks up *Test/*Scenarios.java
 * via surefire `<includes>` in pom.xml.
 */
package pilot;

import static pilot.SignupSpecifications.given_aFreshSignupRegistry;
import static pilot.SignupSpecifications.then_secondSignupIsRejectedAndStateIsUnchanged;
import static pilot.SignupSpecifications.then_userIsAddedToRegistryAndAuditedOnce;
import static pilot.SignupSpecifications.when_userAttemptsDuplicateSignup;
import static pilot.SignupSpecifications.when_userSignsUpWithEmail;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

class SignupScenarios {

    @Test
    @DisplayName("User signs up with a valid email and is added to the registry")
    void userSignsUpAndIsRegistered() throws Exception {
        given_aFreshSignupRegistry();
        when_userSignsUpWithEmail("alice@example.com");
        then_userIsAddedToRegistryAndAuditedOnce("alice@example.com");
    }

    @Test
    @DisplayName("Duplicate signup is rejected and leaves registry+audit unchanged")
    void duplicateSignupIsRejected() throws Exception {
        // Pillar 2: this Given is the composition of the previous scenario's
        // Given + When — start with a registry already containing alice.
        given_aFreshSignupRegistry();
        when_userSignsUpWithEmail("alice@example.com");

        when_userAttemptsDuplicateSignup("alice@example.com");
        then_secondSignupIsRejectedAndStateIsUnchanged();
    }
}
