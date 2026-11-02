---
name: nw-spike-methodology
description: Guides a bounded, decision-relevant probe for a product, visual or technical uncertainty without creating wave authority
user-invocable: false
disable-model-invocation: true
---

# Spike Methodology

SPIKE is a technique inside DISCUSS or DESIGN, not a required wave. The
invoking PO or architect owns the question, evidence and decision. Use it only
when observation can change that decision; otherwise reuse existing evidence.

## Scope

1. State one uncertainty, what evidence could resolve it, and a bounded
   time or resource limit. A technical mechanism may need a small runnable
   experiment; a visual experience may need a prototype and human feedback.
2. Keep any useful code, measurements and findings in the caller-owned
   persistent workspace outside production paths. Use the project's native
   toolchain. Label mocks and untested integration accurately.
3. Observe the result and retain commands, inputs, outcomes and limitations.
   Missing human feedback remains unresolved, not a failed or passed verdict.
4. Return evidence and the remaining decision to the owner, who owns any
   resulting durable authority revision.
   No feature-local `findings.md` or other wave artifact is required.

Do not automatically delete the evidence, promote prototype code to production,
or reopen DISCUSS. If the answer changes scope or invalidates a design
assumption, name the conflict and let its owner decide where to correct it.
