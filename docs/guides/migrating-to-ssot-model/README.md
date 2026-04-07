# Migrating to nWave's SSOT Model

You're upgrading to a version of nWave that uses a new document model. This guide tells you what changed, what you need to do, and how to bootstrap your product from existing features.

---

## What Changed

nWave previously produced ~26 documents per feature across 7 wave directories. There was no reconciliation — after 10 features, you had 10 versions of the architecture, 10 versions of the journey, 10 versions of the KPIs, but no single current one.

The new model: **SSOT + Delta**.

- **SSOT** (`docs/product/`) — what the system IS now. Updated once, never duplicated. Agents read this.
- **Delta** (`docs/features/{id}/`) — what THIS feature changes. Max 6 files. Teams implement from this.

Result: agents read 77% fewer documents. Single source of truth is always current.

See [Understanding the SSOT Model](../understanding-ssot-model/) for the full explanation.

---

## Do I Need To Do Anything?

**Short answer: It depends on your situation.**

### If you have NO features yet
Nothing to do. The first `/nw-discuss` or `/nw-diverge` creates the SSOT automatically.

### If you have features in the old model and want to keep working
Nothing to do. Old features in `docs/feature/` continue to work in fallback mode. Agents check `docs/product/` first, then fall back to old directories.

### If you want to bootstrap the SSOT from existing work (optional)
Follow the migration procedure below. This makes new features benefit from consolidated product knowledge immediately.

---

## Migration Procedure: Bootstrap SSOT from Existing Features

**Time estimate: 30 minutes for a typical product with 3-5 features.**

### Step 1: Create the SSOT directory structure

```bash
mkdir -p docs/product/journeys docs/product/architecture
```

### Step 2: Extract and merge all validated jobs

For each feature that has a JTBD analysis (look in `docs/feature/{id}/discuss/jtbd-analysis.md` or `docs/feature/{id}/diverge/jtbd-analysis.md`):

1. Read the JTBD analysis
2. Extract each job statement into `docs/product/jobs.yaml` using this schema:

```yaml
schema_version: 1

jobs:
  - id: JOB-001
    statement: "When a developer joins the team, I want to understand the architecture quickly, so I can contribute without asking 10 questions"
    level: strategic
    type: functional
    outcomes:
      - "Minimize time to first contribution"
      - "Reduce onboarding support overhead"
    opportunity_score: 14.0
    validated_by: "feat-onboarding-guide"
    status: validated
    feature: "feat-onboarding-guide"

changelog:
  - date: "2026-04-05"
    feature: "ssot-bootstrap"
    change: "Initial SSOT bootstrap — extracted 3 jobs from 2 existing features"
```

**Concrete example**: If Feature A has a job "When users integrate our API, I want clear documentation, so I can ship faster", create the JOB-001 entry above with that statement.

### Step 3: Consolidate journeys

For each journey file in your features (look for `docs/feature/{id}/discuss/journey-*.yaml`):

1. Copy the YAML to `docs/product/journeys/{journey-name}.yaml`
2. Add `schema_version: 1` at the top if not present
3. Ensure each step has a `failure_modes: []` array (empty for now — populate later if needed)
4. Add a `changelog:` section at the end:

```yaml
changelog:
  - date: "2026-04-05"
    feature: "feat-001"
    change: "Migrated onboarding journey from old model"
```

5. Copy the visual markdown to `docs/product/journeys/{journey-name}-visual.md`

### Step 4: Create architecture brief

Read architecture files from your features (`docs/feature/{id}/design/architecture-design.md`). Create `docs/product/architecture/brief.md` with:

```markdown
# Architecture Brief

## For Acceptance Designer

**Driving ports** (entry points for tests):
- HTTP REST API on `:8000`
- CLI via `nwave` command
- Configuration files in `~/.config/nwave/`

**Test entry points**:
- Use HTTP API for integration tests
- Use CLI for end-to-end tests
- Use config files for state setup

## For Software Crafter

**Component boundaries**:
- API layer (FastAPI)
- Domain layer (business logic, no dependencies)
- Adapters (database, file system, external APIs)

**Key decisions**:
- Use domain-driven design — domain is framework-agnostic
- Adapters are replaceable — all external deps in adapters/
```

Add decision references: if your features have ADRs, copy them to `docs/product/architecture/adr-001.md`, `adr-002.md`, etc.

### Step 5: Extract KPI contracts

For each feature with KPI definitions (look for `docs/feature/{id}/devops/kpi-contracts.yaml` or similar):

Create or update `docs/product/kpi-contracts.yaml`:

```yaml
schema_version: 1

contracts:
  - id: KPI-001
    feature: "feat-api-docs"
    job: "When a developer integrates our API..."
    metric: "time_to_first_api_call"
    baseline: "45 minutes"
    target: "15 minutes"
    threshold_alert: "30 minutes"
    measurement_method: "event captured on successful /api/v1/authenticate"
    status: active
    added: "2026-04-05"

  - id: KPI-002
    feature: "feat-error-messages"
    job: "When something fails, I want clear guidance..."
    metric: "support_tickets_about_errors"
    baseline: "12 per week"
    target: "3 per week"
    threshold_alert: "8 per week"
    measurement_method: "count from support system"
    status: active
    added: "2026-04-05"

changelog:
  - date: "2026-04-05"
    feature: "ssot-bootstrap"
    change: "Extracted N KPI contracts from M features"
```

### Step 6: Create a vision document

Create `docs/product/vision.md` (one-time, 40-50 lines):

```markdown
# Product Vision

## Mission

Enable developers to build with confidence by providing clear, executable guidance at every step.

## Value Proposition

- Reduce onboarding time from weeks to days
- Eliminate "how do I?" support overhead through documentation-first design
- Enable teams to work autonomously without blocking on subject matter experts

## Core Principles

1. **Documentation as code** — acceptance tests verify it's current
2. **One source of truth** — single journey, single architecture, single set of KPIs
3. **Validated through discovery** — every job is grounded in real user research
```

### Step 7: Verify the migration

After completing all steps, verify the SSOT structure:

```bash
# Check files exist
ls -la docs/product/
ls -la docs/product/journeys/
ls -la docs/product/architecture/

# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('docs/product/jobs.yaml'))"
python -c "import yaml; yaml.safe_load(open('docs/product/kpi-contracts.yaml'))"

# Check git status
git status docs/product/
```

Commit:
```bash
git add docs/product/
git commit -m "feat(ssot): bootstrap SSOT from existing features"
```

---

## Documents No Longer Produced

The new model eliminates 4 documents that were duplicated per feature:

| Old Document | Reason | New Location |
|---|---|---|
| `acceptance-criteria.md` | Non-executable duplicate of tests | Embedded in `acceptance-tests.feature` |
| `requirements.md` | Duplicate of user stories | Consolidated in `user-stories.md` |
| `prioritization.md` | Always derivative of story map | Moved to `story-map.md` as a section |
| `journey.feature` | Gherkin already in `journey.yaml` | DISTILL extracts from YAML — no separate file |

---

## FAQ

**Q: Can I mix old and new features in the same project?**

A: Yes. Agents check `docs/product/` first (new model), then fall back to `docs/feature/{id}/` (old model) if SSOT doesn't exist. Both work.

**Q: Do I have to migrate all features?**

A: No. Only bootstrap SSOT if you want new features to benefit from consolidated product knowledge. Old features remain read-only archives.

**Q: What if two features update the same journey?**

A: Git handles conflicts at merge time. The `changelog:` section in YAML helps resolve — you can see which feature changed what.

**Q: What if I skip DEVOPS and there's no kpi-contracts.yaml?**

A: DISTILL proceeds with a warning: "KPI contracts missing — acceptance tests cover behavior only, not observability." The feature is still shippable.

**Q: When does `/nw-continue` detect that SSOT exists?**

A: When `docs/product/` directory is present. If it exists, waves use the new model (read SSOT first). If it doesn't, waves use the old model (fallback to `docs/feature/{id}/`).

---

## Next Steps

1. **Bootstrap SSOT** (optional) — follow the procedure above
2. **Start a new feature** — `/nw-diverge` or `/nw-discuss` will read from `docs/product/`
3. **Review the SSOT updates** — after each wave, check what changed in `docs/product/`

For detailed explanation of the model, see [Understanding the SSOT Model](../understanding-ssot-model/).

For directory reference, see [Wave Directory Structure](../wave-directory-structure/).
