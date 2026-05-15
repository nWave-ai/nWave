// ProductionApp.cs — toy signup feature for the C# polyglot pilot.
//
// Minimal composition root: in-memory registry + audit log, exposes
// SignupAsync (driving operation) and CaptureUniverseAsync (state inspection
// at port-exposed slots).
//
// Universe slots exposed:
//   - "registry.users" : IReadOnlyList<UserRecord>
//   - "audit.events"   : IReadOnlyList<AuditEvent>
//
// Internal field names are NOT part of the universe — refactoring internals
// stays GREEN.

#nullable enable

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

namespace NWave.Polyglot.SignupPilot;

public sealed record UserRecord(string Email);

public sealed record AuditEvent(string Type, string Email);

public sealed class DuplicateSignupException : Exception
{
    public string Email { get; }

    public DuplicateSignupException(string email)
        : base($"Duplicate signup rejected: {email}")
    {
        Email = email;
    }
}

public sealed class ProductionApp
{
    // Driven-port state (in-memory).
    private readonly List<UserRecord> _users = new();
    private readonly List<AuditEvent> _events = new();

    /// <summary>
    /// Driving port — signup a user by email. Rejects duplicates by throwing
    /// DuplicateSignupException. On success: appends to registry AND appends
    /// a single UserSignedUp audit event.
    /// </summary>
    public Task<UserRecord> SignupAsync(string email)
    {
        var normalized = email.Trim().ToLowerInvariant();
        if (normalized.Length == 0)
        {
            throw new ArgumentException("signup: email must be non-empty", nameof(email));
        }
        if (_users.Any(u => u.Email == normalized))
        {
            throw new DuplicateSignupException(normalized);
        }
        var record = new UserRecord(normalized);
        _users.Add(record);
        _events.Add(new AuditEvent("UserSignedUp", normalized));
        return Task.FromResult(record);
    }

    /// <summary>
    /// State-inspection port — return a snapshot of the universe slots
    /// requested. Snapshot returns defensive copies so test assertions cannot
    /// mutate production state by accident. Anonymous-shaped dictionaries
    /// match the test's expected predicates (StateDelta uses reflection
    /// deep-equal on public properties).
    /// </summary>
    public Task<Dictionary<string, object?>> CaptureUniverseAsync(IEnumerable<string> keys)
    {
        var snapshot = new Dictionary<string, object?>();
        foreach (var key in keys)
        {
            switch (key)
            {
                case "registry.users":
                    snapshot[key] = _users
                        .Select(u => (object?)new Dictionary<string, object?> { ["Email"] = u.Email })
                        .ToList();
                    break;
                case "audit.events":
                    snapshot[key] = _events
                        .Select(e => (object?)new Dictionary<string, object?>
                        {
                            ["Type"] = e.Type,
                            ["Email"] = e.Email,
                        })
                        .ToList();
                    break;
                default:
                    // Unknown slot — record null so state-delta sees the absence
                    // explicitly rather than silently fabricating a value.
                    snapshot[key] = null;
                    break;
            }
        }
        return Task.FromResult(snapshot);
    }
}
