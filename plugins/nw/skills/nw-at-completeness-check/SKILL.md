---
name: nw-at-completeness-check
description: Canonical AT completeness gate — research-anchored 7-category taxonomy (C1-C7) + 15-item mechanical checklist. Paradigm-neutral. Drives acceptance-designer reviewer verdict deterministically.
user-invocable: false
disable-model-invocation: true
---

# AT Completeness Check — Canonical Taxonomy

Mechanical gate for acceptance-test completeness. Runs against any candidate AT set. Each unchecked item = potential gap. Verdict deterministic by count, not judgment.

**Provenance**: research-anchored 7-category taxonomy, paradigm-neutral. See `docs/research/at-edge-case-taxonomy-2026-05-19.md` for full literature review.

**Anchors** [1]-[14] reference research doc bibliography.

## Domain extensions

Project-specific AT-class specializations live as YAML overlays in `domain-extensions/` (sibling dir to this SKILL.md). The canonical 7-category taxonomy stays paradigm-neutral; domain overlays add `extra_checks` that the reviewer appends to the 15-item checklist for features opting in.

**When to add an extension**: project surfaces an AT-class that is a specialization of one or more canonical categories (typically C5 + C6) but not a new general category. Example: nWave IP/Privacy boundary = `public:false` mode flag (C5) + leak-in-output failure-contract (C6) — lives in `domain-extensions/nwave-installer.yaml`, NOT in canonical taxonomy.

**Overlay schema** (`domain-extensions/<kebab-case-domain-id>.yaml`):

```yaml
name: <kebab-case-domain-id>
version: <semver>
applies_to: <project / package / feature-pattern>
extends_canonical: [C5, C6]      # which canonical categories this specializes
extra_checks:
  - id: <DomainID>a
    description: <what to verify>
    maps_to_canonical: C6
    mandatory: <bool>
```

**Opt-in per feature** — in `docs/feature/{id}/distill/at-completeness-extensions.yaml`:

```yaml
extensions: [nwave-installer]
```

Reviewer adds overlay's `extra_checks` to the canonical 15-item checklist for that feature only. Verdict thresholds scale with total item count.

## 1. Canonical 7-category taxonomy (paradigm-neutral)

| ID | Category | Anchor | One-line definition |
|----|----------|--------|---------------------|
| **C1** | Equivalence & Boundary | ISTQB §4.2 [1] / Beizer ch.5 [2] | Partition input domain + test at/adjacent to each boundary |
| **C2** | State & Transition | ISTQB §4.2.4 [1] / Hendrickson [3] / Hypothesis stateful [4] | Every legal transition + illegal-event-from-each-state + self-loops/terminal exits |
| **C3** | Count Cardinality (0/1/N) | Hendrickson "Count" [3] / Adzic key examples [5] | Empty / singleton / many for every collection input or output |
| **C4** | CRUD-Lifecycle & Idempotency | Hendrickson "CRUD" [3] / Hillel Wayne PBT+Contracts [6] | Repeat / replay / out-of-order ops preserve invariants; `f(f(x)) == f(x)` for idempotent ops |
| **C5** | Mode-Flag / Decision-Table | ISTQB §4.2.3 [1] / Adzic "key examples" [7] | Every materially-distinct Cartesian combination of mode flags exercised |
| **C6** | Negative & Robustness (Postel) | RFC 760 §1.2.10 [8] / FEW HICCUPPS [9] / Kaner LLST [10] / RIMGEA [11] | Hostile/degenerate input → explicit typed-error contract, never silent coercion |
| **C7** | Configuration / Environment / Interruption | Bach HTSM SFDIPOT [12] / Hendrickson "Configurations+Interruptions+Starvation" [3] / Marick Q4 [13] | Resource starvation + interruption mid-flow + concurrent actors |

### C1. Equivalence & Boundary
Partition the input domain into equivalence classes; test at least one representative per class plus values immediately on/adjacent to each partition boundary. Failures cluster at edges, not interiors. **Citation**: ISTQB Foundation v4.0 §4.2 [1]; Beizer 1990 ch.5 "Domain Testing" [2].

### C2. State & Transition
Model the SUT as states + events + guards + transitions. Cover (a) every legal transition, (b) ≥1 illegal-event-from-each-state (rejected gracefully), (c) self-loops and terminal-state exits. **Citation**: ISTQB §4.2.4 [1]; Hendrickson "State Analysis" [3]; Hypothesis `RuleBasedStateMachine` [4].

### C3. Count Cardinality (0/1/N)
For every collection-shaped input or output, exercise zero, one, and many. Zero is the canonical bug magnet (null-deref, divide-by-zero, "no items" UI). **Citation**: Hendrickson/Lyndsay/Emery cheat sheet — "Count: Zero, One, Many" [3]; Adzic [5].

### C4. CRUD-Lifecycle & Idempotency
Full Create/Read/Update/Delete lifecycle + verify repeat/replay/out-of-order operations preserve invariants. Idempotency = `f(f(x)) == f(x)`. **Citation**: Hendrickson "CRUD" [3]; Hillel Wayne PBT+Contracts [6]; ISTQB decision-table [1].

### C5. Mode-Flag / Decision-Table Coverage
When SUT exposes mode flags (`dry_run`, `force`, `verbose`, `public`), every Cartesian combination materially-different in behavior is a distinct AT. **Citation**: ISTQB §4.2.3 decision-table [1]; Adzic "Focus on key examples" [7]; Adzic SbE [5].

### C6. Negative & Robustness (Postel)
Every input channel accepts hostile/degenerate input; SUT must respond with explicit, asserted failure contract (typed error, exit code, empty-valid output) — never crash, never silently accept. **Citation**: RFC 760 §1.2.10 [8]; FEW HICCUPPS "Standards"+"Claims" [9]; Kaner/Bach/Pettichord LLST [10]; RIMGEA [11].

### C7. Configuration / Environment / Interruption
SUT runs under varying resource availability and may be interrupted mid-flow. Cover (a) resource starvation, (b) interruption mid-transaction, (c) concurrent actors. **Citation**: Bach HTSM SFDIPOT [12]; Hendrickson "Configurations"/"Interruptions"/"Starvation"/"Multi-user"/"Flood" [3]; Marick Q4 [13].

---

## 2. Mechanical 15-item application checklist

Run against any candidate AT set. Unchecked = potential completeness gap.

```
C1a — ≥1 AT exercises empty/zero/minimum-size input
C1b — ≥1 AT on each partition boundary (max-1, max, max+1)
C2a — SUT state machine documented in AT module docstring
C2b — For each state, ≥1 AT for illegal-event-from-that-state
C3  — parametrize/PBT covering n ∈ {0, 1, many} for each collection input
C4a — Each mutating op has "apply twice" AT (idempotency or correct non-idempotency)
C4b — ≥1 AT for inverse op without prerequisite (uninstall-without-install)
C5a — Each mode flag: every materially-distinct combination exercised
C5b — ≥1 AT asserting flag orthogonality (verbose toggles output only)
C6a — Each input param: ≥1 AT with malformed value (wrong type, malformed encoding)
C6b — Each declared error in contract: ≥1 AT triggers exactly that error
C6c — ≥1 AT asserts closed error set (no other error escapes)
C7a — ≥1 AT under degraded-resource condition (read-only FS / no network / low disk)
C7b — ≥1 AT for interruption mid-operation (SIGINT / timeout / partial commit)
C7c — If concurrent-safe by claim: ≥1 multi-actor AT (two parallel invocations)
```

Machine-readable form: `checklist-15-item.yaml` (alongside this file).

### Verdict thresholds (deterministic)

| Count passing | Verdict |
|---------------|---------|
| < 10 / 15 | **INCOMPLETE** — reject; route per §4 |
| 10–12 / 15 | **ACCEPTABLE_WITH_DOCUMENTED_GAPS** — pass with explicit listed gaps |
| ≥ 13 / 15 | **COMPLETE** — pass |

The reviewer agent **computes the count mechanically**, not subjectively. Items not applicable (e.g. C7c for non-concurrent SUTs) count as passing — document the rationale in verdict output.

---

## 3. PBT / parametrize signatures per category

One-line code template per category. Crafter/acceptance-designer copy-adapt.

```python
# C1 — Equivalence & Boundary
@given(st.lists(elt, min_size=0, max_size=N+1))
@example([]) @example([single])

# C2 — State & Transition
class M(RuleBasedStateMachine):
    @rule(...)
    @invariant()
    @precondition(...)

# C3 — Count Cardinality
@pytest.mark.parametrize("n", [0, 1, 2, 100])
# or st.integers(min_value=0, max_value=...)

# C4 — CRUD-Lifecycle & Idempotency
# Property: f(f(x)) == f(x)
# Or: RuleBasedStateMachine with @rule chains over CRUD sequence

# C5 — Mode-Flag / Decision-Table
from itertools import product
@pytest.mark.parametrize("flags", list(product([True, False], repeat=k)))
# filter degenerate combinations

# C6 — Negative & Robustness
@given(st.one_of(st.text(), st.integers(), st.binary()))
# assert raises typed error from closed set:
# with pytest.raises(DeclaredError): ...

# C7 — Configuration / Environment / Interruption
class M(RuleBasedStateMachine):
    @rule(...)  # includes interruption events
# + parametrize over resource-degradation fixtures
```

Language-equivalent frameworks: Hypothesis (Python), fast-check (TS/JS), QuickCheck (Haskell), quickcheck (Rust), jqwik (Java), FsCheck (C#).

---

## 4. Reviewer output schema

Reviewer emits a typed verdict. Two kinds of finding only.

```python
@dataclass(frozen=True)
class ATGap:
    scenario_class: str            # e.g. "C5a:dry_run-and-force-combo"
    current_at_count: int          # 0 if missing entirely
    reason: str
    kind: ATGapKind
    severity: Severity             # BLOCKER | HIGH | MEDIUM | LOW

class ATGapKind(str, Enum):
    AT_GAP_IN_DELIVERY_SCOPE = "at_gap_in_delivery_scope"
    SPECIFICATION_AMBIGUITY  = "specification_ambiguity"
```

`ARCHITECTURE_SCOPE_MISS` is NOT a reviewer-authored kind. Phase D router derives it via second-order rule (≥2 gaps sharing a scenario_class mapping to component absent from DESIGN output).

---

## 5. Upstream-wave routing rule

Categories C2, C5, C6, C7 require upstream-wave specification. If absent → `SPECIFICATION_AMBIGUITY`, NOT `AT_GAP_IN_DELIVERY_SCOPE`. Phase D routes back to upstream wave, not back to DISTILL.

| Category | Upstream owner | Required artifact |
|----------|----------------|-------------------|
| C2 (state machine) | **DISCUSS** | State diagram in user-stories Elevator Pitch + DoD |
| C5 (mode-flag inventory) | **DESIGN** | Flag enumeration in component manifest |
| C6 (error contract) | **DESIGN** + **DISCUSS** | Typed error set + invariants per port |
| C7 (env / interruption matrix) | **DEVOPS** | Env matrix + concurrency/interruption contract |

Routing decision (mechanical):

```
if upstream artifact for category X missing
    → ATGap.kind = SPECIFICATION_AMBIGUITY → re-enter the upstream wave
else
    → ATGap.kind = AT_GAP_IN_DELIVERY_SCOPE → address within the delivery cycle
```

This closes the Mandate-12 SSOT loop: domain types in DISCUSS/DESIGN/DEVOPS drive taxonomy population.

---

## 6. Domain extensions

Canonical taxonomy is paradigm-neutral. Project-specific instantiations live in `domain-extensions/*.yaml`.

```
nWave/skills/nw-at-completeness-check/
├── SKILL.md                          # this file — canonical 7-category (GENERIC)
├── checklist-15-item.yaml            # machine-readable mechanical gate
└── domain-extensions/                # per-project overlays (kebab-case)
    ├── README.md                     # how to add a domain extension
    ├── nwave-installer.yaml          # IP/Privacy + filesystem-shape (nWave-specific) [SLOT]
    └── nwave-des.yaml                # DES marker-specific extensions [SLOT]
```

Per-feature opt-in: `docs/feature/{id}/distill/at-completeness-extensions.yaml` lists which overlays apply (e.g. `extensions: [nwave-installer]`).

**Example mapping**: IP/Privacy boundary (nWave domain) → instance of C5 (`public:false` mode flag) + C6 (leak-in-output as failure-contract assertion). Lives in `domain-extensions/nwave-installer.yaml`, NOT in canonical taxonomy.

---

## 7. Falsifier-gate (taxonomy self-pruning)

Telemetry per gate run: `(feature_id, category_id, finding_count, severity_max)` → 3-month rolling window.

| Signal | Decision |
|--------|----------|
| 3 consecutive zero-findings on category X across pilot features | **PRUNE** X from default checklist (cost ≤ benefit) |
| 1 BLOCKER found via category X | **ESCALATE** X to MANDATORY (cannot be skipped) |

This makes the taxonomy itself empirically-falsifiable. Default state: all 7 categories active.

---

## 8. Empirical class → research category mapping (proves generality)

| Empirical class (spike-3 2026-05-19) | Research category | Notes |
|--------------------------------------|-------------------|-------|
| IP/Privacy boundary | C5 + C6 (instantiation) | Domain-specific overlay, NOT general |
| Negative paths (missing file, malformed JSON) | C6 direct | Canonical robustness/Postel |
| Idempotency (uninstall w/o install) | C4 direct | CRUD lifecycle + idempotency property |
| Mode flags (dry_run / force / verbose) | C5 direct | Decision-table coverage |
| Failure contract on degenerate state | C6 direct | FEW HICCUPPS "Claims" consistency |
| Type-domain (bool/int where str expected) | C6 direct | Type-level robustness; PBT `st.one_of` natural fit |

Empirical classes 2–6 generalize via C4+C5+C6. Class 1 (IP/Privacy) → domain extension. C1, C2, C3, C7 = categories spikes did NOT surface — predictable next adversarial-reviewer hits.

---

## References (research doc bibliography)

[1] ISTQB Foundation v4.0 §4.2 Black-Box Test Techniques (2023).
[2] Beizer, *Software Testing Techniques* 2nd ed., 1990, ch.5 Domain Testing.
[3] Hendrickson/Lyndsay/Emery, Test Heuristics Cheat Sheet, testobsessed.com / Ministry of Testing.
[4] Hypothesis stateful tests docs.
[5] Adzic, *Specification by Example*, Manning 2011.
[6] Wayne, "Property Tests + Contracts = Integration Tests", hillelwayne.com 2019.
[7] Adzic, "Focus on key examples", 2014.
[8] RFC 760 §1.2.10 Robustness Principle (Postel, IETF 1980).
[9] Bolton/Bach, "FEW HICCUPPS", DevelopSense.
[10] Kaner/Bach/Pettichord, *Lessons Learned in Software Testing*, Wiley 2001.
[11] Kaner, RIMGEA/RIMGEN bug-reporting mnemonic.
[12] Bach, Heuristic Test Strategy Model v6.3 (SFDIPOT), Satisfice.
[13] Crispin/Gregory, *Agile Testing*, Addison-Wesley 2009 (Marick quadrants synthesis).
[14] Thomson/Nottingham, "The Robustness Principle Reconsidered", CACM 2011.

Full research doc: `docs/research/at-edge-case-taxonomy-2026-05-19.md`.
