# Tutorial: Production Readiness

**Time**: ~15 minutes (7 steps)
**Platform**: macOS or Linux (Windows: use WSL)
**Prerequisites**: Python 3.10+, Claude Code with nWave installed, [Tutorial 8](../tutorial-deliver-feature/) completed
**What this is**: A hands-on walkthrough of `/nw-devops` -- nWave's production readiness command. You will take the delivered bookmark CLI from Tutorial 8 and generate CI/CD pipeline design, infrastructure recommendations, deployment strategy, and a production readiness checklist.

---

## What You'll Build

A complete production readiness package -- CI/CD workflow, deployment strategy, infrastructure recommendations, and a go-live checklist -- all designed by Apex, nWave's platform architect agent.

**Before**: You have a fully implemented bookmark CLI from Tutorial 8. All acceptance tests pass. The code is mutation-tested and reviewed. But you have no CI/CD pipeline, no deployment plan, no monitoring strategy, and no checklist to know when it is safe to release.

**After**: You have a GitHub Actions workflow with quality gates at every stage. You have a deployment strategy matched to your project's risk profile. You have infrastructure recommendations for packaging and distribution. You have a production readiness checklist that tells you exactly what remains before go-live. Everything is documented and peer-reviewed.

**Why this matters**: Working code is not the same as shippable code. `/nw-devops` bridges the gap between "all tests pass" and "safe to release" by applying the same evidence-based methodology the rest of the wave used. The platform architect does not guess -- it reads your architecture, your test suite, and your deployment target, then designs infrastructure that fits.

---

## Step 1 of 7: Confirm Your Starting Point (~1 minute)

You should be in the `bookmark-cli` project from Tutorial 8, with all acceptance tests passing.

Verify your tests pass:

```bash
pytest tests/ -v --no-header 2>&1 | tail -5
```

You should see all tests passing:

```
...
PASSED
PASSED

===== X passed in Y.YYs =====
```

Verify your architecture document exists:

```bash
ls docs/feature/bookmark-cli/design/architecture-design.md
```

You should see:

```
docs/feature/bookmark-cli/design/architecture-design.md
```

Verify your evolution document exists:

```bash
ls docs/evolution/
```

You should see:

```
bookmark-cli.md
```

> **If tests fail or files are missing**: Complete [Tutorial 8](../tutorial-deliver-feature/) first. `/nw-devops` reads architecture documents, test results, and the delivered codebase to make infrastructure decisions. Without them, the platform architect cannot assess what needs to be deployed.

*Next: you will launch the devops command and answer Apex's configuration questions.*

---

## Step 2 of 7: Launch the DevOps Session (~1 minute)

In Claude Code, type:

```
/nw-devops bookmark-cli
```

> **AI output varies between runs.** Your session with Apex will differ from the examples below. The agent designs infrastructure based on your specific architecture and deployment target. What matters is the structure (decisions, artifacts, peer review), not the exact output.

Apex (the platform architect agent) will ask eight configuration questions to tailor the infrastructure design to your project. When Apex asks each question, select the option shown below.

| Question | Answer | Why |
|----------|--------|-----|
| Deployment target? | **Cloud-native** (a) | Standard for modern Python packages published to PyPI (Python's public package registry) |
| Container orchestration? | **None** (d) | CLI tools run locally on the user's machine, not as services -- no containers needed |
| CI/CD platform? | **GitHub Actions** (a) | GitHub Actions is GitHub's built-in CI/CD automation -- most common for open-source Python projects |
| Existing infrastructure? | **No** (d) | Greenfield project -- design everything from scratch |
| Observability and logging? | **None** (g) | CLI tools use structured stderr for errors, not monitoring dashboards -- those are for long-running services |
| Deployment strategy? | **Recreate** (d) | Each PyPI publish fully replaces the previous version -- no gradual rollout needed for a CLI tool |
| Existing monitoring? | **No** (b) | Foundational setup only -- no existing systems to integrate with |
| Git branching strategy? | **GitHub Flow** (b) | Simple model: feature branches merge to main via pull request review |

<details>
<summary>Alternative answers for different project types</summary>

- **Deployment target**: Choose "On-premise" for internal tools, "Hybrid" for tools that also run as a service.
- **Container orchestration**: Choose "Kubernetes" for web services, "Docker Compose" for local development environments.
- **CI/CD platform**: Choose "GitLab CI" or "Azure DevOps" if that is your team's standard.
- **Observability**: Choose "Prometheus + Grafana" or "OpenTelemetry" for web services that need runtime monitoring.
- **Deployment strategy**: Choose "Blue-green" or "Canary" (gradual traffic shifting to detect issues early) for services with uptime requirements.
- **Branching strategy**: Choose "Trunk-Based Development" for teams with strong CI gates, "GitFlow" for formal release processes.

</details>

**What just happened?** Apex read your architecture documents, test suite, and codebase to understand what needs to be deployed. These eight answers configure the infrastructure design -- deployment target determines packaging, CI/CD platform determines workflow format, branching strategy determines pipeline triggers, and deployment strategy determines release mechanics. The key concept here is the interaction itself: Apex asks simple multiple-choice questions, then uses your answers plus your codebase to generate a complete infrastructure design.

*Next: Apex will design the CI/CD pipeline.*

---

## Step 3 of 7: Watch the CI/CD Pipeline Design (~3 minutes)

After your answers, Apex designs a CI/CD pipeline. You will see:

```
● nw-platform-architect(Analyzing existing infrastructure...)
● nw-platform-architect(Designing CI/CD pipeline...)
● nw-platform-architect(Creating .github/workflows/bookmark-cli.yml)
● nw-platform-architect(Creating docs/feature/bookmark-cli/devops/ci-cd-pipeline.md)
```

The generated GitHub Actions workflow will look something like:

```yaml
name: bookmark-cli CI/CD
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - run: pip install ruff
      - run: ruff check src/ tests/

  test:
    needs: lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - run: pip install -e ".[test]"
      - run: pytest tests/ -v --cov=bookmark_cli

  security:
    needs: lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install safety
      - run: safety check

  publish:
    needs: [test, security]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install build twine
      - run: python -m build
      - run: twine upload dist/*
```

> **Your workflow will differ.** Apex tailors the pipeline to your specific architecture and test setup. The pattern is what matters: lint first, then test and security in parallel, then publish only on main.

Two things to notice:

1. **Quality gates at every stage.** The pipeline does not publish unless lint, tests, and security scanning all pass. This mirrors the quality gates from the delivery pipeline in Tutorial 8 -- the same discipline, applied to the release process.
2. **Branch-aware triggers.** Pull requests run lint, test, and security. Only pushes to main trigger publish. This matches the GitHub Flow branching strategy you selected.

*Next: Apex will design the deployment strategy and infrastructure recommendations.*

---

## Step 4 of 7: Review Infrastructure and Deployment Design (~3 minutes)

After the pipeline, Apex designs deployment and infrastructure:

```
● nw-platform-architect(Designing deployment strategy...)
● nw-platform-architect(Creating docs/feature/bookmark-cli/devops/deployment-strategy.md)
● nw-platform-architect(Designing infrastructure recommendations...)
● nw-platform-architect(Creating docs/feature/bookmark-cli/devops/platform-architecture.md)
```

Check the deployment strategy:

```bash
ls docs/feature/bookmark-cli/devops/
```

You should see something like:

```
ci-cd-pipeline.md
deployment-strategy.md
platform-architecture.md
branching-strategy.md
```

> **Your file names and count may differ.** Apex may split or combine documents based on complexity. Look for files covering CI/CD, deployment, and infrastructure.

The deployment strategy for a CLI tool typically covers:

- **Packaging**: Python wheel and sdist via `python -m build`
- **Distribution**: PyPI publish with version tagging
- **Versioning**: Semantic versioning aligned to conventional commits
- **Rollback**: Publish a patch version -- PyPI does not support unpublishing, so rollback means "release a fix fast"

**What just happened?** Apex applied Principle 4 (simplest infrastructure first) from its methodology. A CLI tool does not need Kubernetes, load balancers, or canary deployments. It needs a build, a publish, and a version strategy. Apex documented why simpler alternatives were chosen over complex ones.

> **If you see Kubernetes or container recommendations**: Apex may have misread the project type. This is rare but possible. Check `docs/feature/bookmark-cli/design/architecture-design.md` to confirm it describes a CLI tool, not a web service.

*Next: Apex will generate the production readiness checklist.*

---

## Step 5 of 7: Review the Production Readiness Checklist (~2 minutes)

Apex generates a production readiness assessment:

```
● nw-platform-architect(Generating production readiness checklist...)
● nw-platform-architect(Creating docs/feature/bookmark-cli/devops/production-readiness.md)
```

The checklist covers items like:

```markdown
## Production Readiness Checklist

### Code Quality
- [x] All acceptance tests pass
- [x] Unit test coverage above 80%
- [x] Mutation testing kill rate above 80%
- [x] Adversarial code review passed

### Packaging
- [ ] pyproject.toml has correct metadata (name, version, description)
- [ ] Entry point defined (console_scripts)
- [ ] README with installation instructions
- [ ] LICENSE file present

### CI/CD
- [ ] GitHub Actions workflow committed
- [ ] Branch protection enabled on main
- [ ] PyPI API token configured as repository secret

### Security
- [ ] No hardcoded secrets in codebase
- [ ] Dependency vulnerability scan passes
- [ ] SBOM (Software Bill of Materials) generated
```

> **Your checklist will differ.** Apex generates items based on what exists in your project versus what production requires. Items already completed (from tutorials 4-8) are checked. Items that still need manual action are unchecked.

The checked items are evidence the wave process already handled. The unchecked items are what remains between "working code" and "shippable product." This is the value of `/nw-devops` -- it tells you exactly what is left.

*Next: the peer reviewer will validate the entire design.*

---

## Step 6 of 7: The Peer Review (~2 minutes)

After all designs are complete, Apex invokes Atlas (the platform architect reviewer):

```
● nw-platform-architect-reviewer(Review)
  Checking external validity...
  Checking pipeline quality...
  Checking deployment readiness...
  Checking observability completeness...
  Review result: APPROVED (or CONDITIONALLY_APPROVED)
```

The reviewer checks five dimensions:

| Dimension | What It Checks for Bookmark CLI |
|-----------|-------------------------------|
| External validity | Deployment path is complete (commit to PyPI) |
| Pipeline quality | Quality gates at every stage, no skipped steps |
| Deployment readiness | Rollback procedure documented |
| Security | Dependency scanning and secrets detection present |
| Handoff completeness | All design documents produced |

If the reviewer requests changes, Apex fixes them automatically. You will see a second round of document updates. Maximum two rounds -- if it still fails, the pipeline stops for your manual intervention.

> **If you see "CONDITIONALLY_APPROVED"**: This means the design is sound but has medium-severity items to address before go-live. Check the review output for specific recommendations. These are typically documentation gaps, not design flaws.

*Next: verify the final artifacts and see the complete wave.*

---

## Step 7 of 7: The Complete Wave (~3 minutes)

Check all the artifacts Apex produced:

```bash
find docs/feature/bookmark-cli/deliver -type f | sort
```

You should see something like:

```
docs/feature/bookmark-cli/devops/branching-strategy.md
docs/feature/bookmark-cli/devops/ci-cd-pipeline.md
docs/feature/bookmark-cli/devops/deployment-strategy.md
docs/feature/bookmark-cli/devops/platform-architecture.md
docs/feature/bookmark-cli/devops/production-readiness.md
```

Check for the GitHub Actions workflow:

```bash
ls .github/workflows/
```

You should see:

```
bookmark-cli.yml
```

> **Your file names will differ.** What matters is the pattern: design documents explaining the "why," a workflow file implementing the "how," and a checklist tracking what remains.

### What You Built Across All Six Tutorials

You started with an idea and ended with a production-ready feature:

```
bookmark-cli/
  src/bookmark_cli/
    domain/
      bookmark.py              # Entity
      services.py              # Use cases
      ports.py                 # Repository interface
    adapters/
      cli.py                   # CLI entry point
      sqlite_repository.py     # Storage implementation
  tests/
    acceptance/                # BDD scenarios (all green)
    unit/                      # TDD unit tests
  docs/
    feature/bookmark-cli/
      discover/                # Problem validation
      discuss/                 # User stories + acceptance criteria
      design/                  # Hexagonal design
      distill/                 # Test design docs
      deliver/                 # Roadmap + execution log
      devops/                  # DevOps artifacts (this tutorial)
    adrs/                      # Architecture decision records
    evolution/bookmark-cli.md  # Permanent delivery record
  .github/workflows/
    bookmark-cli.yml           # CI/CD pipeline
```

> **Your file structure will differ.** The agents organize files based on your specific project. The pattern is what matters.

### The Full nWave

```
DISCOVER         DISCUSS          DESIGN           DISTILL          DELIVER          DEVOPS
(/nw-discover)   (/nw-discuss)    (/nw-design)     (/nw-distill)    (/nw-deliver)    (/nw-devops)
──────────────   ──────────────   ──────────────   ──────────────   ──────────────   ──────────────
"Is the problem  "What should     "How should we   "What does done  "Build it with   "Get to
 real?"           we build?"       build it?"       look like?"      quality gates"   production"

Evidence-based   User stories +   Hexagonal arch   Acceptance       Domain-first     CI/CD pipeline
validation       acceptance       + ADRs +         tests + walking  TDD + review +   + deployment +
                 criteria         diagrams         skeleton         mutation test    readiness

Tutorial 4       Tutorial 5       Tutorial 6       Tutorial 7       Tutorial 8       This tutorial
```

Each wave constrained the next. The problem shaped the requirements. Requirements shaped the architecture. Architecture shaped the tests. Tests shaped the implementation. Implementation shaped the infrastructure. Nothing was generated in a vacuum.

You went from "I have an idea for a bookmark CLI" to a production-ready, fully tested, architecturally sound application with CI/CD -- and every decision along the way is documented and traceable.

---

## Next Steps

- **Act on the checklist** -- Open `docs/feature/bookmark-cli/devops/production-readiness.md` and work through the unchecked items. Each one brings you closer to a real release.
- **Run the pipeline** -- Commit the GitHub Actions workflow, push to a repository, and watch the pipeline execute. The quality gates should all pass on the first run.
- **Try a different project** -- Run through tutorials 4-9 again on a new idea. The wave process works the same way regardless of the feature.
- **Explore standalone tutorials** -- [Tutorial 10: Safe Refactoring](../TUTORIALS.md) and [Tutorial 11: Debugging with 5 Whys](../TUTORIALS.md) cover everyday tasks that do not require the full wave.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `/nw-devops` does not start | Make sure nWave is installed. Run `/nw-help` to verify. |
| Apex cannot find architecture docs | Ensure `docs/feature/bookmark-cli/design/architecture-design.md` exists. Complete [Tutorial 6](../tutorial-design/) if missing. |
| Apex designs overly complex infrastructure (Kubernetes for a CLI) | Interrupt and clarify: "This is a CLI tool distributed via PyPI, not a web service." Apex will simplify. |
| Pipeline workflow has syntax errors | Copy the workflow to `.github/workflows/`, push to a branch, and check the GitHub Actions tab for validation errors. Fix inline. |
| Reviewer rejects repeatedly (3+ rounds) | The pipeline stops after 2 rounds. Review the findings manually, make the changes Apex could not, and run `/nw-devops` again. |
| No `.github/workflows/` directory created | Apex may have placed the workflow in `docs/feature/bookmark-cli/devops/` as a design document rather than a live file. Copy it to `.github/workflows/`. |
| Production readiness checklist shows items you already completed | Apex may not have detected all prior artifacts. Manually check the items you know are done. |
| Want to start fresh | Delete `docs/feature/bookmark-cli/devops/` and `.github/workflows/bookmark-cli.yml`, then run `/nw-devops` again. |

---

**Last Updated**: 2026-02-17
