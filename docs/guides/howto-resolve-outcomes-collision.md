# How to resolve an outcomes collision

You ran `nwave-ai outcomes check` and it exited `1`. The CLI flagged your candidate against an existing `OUT-id`. This guide walks you through the three-step triage that resolves the flag.

If you have never registered an outcome, start with the **[Your First Outcome tutorial](outcomes-first-outcome/README.md)** instead — this guide assumes you already understand the verdict matrix.

## Prerequisites

- The CLI exited `1` with one of:
  - `COLLISION: OUT-X (Tier-1 + Tier-2 <score>)`
  - `AMBIGUOUS: OUT-X (Tier-1 only)` or `(Tier-2 <score> only)`
- You have write access to `docs/product/outcomes/registry.yaml`.

## Step 1: Inspect the colliding outcome

Look up the existing outcome the CLI is pointing at. Open `docs/product/outcomes/registry.yaml` and find the entry whose `id` matches the flag. Note three fields:

- `summary` — what does the existing outcome do?
- `artifact` — where is its implementation?
- `keywords` — what intent did the registrant capture?

Example: the CLI flagged `COLLISION: OUT-E3 (Tier-1 + Tier-2 0.67)`. You read the entry:

```yaml
- id: OUT-E3
  summary: Every CommitmentRow non-empty across 4 columns
  keywords: [non-empty, required, cell]
  artifact: nwave_ai/outcomes/application/collision_detector.py
```

You wrote your candidate intending it to detect *cherry-picks* (downstream row count exceeds upstream without a ratifying DDD). The summary says non-empty cells. **They are different rules with overlapping vocabulary.** Move to step 2.

## Step 2: Decide link vs supersede vs annotate

Use this decision tree:

```
Is your candidate semantically equivalent to OUT-X?
├── YES, exactly the same → DO NOT REGISTER. Reuse OUT-X. Stop here.
│
├── YES, but yours improves on OUT-X (clearer, more general, or correct) →
│       SUPERSEDE: register your new OUT-id, then mark the old:
│         superseded_by: OUT-NEW
│       in the OUT-X entry. The old entry stays for audit.
│
└── NO, they are genuinely different (the CLI is over-flagging) →
    Are the keywords actually overlapping?
    ├── YES (Tier-2 fired): refine your keywords to disambiguate.
    │       Pick keywords that capture YOUR intent, not the surface area.
    │       Re-run check; if still flagged, ANNOTATE via `related`.
    │
    └── NO (only Tier-1 fired, verdict was AMBIGUOUS):
            ANNOTATE: register your candidate, then add OUT-X
            to its `related` field. This declares "we know these share
            shape; they are intentionally different rules."
```

The three actions in writing:

### Link via `related` (most common for ambiguous)

Register your candidate normally. Then edit `docs/product/outcomes/registry.yaml` and add a `related` line to the new entry:

```yaml
- id: OUT-MY-NEW
  ...
  related: [OUT-E3]
  superseded_by: null
```

This tells future authors "we considered OUT-E3, decided we are different, and the link is intentional."

### Supersede via `superseded_by`

Edit the *old* entry (not yours) to add `superseded_by: OUT-MY-NEW`. The old entry stays in the registry for audit; future `check` calls still flag the shape but the chain shows it has been replaced.

```yaml
- id: OUT-E3
  ...
  superseded_by: OUT-MY-NEW
```

Then delete or refactor the named artifact per your supersession plan. The registry tracks the contract; you still own the code.

### Dismiss as ambiguous (do nothing)

If the CLI exited `1` with `AMBIGUOUS` and on inspection the rules are genuinely different, the safest action is to:

1. Refine your candidate's `--keywords` so they capture your intent more precisely.
2. Re-run `nwave-ai outcomes check` with the refined keywords.
3. If still flagged, register with `related: [OUT-X]` per "Link via `related`" above.

Do **not** simply ignore the flag and ship — the next author will hit the same flag and waste time re-discovering your reasoning.

## Step 3: Re-run the check and confirm clean

After editing the registry, re-run the original check:

```bash
nwave-ai outcomes check \
  --input-shape "FeatureModel" \
  --output-shape "tuple[Violation, ...]" \
  --keywords "<your refined keywords>"
```

If the verdict is now `NO COLLISIONS` (exit `0`), proceed.

If the verdict is still `COLLISION` and you have already supersede'd or annotated, that is expected — the CLI does not look at `related` or `superseded_by` when deciding to flag (those are documentation, not gates). What matters is that your decision is *recorded* in the registry, so the next author reads the chain instead of re-litigating.

## Worked example: E3 vs E3b (cherry-pick)

This is the canonical case the registry was designed to catch.

**E3** (`OUT-E3` in the seeded registry): "Every CommitmentRow non-empty across 4 columns." Input: `FeatureDeltaModel`. Output: `tuple[ValidationViolation, ...]`. Keywords: `non-empty, required, cell`.

**E3b** (proposed during a later DISTILL wave): "Downstream wave row count >= upstream OR DDD-authorized cherry-pick." Same input. Same output shape. Keywords: `cherry-pick, row-count, ddd`.

Running the check on E3b:

```bash
nwave-ai outcomes check \
  --input-shape "FeatureDeltaModel" \
  --output-shape "tuple[ValidationViolation, ...]" \
  --keywords "cherry-pick,row-count,ddd"
```

Output:

```
AMBIGUOUS: OUT-E3 (Tier-1 only)
```

Exit `1`.

**Why ambiguous?** Tier-1 fires (identical shape — both rules walk the same model and emit the same violation tuple) but Tier-2 does not (`{cherry-pick, row-count, ddd}` ∩ `{non-empty, required, cell}` = ∅, Jaccard = 0).

**Resolution**: This is the "annotate via `related`" case. The two rules genuinely check different predicates — they happen to share the violation-collection contract. Register E3b normally, then add `related: [OUT-E3]` to its entry. The annotation says "yes, we know these collide on shape; they are intentionally separate predicates."

Six months later, when an author proposes E3c with the same shape, the chain `OUT-E3 → OUT-E3b → OUT-E3c` makes the rationale visible.

## What this guide does *not* cover

- **Auto-resolution via supersede sweep** — out of scope for the MVP. The registry tracks supersession; cleaning up superseded artifacts is manual.
- **Cross-feature collision dashboards** — defer until a measured need justifies a project-wide aggregation surface.
- **CI gate on collisions** — no default gate; add one only if collision evidence proves marginal value.

If your situation is none of the above, file an issue with the exact CLI invocation and verdict so we can extend the decision tree.
