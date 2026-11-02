---
name: nw-distill-prior-wave-reading
description: "Reads and reconciles durable product, architecture, and platform authorities before DISTILL compiles an executable oracle."
user-invocable: false
disable-model-invocation: true
---

# DISTILL Prior-Authority Reconciliation

Run before authoring or binding an acceptance oracle.

1. Read the value seed and only the durable product authorities it names:
   vision, job, journey and KPI identities.
2. Read the relevant architecture brief/ADRs, including reuse, route,
   prefactoring, paradigm, targets, ports/boundaries, cross-layer laws,
   residual stress decisions and test substrate.
   For a multi-value feature read the relevant common authority plus the local
   slice delta. If the public oracle needs a semantic decision neither states,
   ask its owner only for that decision; adequate existing authority needs no
   new ceremony, and you never write authority yourself.
3. Read platform/environment authorities only when the delivery has an
   operational obligation.
4. Reconcile contradictions by their durable owner. A contradiction blocks and is
   returned to the durable authority that owns the fact; do not write an
   upstream-issues file or copy the dispute into a second document.
5. Missing design required for an executable oracle blocks with WHAT/WHY/HOW.
   A genuinely unaffected optional lens is `NOT_APPLICABLE`, not a fabricated
   section.
6. Record semantic decisions only in their durable authority. No wave log,
   handover, delta or progress ledger.

The output is the minimum verified semantic input needed by `nw-distill`:
product intent, durable design decisions, oracle choice, boundaries,
obligations and applicability. Software derives execution details.
