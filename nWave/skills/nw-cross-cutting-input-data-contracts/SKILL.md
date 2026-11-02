---
name: nw-cross-cutting-input-data-contracts
description: KNOWLEDGE — use when adding data, declaring inputs, or choosing a join key.
user-invocable: false
disable-model-invocation: true
---

# Input and Data Contracts

**Composition:** Load with `nw-cross-cutting-invariants`; no forced sequence; return to its routing table for other concerns.

## `data:consumer-known-before-produced` — a datum is produced because we already know who needs it (STANDING)

**A datum is justified only by a named consumer.** Before adding a field, an event, a config key,
an artifact section, or a telemetry record, name **who reads it** and **through which mechanism**.
No named reader → the datum is unjustified and must not be added. This is not bookkeeping
hygiene: unread data is what makes a system incoherent, because every future reader must decide
whether it means something and none can tell.

**Second half, and it is the one that gets forgotten: name the JOIN KEY.** Knowing who reads a
datum is not enough — it must be indexable against what the reader already holds. Two data both
faithfully consumed, indexed on keys that do not meet, cannot be related: the information exists
and is unusable. State the key the consumer will join on, at the moment you declare the field.

Measured instances of the failure, all in this repository:

| Datum | Declared | Consumed |
|---|---|---|
| `inline_in_feature_delta` | was 4 wave contracts + 1 schema | **0** reads — REMOVED 2026-07-28 once measured; kept here as the worked example |
| `adr-refs` (`RefList`) | its own definition | **0** dereferences |
| `skill_tracking` | full transcript-mining service exists | default **`"disabled"`** |
| Historical `RedObserved` / `SliceCommitVerified` | consumed by the retired slice-seal protocol | **no common key** — duration could not be computed from those ledgers |

The last example describes the retired protocol, not live producers or readers.
Its feature+slice+time and test-file-content-hash keys could not answer
"how long did this slice take to go green". A consumer was known; the join was not.
Current completion evidence comes from native verification/integration results
and independent review/EXAMINE records, not a `SliceCommitVerified` seal.
For new data, name the current reader and its actual join key.

**Corollary — instrumentation that must be switched on is not instrumentation.** A datum whose
producer defaults to off (see `skill_tracking`) is unjustified in the same way as one with no
reader: on the machine where it matters, nobody enabled it. Default it on, or do not claim the
measurement exists.

## `contract:declared-inputs-not-ambient-reads` — what does this READ that nobody passed it? (STANDING)

Paradigm-independent, and it applies to a component, a function and a test alike.

> **List everything the behaviour is gated on, then ask which of those it RECEIVES and which it
> goes and reads.** Answering "it works on my machine and in CI" is the wrong answer — that is
> two samples of one environment class, and the gate is invisible in both. **If any gate is read
> rather than received, lift it into the contract** — a parameter, an injected capability, an
> explicit override — and keep the ambient lookup as a default the caller may state, never as the
> only source.

The gates worth walking, as one list so it cannot drift between copies: **host or platform
presence · `$HOME` · a resolved config directory · cwd · `PATH` · environment variables · the
clock · locale · network reachability**.

Why it is not a style preference:

- A component whose result depends on state absent from its inputs takes a different branch in a
  different environment and reports honestly about a question nobody asked it.
- Its tests are the first casualty. They pass on the author's machine, on any machine that
  resembles it, **and because a sibling test created the state first** — which makes them
  order-dependent with nothing in the source saying so. A `tmp_path` fixture is not evidence:
  isolating the filesystem is not isolating the environment.
- A property test cannot reach the cases ambient state is silently fixing, so the generator looks
  thorough while the interesting partition is unreachable.

Empirical anchor, 2026-08-06: `NWaveInstaller.effective_target_platforms` resolves the target host
by ambient detection, lazily at first use. Three separate suites reached a no-host early return on
CI instead of the behaviour they asserted; each was repaired by declaring the platform, and each
took several refuted hypotheses to diagnose, because a component that reads ambient state gives no
signal about WHICH state it read.

Consumers: `nw-code-design-oo` and `nw-code-design-fp` (design-time, per paradigm) and the
Algebraic Analysis Before the Scenario mandate in `nw-test-design-mandates` (authoring-time).
They reference this clause; they do not restate the list.

## `join-key:shape-conformance-over-uniqueness` — a borrowed identifier is not a key until its shape is declared (STANDING)

A field supplied by an external producer — a platform, a harness, another team's payload — is
not a join key until EVERY value in the population conforms to a declared id shape. A single
non-conforming value disqualifies the field, however rare. The tempting weaker test is
"measure whether it is unique": that test passes on exactly the fields that hurt most, because
the usual defect is not a field that collides often but a field that is a well-formed
identifier almost everywhere and carries a hardcoded literal — a lifecycle-event name, a
placeholder, a fallback string — in a small minority of records. Rarity is not safety here; it
is the reason the field survived every informal check that came before. A join keyed on such a
field silently folds unrelated records together, and a reader that takes first-wins or MAX over
the group discards the rest without reporting anything.

Two properties make shape the right test rather than a proxy for uniqueness. It is
LOCALLY DECIDABLE: a checker holding one record can decide whether that record's value is
well-formed, whereas uniqueness is a property of a population the checker usually never sees —
a rule that cannot be executed at the point it is needed is not a control. And it is
DISCOVERABLE WITHOUT FOREKNOWLEDGE: conformance finds the offending values in one pass without
anyone knowing in advance which literal to look for, while a sampling check must draw the rare
value AND notice it collides.

**A key must be exercised at N≥2, and a one-occurrence suite cannot test one at all.** Ask what the
candidate is addressed BY: an EVENT key is unique per occurrence; a CONTENT key is unique per
payload, and the two are indistinguishable until two occurrences carry the same payload. Measured
instance: a hook's stdout digest was adopted as the parent↔child join, and the hook's stdout is a
module constant — two firings produced 2 parents and exactly **1** distinct digest, so every child
joined BOTH parents and the reader emitted a silent cross product. Every scenario that had validated
that key fired exactly ONCE, which is why the whole suite was green: a single-firing test makes the
defect structurally unreachable, so it was never a weak test but a test of the wrong thing. The
remedy is not more assertions, it is a second occurrence — and where a content key must be carried
anyway (it is often the only value both sides can compute), it carries a mandatory
`join_key_collision` third state, and the collision must be COUNTED and reported rather than
resolved by picking one of N.

The shape itself must be written down LITERALLY — the accepted pattern, and which
near-miss forms are excluded. "Conforms to an id shape" is not a specification: two honest
implementers will resolve an ambiguous form differently and reach opposite verdicts on the same
data, which reproduces the original silent-wrong one level up. Where a borrowed field must be
carried for a best-effort correlation it cannot guarantee, carry it as an ATTRIBUTE and mint
the structural key yourself: a key you generate is one whose uniqueness you own rather than
assume. When a value fails the shape check, the record degrades to the third state with a
reason naming the field — never to a silent drop, and never to a guess at which group it
belonged to.
