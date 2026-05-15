// FeatureSpecifications.kt — step-method module backing SignupScenarios.
// Pilot proof of the
// `nWave/templates/polyglot/kotlin/FeatureSpecifications.kt.template` shape.

import nwave.polyglot.statedelta.StateDelta
import nwave.polyglot.statedelta.arrayAppended
import nwave.polyglot.statedelta.unchanged

object FeatureSpecifications {

    private val SIGNUP_UNIVERSE: Set<String> = setOf("registry.users", "audit.events")

    private var app: ProductionApp? = null
    private var stateBefore: Map<String, Any?> = emptyMap()

    fun setup() {
        app = ProductionApp()
        stateBefore = requireApp().captureUniverse(SIGNUP_UNIVERSE)
    }

    private fun requireApp(): ProductionApp =
        app ?: error("ProductionApp not initialised — call setup() in beforeEach")

    fun given_aFreshSignupRegistry() {
        stateBefore = requireApp().captureUniverse(SIGNUP_UNIVERSE)
    }

    fun `when_userSignsUpWithEmail`(email: String) {
        requireApp().signup(email)
    }

    fun then_userIsAddedToRegistryAndAuditedOnce(email: String) {
        val stateAfter = requireApp().captureUniverse(SIGNUP_UNIVERSE)
        StateDelta.assert(
            before = stateBefore,
            after = stateAfter,
            universe = SIGNUP_UNIVERSE,
            expected = mapOf(
                "registry.users" to arrayAppended(mapOf("email" to email)),
                "audit.events" to arrayAppended(mapOf("type" to "UserSignedUp", "email" to email)),
            ),
        )
    }

    fun `when_userAttemptsDuplicateSignup`(email: String) {
        stateBefore = requireApp().captureUniverse(SIGNUP_UNIVERSE)
        try {
            requireApp().signup(email)
        } catch (_: DuplicateSignupError) {
            // Expected rejection — swallowed; then_ asserts the rejection's
            // observable consequence (zero state delta).
        }
    }

    fun then_secondSignupIsRejectedAndStateIsUnchanged() {
        val stateAfter = requireApp().captureUniverse(SIGNUP_UNIVERSE)
        StateDelta.assert(
            before = stateBefore,
            after = stateAfter,
            universe = SIGNUP_UNIVERSE,
            expected = mapOf(
                "registry.users" to unchanged(),
                "audit.events" to unchanged(),
            ),
        )
    }
}
