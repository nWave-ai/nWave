---
name: nw-devops
description: "Establishes durable deployment, environment, observability, recovery, and CI constraints when platform risk requires the DEVOPS lens."
user-invocable: true
argument-hint: '[platform risk or deployment target]'
---

# NW-DEVOPS

Read `~/.claude/skills/nw-human-collaboration/SKILL.md` to offer and conduct
interactive refinement with the human. Honor an already selected final-review
or full-delegation mode; the LLM manages the dialogue and progression.


The installed `nw-platform-architect` supplies semantic platform facts to the
solution architect. Keep operational advice in the coherent design authority,
not a separate constructor or sidecar.

When the platform role reads this skill, it applies only the semantic workflow
and returns its findings and human questions to its caller; it never invokes
itself or writes generated authority.

## Purpose

Apply the platform lens only when infrastructure, deployment, recovery,
observability or environment risk is material. Update existing durable platform
architecture, environment inventory and ADRs; do not create a per-delivery
narrative.

## Workflow

1. Read stable product KPI identities and durable architecture decisions.
2. Inventory actual environments, toolchains, trust boundaries and ownership.
3. Define deployment and rollback observations, health signals, SLOs and alert
   ownership.
4. Model infrastructure/recovery outcomes explicitly: timeout, unavailable,
   partial success, retryable, permanent refusal, replay and operator action.
   Ensure the application/port contract cannot silently ignore a required
   failure mode.
5. Define literal environment-native verification commands and dependency
   ownership. Never substitute an ambient `.venv` or assume a language.
6. Return platform constraints, decisions and evidence to the solution architect
   through `--root-context`. That owner incorporates relevant facts in the
   current design payload; do not create a parallel operational authority.
7. When independent operational review is selected, follow `nw-role-invocation`'s selected-review branch: the native caller invokes `nw-platform-architect-reviewer` on the current constructed authority, bound facts, scope and observations, then consumes its actual result. Keep review outside the closed constructor JSON. Required revisions return to the platform authority owner; construction alone is not completion of an enabled selected review. No unselected review turn or live rollout is implied.

DEVOPS does not author a handover, feature workspace, rollout ledger or CI
status copy. A downstream operational contradiction returns to the platform
authority; software re-derives any needed execution facts.

## Integration and lifecycle

Keep platform review replies verbatim. The host invokes models, runs native
checks and retains actual output. Declared operational facts and rendered
documents do not deploy or verify infrastructure.

Before creating or inheriting a lane, or finalizing/resuming cleanup, apply
the worktree lifecycle in `nw-throughput`. The feature's handoff and product
brief are its record; there is no separate evolution constructor.

## Human-readable authority

Use current full briefs and HTML with `nw-doc-as-artifact` for human review.
Rendering introduces no density preference or automatic expansion-offer mechanism.
