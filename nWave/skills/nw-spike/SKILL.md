---
name: nw-spike
description: A bounded probe of one product, visual-experience or technical uncertainty; returns evidence to its owner without starting a wave or promoting code automatically.
user-invocable: true
argument-hint: '[question or uncertain experience]'
---

# NW-SPIKE

The LLM selects a probe when an unanswered question changes a product or design
decision. This is a technique inside DISCUSS/DESIGN, not an extra mandatory wave.
Honor an existing delegation or stop boundary; do not repeat permission requests.

1. State one question, the evidence that would change the decision, and a bounded
   scope/time budget. Skip a probe that cannot inform a decision.
2. Reuse relevant artifacts. For visual uncertainty, the PO supplies actor,
   journey and feedback question; `nw-ux-designer` supplies UX/UI competence.
   Choose sketch, wireframe or navigable prototype according to uncertainty.
   For technical uncertainty, select the applicable technical specialist.
3. Keep artifacts and findings in the caller-owned persistent workspace, outside
   production paths; never rely on `/tmp` for valuable work. Use the project's
   native toolchain. Clearly label simulated data, mocked effects and absent
   integration. Prototype only enough behavior to answer the question.
4. Observe the result. For a visual prototype, show it to the human and retain
   actual feedback separately from model inference. Pending feedback stays open;
   an attractive page is not usability evidence. Do not force a binary verdict
   for a human preference or an unresolved question.
5. Return evidence, limitations and the decision still needed to the PO or
   architect, who owns any resulting authority revision.
   Do not write wave authority or handover documents yourself.

No automatic promotion, commit or cleanup. A separately selected implementation
may reuse prototype code after normal design, oracle and review work. A mocked
prototype is not the feature's walking skeleton. Preserve useful evidence before
any explicitly selected disposal; meaningful prototype changes require renewed
feedback, not reuse of an old approval.
