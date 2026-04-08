# Privacy Policy

**Last updated**: 2026-02-28

nWave is an open-source AI workflow framework that runs inside [Claude Code](https://claude.com/product/claude-code) and stores all data locally on your machine. This privacy policy explains what data nWave handles and how.

## No User Data Collection

nWave does not collect, transmit, or store any user data. There is no analytics, telemetry, tracking, or usage reporting of any kind.

## Local-Only Storage

All data nWave creates stays on your machine:

| Data | Location | Purpose |
|------|----------|---------|
| DES audit logs | `~/.nwave/des/` | TDD phase compliance records |
| Execution logs | `docs/feature/{project}/execution-log.json` | Per-feature delivery tracking |
| Skill loading log | `~/.nwave/des/skill-loading.log` | Debug log for skill file loading |
| Configuration | `~/.nwave/des-config.json` | Rigor profile and settings |

None of these files are transmitted anywhere. You can delete them at any time.

## Outbound Network Calls

nWave makes **one optional network check** on session start to notify you of available updates:

- `https://pypi.org/pypi/nwave-ai/json` — checks latest PyPI version
- `https://api.github.com/repos/nWave-ai/nWave/releases/latest` — checks latest GitHub release

**What is sent**: a standard HTTPS GET request with no user-identifiable information. These requests are anonymous and unauthenticated. If they fail (network unavailable, rate limit), nWave silently continues without blocking your session.
**What is not sent**: no user data, no machine identifiers, no usage statistics.

You can disable this check entirely by setting `update_check.frequency` to `"never"` in `~/.nwave/des-config.json`:

```json
{
  "update_check": {
    "frequency": "never"
  }
}
```

## No Third-Party Data Sharing

nWave operates no servers and shares no data with third parties. All AI processing happens through your existing Claude Code session — nWave adds agents and commands but does not intercept, proxy, or modify your communication with Claude.

## Does nWave See My Code?

Yes — like any Claude Code extension, nWave agents can read and analyze files in your project when you ask them to work on it. This happens entirely within your local Claude Code session. nWave does not upload, copy, or transmit your code to any external server. Your prompts and code are subject to [Anthropic's privacy policy](https://www.anthropic.com/privacy).

## Open Source

nWave is MIT licensed. The complete source code is available at [github.com/nWave-ai/nWave](https://github.com/nWave-ai/nWave) for audit and verification.

## Contact

Questions about this privacy policy: [hello@nwave.ai](mailto:hello@nwave.ai)
