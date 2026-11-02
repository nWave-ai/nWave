---
name: nw-code-analysis-port
description: "KNOWLEDGE — resolve code facts (who-calls-X / where-defined-or-read / call-graph / change-scope / file-atoms) through the vendor-neutral CLI `code-fact`, degrading LOUD through bundled adapters (AST, TextSearch). Trigger: any time an agent designs, writes, analyzes, or reviews code or tests and needs a structural code fact."
user-invocable: false
---

# nw-code-analysis-port (KNOWLEDGE)

**Kind**: KNOWLEDGE (reference / discipline). Consulted whenever you need a fact about code. No forced sequence — load it, obey the resolution rule.

## TRIGGER

Any time you design, write, analyze, or review code or tests and need a code fact — who calls X, where Y is defined or read, the call graph, the blast-radius of a change, or what a file contains — resolve it **through the vendor-neutral `code-fact` CLI**, not ad-hoc grep.

## Public CLI — available now

The five-capability public stable core is wrapped in the production CLI:

```bash
code-fact query.callers-of SYMBOL --root ROOT
code-fact query.reads-of SYMBOL --root ROOT
code-fact query.never-wired SYMBOL --root ROOT
code-fact query.atoms-in-file --root FILE_OR_ROOT
code-fact query.adr-section ANCHOR --root ROOT
```

The CLI returns JSON: `{ provider, confidence, payload, index, coverage, trace }`. Agents consume that envelope and degrade LOUD; they never probe/install/select an analyzer themselves. `code-fact refresh --root ROOT` is the one explicit way to regenerate the index (see "Index snapshot, coverage and refresh").

## The resolution rule (one order, every time)

The CLI delegates to the best available bundled adapter. You report the answer tagged with which adapter answered.

The chain is walked top-down, highest declared precision first; the first provider covering the capability answers. The query's `trace` names the answering provider and scope. Do not duplicate a provider ranking in prose or infer precision from a familiar module name. What is stable, and all a consumer needs:

- AST gives `approx` confidence (structural, per-language) on any parseable target.
- grep / lexical search is the **last resort**, never the default. Reach for it only when AST cannot answer.

## DEGRADE-LOUD (never silent)

- Always state which adapter answered and at what confidence: `approx` | `binding-resolved` | `noisy`.
- If the answer came from **TextSearch (grep)**, announce the degradation AND its limits. Example: "AST unavailable → grep fallback (`noisy`): may include false positives, miss dynamic/indirect references, and conflate same-named symbols."
- Never silently let grep stand in for the port. A `noisy` answer presented as fact is the failure mode this skill exists to prevent.
- The CLI's `trace` array names which provider answered and its scan-scope honesty (`complete` | `filtered` | `unfiltered`) — that per-query record is the loud announcement a gate reads.

## Operations quick-reference (question → CLI command)

| Code fact you need | CLI command | Stable |
|--------------------|-------------|--------|
| Who calls X? | `code-fact query.callers-of SYMBOL --root ROOT` | yes |
| Where is Y read / referenced? | `code-fact query.reads-of SYMBOL --root ROOT` | yes |
| Is this symbol defined-but-never-wired/used? | `code-fact query.never-wired SYMBOL --root ROOT` | yes |
| What atoms (defs/symbols) does this file contain? | `code-fact query.atoms-in-file --root FILE_OR_ROOT` | yes |
| What does an ADR / design-prose section say? | `code-fact query.adr-section ANCHOR --root ROOT` | yes |
| Call graph / change-scope / scope-delta | **unsupported by stable CLI** — use bounded stable queries + manual inspection with explicit limitation note | no |

The five stable-core capabilities answer on any UTF-8 repository, including repositories without Python: textsearch supplies the lexical floor at `noisy` confidence. A capability with no covering adapter returns no answer (none faked), records the honest failure in `trace`, and the work proceeds — do NOT substitute grep and call it the same fact.

## Index snapshot, coverage and refresh

A query never writes a file and never regenerates anything. Every answer states where it was read from and what that source covers:

- `index` is `{ "kind": "present", graph_sha256, manifest_sha256, indexed_files }` when a paired code index answered, or `{ "kind": "live-source" }` when the answer was read from live sources (no index, or an index no refresh has paired).
- `coverage` is `{ missing, stale, empty_unindexed }`: non-empty files in scope the index never recorded, files whose recorded modification time differs from the live one, and 0-byte files absent from the index. The lists are complete and sorted, matched by exact path (never by a shared file name). An empty unindexed file is reported but never makes an answer indeterminate.
- When the index claims a capability and `missing` or `stale` is non-empty, the CLI prints `{ "resolution": "indeterminate", uncovered, index, coverage, trace }` and exits 1. `uncovered` is exactly `missing` plus `stale`. No lower tier answers in its place. Do NOT treat it as an answer, and do NOT treat an empty result as "none": say which files are uncovered.
- To regenerate the index, run `code-fact refresh --root ROOT`. It prints `{ "refresh": "refreshed", index, coverage }` and exits 0; `refused` (index unchanged) or `indeterminate` (naming the changed index files) exit 1 with a reason. It is the only command that regenerates, it needs the indexing tool on PATH, and refuses without it.

## Invocation — how to use the CLI

For ANY structural code fact, call the CLI directly:

1. **Stable-core queries** — use `code-fact query.<capability>` with the exact form above.
   - The CLI parses JSON and emits it; consume the `provider`, `confidence`, and `payload` fields.
   - Inspect `trace` for the answering provider + scan-scope honesty (AST unavailable → TextSearch fallback).
2. **Beyond the five capabilities** — feature-level change-scope / call-graph analysis has no stable CLI today.
   Say so and take the fallback: bounded stable queries (e.g. `query.callers-of` per known seams) + manual inspection + explicit limitation note.
3. **Bundled additive tools** — `code-fact find-similar-responsibility --scope ROOT --name NAME` locates similar responsibilities; `code-fact impacted-tests PATH... --root ROOT` reports test reach. Neither requires selecting an external provider.

Tag every answer with provider + confidence (`approx` | `binding-resolved` | `noisy`). Defaulting to grep/Read for a structural fact (callers/reads/never-wired/atoms) is the anti-pattern this skill exists to prevent — CLI first, grep last.


## WHY through the CLI, not grep

- **Structural vs lexical.** AST is structural and reports `approx` confidence; TextSearch (grep) is lexical and reports `noisy` confidence. grep over-reports (same-named symbols, comments, strings) and under-reports (dynamic/indirect refs).
- **Confidence is carried, not assumed.** Every answer comes back in a `{provider, confidence, payload, index, coverage, trace}` envelope. The confidence label is the honesty signal — a consumer can see whether a fact is `approx`, `binding-resolved` or `noisy` — and `index` and `coverage` say which snapshot it was read from and which files that snapshot covers.
- **`reason_code` disambiguates** `live-non-callable` from `absent` inside a capability's own `payload` (e.g. `query.never-wired`) — a distinction grep cannot make. Degrade signals — which adapter answered, and its scan-scope honesty — live in the envelope's `trace`: per-query entries carrying `provider_id`, `event`, `fault_count` and `scope`.
- **One seam, no per-task `import ast`.** Re-deriving a fact through one honest provider beats each agent hand-rolling its own search.

## Implementation ownership

`src/codefact/model.py` owns the envelope and the provider port: each provider record declares its id, a cover function returning an answer capability, stale coverage or a pass, and an answer function returning a reply or fault. `src/codefact/fold.py` owns resolution over the single provider tuple composed in `src/codefact/shell/cli.py`. Each provider reads immutable snapshots. The index-backed provider admits an index only when its pairing record contains exactly `graph_sha256` and `manifest_sha256`, matching the bytes read. Filesystem and refresh effects belong only to `src/codefact/shell/`. The public wheel binds only the AST and text-search providers: answers name their provider and carry approx or noisy confidence. It binds no code index, so refresh refuses with a reason explaining that there is nothing to regenerate and queries answer from live sources.

## Scope note

This complements — it does NOT replace — reading the code and tests. Use the port to LOCATE facts (callers, definitions, references, atoms) precisely; then read the located code to understand it. The port answers "where / who / what", not "is this correct".
