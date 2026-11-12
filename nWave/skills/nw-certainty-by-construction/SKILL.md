---
name: nw-certainty-by-construction
description: Load when a state must be unrepresentable, evidence must carry instead of a boolean, or a representation change must preserve meaning - redirect plus the byte-preservation and structural-owner rules.
---

# Certainty by construction

Construction rules (unrepresentable states, evidence instead of booleans, honest claim strength, witness granularity) live in `nw-type-level-design`. Representation-preservation arguments (isomorphism, homomorphism, rewrite and cache equivalence) live in `nw-algebraic-design-protocol`. The two rule families below are defined only here.

## Semantic comparison versus retained bytes

When a format admits LF and CRLF as the same layout but promises byte preservation, normalize the comparison view, not the retained source. Law: no semantic change returns the original bytes; a status-only update changes only its designated region, preserving all other bytes. Exercise both admitted line endings and byte-distinct surrounding text. A new export explicitly specified as canonical LF needs no original-byte buffer.

## One structural owner

When multiple boundary views express a declared closed structural contract, derive the needed schema, shape parser or field-aware traversal from one description rather than re-declaring alternatives in preflight. Check raw allowed keys before normalizing declared slots: an unknown key remains invalid even when its value is null or empty. Resolve a selector once and return its witness to the consumer. On the declared structural input domain, `schemaAccepts(x) iff shapeParse(x) succeeds`; reference existence and mutable policy remain separate semantic obligations.
