// SignupScenarios.cs — domain-language scenarios (partial class).
//
// Generated from FeatureScenarios.cs.template for the polyglot pilot toy
// feature. Pillars 1+2 — composed from step methods in SignupSpecifications.cs.

#nullable enable

using System.Threading.Tasks;
using Xunit;

namespace NWave.Polyglot.SignupPilot.Tests;

public partial class SignupTests
{
    [Fact]
    public async Task UserSignsUpWithValidEmailAndIsAddedToRegistry()
    {
        await Given_AFreshSignupRegistry();
        await When_UserSignsUpWithEmail("alice@example.com");
        await Then_UserIsAddedToRegistryAndAuditedOnce("alice@example.com");
    }

    [Fact]
    public async Task DuplicateSignupIsRejectedAndLeavesRegistryAuditUnchanged()
    {
        await Given_AFreshSignupRegistry();
        await When_UserSignsUpWithEmail("alice@example.com");

        await When_UserAttemptsDuplicateSignup("alice@example.com");
        await Then_SecondSignupIsRejectedAndStateIsUnchanged();
    }
}
