# Configure Jev

This guide shows how to turn Jev on or off for a project, and how to set the
key that Jev needs. Read [Understanding Jev](./understanding-jev.md) first if
you want the full picture. The data rules are in the
[Privacy Policy](../../PRIVACY.md).

## What Jev is and what it sends

Jev is a remote service. It answers bounded questions about a decision. For
example, it can choose the candidate that fits a stated need, or score an
artifact against a rubric.

A Jev call sends:

- a short **state**, which is a redacted description of the decision;
- one or more typed questions.

Jev returns a structured answer. It does not write code, run commands, or
decide a delivery.

Jev never receives:

- credentials or secrets;
- personal data;
- private findings;
- logs that contain secrets;
- whole repositories.

Jev is external processing, not telemetry. nWave sends no usage data.

## Jev is on by default

When a project has no `jev` setting, Jev is on. Each project can change this
with the `jev` key in its own `.nwave/config.json`:

```json
{
  "jev": "authorized"
}
```

Use `"jev": "unauthorized"` to turn Jev off for that project. Use
`"jev": "authorized"` to turn it on again.

Two other places can set `jev`. The order is:

| Order | Where | Effect |
|---|---|---|
| 1, highest | `--jev` flag on one call | Refuses Jev for that call when set to `unauthorized` |
| 2 | `.nwave/config.json` in the project | The project value |
| 3 | `~/.nwave/config.json` on your machine | The value for projects that declare none |
| 4, default | none set | Jev is on |

On a terminal, `nwave-ai install` and `nwave-ai project enable` ask whether
Jev may be used in the project. An empty answer keeps the machine-wide value.
Without a terminal, the command writes the default and says so.

## Set the key

Jev also needs the `TYPESAFE_API_KEY` environment variable. The variable holds
your key. Without the key, Jev cannot answer, and nothing is sent.

The key comes from your Jev provider. nWave does not issue, store or log keys.

nWave only checks that the variable is set. The key value is sent only in the
request header to Jev.

The default endpoint is `https://api.typesafe.ai/v1/systemone`. You can change
the endpoint with `TYPESAFE_BASE_URL`. That variable changes the endpoint
only. It does not set the key.

Replace `<your key>` with your own key in each command below. Never paste a
real key into a file that you share.

### bash or zsh

For this terminal session:

```bash
export TYPESAFE_API_KEY='<your key>'
```

To keep the key, add that line to ~/.bashrc or ~/.zshrc. Then open a new
terminal.

### fish

For this terminal session:

```fish
set -x TYPESAFE_API_KEY '<your key>'
```

To keep the key:

```fish
set -Ux TYPESAFE_API_KEY '<your key>'
```

### PowerShell

For this terminal session:

```powershell
$env:TYPESAFE_API_KEY = '<your key>'
```

To keep the key:

```powershell
[Environment]::SetEnvironmentVariable('TYPESAFE_API_KEY','<your key>','User')
```

The persistent command applies to new terminal windows only. Open a new
window after you run it.

### Windows cmd

For this terminal session:

```bat
set "TYPESAFE_API_KEY=<your key>"
```

To keep the key:

```bat
setx TYPESAFE_API_KEY "<your key>"
```

`setx` applies to new terminal windows only. It does not change the window
where you ran it. Open a new window after you run it.

### Start your coding host from that shell

A coding host reads the variable when it starts. Start the host from the same
shell where you set the key. A host that was already running does not see a
new value. Start it again.

A tool kernel, such as a Python eval kernel, may not inherit the session
environment. Run the Jev client from a shell command instead.

## Check the setup

Run:

```bash
nwave-ai status
```

Look at the Jev line:

- `Jev: authorized (project .nwave/config.json) | key: set` means Jev is on
  for the project and the variable is visible. This is the working state.
- `key: MISSING` means the variable is not visible in this shell. Set it
  again, then start your host from that shell.
- `Jev: unauthorized` means Jev is turned off for the project. No key is needed.

`nwave-ai status` never prints the key value.

## What the warning means

When Jev is on but the key is missing, nWave prints this warning during
`nwave-ai install`, `nwave-ai project enable` and `nwave-ai status`:

```text
WHAT: Jev is on for this project but TYPESAFE_API_KEY is not set in this process; Jev questions are skipped and nWave continues without Jev.
```

The warning does not stop the command. It does not change the exit code.
Nothing is sent to Jev while the key is missing.

When you build a role bundle with `nwdes prompt`, nWave adds one short line,
`jev_access:`, that names the missing key. That line appears only when Jev is on
and the key is missing.

If you do not want Jev, turn it off for the project. You do not need to set
a key.

## Turn Jev off for one project

Set the project value in `.nwave/config.json`:

```json
{
  "jev": "unauthorized"
}
```

Nothing is sent to Jev in that project. Other projects keep their own setting.

To refuse Jev for one call only, pass `--jev unauthorized` on that call.

## Without the key

When the key is not set, nothing is sent. Each role records
`typesafe: unavailable` and continues its work locally. No judgment is
invented, and no step waits for Jev.

## Related pages

| Topic | Page |
|---|---|
| What Jev answers and why | [Understanding Jev](./understanding-jev.md) |
| Data handling and privacy | [Privacy Policy](../../PRIVACY.md) |
| The `jev` configuration key | [nwdes reference: configuration](./nwdes/reference/index.md#configuration) |
| Turn nWave on or off per project | [Activate nWave in a project](./activating-nwave-per-project.md) |
