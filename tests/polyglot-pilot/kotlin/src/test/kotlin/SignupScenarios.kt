// SignupScenarios.kt — domain-language acceptance scenarios for the toy
// signup feature. Pilot proof that the
// `nWave/templates/polyglot/kotlin/FeatureScenarios.kt.template` shape works
// end-to-end against a real ProductionApp.

import io.kotest.core.spec.style.FunSpec

class SignupScenarios : FunSpec({

    beforeEach {
        FeatureSpecifications.setup()
    }

    test("User signs up with a valid email and is added to the registry") {
        FeatureSpecifications.given_aFreshSignupRegistry()
        FeatureSpecifications.`when_userSignsUpWithEmail`("alice@example.com")
        FeatureSpecifications.then_userIsAddedToRegistryAndAuditedOnce("alice@example.com")
    }

    test("Duplicate signup is rejected and leaves registry+audit unchanged") {
        FeatureSpecifications.given_aFreshSignupRegistry()
        FeatureSpecifications.`when_userSignsUpWithEmail`("alice@example.com")

        FeatureSpecifications.`when_userAttemptsDuplicateSignup`("alice@example.com")
        FeatureSpecifications.then_secondSignupIsRejectedAndStateIsUnchanged()
    }
})
