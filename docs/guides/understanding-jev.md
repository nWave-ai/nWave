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

Jev is authorized by default, and the refusal switch is yours:

- **Authorized by default.** When neither the call nor a configuration tier
  declares `jev`, the resolved authorization is `authorized`. Nothing
  refuses and no declaration is asked for.
- **Refusal wins at any time.** `--jev unauthorized` on a call, or
  `"jev": "unauthorized"` in the repository's `.nwave/config.json` or in
  `~/.nwave/config.json`, stops Jev use; the rest of nWave keeps working.
  The flag wins over the repository tier, and the repository tier over the
  global tier. Any other value is refused as malformed, and the feature and
  epic tiers cannot declare `jev`. nwdes never writes this key for you.
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
