# Your First Outcome

This tutorial walks you from zero to a working outcome registry in about ten minutes. By the end you will have:

- registered your first outcome (`OUT-MY-FIRST`),
- seen the registry catch a colliding candidate,
- seen the registry pass a clean candidate, and
- understood the verdict matrix (clean / collision / ambiguous) the CLI prints.

You do not need to know the registry's internals to follow along. We use placeholder shapes; everything you type is copy-paste-ready.

## Prerequisites

- nWave installed (`nwave-ai --version` prints a version)
- A scratch directory you do not mind writing files to

## Step 1: Pick a working directory

Outcomes live in `docs/product/outcomes/registry.yaml` relative to the directory you run `nwave-ai outcomes` from. For this tutorial we use a clean scratch directory so the seeded production registry stays untouched.

```bash
mkdir -p /tmp/outcomes-tutorial
cd /tmp/outcomes-tutorial
```

The first `register` or `check` call will create `docs/product/outcomes/registry.yaml` for you. You do not need to seed it.

## Step 2: Register your first outcome

Run:

```bash
nwave-ai outcomes register \
  --id OUT-MY-FIRST \
  --kind specification \
  --input-shape "FeatureModel" \
  --output-shape "tuple[Violation, ...]" \
  --keywords "non-empty,required,cell" \
  --summary "Every row must have all four cells filled" \
  --feature my-feature \
  --artifact my_feature/domain/rules/non_empty_rows.py
```

Expected output:

```
REGISTERED: OUT-MY-FIRST
```

Exit code: `0`.

The CLI created `docs/product/outcomes/registry.yaml` and appended your entry. Open it to confirm:

```bash
cat docs/product/outcomes/registry.yaml
```

You should see a YAML document with `schema_version: '0.1'` and one outcome under `outcomes:`.

## Step 3: Check a candidate that collides

Now imagine you are about to write a second rule. The proposed rule has the *same input/output shape* as `OUT-MY-FIRST` and *similar intent* (its keywords overlap):

```bash
nwave-ai outcomes check \
  --input-shape "FeatureModel" \
  --output-shape "tuple[Violation, ...]" \
  --keywords "non-empty,required,column"
```

Expected output:

```
COLLISION: OUT-MY-FIRST (Tier-1 + Tier-2 0.50)
```

Exit code: `1`.

What this is telling you:

- **Tier-1** fired: the input/output shape tuple matches `OUT-MY-FIRST` exactly. That is the structural signal.
- **Tier-2** fired with Jaccard score `0.50`: two of three keywords match (`non-empty`, `required`), one differs (`column` vs `cell`). That is the intent signal.
- Both signals agreeing → verdict `COLLISION`. The CLI is telling you: this candidate is almost certainly a duplicate of `OUT-MY-FIRST`. Either link to it (via `related: [OUT-MY-FIRST]`) or supersede it.

If you saw `COLLISION` exit code `1` you are on the happy path.

## Step 4: Check a candidate that is clean

Now run a candidate that has nothing in common with `OUT-MY-FIRST`:

```bash
nwave-ai outcomes check \
  --input-shape "int" \
  --output-shape "bool" \
  --keywords "totally,different,thing"
```

Expected output:

```
NO COLLISIONS
```

Exit code: `0`.

Different shape tuple → Tier-1 silent. Different keywords → Tier-2 silent. Verdict `clean`. You are free to register this candidate without worrying about duplication.

## Step 5: See the verdict matrix in action

The third verdict — `ambiguous` — fires when *exactly one* signal agrees. This happens when shapes match but intent differs (or vice versa). Try it:

```bash
nwave-ai outcomes check \
  --input-shape "FeatureModel" \
  --output-shape "tuple[Violation, ...]" \
  --keywords "checksum,hash,bytewise"
```

Expected output:

```
AMBIGUOUS: OUT-MY-FIRST (Tier-1 only)
```

Exit code: `1`.

Tier-1 fired (same shape) but Tier-2 did not (Jaccard = 0). The CLI is telling you: the structural signature collides, but the keywords suggest different intent. This is a **judgement call** — most likely two genuinely different rules that happen to share a return shape. The CLI flags it for your inspection but does not assert duplication.

The full verdict matrix:

| Tier-1 fires? | Tier-2 ≥ 0.4? | Verdict     | Exit |
|---------------|---------------|-------------|------|
| Yes           | Yes           | `COLLISION` | 1    |
| Yes           | No            | `AMBIGUOUS` | 1    |
| No            | Yes           | `AMBIGUOUS` | 1    |
| No            | No            | `clean`     | 0    |

## Step 6: Verify

Confirm everything you just learned in one go. Re-run the original collision check:

```bash
nwave-ai outcomes check \
  --input-shape "FeatureModel" \
  --output-shape "tuple[Violation, ...]" \
  --keywords "non-empty,required,column"
echo "exit code: $?"
```

You should see:

```
COLLISION: OUT-MY-FIRST (Tier-1 + Tier-2 0.50)
exit code: 1
```

If the command prints `COLLISION` and the exit code is `1`, the registry is working as expected. You have completed the tutorial.

## Where to go next

- **[How to resolve a collision](../howto-resolve-outcomes-collision.md)** — your `check` exited 1 and you need to decide link vs supersede vs annotate.
- **[Outcomes CLI reference](../../reference/outcomes-cli.md)** — every flag, exit code, and stdout/stderr format for `register | check`.
- **[Why an outcomes registry?](../../product/outcomes/README.md)** — the design rationale, locked decisions, and empirical validation.

## Cleanup

To restore the scratch directory to its original state:

```bash
rm -rf /tmp/outcomes-tutorial
```

The seeded production registry at `<your-project>/docs/product/outcomes/registry.yaml` is untouched.
