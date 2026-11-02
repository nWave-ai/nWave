# Experimental migration-decision bundle

> **Who this is for:** maintainers running an nWave release. It records how
> to package and attach the experimental migration-decision bundle to a
> transport release. Normal users can skip this page entirely.

Before dispatching the experimental publisher, create a directory containing
`decision.json` and every file named by its relative `{file, sha256}`
references: the candidate wheel, evidence, upgrade-proof record, checkpoint
documents, and their retained command or result bytes. Package that directory
without a parent directory as `experimental-migration-decision.zip`.

Create a transport release targeted at the exact candidate commit, then upload
the bundle. The `migration-evidence-` prefix is deliberately not a `v*` product
release tag, and that prefix is what keeps this record out of the product
release sequence.

```bash
TAG=migration-evidence-<candidateSHA>
gh release create "$TAG" --target <candidateSHA> --title "$TAG"
gh release upload "$TAG" experimental-migration-decision.zip
gh workflow run publish-experimental.yml --ref atdd_pure_staging \
  -f migration_decision_release_tag="$TAG"
```

The workflow downloads, safely extracts, and validates this exact bundle before
smoking the wheel and invoking the writer.

**Do not make it a draft.** This instruction said `--draft` until 2026-09-11
and described the draft as private transport. That was unworkable: a draft
carries no git tag and is invisible to a read-scoped token, so the publisher
answered `release not found` for a release that was present, tagged and
correct. The publisher reads the bundle with its own token, and
`contents: read` suffices for a published release.

The candidate wheel ships only the AST and TextSearch code-fact providers.
The source checkout's optional indexed provider and its generated index are
not public wheel assets. Check the built wheel, not only the source tree,
before attaching it to the decision bundle.
