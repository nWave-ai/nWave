// StateDeltaTests.cs — xUnit + FsCheck contract tests for the C# port.
//
// Generated from StateDeltaTests.cs.template for the polyglot pilot.

#nullable enable

using System;
using System.Collections.Generic;
using FsCheck;
using FsCheck.Xunit;
using Xunit;

using static NWave.Polyglot.StateDelta.StateDelta;

namespace NWave.Polyglot.StateDelta.Tests;

public class StateDeltaContractTests
{
    [Fact]
    public void Assert_PassesOnCleanPrependTransition()
    {
        var before = new Dictionary<string, object?> { ["PATH"] = "/usr/bin" };
        var after = new Dictionary<string, object?> { ["PATH"] = "/des/bin:/usr/bin" };
        var universe = new HashSet<string> { "PATH" };
        var expected = new Dictionary<string, Predicate>
        {
            ["PATH"] = PrependedWith("/des/bin"),
        };

        Assert(before, after, universe, expected);
    }

    [Fact]
    public void Assert_ThrowsStateDeltaExceptionOnPredicateFailure()
    {
        var before = new Dictionary<string, object?> { ["PATH"] = "/usr/bin" };
        var after = new Dictionary<string, object?> { ["PATH"] = "/wrong" };
        var universe = new HashSet<string> { "PATH" };
        var expected = new Dictionary<string, Predicate>
        {
            ["PATH"] = PrependedWith("/des/bin"),
        };

        var ex = Xunit.Assert.Throws<StateDeltaException>(() =>
            Assert(before, after, universe, expected));

        Xunit.Assert.Single(ex.Violations);
        var v = ex.Violations[0];
        Xunit.Assert.Equal(ViolationKind.PredicateFailed, v.Kind);
        Xunit.Assert.Equal("PATH", v.Key);
        Xunit.Assert.Equal("/usr/bin", v.Old);
        Xunit.Assert.Equal("/wrong", v.New);
        Xunit.Assert.Equal("prepended_with(/des/bin)", v.PredicateName);
    }

    [Fact]
    public void Assert_ImplicitUnchangedCatchesUndeclaredChange()
    {
        var before = new Dictionary<string, object?>
        {
            ["PATH"] = "/u/bin",
            ["HOME"] = "/home/u",
        };
        var after = new Dictionary<string, object?>
        {
            ["PATH"] = "/des/bin:/u/bin",
            ["HOME"] = "/home/changed",
        };
        var universe = new HashSet<string> { "PATH", "HOME" };
        var expected = new Dictionary<string, Predicate>
        {
            ["PATH"] = PrependedWith("/des/bin"),
        };

        var ex = Xunit.Assert.Throws<StateDeltaException>(() =>
            Assert(before, after, universe, expected));

        Xunit.Assert.Single(ex.Violations);
        var v = ex.Violations[0];
        Xunit.Assert.Equal(ViolationKind.UndeclaredChange, v.Kind);
        Xunit.Assert.Equal("HOME", v.Key);
    }

    [Fact]
    public void Assert_CollectsMultipleViolationsIntoSingleException()
    {
        var before = new Dictionary<string, object?>
        {
            ["PATH"] = "/u",
            ["HOME"] = "/h",
            ["X"] = "1",
        };
        var after = new Dictionary<string, object?>
        {
            ["PATH"] = "/wrong",
            ["HOME"] = "/h2",
            ["X"] = "1",
        };
        var universe = new HashSet<string> { "PATH", "HOME", "X" };
        var expected = new Dictionary<string, Predicate>
        {
            ["PATH"] = PrependedWith("/des"),
            ["HOME"] = Unchanged(),
        };

        var ex = Xunit.Assert.Throws<StateDeltaException>(() =>
            Assert(before, after, universe, expected));

        Xunit.Assert.Equal(2, ex.Violations.Count);
    }

    [Fact]
    public void Assert_StrictModeFlagsExtraKeys()
    {
        var before = new Dictionary<string, object?>
        {
            ["PATH"] = "/u",
            ["EXTRA"] = "x",
        };
        var after = new Dictionary<string, object?>
        {
            ["PATH"] = "/des:/u",
            ["EXTRA"] = "x2",
        };
        var universe = new HashSet<string> { "PATH" };
        var expected = new Dictionary<string, Predicate>
        {
            ["PATH"] = PrependedWith("/des"),
        };

        var ex = Xunit.Assert.Throws<StateDeltaException>(() =>
            Assert(before, after, universe, expected, strict: true));

        bool found = false;
        foreach (var v in ex.Violations)
        {
            if (v.Kind == ViolationKind.StrictUniverseMismatch && v.Key == "EXTRA")
            {
                found = true;
                break;
            }
        }
        Xunit.Assert.True(found);
    }

    [Fact]
    public void Unchanged_PassesOnDeepEqual()
    {
        Xunit.Assert.True(Unchanged()(1, 1).Ok);
        Xunit.Assert.False(Unchanged()(1, 2).Ok);
    }

    [Property]
    public Property Unchanged_AlwaysPassesOnReferenceEqual(int v) =>
        Unchanged()(v, v).Ok.ToProperty();

    [Fact]
    public void PrependedWith_PassesOnPrefixComposition()
    {
        Xunit.Assert.True(PrependedWith("/des/bin")("/usr/bin", "/des/bin:/usr/bin").Ok);
        Xunit.Assert.False(PrependedWith("/des/bin")("/usr/bin", "/wrong").Ok);
    }

    [Property]
    public Property PrependedWith_HoldsForAnyTail(NonEmptyString tail)
    {
        var composed = $"PRE:{tail.Get}";
        return PrependedWith("PRE")(tail.Get, composed).Ok.ToProperty();
    }

    [Fact]
    public void AppendedWith_PassesOnSuffixComposition()
    {
        Xunit.Assert.True(AppendedWith(".bak")("/etc/hosts", "/etc/hosts:.bak").Ok);
        Xunit.Assert.False(AppendedWith(".bak")("/etc/hosts", "/etc/hosts").Ok);
    }

    [Fact]
    public void SetTo_IgnoresOldAndMatchesNew()
    {
        Xunit.Assert.True(SetTo("active")("inactive", "active").Ok);
        Xunit.Assert.False(SetTo("active")("inactive", "pending").Ok);
    }

    [Fact]
    public void Containing_ChecksSubstringOrArrayElement()
    {
        Xunit.Assert.True(Containing("/usr/bin")("", "/des/bin:/usr/bin").Ok);
        Xunit.Assert.False(Containing("/usr/bin")("", "/des/bin:/opt/bin").Ok);
    }

    [Fact]
    public void NormalizedTo_ComparesUnderNormaliser()
    {
        object? ExpandHome(object? v) =>
            v is string s ? s.Replace("$HOME", "/home/u") : v;
        Xunit.Assert.True(NormalizedTo(ExpandHome)("/home/u/.local/bin", "$HOME/.local/bin").Ok);
        Xunit.Assert.False(NormalizedTo(ExpandHome)("/home/u/.local/bin", "$HOME/.other/bin").Ok);
    }

    [Fact]
    public void IdempotentAfter_ChecksFirstSegment()
    {
        Xunit.Assert.True(IdempotentAfter("DES_BIN")("anything", "DES_BIN:/usr/bin").Ok);
        Xunit.Assert.False(IdempotentAfter("DES_BIN")("anything", "/usr/bin:/opt/bin").Ok);
    }

    [Fact]
    public void LegacyHealed_ImplementsPaperTrace()
    {
        const string LEGACY = "DES_BIN:SYSTEM_PATH_FALLBACK";
        var pred = LegacyHealed(
            old => old is string s && s == LEGACY,
            next => next is string s && s != LEGACY && s.StartsWith("DES_BIN:"));
        Xunit.Assert.True(pred(LEGACY, "DES_BIN:/usr/bin").Ok);
        Xunit.Assert.False(pred(LEGACY, LEGACY).Ok);
        Xunit.Assert.False(pred("/usr/bin", "DES_BIN:/usr/bin").Ok);
    }

    [Fact]
    public void ArrayPrepended_MatchesItemPlusOld()
    {
        Xunit.Assert.True(ArrayPrepended("a")(new List<object?>(), new List<object?> { "a" }).Ok);
        Xunit.Assert.True(ArrayPrepended("a")(new List<object?> { "x" }, new List<object?> { "a", "x" }).Ok);
        Xunit.Assert.False(ArrayPrepended("a")(new List<object?> { "x" }, new List<object?> { "x", "a" }).Ok);
    }

    [Fact]
    public void ArrayAppended_MatchesOldPlusItem()
    {
        Xunit.Assert.True(ArrayAppended("z")(new List<object?>(), new List<object?> { "z" }).Ok);
        Xunit.Assert.True(ArrayAppended("z")(new List<object?> { "x" }, new List<object?> { "x", "z" }).Ok);
        Xunit.Assert.False(ArrayAppended("z")(new List<object?> { "x" }, new List<object?> { "z", "x" }).Ok);
    }
}
