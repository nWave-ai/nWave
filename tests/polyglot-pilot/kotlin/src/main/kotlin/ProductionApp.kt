// ProductionApp.kt — toy signup feature for the Kotlin polyglot pilot.
//
// Composition root: constructs the in-memory registry and audit log, exposes
// `signup` (driving operation) and `captureUniverse` (state inspection at
// port-exposed slots). Real-feature shape: in-process domain + driven ports
// (here both in-memory).
//
// Universe slots exposed:
//   - "registry.users" : List<Map<String, Any?>> — each entry is { email }
//   - "audit.events"   : List<Map<String, Any?>> — each entry is { type, email }
//
// Internal field names are NOT part of the universe — refactoring internals
// stays GREEN.

class DuplicateSignupError(val email: String) :
    RuntimeException("Duplicate signup rejected: $email")

class ProductionApp {

    // Driven-port state (in-memory).
    private val users: MutableList<Map<String, Any?>> = mutableListOf()
    private val events: MutableList<Map<String, Any?>> = mutableListOf()

    /**
     * Driving port — signup a user by email. Rejects duplicates by throwing
     * [DuplicateSignupError]. On success: appends to registry AND appends a
     * single `UserSignedUp` audit event.
     */
    fun signup(email: String): Map<String, Any?> {
        val normalised = email.trim().lowercase()
        require(normalised.isNotEmpty()) { "signup: email must be non-empty" }
        if (users.any { it["email"] == normalised }) {
            throw DuplicateSignupError(normalised)
        }
        val record = mapOf("email" to normalised)
        users.add(record)
        events.add(mapOf("type" to "UserSignedUp", "email" to normalised))
        return record
    }

    /**
     * State-inspection port — return a snapshot of the universe slots
     * requested. Snapshot returns immutable copies so test assertions cannot
     * mutate production state by accident.
     */
    fun captureUniverse(keys: Set<String>): Map<String, Any?> {
        val snapshot = mutableMapOf<String, Any?>()
        for (key in keys) {
            snapshot[key] = when (key) {
                "registry.users" -> users.map { it.toMap() }
                "audit.events" -> events.map { it.toMap() }
                // Unknown slot — return null so state-delta sees the absence
                // explicitly rather than silently fabricating a value.
                else -> null
            }
        }
        return snapshot
    }
}
