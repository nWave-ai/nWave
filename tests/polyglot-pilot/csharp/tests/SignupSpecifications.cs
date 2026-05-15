// SignupSpecifications.cs — step-method partial class for the polyglot pilot.
//
// Generated from FeatureSpecifications.cs.template. Differs from the template
// in one respect: xUnit per-test class instantiation already handles per-test
// state reset (no beforeEach needed; fields reset because a new SignupTests
// instance is constructed per [Fact]).

#nullable enable

using System.Collections.Generic;
using System.Threading.Tasks;
using NWave.Polyglot.StateDelta;

using static NWave.Polyglot.StateDelta.StateDelta;

namespace NWave.Polyglot.SignupPilot.Tests;

public partial class SignupTests
{
    private ProductionApp _app;
    private Dictionary<string, object?> _stateBefore;

    private static readonly HashSet<string> SIGNUP_UNIVERSE = new()
    {
        "registry.users",
        "audit.events",
    };

    public SignupTests()
    {
        _app = new ProductionApp();
        _stateBefore = new Dictionary<string, object?>();
    }

    private async Task Given_AFreshSignupRegistry()
    {
        _app = new ProductionApp();
        _stateBefore = await _app.CaptureUniverseAsync(SIGNUP_UNIVERSE);
    }

    private async Task When_UserSignsUpWithEmail(string email)
    {
        await _app.SignupAsync(email);
    }

    private async Task Then_UserIsAddedToRegistryAndAuditedOnce(string email)
    {
        var normalized = email.Trim().ToLowerInvariant();
        var stateAfter = await _app.CaptureUniverseAsync(SIGNUP_UNIVERSE);

        var expectedUser = new Dictionary<string, object?> { ["Email"] = normalized };
        var expectedEvent = new Dictionary<string, object?>
        {
            ["Type"] = "UserSignedUp",
            ["Email"] = normalized,
        };

        Assert(
            _stateBefore,
            stateAfter,
            SIGNUP_UNIVERSE,
            new Dictionary<string, Predicate>
            {
                ["registry.users"] = ArrayAppended(expectedUser),
                ["audit.events"] = ArrayAppended(expectedEvent),
            });
    }

    private async Task When_UserAttemptsDuplicateSignup(string email)
    {
        _stateBefore = await _app.CaptureUniverseAsync(SIGNUP_UNIVERSE);
        try
        {
            await _app.SignupAsync(email);
        }
        catch (DuplicateSignupException)
        {
            // Expected — Then_ asserts zero observable delta.
        }
    }

    private async Task Then_SecondSignupIsRejectedAndStateIsUnchanged()
    {
        var stateAfter = await _app.CaptureUniverseAsync(SIGNUP_UNIVERSE);
        Assert(
            _stateBefore,
            stateAfter,
            SIGNUP_UNIVERSE,
            new Dictionary<string, Predicate>
            {
                ["registry.users"] = Unchanged(),
                ["audit.events"] = Unchanged(),
            });
    }
}
