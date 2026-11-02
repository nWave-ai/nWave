---
name: nw-product-value-slicing
description: Product-owner foundation for slicing value — elephant carpaccio thin vertical slices, one walking skeleton per feature (not per slice), feature identity from user/product authority, JTBD/domain language framing. Consult when decomposing a feature into independently observable increments.
user-invocable: false
disable-model-invocation: true
---

# Product Value Slicing — PO Foundation

**Kind**: KNOWLEDGE (reference). No forced sequence — consult while slicing a feature.
**Trigger**: decomposing a feature into delivery increments, or judging whether a proposed slice is real value.

## Elephant Carpaccio

Slice thin, vertically, not horizontally. Each slice is an independently observable increment of user/business value — it can be demoed and judged on its own, not "the database layer" or "the API contract" in isolation. Reject purely technical/horizontal work items as standalone value; fold necessary technical groundwork into the thinnest slice that also delivers observable value, or make it explicit non-value infrastructure the product owner accepts as a dependency, never as a slice.

Order slices by dependency, not by convenience: a slice may depend on an earlier slice's plumbing, but the plumbing itself is never the delivered value.

## One Walking Skeleton Per Feature

Exactly one initial end-to-end walking skeleton establishes the path for a FEATURE — proving the thinnest real path through the system once. Every subsequent slice EXTENDS that same skeleton with more value; it does not introduce a new skeleton. A walking skeleton per slice is the anti-pattern this rule exists to block.

Additional end-to-end scenarios beyond the skeleton are allowed when independently justified (a distinct integration boundary the skeleton cannot exercise) — never as a reflexive "one skeleton per slice" habit.

**Feature identity** comes from user/product authority — what a user or the business recognizes as one coherent capability — never from a delivery/ticket id. Do not equate "this delivery slice" with "this feature": several delivery slices extend one feature's single skeleton. Before starting a new skeleton, check whether the feature already has one; if it does, reuse and extend it.

## JTBD and Domain Language

Frame every slice in Jobs-to-be-Done / domain language: who is the user, what job are they hiring this for, what business outcome does the slice deliver. State explicit scope and dependencies. Provide at least one example and one counterexample distinguishing real slice value from a technical stand-in that looks like a slice.

## Collaboration and Authority

Collaborate with the human via `nw-human-collaboration`. Describe each independently observable increment, its dependencies, known work size and value, and applicable rework intent. Preserve dependency direction and the user's observable result. Slicing discipline applies wherever slicing decisions are made; this skill imposes no mandatory wave sequence.
