---
name: nw-cross-cutting-context-residency
description: KNOWLEDGE — use when choosing resident, map-only, or on-demand context.
user-invocable: false
disable-model-invocation: true
---

# Context Residency

**Composition:** Load with `nw-cross-cutting-invariants`; no forced sequence; return to its routing table for other concerns.

## `context:pay-on-demand-not-every-session` — resident context is paid every session (STANDING)

**Whoever needs it loads it; whoever does not need it must not pay for it in every session.**
Context injected at session start is a per-session tax on every reader, including the readers who
will never touch that subject. Detail belongs where it is needed, at the moment it is needed — not
resident.

Three residency classes; classify before you inject anything:

- **MUST-BE-RESIDENT** — if it is absent from context, it does not happen. The load-bearing case is
  a **trigger**: an instruction to arm, to check, to refuse. Nobody goes looking for what they do not
  know exists, so a trigger cannot be made reachable-on-demand — its absence is silent. Same for a
  safety warning whose omission causes harm before anyone would think to consult it.
- **MAP-ONLY** — the reader must know THAT a thing exists and roughly WHEN to reach for it. Not how
  it works. A name plus a one-line "reach for this when…" is the whole resident cost.
- **REFERENCEABLE** — pure detail, needed only by whoever is doing that specific thing.

**Density is a second axis, independent of residency.** Normative content cannot be GENERATED from
code, but it can be COMPRESSED: doctrine is usually rules — subject · condition · action — written
as narrative. A table says the same thing in a fraction of the bytes and reads better. Do not confuse
"not derivable" with "not compressible"; measuring the first tells you nothing about the second.

**The failure this clause prevents**: a projection that ADDS instead of REPLACING. Retiring a
duplicate is a saving; generating a new view beside a surviving hand-written one is a new divergence
surface AND a bigger payload.

## `context:resident-doctrine-can-be-compensation-debt` — resident prose that patches bad guidance is debt (STANDING)

When a body of resident context exists to compensate for guidance that **fails to arrive at the point
of need**, that context is not doctrine — it is **debt**, and it is the SECOND cost of a defect whose
first cost is already being paid at the gate.

The chain: a gate refuses reactively instead of guiding at the authoring surface (the GDP-2 emission
corollary) → readers keep getting caught → someone compensates by injecting standing prose into
every session → now everyone pays, every session, for a message that should have arrived once, in
place, to the one person who needed it.

**So, before adding anything to a resident payload, ask: is the real gap a MESSAGE that fails to
guide?** If yes, fix the message; the resident need dissolves rather than being served. And the
converse is the practical lever: **as guidance moves to the point of need, resident doctrine can thin
without losing anything** — the two workstreams compose, and the thinning is only safe in that order.

**Do not thin first.** Removing resident prose while the corresponding guidance still arrives too
late removes the compensation and keeps the defect.
