# Outcomes CLI Reference

Reference for `nwave-ai outcomes register | check`. For learning the workflow, see the **[Your First Outcome tutorial](../guides/outcomes-first-outcome/README.md)**. For triaging a collision, see the **[How-to resolve a collision](../guides/howto-resolve-outcomes-collision.md)**.

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

```

## Global options

| Flag         | Default                                  | Description                          |
|--------------|------------------------------------------|--------------------------------------|
| `--registry` | `docs/product/outcomes/registry.yaml`    | Path to the registry YAML file.      |

If the registry path does not exist, `register` and `check` create an empty skeleton (`schema_version: "0.1"`, `outcomes: []`) before proceeding.

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
| 2    | Refused after checking: duplicate `--id`, or the Outcome fails the schema. |
| 3    | Refused *without* checking: the packaged JSON Schema could not be read. Nothing was written. Reinstall `nwave-ai`. |

`2` and `3` are distinct on purpose. `2` means the outcome was validated and rejected — fix the outcome. `3` means validation could not run at all (a damaged install, whose schema resource is missing or corrupt) — fix the install. An unvalidated outcome is never written and never reported as registered.

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
  --feature outcomes-registry \
  --keywords "invocation,limits,validate,field,shape" \
  --artifact nwave_ai/outcomes/application/collision_detector.py
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

## Registry schema

The registry file is YAML matching the JSON Schema at `nwave_ai/outcomes/schema.json` (draft-07). Each entry is one element of the top-level `outcomes:` list. The schema is a *package resource*: it ships inside `nwave_ai` and is loaded via `importlib.resources`, so it is present in every install (a schema living under `docs/` would be stripped from every distribution channel).

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
| `WARNING: OUT-X referenced in delta but not in registry` | Delta references an OUT-id you have not registered. | Register it, or remove the reference.            |

## Related documentation

- **[Your First Outcome](../guides/outcomes-first-outcome/README.md)** — tutorial for new authors.
- **[How to resolve a collision](../guides/howto-resolve-outcomes-collision.md)** — triage flagged candidates.
- **[Why an outcomes registry?](../product/outcomes/README.md)** — design rationale and locked decisions.
- **JSON Schema** — `nwave_ai/outcomes/schema.json` (a packaged resource, shipped inside the wheel).
- **Seeded registry** — `docs/product/outcomes/registry.yaml`.
