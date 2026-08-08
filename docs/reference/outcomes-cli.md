# Outcomes CLI Reference

Reference for `nwave-ai outcomes register | check | check-delta`. For learning the workflow, see the **[Your First Outcome tutorial](../guides/outcomes-first-outcome/README.md)**. For triaging a collision, see the **[How-to resolve a collision](../guides/howto-resolve-outcomes-collision.md)**.

## Synopsis

```
nwave-ai outcomes [--registry PATH] register --id OUT-ID --kind KIND \
                                              --input-shape SHAPE \
                                              --output-shape SHAPE \
                                              [--summary STR] \
                                              [--feature STR] \
                                              [--keywords CSV] \
                                              [--artifact PATH]

nwave-ai outcomes [--registry PATH] check --input-shape SHAPE \
                                          --output-shape SHAPE \
                                          [--keywords CSV]

nwave-ai outcomes [--registry PATH] check-delta DELTA_PATH
```

## Global options

| Flag         | Default                                  | Description                          |
|--------------|------------------------------------------|--------------------------------------|
| `--registry` | `docs/product/outcomes/registry.yaml`    | Path to the registry YAML file.      |

If the registry path does not exist, `register` and `check` create an empty skeleton (`schema_version: "0.1"`, `outcomes: []`) before proceeding. `check-delta` does the same.

If the path cannot be read or created — a read-only filesystem, a denied permission, or a path occupied by a directory — every subcommand exits **4** and prints `ERROR: <cause>` naming the path on stderr.

## Verdict matrix

The detector runs two tiers and combines them into a verdict.

| Tier-1 (shape match) | Tier-2 Jaccard ≥ 0.4 | Verdict     | Exit code |
|----------------------|----------------------|-------------|-----------|
| Yes                  | Yes                  | `COLLISION` | 1         |
| Yes                  | No                   | `AMBIGUOUS` | 1         |
| No                   | Yes                  | `AMBIGUOUS` | 1         |
| No                   | No                   | `clean`     | 0         |

- **Tier-1** = exact normalized match on `(input_shape, output_shape)` tuple. High precision on identical-intent duplicates.
- **Tier-2** = Jaccard similarity over tokenized keyword sets. Threshold 0.4. Disambiguates same-shape-different-intent cases.

---

## `nwave-ai outcomes register`

Register a new outcome in the registry.

### Synopsis

```
nwave-ai outcomes register --id OUT-ID --kind KIND \
                           --input-shape SHAPE --output-shape SHAPE \
                           [--summary STR] [--feature STR] \
                           [--keywords CSV] [--artifact PATH]
```

### Flags

| Flag             | Required | Type    | Description                                                                  |
|------------------|----------|---------|------------------------------------------------------------------------------|
| `--id`           | yes      | string  | Stable identifier matching `^OUT-[A-Z0-9-]+$` (e.g. `OUT-E3`, `OUT-FORMAT`). |
| `--kind`         | yes      | enum    | One of `specification`, `operation`, `invariant`.                            |
| `--input-shape`  | yes      | string  | Type expression for the input contract (e.g. `FeatureDeltaModel`).           |
| `--output-shape` | yes      | string  | Type expression for the output contract (e.g. `tuple[Violation, ...]`).      |
| `--summary`      | no       | string  | One-line description. Default: empty string.                                 |
| `--feature`      | no       | string  | Owning feature name. Default: `unknown`.                                     |
| `--keywords`     | no       | CSV     | Comma-separated lowercase tokens (max 6). Default: empty.                    |
| `--artifact`     | no       | string  | Repo-relative path to the implementing artifact. Default: empty string.      |

### Exit codes

| Code | Condition                                                            |
|------|----------------------------------------------------------------------|
| 0    | Outcome registered successfully.                                     |
| 2    | Duplicate `--id` (already in registry), or invalid Outcome (schema). |
| 3    | The packaged JSON Schema could not be loaded — the installation is incomplete. Reinstall `nwave-ai`. |
| 4    | The registry path is unusable (read-only filesystem, permission denied, or not a regular file). |

### Output

**stdout** on success:

```
REGISTERED: OUT-MY-FIRST
```

**stderr** on failure:

```
ERROR: <error description>
```

### Example

```bash
nwave-ai outcomes register \
  --id OUT-E6 \
  --kind specification \
  --input-shape FeatureDeltaModel \
  --output-shape "tuple[ValidationViolation, ...]" \
  --summary "Validate invocation_limits field shape" \
  --feature unified-feature-delta \
  --keywords "invocation,limits,validate,field,shape" \
  --artifact nwave_ai/feature_delta/domain/rules/e6_invocation_limits.py
```

Idempotency: registration is **not** idempotent on re-run. Calling `register` twice with the same `--id` exits 2.

---

## `nwave-ai outcomes check`

Check a candidate outcome against the registry without registering it.

### Synopsis

```
nwave-ai outcomes check --input-shape SHAPE --output-shape SHAPE \
                        [--keywords CSV]
```

### Flags

| Flag             | Required | Type   | Description                                          |
|------------------|----------|--------|------------------------------------------------------|
| `--input-shape`  | yes      | string | Candidate's input shape.                             |
| `--output-shape` | yes      | string | Candidate's output shape.                            |
| `--keywords`     | no       | CSV    | Candidate's keywords (used for Tier-2). Default: ``. |

### Exit codes

| Code | Condition                          |
|------|------------------------------------|
| 0    | No collisions detected (`clean`).  |
| 1    | One or more collisions detected.   |
| 4    | The registry path is unusable.     |

### Output

**stdout** when clean:

```
NO COLLISIONS
```

**stdout** when collisions detected: one line per matched OUT-id, in registration order:

```
COLLISION: OUT-E3 (Tier-1 + Tier-2 0.67)
COLLISION: OUT-FORMAT (Tier-1 + Tier-2 0.50)
```

```
AMBIGUOUS: OUT-E3 (Tier-1 only)
```

```
AMBIGUOUS: OUT-E1 (Tier-2 0.45 only)
```

The label (`COLLISION` / `AMBIGUOUS`) reflects the overall verdict; the parenthetical annotation lists which tier(s) fired and the Jaccard score where applicable.

### Examples

Tier-1 + Tier-2 hit:

```bash
nwave-ai outcomes check \
  --input-shape FeatureDeltaModel \
  --output-shape "tuple[ValidationViolation, ...]" \
  --keywords "non-empty,required,column"
# → exit 1
# → COLLISION: OUT-E3 (Tier-1 + Tier-2 0.67)
```

Same shape, different intent (Tier-1 only):

```bash
nwave-ai outcomes check \
  --input-shape FeatureDeltaModel \
  --output-shape "tuple[ValidationViolation, ...]" \
  --keywords "cherry-pick,row-count,ddd"
# → exit 1
# → AMBIGUOUS: OUT-E3 (Tier-1 only)
```

Clean candidate:

```bash
nwave-ai outcomes check \
  --input-shape int \
  --output-shape bool \
  --keywords "totally,different"
# → exit 0
# → NO COLLISIONS
```

---

## `nwave-ai outcomes check-delta`

Aggregate scan: parse `OUT-<id>` references from a `feature-delta.md` and run a self-excluding collision check on each.

### Synopsis

```
nwave-ai outcomes check-delta DELTA_PATH
```

### Positional arguments

| Argument     | Required | Type | Description                              |
|--------------|----------|------|------------------------------------------|
| `delta_path` | yes      | path | Path to the `feature-delta.md` file.     |

### Exit codes

| Code | Condition                                                  |
|------|------------------------------------------------------------|
| 0    | Zero collisions across all referenced OUT-ids.             |
| 1    | One or more referenced OUT-ids collide with another entry. |
| 2    | `delta_path` does not exist.                               |
| 4    | The registry path is unusable.                             |

### Output

**stdout** aggregate report (always):

```
3 outcomes checked, 1 collision found across 1 outcome
  COLLISION: OUT-E3
```

**stdout** warning when an OUT-id is referenced in the delta but missing from the registry:

```
WARNING: OUT-E99 referenced in delta but not in registry
```

**stderr** on missing delta file:

```
ERROR: feature-delta not found: <path>
```

### How OUT-ids are extracted

The CLI scans `delta_path` text for the regex `\bOUT-[A-Z0-9-]+\b` and processes each unique match in document order. There is no semantic parsing of section headings; if your delta references `OUT-E3` in prose, it is checked.

### Self-exclusion

When the CLI checks `OUT-E3`, it excludes `OUT-E3` itself from the snapshot. Otherwise every registered outcome would trivially collide with itself.

### Example

```bash
nwave-ai outcomes check-delta docs/feature/my-feature/feature-delta.md
# → exit 1
# → 3 outcomes checked, 1 collision found across 1 outcome
# →   COLLISION: OUT-E3
```

---

## Registry schema

The registry file is YAML matching the JSON Schema shipped inside the package at `nwave_ai/outcomes/schema.json` (draft-07). Each entry is one element of the top-level `outcomes:` list.

### Top-level structure

```yaml
schema_version: "0.1"
outcomes:
  - id: OUT-...
    kind: specification | operation | invariant
    summary: <string>
    feature: <string>
    inputs:
      - shape: <string>
    output:
      shape: <string>
    keywords: [<token>, ...]
    artifact: <path>
    related: [<OUT-id>, ...]
    superseded_by: <OUT-id> | null
```

### Field reference

| Field            | Type       | Required | Constraint / Notes                                                      |
|------------------|------------|----------|-------------------------------------------------------------------------|
| `id`             | string     | yes      | Pattern `^OUT-[A-Z0-9-]+$`.                                             |
| `kind`           | enum       | yes      | One of `specification`, `operation`, `invariant`.                       |
| `summary`        | string     | yes      | Free-form, one-line description.                                        |
| `feature`        | string     | yes      | Feature name owning the outcome.                                        |
| `inputs`         | array      | yes      | At least one `{shape: <string>}` entry. Currently a single shape used.  |
| `output`         | object     | yes      | Single `{shape: <string>}` entry.                                       |
| `keywords`       | array      | yes      | ≤ 6 tokens; each matches `^[a-z0-9][a-z0-9-]*$`. May be empty.          |
| `artifact`       | string     | yes      | Repo-relative path to the implementation. May be empty.                 |
| `related`        | array      | yes      | OUT-ids declaring "intentional non-collision". May be empty.            |
| `superseded_by`  | string\|null | yes    | OUT-id replacing this outcome, or `null`.                               |

`additionalProperties` is `false` — unrecognized keys cause a schema validation error.

### Canonical order

Outcomes are written in **registration order** (newest at the bottom). Within an entry, fields appear in the order shown above.

---

## Shape normalization

Tier-1 matches normalized shape strings, not raw user input. The normalizer:

- strips leading and trailing whitespace,
- strips parameter names from tuple shapes — `(name: T, ...)` → `(T, ...)`,
- preserves type alias differences (`Path` and `str` are *not* automatically equated; that is reserved for v2 with an opt-in flag).

Practical implication: `(text: str, file_path: str)` and `(str, str)` normalize to the same string and Tier-1-collide. `Path` and `str` do not.

---

## Keyword tokenization

Tier-2 tokenizes `keywords` as follows:

- Lowercase.
- Split on `-`, `_`, and whitespace.
- Drop tokens of length ≤ 2.
- Treat result as a set; compute Jaccard similarity `|A ∩ B| / |A ∪ B|`.

Threshold: ≥ 0.4 → Tier-2 fires.

---

## Common error messages

| Stderr                                          | Cause                                                       | Fix                                              |
|-------------------------------------------------|-------------------------------------------------------------|--------------------------------------------------|
| `ERROR: duplicate id: OUT-X`                    | `register --id OUT-X` and `OUT-X` already in registry.      | Pick a different id, or use the existing entry.  |
| `ERROR: <validation message>`                   | Outcome fails schema validation (e.g. malformed id, kind).  | Fix the offending field.                         |
| `ERROR: feature-delta not found: <path>`        | `check-delta` given a path that does not exist.             | Pass a real `feature-delta.md` path.             |
| `WARNING: OUT-X referenced in delta but not in registry` | Delta references an OUT-id you have not registered. | Register it, or remove the reference.            |

## Related documentation

- **[Your First Outcome](../guides/outcomes-first-outcome/README.md)** — tutorial for new authors.
- **[How to resolve a collision](../guides/howto-resolve-outcomes-collision.md)** — triage flagged candidates.
- **[Why an outcomes registry?](../product/outcomes/README.md)** — design rationale and locked decisions.
- **JSON Schema** — `nwave_ai/outcomes/schema.json`, loaded as a package resource so it travels with the install.
- **Seeded registry** — `docs/product/outcomes/registry.yaml`.
