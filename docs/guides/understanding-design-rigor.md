# Understanding design rigor

nWave can apply two layers of rigor before code is written: an algebraic
design method with prefactoring, and formal checkers. Both belong to the
design phase of a delivery; both are grounded in how the roles actually
work, not in extra ceremony.

## Algebraic design, in short

The algebraic design method (the
[nw-algebraic-design-protocol](../reference/skills/nw-algebraic-design-protocol.md)
skill, with the structure catalogue in
[nw-fp-algebra-driven-design](../reference/skills/nw-fp-algebra-driven-design.md))
says: name what a user can **observe** first, define equality as agreement
under those observations, and only then choose constructors and
representations. When a stated law fails, follow the contradiction back to
the observation or type that causes it, instead of patching the symptom. It
runs whenever a design decision is contested, a law has exceptions, or a
representation change must preserve meaning — most visibly in features with
real invariants (parsers, state machines, money, ordering).

## Prefactoring

**Prefactoring** is a behavior-preserving production move that DESIGN declares
before new behavior is built — for example collapsing three copies of the
same guard into one owner so the next change lands in a single place. When
the architect declares it:

- it is recorded as part of the feature's design facts, with the verification
  command it must keep green ([design reference](nwdes/reference/design.md));
- the host runs that command before the move and again on the
  after-move-before-behavior state, keeping both observations;
- only then does the crafter implement the new behavior on the prepared
  ground.

It is deliberately minimal: reuse first, one preserving move at a time, and
an explicit note of what was looked at and *not* prefactored.

## Formal checkers, per role

| Role | Tool | When | Required? |
|---|---|---|---|
| Product owner | Quint | Exploring a product question with a bounded executable model | Required for Quint-relevant values: any sad path (refusal, conflict, race, stale input, missing operand) or unclear order/timing/state. Skipping is legitimate only for settled happy-path-only behavior, an unavailable tool, or a recorded human refusal |
| Solution architect | Quint, TLA+/TLC, Agda | Checking declared formal claims: Quint for bounded state machines, TLA+ when Quint is insufficient, Agda for proofs | The assessment runs in every design, and a selected checker must actually run. nWave ships none of them: a missing checker leaves the claim INDETERMINATE behind an installation offer or a recorded human waiver — never a silent skip |
| Reviewer | same tools, replay | Replaying the recorded checker run on the model it was recorded for | Follows the role it reviews |

Two honest limits. First, nWave does not install Agda, TLA+ or Quint; the
root assistant offers the installation once, and a proof is never invented.
A claim whose checker did not run stays INDETERMINATE — it is not silently
skipped, and a human can waive it explicitly on record. Second, when a
checker does run, its receipt is kept beside the model — checker and
version, the literal command, exit status, outputs and the model's checksum
— so the claim stays replayable.

Where this lands in a delivery: the architect's design facts carry the
paradigm, reuse and prefactoring declarations ([design
reference](nwdes/reference/design.md)), and the formal-verification
policy is part of the
[nw-solution-architect](../reference/agents/nw-solution-architect.md)
role. For product questions, the Quint route is described in
[nw-po-scenario-exploration](../reference/skills/nw-po-scenario-exploration.md).
