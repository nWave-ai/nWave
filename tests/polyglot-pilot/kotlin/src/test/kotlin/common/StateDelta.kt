// StateDelta.kt — pilot copy of the Kotlin state-delta port template.
//
// Canonical template lives at
// `nWave/templates/polyglot/kotlin/StateDelta.kt.template`. This file MUST
// stay in lockstep with it; the smoke pilot is the contract proof.

package nwave.polyglot.statedelta

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

data class PredicateResult(val ok: Boolean, val reason: String = "") {
    companion object {
        fun pass(): PredicateResult = PredicateResult(true)
        fun fail(reason: String): PredicateResult = PredicateResult(false, reason)
    }
}

class Predicate(
    val name: String,
    private val fn: (Any?, Any?) -> Boolean,
) {
    operator fun invoke(oldValue: Any?, newValue: Any?): PredicateResult =
        try {
            if (fn(oldValue, newValue)) PredicateResult.pass()
            else PredicateResult.fail(name)
        } catch (_: Throwable) {
            PredicateResult.fail("predicate threw")
        }
}

enum class ViolationKind {
    UNDECLARED_CHANGE,
    PREDICATE_FAILED,
    STRICT_UNIVERSE_MISMATCH,
}

data class StateDeltaViolation(
    val kind: ViolationKind,
    val key: String,
    val oldValue: Any?,
    val newValue: Any?,
    val predicateName: String?,
)

class StateDeltaException(
    val violations: List<StateDeltaViolation>,
) : AssertionError(format(violations)) {
    companion object {
        private fun format(violations: List<StateDeltaViolation>): String {
            val header = "StateDelta.assert: ${violations.size} violation(s) detected:"
            val lines = violations.map { v ->
                val base = "  kind='${v.kind}' key='${v.key}' " +
                    "old=${repr(v.oldValue)} new=${repr(v.newValue)}"
                if (v.predicateName != null) "$base predicate_name='${v.predicateName}'"
                else base
            }
            return (listOf(header) + lines).joinToString("\n")
        }

        private fun repr(value: Any?): String = when (value) {
            null -> "null"
            is String -> "\"$value\""
            is Map<*, *> -> "{${value.entries.joinToString(",") { "${repr(it.key)}=${repr(it.value)}" }}}"
            is Iterable<*> -> "[${value.joinToString(",") { repr(it) }}]"
            is Array<*> -> "[${value.joinToString(",") { repr(it) }}]"
            else -> value.toString()
        }
    }
}

// ---------------------------------------------------------------------------
// Deep equality
// ---------------------------------------------------------------------------

fun deepEquals(a: Any?, b: Any?): Boolean {
    if (a === b) return true
    if (a == null || b == null) return false

    if (a is Map<*, *> && b is Map<*, *>) {
        if (a.size != b.size) return false
        for ((k, v) in a) {
            if (!b.containsKey(k)) return false
            if (!deepEquals(v, b[k])) return false
        }
        return true
    }

    if (a is String || b is String) return a == b

    val al = toListOrNull(a)
    val bl = toListOrNull(b)
    if (al != null && bl != null) {
        if (al.size != bl.size) return false
        for (i in al.indices) {
            if (!deepEquals(al[i], bl[i])) return false
        }
        return true
    }
    if (al != null || bl != null) return false

    return a == b
}

private fun toListOrNull(value: Any?): List<Any?>? = when (value) {
    is List<*> -> value
    is Array<*> -> value.toList()
    is IntArray -> value.toList()
    is LongArray -> value.toList()
    is DoubleArray -> value.toList()
    is FloatArray -> value.toList()
    is BooleanArray -> value.toList()
    is ByteArray -> value.toList()
    is ShortArray -> value.toList()
    is CharArray -> value.toList()
    is Iterable<*> -> value.toList()
    else -> null
}

// ---------------------------------------------------------------------------
// Predicate factories
// ---------------------------------------------------------------------------

fun unchanged(): Predicate = Predicate("unchanged()") { old, next -> deepEquals(old, next) }

fun prependedWith(prefix: String, sep: String = ":"): Predicate {
    val expected = prefix + sep
    return Predicate("prepended_with($prefix)") { old, next ->
        old is String && next is String && next == expected + old
    }
}

fun appendedWith(suffix: String, sep: String = ":"): Predicate =
    Predicate("appended_with($suffix)") { old, next ->
        old is String && next is String && next == "$old$sep$suffix"
    }

fun setTo(value: Any?): Predicate =
    Predicate("set_to(${value ?: "null"})") { _, next -> deepEquals(next, value) }

fun containing(substring: Any?): Predicate =
    Predicate("containing(${substring ?: "null"})") { _, next ->
        when {
            next is String && substring is String -> next.contains(substring)
            next is Iterable<*> -> next.any { deepEquals(it, substring) }
            next is Array<*> -> next.any { deepEquals(it, substring) }
            else -> false
        }
    }

fun normalizedTo(normalizer: (Any?) -> Any?): Predicate =
    Predicate("normalized_to(<normalizer>)") { old, next ->
        deepEquals(normalizer(old), normalizer(next))
    }

fun idempotentAfter(prefix: String, sep: String = ":"): Predicate =
    Predicate("idempotent_after($prefix)") { _, next ->
        next is String && next.split(sep).firstOrNull() == prefix
    }

fun legacyHealed(
    detector: (Any?) -> Boolean,
    healedCheck: (Any?) -> Boolean,
): Predicate = Predicate("legacy_healed(<det>,<heal>)") { old, next ->
    detector(old) && healedCheck(next)
}

fun arrayPrepended(item: Any?): Predicate =
    Predicate("array_prepended(${item ?: "null"})") { old, next ->
        val ol = toListOrNull(old)
        val nl = toListOrNull(next)
        when {
            ol == null || nl == null -> false
            nl.size != ol.size + 1 -> false
            !deepEquals(nl[0], item) -> false
            else -> ol.indices.all { deepEquals(nl[it + 1], ol[it]) }
        }
    }

fun arrayAppended(item: Any?): Predicate =
    Predicate("array_appended(${item ?: "null"})") { old, next ->
        val ol = toListOrNull(old)
        val nl = toListOrNull(next)
        when {
            ol == null || nl == null -> false
            nl.size != ol.size + 1 -> false
            !deepEquals(nl.last(), item) -> false
            else -> ol.indices.all { deepEquals(nl[it], ol[it]) }
        }
    }

// ---------------------------------------------------------------------------
// Driving object — StateDelta.assert
// ---------------------------------------------------------------------------

object StateDelta {
    fun assert(
        before: Map<String, Any?>,
        after: Map<String, Any?>,
        universe: Set<String>,
        expected: Map<String, Predicate>,
        strict: Boolean = false,
    ) {
        val violations = mutableListOf<StateDeltaViolation>()

        if (strict) {
            val seen = (before.keys + after.keys)
            val extras = seen.filter { it !in universe }.sorted()
            for (key in extras) {
                violations += StateDeltaViolation(
                    kind = ViolationKind.STRICT_UNIVERSE_MISMATCH,
                    key = key,
                    oldValue = before[key],
                    newValue = after[key],
                    predicateName = null,
                )
            }
        }

        for (key in universe) {
            val oldValue = before[key]
            val newValue = after[key]
            val predicate = expected[key]

            if (predicate != null) {
                val result = predicate(oldValue, newValue)
                if (!result.ok) {
                    violations += StateDeltaViolation(
                        kind = ViolationKind.PREDICATE_FAILED,
                        key = key,
                        oldValue = oldValue,
                        newValue = newValue,
                        predicateName = predicate.name,
                    )
                }
            } else if (!deepEquals(oldValue, newValue)) {
                violations += StateDeltaViolation(
                    kind = ViolationKind.UNDECLARED_CHANGE,
                    key = key,
                    oldValue = oldValue,
                    newValue = newValue,
                    predicateName = null,
                )
            }
        }

        if (violations.isNotEmpty()) {
            throw StateDeltaException(violations)
        }
    }
}
