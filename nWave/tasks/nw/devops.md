---
description: "Designs CI/CD pipelines, infrastructure, observability, and deployment strategy. Use when preparing platform readiness for a feature."
argument-hint: "[deployment-target] - Optional: --environment=[staging|production] --validation=[full|smoke]"
---

# NW-DEVOPS

**Delivery route**: `nwdes` design verbs; no separate operational constructor.

Use this optional step only when deployment, environment, observability or
recovery risk affects the Request. Do not impose DEVOPS on work with no platform
delta. Read current product and architecture authority; resolve a real
contradiction with its owner rather than creating a side ledger.

Invoke the installed `nw-platform-architect` role for operational facts,
including observable constraints, actual environment-native verification
commands, rollback and failure behavior. As the assigned design owner, the role
records these values through generated design `add`/`set` verbs (the first one
creates the draft) and `nwdes design close --outcome accepted --diagnostic TEXT`; use the
supplied generated verb-contract scope and arguments only (roots default to the
working directory). nwdes
constructs authority; the role does not edit an architecture document, KPI file,
handover or CI config merely to satisfy this step. Unresolved work closes with
`rejected` or `indeterminate`; revise with `open --from-current`, or correct the
retained draft after a refused close.

When invoked only as a platform consultation, pass its plain advice to the
coordinating solution architect through `nwdes prompt --root-context` instead
of opening a competing draft. That architect records the integrated operational
constraints through the same design verbs. The host runs declared environment-native
commands and retains actual results as evidence; there is no sidecar publication.

If an existing authority already answers the question, reuse it without a
role turn or duplicate document. No automatic SSOT bootstrap, KPI YAML
mutation, dashboard, status report or separate handoff is required.
