# Understanding Jev

**Jev** is the remote TypeSafe System One service nWave can consult for
bounded, typed semantic judgments while you work. This page explains what it
is, when it runs, and how to refuse it. The data-handling rules are in the
[Privacy Policy](../../PRIVACY.md).

## What it is and what it answers

Jev is reached over HTTPS at `https://api.typesafe.ai/v1/systemone`. A call
sends a compact **state** (a redacted description of the decision context)
and one or more typed questions, and gets back a structured judgment — for
example a **Choice** between named candidates with probabilities, a **Score**
against a rubric, or a **Noul** (a tested yes/no condition). It is a second
opinion on semantic questions, not a proof, not a gate, and not a runner: it
never writes code, executes commands, or decides a delivery.

Typical supported questions during a delivery: is this finding about the
same defect as that one, does this evidence item directly prove the stated
requirement, which candidate skill is relevant here. Mechanical work —
arithmetic, hashes, dates, parsing, schema checks, symbol resolution — always
stays local in deterministic tools.

## When it runs

- Questions are asked by the roles and the root assistant at existing
  decision points. No extra phase, hook or quota is introduced, and no
  delivery step blocks on the service.
- The client needs the `TYPESAFE_API_KEY` environment variable. Without a
  key, or when the network or service is unavailable, the caller records
  `typesafe: unavailable` and continues locally. Nothing retries blindly or
  invents a judgment.
- Source-blind EXAMINE does not use Jev: the examiner works only from its
  own observations in its public-only workspace.

## Authorization

Jev is authorized by default, and the switch is yours, per project:

- **Decided at install or enable.** On a terminal, `nwave-ai install` and `nwave-ai project enable` ask whether Jev may be used in the project and write the answer into the project's `.nwave/config.json` as `"jev": "authorized"` or `"jev": "unauthorized"`. The question names the machine-wide value when `~/.nwave/config.json` sets one, and an empty answer keeps it. Without a terminal (CI, or `--yes`) the same command writes the declared default and says so: nWave wrote it and you did not choose it. The default is `"jev": "unauthorized"` when your machine-wide file refuses Jev, so a machine-wide refusal is never loosened by an install or an enable. A machine-wide value that is not a Jev choice fails closed to `"unauthorized"`, with the reason on stderr. An unreadable machine-wide file stops `nwave-ai install` before anything is written, and `nwave-ai project enable` records `"unauthorized"` with the reason on stderr. The declaration itself adds only the `jev` entry and keeps every other byte. `nwave-ai project enable` first runs its own activation write, which sets `enabled` and the schema version, and the declaration then adds the `jev` entry to that result. A project that already holds a `jev` value is never asked about again, and that value is never replaced.
- **Two positions per project.** `"jev": "authorized"` allows Jev in that project, and `"jev": "unauthorized"` refuses it there. The same key in `~/.nwave/config.json` is the machine-wide value, used by a project that declares none. The flag `--jev unauthorized` refuses Jev for one call and wins over both files. The repository tier wins over the global tier. Any other value is refused as malformed, and the feature and epic tiers cannot declare `jev`. nwdes never writes this key.
- **The key is a technical prerequisite, not the authorization.** What
  authorizes Jev is the default policy above plus your refusal switch. The
  `TYPESAFE_API_KEY` environment variable only lets the service accept
  requests; without it nothing is sent and the caller records
  `typesafe: unavailable` — nwdes never reads the variable.

nWave's skill policy treats the default authorization as standing for
supported task-level questions.

## What is never sent

These data classes are never transmitted, regardless of authorization:
credentials and secrets, personal data, private findings, source-blind
material, secret-bearing logs, and confidential account, host or resource
identifiers. State is kept minimal — named, relevant fields, never a
repository dump. Reviewers and examiners form their own questions and never
inherit producer-owned judgments.

## Costs and records

Each call records its model, input/output tokens, duration and cost when the
service reports them; unknown cost is not reported as zero. Request records
stay local. If knowing what was asked matters to you, ask the root assistant
to show the local record.

## Where to read next

| Topic | Page |
|---|---|
| Data handling and privacy | [Privacy Policy](../../PRIVACY.md) |
| The `jev` configuration key | [nwdes reference — configuration](nwdes/reference/index.md#configuration) |
| The full policy text | [nw-typesafe-system-one skill](../reference/skills/nw-typesafe-system-one.md) |
| What changed in v4 | [What's new in v4](whats-new-v4/) |
