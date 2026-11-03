# How to Install nWave on an Air-Gapped Machine

## Who This Is For

This guide is for developers in government, military, or corporate-hardened environments where target machines have no access to PyPI or the internet. It assumes you know Python and have Claude Code installed or know how to install it via your organization's approved mechanism. **Host scope:** the bundle's install script deploys the Claude Code surface (`~/.claude/`); for other hosts, transfer the bundle and run `nwave-ai install --platform <host>` yourself — this guide does not walk through that per host.

## How It Works

You build a self-contained bundle on a connected machine, transfer it to the target, and run a single install script. The bundle includes the nWave CLI wheel, all Python dependencies, and the nWave framework assets. No network calls happen during install.

```
connected machine          transfer          air-gapped target
      |                      |                      |
build bundle  ------> scp / USB / etc. ------> unpack + run install-offline.sh
```

## Build the Bundle

**Prerequisites on the connected machine**: Python 3.11+, pip, and either `uv` or `pipx`.

From the root of the nWave repository, run:

```bash
python scripts/build_offline_bundle.py
```

Expected output:

```
[INFO] Bundle created: dist/releases/nwave-offline-bundle-{version}.tar.gz
[INFO] SHA256: a3f1c2d4e5...
[INFO] Companion: dist/releases/nwave-offline-bundle-{version}.tar.gz.sha256
```

The tarball is placed at `dist/releases/nwave-offline-bundle-{version}.tar.gz`. Bundle size varies with the dependency tree; expect under 100 MB for typical builds.

The build script also writes a companion checksum file at `dist/releases/nwave-offline-bundle-{version}.tar.gz.sha256`. Keep both files together during transfer.

**Platform note**: The optional `--python` flag selects which Python interpreter runs `pip download`. It does **not** change the target platform. Wheels fetched will always match the builder machine's OS and CPU architecture. To target a different platform, build on a machine whose OS, architecture, and Python minor version match the target.

## Transfer the Bundle

Use whatever transfer mechanism your organization approves: `scp`, USB drive, internal file server, or encrypted email attachment.

```bash
# Example: scp to target
scp dist/releases/nwave-offline-bundle-{version}.tar.gz \
    dist/releases/nwave-offline-bundle-{version}.tar.gz.sha256 \
    user@target-host:/tmp/
```

Verify the checksum on the target before proceeding:

```bash
sha256sum -c nwave-offline-bundle-{version}.tar.gz.sha256
# Expected: nwave-offline-bundle-{version}.tar.gz: OK
```

## Install on the Target Machine

Unpack the bundle into a dedicated directory:

```bash
mkdir nwave-bundle && tar -xzf nwave-offline-bundle-{version}.tar.gz -C nwave-bundle
cd nwave-bundle
```

The tarball extracts directly into the target directory (there is no wrapper subdirectory inside the archive).

Run the install script:

```bash
./install-offline.sh
```

The script installs the `nwave-ai` CLI from the bundled wheels using `pip install --no-index --find-links wheels/`, then calls `nwave-ai install` to deploy agents, commands and skills into `~/.claude/`.

Verify the installation:

```bash
nwave-ai doctor
```

The offline bundle changes nothing about who runs what: the `nwave-ai` CLI is
yours, the `nwdes` steps are your assistant's — see
[For your assistant](README.md#for-your-assistant).

## Verification

Read the actual doctor output for the installed bundle. Check the reported
paths and causes rather than relying on a fixed count or a sample from an
older release.

Key items to confirm:

- **CLI version**: matches the bundle version you built
- **Framework assets**: agents, commands, and skills are in `~/.claude/`
- **Claude Code**: the `claude` binary is on PATH; if not, Claude Code is not installed (see Limitations)

Restart Claude Code after a successful install. You should see `nWave ready` in your session context.

## Troubleshooting

### `pip install --no-index` fails

The wheels directory is missing a required wheel or contains wheels built for the wrong platform.

**Check**: Confirm all wheels are present for your Python version and platform.

```bash
ls wheels/
pip install --no-index --find-links wheels/ nwave-ai --dry-run
```

If wheels are missing, rebuild the bundle on a connected machine that matches the target's OS and Python version. See [Platform constraints](#python-version-or-platform-mismatch) below.

### `nwave-ai install` fails

Claude Code is not installed on the target machine. The bundle does not ship Claude Code; that is out of scope and must be installed via your organization's approved mechanism.

**Check**: Confirm `claude` is on PATH.

```bash
which claude
claude --version
```

If Claude Code is absent, install it first, then rerun `nwave-ai install`.

### `nwave-ai doctor` reports missing framework assets

Read the named path and remedy. Check that installation used the intended
environment and host configuration root.

**Fix**: Close Claude Code and rerun installation after correcting the cause:

```bash
nwave-ai install
```

Then reopen Claude Code and run `nwave-ai doctor` again.

### Bundle is too large

The bundle includes all transitive dependencies. There is currently no automated way to strip optional dependencies. This is a known limitation. If bundle size is a hard constraint, open an issue in the nWave repo to track a slimmed-bundle option.

### Python version or platform mismatch

Wheels are platform-specific. A bundle built on Linux x86_64 will not install on macOS ARM, and vice versa. Build the bundle on a machine whose OS, CPU architecture, and Python minor version match the target.

```
Connected machine    Target machine      Result
Linux x86_64 3.11    Linux x86_64 3.11   OK
Linux x86_64 3.11    Linux x86_64 3.12   Likely fails (ABI mismatch)
Linux x86_64 3.11    macOS ARM 3.11      Fails (platform mismatch)
```

Build one bundle per distinct target environment.

## Limitations

- **Claude Code is not included.** The bundle only covers nWave and its Python dependencies. Claude Code must be installed on the target via its own offline or enterprise mechanism before running `nwave-ai install`.
- **Platform-specific wheels.** Bundles are not cross-platform. Build a separate bundle for each OS and CPU architecture you need to support.
- **No automatic updates.** Air-gapped machines cannot receive update notifications. Distribute updated bundles manually when a new nWave version is released.
- **Corporate proxy or TLS interception.** Transfer may still be blocked by DLP or firewall rules. Use your organization's approved transfer channel.
## Security Considerations

- **Verify tarball integrity** using the `.sha256` companion file before unpacking on the target (see Transfer section above).
- **Audit wheels before install.** The `wheels/` directory contains all Python packages the installer will execute. You can inspect them with `pip show --files <package>` on a sandboxed machine before approving the bundle for distribution.
- **No network calls during install.** `install-offline.sh` uses `pip install --no-index` exclusively. No package index or CDN is contacted at any point during installation.
- **Run as the installing user.** Framework installation does not require a persistent system service.

## See Also

- [Troubleshooting Guide](troubleshooting-guide/) -- common issues and fixes across all install methods
- [Team Rollout Guide](team-rollout.md) -- onboarding multiple developers once nWave is installed
- [Agents and Commands Reference](../reference/index.md) -- full agent and command listing
