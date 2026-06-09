# Enforcement Recipes

Integration recipes for `nwave-ai validate-feature-delta` across VCS systems, CI providers, IDE environments, and bare Make targets.

## Vendor-Neutrality Statement

**nwave-ai does NOT auto-install any integration.**

You choose where and when the validator runs. Installing nwave-ai (`uv tool install nwave-ai`, or `pipx install nwave-ai` as a fallback) gives you a CLI binary and nothing else. No hooks are registered, no CI files are created, no configuration files are modified. Pick the recipe that fits your stack and paste it in — that is the full integration story.

This design is intentional (DD-D14). Teams using Mercurial, Jenkins, bare Make, or no automation at all are first-class citizens alongside GitHub Actions users.

---

## JSON Output Schema (US-07A cross-reference)

Every recipe invokes `nwave-ai validate-feature-delta <path>`. When your integration needs machine-parseable output, add `--format=json`:

```
nwave-ai validate-feature-delta docs/feature/my-feature/feature-delta.md --format=json
```

JSON output schema (schema_version 1):

```json
{
  "schema_version": 1,
  "results": [
    {
      "check": "E3",
      "severity": "error",
      "file": "docs/feature/my-feature/feature-delta.md",
      "line": 42,
      "offender": "DESIGN decision dropped between DESIGN and DISTILL",
      "remediation": "Re-add the decision or mark it explicitly ratified"
    }
  ]
}
```

Fields: `check` (rule ID), `severity` (`error`|`warn`), `file` (absolute path), `line` (1-based), `offender` (the offending text), `remediation` (human-readable fix hint).

Exit codes: `0` = no violations, `1` = violations found (enforce mode or JSON mode), `2` = usage error, `65` = parse error, `70` = startup probe failure, `78` = misconfiguration.

---

## Trigger Matrix

| Trigger event | Recipe section |
|---------------|----------------|
| `git commit` | [Git + pre-commit](#recipe-1-git--pre-commit-framework), [Git + husky](#recipe-2-git--husky), [Git + lefthook](#recipe-3-git--lefthook) |
| `git push` | [Git + pre-commit](#recipe-1-git--pre-commit-framework) (push stage), [Git + husky](#recipe-2-git--husky) (pre-push) |
| Pull request / merge request | [GitHub Actions](#recipe-4-github-actions), [GitLab CI](#recipe-5-gitlab-ci), [Jenkins](#recipe-6-jenkins), [CircleCI](#recipe-7-circleci), [Bitbucket Pipelines](#recipe-8-bitbucket-pipelines) |
| Scheduled / nightly | [GitHub Actions](#recipe-4-github-actions) (schedule trigger), [GitLab CI](#recipe-5-gitlab-ci) (pipeline schedules) |
| Manual one-shot | [Manual](#recipe-11-manual-one-liner) |
| IDE save | [VS Code on-save](#recipe-10-vs-code-on-save) |
| `make` target | [Makefile](#recipe-9-makefile) |
| Mercurial changegroup | [Mercurial hgrc](#recipe-12-mercurial-hgrc) |

---

## Recipe 1: Git + pre-commit Framework

**When it fires**: on `git commit` (pre-commit stage) and optionally on `git push` (pre-push stage).

**Prerequisites**: `pip install pre-commit` and `nwave-ai` both on PATH.

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: validate-feature-delta
        name: Validate feature-delta (nwave-ai)
        language: system
        entry: nwave-ai validate-feature-delta
        args: []
        files: '^docs/feature/.*feature-delta\.md$'
        pass_filenames: true
        stages: [pre-commit]
```

For push-time enforcement, change `stages: [pre-commit]` to `stages: [pre-push]` or list both.

Install the hook after adding the config:

```bash
pre-commit install
# also for push-stage:
pre-commit install --hook-type pre-push
```

**Smoke test**: `tests/fixtures/recipe-smoke/pre-commit-stanza.yaml` validates this stanza as correct YAML with the required `repos`/`hooks` structure.

---

## Recipe 2: Git + Husky

**When it fires**: on `git commit` (pre-commit) or `git push` (pre-push), depending on the hook file.

**Prerequisites**: `npm install --save-dev husky` and `nwave-ai` on PATH.

Initialize husky once:

```bash
npx husky init
```

Add a pre-commit hook file at `.husky/pre-commit`:

```bash
#!/usr/bin/env sh
. "$(dirname -- "$0")/_/husky.sh"

# Validate any staged feature-delta.md files
git diff --cached --name-only --diff-filter=ACM | grep 'feature-delta\.md' | while read f; do
  nwave-ai validate-feature-delta "$f" || exit 1
done
```

For push enforcement instead of commit enforcement, create `.husky/pre-push` with the same body.

---

## Recipe 3: Git + Lefthook

**When it fires**: on `git commit` (pre-commit) or `git push` (pre-push).

**Prerequisites**: [lefthook](https://github.com/evilmartians/lefthook) installed and `nwave-ai` on PATH.

Add to `lefthook.yml`:

```yaml
pre-commit:
  commands:
    validate-feature-delta:
      glob: "docs/feature/**/feature-delta.md"
      run: nwave-ai validate-feature-delta {staged_files}
      stage_fixed: false

# For push enforcement instead:
# pre-push:
#   commands:
#     validate-feature-delta:
#       glob: "docs/feature/**/feature-delta.md"
#       run: nwave-ai validate-feature-delta {staged_files}
```

Install the hooks after editing:

```bash
lefthook install
```

---

## Recipe 4: GitHub Actions

**When it fires**: on pull request (paths filter) and/or push to main/master. Optionally on a schedule.

**Prerequisites**: `nwave-ai` installable via pip in the runner environment.

Create `.github/workflows/feature-delta.yml`:

```yaml
name: Feature Delta Validation

on:
  pull_request:
    paths:
      - 'docs/feature/**/feature-delta.md'
  push:
    branches: [main, master]
    paths:
      - 'docs/feature/**/feature-delta.md'
  schedule:
    - cron: '0 6 * * 1'   # every Monday at 06:00 UTC (optional nightly/weekly scan)

jobs:
  validate-feature-delta:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install nwave-ai
        run: pip install nwave-ai

      - name: Validate feature deltas
        run: |
          find docs/feature -name "feature-delta.md" | while read f; do
            nwave-ai validate-feature-delta "$f" --enforce
          done
```

For JSON output piped to a downstream step, add `--format=json` and capture stdout:

```yaml
      - name: Validate (JSON output)
        id: validate
        run: |
          nwave-ai validate-feature-delta docs/feature/my-feature/feature-delta.md \
            --format=json > /tmp/delta-report.json || true
          cat /tmp/delta-report.json
```

**Smoke test**: `tests/fixtures/recipe-smoke/github-actions-workflow.yaml` validates this workflow as correct YAML with the required `jobs`/`steps` structure.

---

## Recipe 5: GitLab CI

**When it fires**: on merge request events and/or push to protected branches.

**Prerequisites**: `nwave-ai` installable via pip in the CI image.

Add to `.gitlab-ci.yml`:

```yaml
validate-feature-delta:
  stage: validate
  image: python:3.11-slim
  script:
    - pip install nwave-ai
    - |
      find docs/feature -name "feature-delta.md" | while read f; do
        nwave-ai validate-feature-delta "$f" --enforce
      done
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
      changes:
        - docs/feature/**/feature-delta.md
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
      changes:
        - docs/feature/**/feature-delta.md
```

For JSON artifacts, add:

```yaml
  artifacts:
    when: always
    paths:
      - delta-report.json
    reports:
      junit: delta-report.json
```

---

## Recipe 6: Jenkins

**When it fires**: as a stage in a Declarative Pipeline (PR builds, main branch builds, or scheduled runs).

**Prerequisites**: `nwave-ai` installable via pip in the agent environment or Docker image.

Add to `Jenkinsfile`:

```groovy
pipeline {
    agent { label 'python' }

    stages {
        stage('Validate Feature Deltas') {
            steps {
                sh '''
                    pip install --quiet nwave-ai
                    find docs/feature -name "feature-delta.md" | while read f; do
                        nwave-ai validate-feature-delta "$f" --enforce
                    done
                '''
            }
        }
    }
}
```

For JSON output saved as an artifact:

```groovy
        stage('Validate Feature Deltas (JSON)') {
            steps {
                sh '''
                    pip install --quiet nwave-ai
                    nwave-ai validate-feature-delta docs/feature/my-feature/feature-delta.md \
                        --format=json > delta-report.json || true
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'delta-report.json'
                }
            }
        }
```

---

## Recipe 7: CircleCI

**When it fires**: on every workflow run for the specified branch or tag filters.

**Prerequisites**: a Docker image with Python, or an orb that provides pip.

Add to `.circleci/config.yml`:

```yaml
version: 2.1

jobs:
  validate-feature-delta:
    docker:
      - image: cimg/python:3.11
    steps:
      - checkout
      - run:
          name: Install nwave-ai
          command: pip install nwave-ai
      - run:
          name: Validate feature deltas
          command: |
            find docs/feature -name "feature-delta.md" | while read f; do
              nwave-ai validate-feature-delta "$f" --enforce
            done

workflows:
  feature-delta:
    jobs:
      - validate-feature-delta:
          filters:
            branches:
              only: [main, /feature\/.*/]
```

---

## Recipe 8: Bitbucket Pipelines

**When it fires**: on every push to the configured branches.

**Prerequisites**: a Docker image with Python available.

Add to `bitbucket-pipelines.yml`:

```yaml
image: python:3.11-slim

pipelines:
  default:
    - step:
        name: Validate Feature Deltas
        script:
          - pip install nwave-ai
          - |
            find docs/feature -name "feature-delta.md" | while read f; do
              nwave-ai validate-feature-delta "$f" --enforce
            done

  branches:
    main:
      - step:
          name: Validate Feature Deltas (enforce)
          script:
            - pip install nwave-ai
            - |
              find docs/feature -name "feature-delta.md" | while read f; do
                nwave-ai validate-feature-delta "$f" --enforce
              done
```

---

## Recipe 9: Makefile

**When it fires**: when a developer or CI job runs `make check-feature-delta`.

**Prerequisites**: `nwave-ai` on PATH, GNU Make available.

Add to `Makefile`:

```makefile
# nwave-ai feature-delta enforcement target.
# Usage: make check-feature-delta
#        make check-feature-delta FEATURE_DELTA=docs/feature/my-feature/feature-delta.md

FEATURE_DELTA ?= feature-delta.md

.PHONY: check-feature-delta
check-feature-delta:
	nwave-ai validate-feature-delta $(FEATURE_DELTA)
```

Run:

```bash
make check-feature-delta
# or target a specific file:
make check-feature-delta FEATURE_DELTA=docs/feature/my-feature/feature-delta.md
```

**Smoke test**: `tests/fixtures/recipe-smoke/Makefile.recipe` dry-runs via `make -n check-feature-delta` to confirm the target parses and invokes `nwave-ai`.

---

## Recipe 10: VS Code On-Save

**When it fires**: when you save a `feature-delta.md` file inside VS Code.

### Option A: Run on Save Extension

Install the [Run on Save](https://marketplace.visualstudio.com/items?itemName=emeraldwalk.RunOnSave) extension, then add to `.vscode/settings.json`:

```json
{
  "emeraldwalk.runonsave": {
    "commands": [
      {
        "match": "docs/feature/.*feature-delta\\.md$",
        "cmd": "nwave-ai validate-feature-delta '${file}'",
        "runIn": "terminal"
      }
    ]
  }
}
```

### Option B: VS Code Tasks (no extension required)

Add to `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Validate feature-delta",
      "type": "shell",
      "command": "nwave-ai validate-feature-delta '${file}'",
      "presentation": {
        "reveal": "always",
        "panel": "shared"
      },
      "problemMatcher": []
    }
  ]
}
```

Trigger manually with `Terminal > Run Task > Validate feature-delta` while the feature-delta.md file is open.

---

## Recipe 11: Manual One-Liner

**When it fires**: whenever you choose to run it.

**Prerequisites**: `nwave-ai` on PATH (`uv tool install nwave-ai`, or `pipx install nwave-ai` as a fallback).

```bash
# Validate a single file
nwave-ai validate-feature-delta docs/feature/my-feature/feature-delta.md

# Validate all feature-delta files in the repo
find docs/feature -name "feature-delta.md" | xargs -I{} nwave-ai validate-feature-delta {}

# JSON output (machine-parseable, exit 1 on violations)
nwave-ai validate-feature-delta docs/feature/my-feature/feature-delta.md --format=json

# Enforce mode (exit 1 on violations, error prefix [FAIL])
nwave-ai validate-feature-delta docs/feature/my-feature/feature-delta.md --enforce
```

No automation. No hooks. No CI configuration. `nwave-ai validate-feature-delta` works anywhere Python is installed. Users with no Git, no GitHub, and no CI server are first-class.

---

## Recipe 12: Mercurial hgrc

**When it fires**: on `hg commit` or `hg push` via the `changegroup` or `pretxncommit` Mercurial hooks.

**Prerequisites**: `nwave-ai` on PATH and Mercurial >= 4.0.

Add to `.hg/hgrc` (repository-local) or `~/.hgrc` (user-wide):

```ini
[hooks]
# Run before each commit is finalized (pretxncommit fires once per commit)
pretxncommit.validate_feature_delta = python:hgext.validate_feature_delta.hook

# Alternative: pure shell invocation via changegroup (fires once per push)
# changegroup.validate_feature_delta = /bin/sh -c 'find docs/feature -name "feature-delta.md" | xargs -I{} nwave-ai validate-feature-delta {}'
```

For a simpler shell-only hook (no Python extension needed):

```ini
[hooks]
pretxncommit.validate_feature_delta = /bin/sh -c 'find docs/feature -name "feature-delta.md" | xargs -I{} nwave-ai validate-feature-delta {} || exit 1'
```

This fires on every local commit and blocks it if any feature-delta.md fails validation.

---

## Choosing the Right Recipe

| Situation | Recommended recipe |
|-----------|-------------------|
| Git + Python tooling already in use | [Recipe 1: pre-commit](#recipe-1-git--pre-commit-framework) |
| Node.js project with husky | [Recipe 2: husky](#recipe-2-git--husky) |
| GitHub-hosted project | [Recipe 4: GitHub Actions](#recipe-4-github-actions) |
| GitLab-hosted project | [Recipe 5: GitLab CI](#recipe-5-gitlab-ci) |
| Jenkins-based CI | [Recipe 6: Jenkins](#recipe-6-jenkins) |
| CircleCI | [Recipe 7: CircleCI](#recipe-7-circleci) |
| Bitbucket | [Recipe 8: Bitbucket Pipelines](#recipe-8-bitbucket-pipelines) |
| Make-based project | [Recipe 9: Makefile](#recipe-9-makefile) |
| VS Code-only workflow | [Recipe 10: VS Code on-save](#recipe-10-vs-code-on-save) |
| No automation at all | [Recipe 11: Manual](#recipe-11-manual-one-liner) |
| Mercurial repository | [Recipe 12: Mercurial hgrc](#recipe-12-mercurial-hgrc) |
