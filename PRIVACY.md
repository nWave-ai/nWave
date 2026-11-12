# Privacy Policy

**Last updated**: 2026-11-01

nWave is an open-source AI workflow framework that runs inside coding hosts
such as [Claude Code](https://claude.com/product/claude-code), Codex,
OpenCode, OMP, Cursor, Copilot and Devin, and stores all data locally on your
machine. This privacy policy explains what data nWave handles and how.

## No User Data Collection

nWave collects no analytics, telemetry, tracking or usage reports. Workflow artifacts are stored locally. The one external service, described below, sends only the permitted request data and can be refused.

## Local-Only Storage

Workflow artifacts are stored on your machine:

| Data | Location | Purpose |
|------|----------|---------|
| Feature handoff, briefs and run records | `docs/feature/{id}/` in your repository | Per-feature delivery record (`handoff.json`, rendered briefs, role run records) |
| Audit logs (when enabled) | `<project>/.nwave/des/logs` by default (the directory name is historical) | TDD phase compliance records |
| Configuration | `~/.nwave/config.json` (global) and `.nwave/config.json` (per project) | Preferences and activation; older split files are migrated automatically |
| Legacy runtime files | `~/.nwave/runtime/` | Left only by a 3.x-era install; the v4 installer writes no runtime copy and removes this footprint on upgrade. Safe to delete at any time. |
| Skill loading log | 3.x-era path; not verified for the current release | Debug log in earlier releases |

nWave does not automatically upload these files. A Jev question can include a minimal permitted excerpt; authorization is not permission to upload a repository or log dump. You can delete local artifacts at any time.

## Outbound Network Calls

nWave can make an **optional update check** to notify you of available
releases:

- `https://pypi.org/pypi/nwave-ai/json` — checks latest PyPI version

**What is sent**: a standard HTTPS GET request with no user-identifiable information. This request is anonymous and unauthenticated. If it fails (network unavailable, rate limit), nWave silently continues without blocking your session.
**What is not sent**: no user data, no machine identifiers, no usage statistics.

Automatic release checking and installation are separate permissions, both
**off by default**; a check-only grant cannot install anything (see the
[installation guide](docs/guides/installation-guide/README.md) section
"Controlled startup and update permissions"). The older
`update_check` configuration key is retired and grants neither permission.

## No Third-Party Data Sharing

nWave operates no collection server. Your coding host handles its AI-provider communication. Jev's request is sent to TypeSafe as described below; this is external processing, not local-only computation.

## Jev External Processing

Jev is a remote service at `https://api.typesafe.ai/v1/systemone`. Jev is
external processing of the state that nWave sends it, not telemetry: nWave sends
no usage data. The local client sends the caller-supplied `state`, model and
typed questions over HTTPS, with the configured API credential in the
authorization header. Results and request records remain local.

These data classes are never sent: credentials and secrets, personal data,
private findings, source-blind material, secret-bearing logs, and confidential
account, host or resource identifiers. Send minimal permitted task summaries or
excerpts; authorization is not permission to transmit a repository or log dump.
Independent reviewers own their questions and must not inherit producer-owned
classifications. Source-blind EXAMINE retains its current isolated-access limit.
Service failures are explicit and local work can continue without invented
results. nWave makes no claim here about the remote provider's retention policy.

**Installing into a project and enabling it.** When you run `nwave-ai install` or
`nwave-ai project enable` on a terminal, nWave asks whether Jev may be used in that
project. The question states the machine-wide value in `~/.nwave/config.json` when one
is set; an empty answer keeps that value, and `y` allows Jev for this project even
then. Your answer is written as an explicit value in the project's `.nwave/config.json`.
Without a terminal (for example in CI, or with `--yes`), the same command writes the
declared default: `"jev": "authorized"` when the machine-wide file is silent or allows
Jev, and `"jev": "unauthorized"` when it refuses Jev, so a refusal you made
machine-wide is never loosened by an install or an enable. nWave wrote that value and
you did not choose it for this project, and the command says so. A machine-wide value
that is not a Jev choice fails closed to `"unauthorized"`, with the reason on stderr.
A machine-wide file that cannot be read stops `nwave-ai install` before anything is
written; `nwave-ai project enable` records `"unauthorized"` and prints the reason on
stderr. The declaration adds only the `jev` entry to the project file and keeps every
other byte. `nwave-ai project enable` first runs its own activation write, which sets
`enabled` and the schema version; the declaration then adds the `jev` entry to the file
that write produced. Either way, a project that already holds a `jev` value is never
asked about and that value is never replaced.

**Switching per project or per machine.** The switch is the `jev` key. In a
project, it lives in `.nwave/config.json`:

```json
{
  "jev": "authorized"
}
```

Set `"jev": "unauthorized"` in that file to stop Jev for this project, and
`"jev": "authorized"` to allow it again. The same key in `~/.nwave/config.json`
is the machine-wide switch, used by a project that declares no value of its own.
The project value wins over the machine-wide value, and the `--jev` flag wins
over both for one nwdes call. nwdes reads the key and never writes it.

With no `jev` key in any of these places, Jev is authorized. The
`TYPESAFE_API_KEY` environment variable is a technical prerequisite for the
service to accept requests; it is not the authorization, and without it nothing
is sent. When authorized and the service is available, supported semantic
questions use Jev under the shared skill. This does not disable the rest of nWave.


## Does nWave See My Code?

Yes — like any coding-host extension, nWave agents can read and analyze files in your project when you ask them to work on it. This happens entirely within your local host session. nWave does not automatically upload your code. Jev source excerpts stay within the permitted data scope. Your prompts and code are subject to your host provider's privacy policy (for example, [Anthropic's](https://www.anthropic.com/privacy) for Claude Code).

## Open Source

nWave is MIT licensed. The complete source code is available at [github.com/nWave-ai/nWave](https://github.com/nWave-ai/nWave) for audit and verification.

## Contact

Questions about this privacy policy: [hello@nwave.ai](mailto:hello@nwave.ai)
