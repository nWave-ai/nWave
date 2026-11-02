---
description: Compiles permanent architecture and value authority into an executable public oracle for automatic delivery.
argument-hint: '[requested outcome]'
---

# NW-DISTILL

## Overview

Load `~/.claude/skills/nw-distill/SKILL.md`; it is the sole methodology owner.
ADR-SSOT-002 owns delivery authority. Do not reproduce either authority in this
task.

## Invocation

Role: installed `nw-acceptance-designer`, invoked natively as
`nw-role-invocation` describes. nwdes constructs the supplied facts; it does not
invoke the role.

Resolve the durable value and architecture authority needed for the selected
outcome. Missing authority is `EVIDENCE_GAP`; do not reconstruct it from
workflow history or request an intermediate handoff.

Use nwdes as the delivery route: generate the acceptance designer's current
instructions and verb reference with `nwdes prompt`. The designer authors the
executable public oracle and records acceptance values through `nwdes acceptance
open`, `nwdes acceptance row add` and `nwdes acceptance close`, with the supplied
repository, project and feature arguments and required `--slice S` on every call.
nwdes constructs and writes the record; no model produces JSON or an envelope.
The host runs the declared verification commands against the original source
to observe RED and retains the actual results; closing acceptance does not
execute verification. No model returns a handover or a verification seal.

## Success Criteria

- one executable public oracle grounded in durable value and architecture
  authority;
- no inferred test substrate, workflow history, or manual continuation step.
