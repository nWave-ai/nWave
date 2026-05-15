// StateDelta.cs — C# port of nwave_ai.state_delta (Python canonical).
//
// Polyglot pilot (Epic 3). Mirrors the contract of
// `nwave_ai/state_delta/{matcher,predicates}.py`:
//
//   - Predicate signature: PredicateResult Predicate(object? oldValue, object? newValue)
//   - Universe = IReadOnlySet<string> (set semantics; duplicates ignored)
//   - StateDelta.Assert collects ALL violations across the universe before
//     throwing a single StateDeltaException aggregating them (multi-violation
//     contract A7).
//   - Strict mode reports any key present in before|after but not in universe
//     as a StrictUniverseMismatch violation.
//   - Implicit-unchanged: a key in universe but NOT in expected requires
//     deep-equal between before[key] and after[key]; difference =>
//     UndeclaredChange violation.
//
// Zero external dependencies — uses inline structural deep-equal so this file
// can be dropped into any net6.0+ project without Newtonsoft or AutoFixture.
//
// Source of truth: Python module at `nwave_ai/state_delta/`. Keep the contract
// in sync; deviations are bugs.

#nullable enable

using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Text;

namespace NWave.Polyglot.StateDelta;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/// <summary>Result of a predicate evaluation. Ok=true passes; Ok=false records a violation.</summary>
public readonly record struct PredicateResult(bool Ok, string? Reason = null)
{
    public static PredicateResult Pass() => new(true, null);
    public static PredicateResult Fail(string reason) => new(false, reason);
}

/// <summary>
/// Predicate signature mirrors the Python contract: (old, new) -> bool.
/// Returns PredicateResult so violation messages can include predicate-specific reasons.
/// </summary>
public delegate PredicateResult Predicate(object? oldValue, object? newValue);

/// <summary>Kinds of violations recorded by StateDelta.Assert.</summary>
public enum ViolationKind
{
    UndeclaredChange,
    PredicateFailed,
    StrictUniverseMismatch,
}

/// <summary>A single state-delta violation with full context.</summary>
public sealed record StateDeltaViolation(
    ViolationKind Kind,
    string Key,
    object? Old,
    object? New,
    string? PredicateName
);

/// <summary>Thrown by StateDelta.Assert when one or more violations are detected.</summary>
public sealed class StateDeltaException : Exception
{
    public IReadOnlyList<StateDeltaViolation> Violations { get; }

    public StateDeltaException(IReadOnlyList<StateDeltaViolation> violations)
        : base(Format(violations))
    {
        Violations = violations;
    }

    private static string Format(IReadOnlyList<StateDeltaViolation> violations)
    {
        var sb = new StringBuilder();
        sb.AppendLine($"StateDelta.Assert: {violations.Count} violation(s) detected:");
        foreach (var v in violations)
        {
            sb.Append($"  kind='{v.Kind}' key='{v.Key}' old={Repr(v.Old)} new={Repr(v.New)}");
            if (v.PredicateName is not null)
            {
                sb.Append($" predicate_name='{v.PredicateName}'");
            }
            sb.AppendLine();
        }
        return sb.ToString().TrimEnd();
    }

    private static string Repr(object? value) => value switch
    {
        null => "null",
        string s => $"\"{s}\"",
        IEnumerable e when value is not string => $"[{string.Join(",", e.Cast<object?>().Select(Repr))}]",
        _ => value.ToString() ?? "null",
    };
}

// ---------------------------------------------------------------------------
// Deep equality (zero-dep)
// ---------------------------------------------------------------------------

internal static class DeepEqual
{
    public static bool Equal(object? a, object? b)
    {
        if (ReferenceEquals(a, b)) return true;
        if (a is null || b is null) return false;

        // Dictionaries — compare key-by-key.
        if (a is IDictionary ad && b is IDictionary bd)
        {
            if (ad.Count != bd.Count) return false;
            foreach (DictionaryEntry entry in ad)
            {
                if (!bd.Contains(entry.Key)) return false;
                if (!Equal(entry.Value, bd[entry.Key])) return false;
            }
            return true;
        }

        if (a is string || b is string) return a.Equals(b);

        // Enumerables — compare element-by-element in order.
        if (a is IEnumerable ae && b is IEnumerable be)
        {
            var al = ae.Cast<object?>().ToList();
            var bl = be.Cast<object?>().ToList();
            if (al.Count != bl.Count) return false;
            for (int i = 0; i < al.Count; i++)
            {
                if (!Equal(al[i], bl[i])) return false;
            }
            return true;
        }

        var at = a.GetType();
        var bt = b.GetType();
        if (at != bt) return a.Equals(b);
        var props = at.GetProperties().Where(p => p.CanRead).ToList();
        if (props.Count == 0) return a.Equals(b);
        foreach (var p in props)
        {
            if (!Equal(p.GetValue(a), p.GetValue(b))) return false;
        }
        return true;
    }
}

// ---------------------------------------------------------------------------
// Predicate factories — mirror nwave_ai/state_delta/predicates.py
// ---------------------------------------------------------------------------

public static class StateDelta
{
    private static readonly System.Runtime.CompilerServices.ConditionalWeakTable<object, string> _names = new();

    private static Predicate Named(string name, Func<object?, object?, bool> fn)
    {
        Predicate p = (old, next) => fn(old, next) ? PredicateResult.Pass() : PredicateResult.Fail(name);
        _names.Add(p, name);
        return p;
    }

    internal static string? NameOf(Predicate p) =>
        _names.TryGetValue(p, out var n) ? n : null;

    public static Predicate Unchanged() =>
        Named("unchanged()", (old, next) => DeepEqual.Equal(old, next));

    public static Predicate PrependedWith(string prefix, string sep = ":") =>
        Named($"prepended_with({prefix})", (old, next) =>
        {
            if (old is not string os || next is not string ns) return false;
            return ns == prefix + sep + os;
        });

    public static Predicate AppendedWith(string suffix, string sep = ":") =>
        Named($"appended_with({suffix})", (old, next) =>
        {
            if (old is not string os || next is not string ns) return false;
            return ns == os + sep + suffix;
        });

    public static Predicate SetTo(object? value) =>
        Named($"set_to({value ?? "null"})", (_old, next) => DeepEqual.Equal(next, value));

    public static Predicate Containing(object? substring) =>
        Named($"containing({substring ?? "null"})", (_old, next) =>
        {
            if (next is string ns && substring is string ss) return ns.Contains(ss);
            if (next is IEnumerable ne && next is not string)
            {
                return ne.Cast<object?>().Any(el => DeepEqual.Equal(el, substring));
            }
            return false;
        });

    public static Predicate NormalizedTo(Func<object?, object?> normalizer) =>
        Named("normalized_to(<normalizer>)", (old, next) =>
            DeepEqual.Equal(normalizer(old), normalizer(next)));

    public static Predicate IdempotentAfter(string prefix, string sep = ":") =>
        Named($"idempotent_after({prefix})", (_old, next) =>
        {
            if (next is not string ns) return false;
            return ns.Split(sep)[0] == prefix;
        });

    public static Predicate LegacyHealed(
        Func<object?, bool> detector,
        Func<object?, bool> healedCheck) =>
        Named("legacy_healed(<det>,<heal>)", (old, next) =>
            detector(old) && healedCheck(next));

    public static Predicate ArrayPrepended(object? item) =>
        Named($"array_prepended({item ?? "null"})", (old, next) =>
        {
            if (old is not IEnumerable oe || old is string) return false;
            if (next is not IEnumerable ne || next is string) return false;
            var ol = oe.Cast<object?>().ToList();
            var nl = ne.Cast<object?>().ToList();
            if (nl.Count != ol.Count + 1) return false;
            if (!DeepEqual.Equal(nl[0], item)) return false;
            for (int i = 0; i < ol.Count; i++)
            {
                if (!DeepEqual.Equal(nl[i + 1], ol[i])) return false;
            }
            return true;
        });

    public static Predicate ArrayAppended(object? item) =>
        Named($"array_appended({item ?? "null"})", (old, next) =>
        {
            if (old is not IEnumerable oe || old is string) return false;
            if (next is not IEnumerable ne || next is string) return false;
            var ol = oe.Cast<object?>().ToList();
            var nl = ne.Cast<object?>().ToList();
            if (nl.Count != ol.Count + 1) return false;
            if (!DeepEqual.Equal(nl[^1], item)) return false;
            for (int i = 0; i < ol.Count; i++)
            {
                if (!DeepEqual.Equal(nl[i], ol[i])) return false;
            }
            return true;
        });

    public static void Assert(
        IDictionary<string, object?> before,
        IDictionary<string, object?> after,
        IReadOnlySet<string> universe,
        IDictionary<string, Predicate> expected,
        bool strict = false)
    {
        var violations = new List<StateDeltaViolation>();

        if (strict)
        {
            var seen = new HashSet<string>(before.Keys);
            seen.UnionWith(after.Keys);
            var extras = seen.Where(k => !universe.Contains(k)).OrderBy(k => k, StringComparer.Ordinal);
            foreach (var key in extras)
            {
                before.TryGetValue(key, out var oldValue);
                after.TryGetValue(key, out var newValue);
                violations.Add(new StateDeltaViolation(
                    ViolationKind.StrictUniverseMismatch, key, oldValue, newValue, null));
            }
        }

        foreach (var key in universe)
        {
            before.TryGetValue(key, out var oldValue);
            after.TryGetValue(key, out var newValue);

            if (expected.TryGetValue(key, out var predicate))
            {
                PredicateResult result;
                try
                {
                    result = predicate(oldValue, newValue);
                }
                catch
                {
                    result = PredicateResult.Fail("predicate threw");
                }
                if (!result.Ok)
                {
                    violations.Add(new StateDeltaViolation(
                        ViolationKind.PredicateFailed, key, oldValue, newValue,
                        NameOf(predicate)));
                }
            }
            else if (!DeepEqual.Equal(oldValue, newValue))
            {
                violations.Add(new StateDeltaViolation(
                    ViolationKind.UndeclaredChange, key, oldValue, newValue, null));
            }
        }

        if (violations.Count > 0)
        {
            throw new StateDeltaException(violations);
        }
    }
}
