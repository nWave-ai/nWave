---
name: nw-update
description: "Queues a deferred self-update of nwave-ai. Writes a PendingUpdateFlag that the SessionStart hook replays on the next Claude Code launch, so the current session is not interrupted. Falls back to manual instructions when the package manager cannot be detected."
user-invocable: true
argument-hint: '[target-version] - Optional explicit version (e.g. 1.4.2). Defaults to the latest version discovered by the periodic update check.'
---

# NW-UPDATE: Queue Deferred nWave Self-Update

**Wave**: CROSS_WAVE | **Agent**: Main Instance (self) | **Command**: `/nw-update`

## Overview

`/nw-update` records a `PendingUpdateFlag` on disk. The actual upgrade is performed
by the SessionStart hook on the next Claude Code launch, so the user can keep
working in the current session and apply the new version whenever they restart.

You (the main Claude instance) run this command directly — no subagent delegation.
Do NOT attempt to upgrade nwave-ai in the current session.

## Behavior Flow

### Step 1: Resolve target version

1. If the user passed an argument (`$ARGUMENTS`), treat it as the target version
   after stripping a leading `v`.
2. Otherwise read `update_check.latest_available` from DESConfig
   (`.nwave/des-state.json`).
3. If no argument AND no discovered version: ask the user for the target version
   explicitly. Do not guess.

### Step 2: Detect the package manager and its binary

Invoke the detector and resolve the PM binary absolute path in a single Bash call:

```bash
python3 -c "
import sys, os
sys.path.insert(0, os.path.expanduser('~/.claude/lib/python'))
import shutil
from pathlib import Path
from des.adapters.driven.package_managers.package_manager_detector import detect_pm
pm = detect_pm(Path(sys.executable))
binary = shutil.which(pm) if pm in ('pipx', 'uv') else ''
print(f'{pm}|{binary or \"\"}')"
```

Parse the output as `pm|binary_abspath`.

### Step 3: Handle non-auto-updatable PM

If `pm == "unknown"` OR `pm == "pip"` OR `binary_abspath` is empty:

(`detect_pm` returns `pip` only when forced via `NWAVE_INSTALLER=pip`; pip
installs are not auto-updatable through the deferred-upgrade flow, so they take
the manual path alongside `unknown`.)

1. Do NOT call `PendingUpdateService.request_update`.
2. Print the manual fallback and stop:

```text
nwave-ai was not installed via an auto-updatable package manager.
Please upgrade manually:

  uv tool install nwave-ai@latest && nwave-ai install
    — or —
  pipx upgrade nwave-ai && nwave-ai install
    — or, if you installed with pip —
  pip install -U nwave-ai && nwave-ai install

Then restart Claude Code.
```

### Step 4: Queue the pending update

Call the driving port `PendingUpdateService.request_update`:

```bash
python3 -c "
import sys, os
sys.path.insert(0, os.path.expanduser('~/.claude/lib/python'))
from des.application.pending_update_service import PendingUpdateService
from des.adapters.driven.config.des_config import DESConfig
from des.adapters.driven.package_managers.package_manager_detector import detect_pm
from des.ports.driven_ports.package_manager_port import PackageManagerPort
from pathlib import Path
import shutil

pm = detect_pm(Path(sys.executable))
binary = shutil.which(pm)
target = '${TARGET_VERSION}'

config = DESConfig.load()
# PM adapter is only used by apply(), request_update() does not invoke it.
svc = PendingUpdateService(config=config, pm=None)  # type: ignore[arg-type]
svc.request_update(pm=pm, pm_binary_abspath=binary, target_version=target)
print(f'queued:{pm}:{target}')"
```

Substitute `${TARGET_VERSION}` with the value resolved in Step 1 (no leading `v`).

### Step 5: Confirm to the user

On success, print:

```
Update to vX.Y.Z queued. It will be applied the next time you restart Claude Code.
Package manager: <pipx|uv>  (<binary_abspath>)
```

## Error Handling

| Condition | Response |
|-----------|----------|
| No target version provided and none discovered | Ask the user for an explicit version |
| PM detection returns `unknown` | Print manual fallback (Step 3), do not write flag |
| `shutil.which(pm)` returns empty | Same as `unknown` — print fallback |
| `request_update` raises | Surface the exception, do not claim success |

## Progress Tracking

This command is synchronous and fast (< 1s). Do not create a task list; print
progress inline.

## Success Criteria

- [ ] Target version resolved (explicit arg, discovered, or asked)
- [ ] PM detected and PM binary absolute path obtained
- [ ] Either pending-update flag written OR manual fallback printed
- [ ] User sees confirmation of the queued version and PM used

## Examples

### Example 1: Discovered version, pipx install
```
/nw-update
```
Reads `update_check.latest_available = "1.4.2"`, detects `pipx` at
`/home/alex/.local/bin/pipx`, queues flag, prints:
`Update to v1.4.2 queued. It will be applied the next time you restart Claude Code.`

### Example 2: Explicit version, uv install
```
/nw-update 1.5.0
```
Detects `uv` at `/home/alex/.cargo/bin/uv`, queues flag for `1.5.0`.

### Example 3: Unknown PM
```
/nw-update 1.4.2
```
Detector returns `unknown` (e.g. pip venv install). Prints manual fallback
instructions and exits without writing the flag.
