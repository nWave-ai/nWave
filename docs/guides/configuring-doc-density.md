# Documentation Detail and Wave-End Explanations

Document reading views and optional wave-end explanations serve different needs.
Neither changes a document's required sections, selects a provider/model or
weakens verification, review or examination. Ask the assistant directly for
a shorter or more detailed result when you need one.

## Local document views

nwdes renders full briefs and HTML pages. Use `nwdes document` to render the
feature documents and read the returned paths. The handoff and source briefs
remain the delivery record; a rendered page is a reading aid, not approval.

The former density-driven wave-end rendering route does not apply to nwdes.
Ask the assistant for a shorter or more detailed explanation without changing
the authoritative document.

`nwave-ai status` can report a configured density preference; it does not
control the nwdes renderer.

A project can also ask for a readable HTML brief for people at the charter and design closes, rendered by the nwdes renderer. That is the `documents.readable_brief` setting that `nwave-ai rigor --documents` writes. It is separate from the wave-end explanation below. See the [rigor entry](../reference/cli.md#nwave-ai-rigor).

When `documents.readable_brief` is enabled, `nwdes document` also renders the product page of each feature (`brief.html`) with its text outside code blocks: each non-blank line of the request, work and promises is one escaped paragraph. The page declares the `language` value as its `lang` attribute. The architecture and acceptance pages, and every markdown brief and the handoff, keep their current bytes. The page keeps the nWave style and logo and carries no date. With the setting absent or disabled, every page is unchanged. With `documents.html` false (see below) no HTML page is written, readable brief included, and the closing prompt does not ask for one.

Each Mermaid diagram in the product page declares its description as one `%% alt: <one sentence>` line inside its block. The page shows that sentence as a paragraph directly above a collapsed `Diagram source` block holding the Mermaid code. A diagram with no description, or with more than one, or with an empty one, refuses the whole `nwdes document` run and writes no file. So does a diagram with more than 25 distinct nodes, a provisional limit. Node counting covers `flowchart` and `graph` diagrams (distinct node identifiers), `C4Context`, `C4Container` and `C4Component` diagrams (element ids) and `sequenceDiagram` diagrams (participants); other diagram types are refused because their nodes cannot be counted. The count is a line tokenizer, not a Mermaid parser, so unusual syntax can miscount. Archived documents are not rewritten.

Set `"documents": { "html": false }` in `<repo>/.nwave/config.json` to stop generating every HTML page (feature and project); the markdown briefs and the handoff are unchanged. The default, absent or `true`, keeps the HTML pages.

`nwdes document --overview` writes the project overview to `docs/product/overview.md` and `overview.html`, next to the project brief that `nwdes document --product` writes; the brief is never written by `--overview`, and the reference in [document](nwdes/reference/document.md) lists both options. It joins the texts of `vision.md`, `roadmap.md` and `backlog.md` from the product directory and lists every decision file of the configured `adr.directory` with its title, the whole Status paragraph its own text states, and a link to the file. Only that command writes it; no other `nwdes document` run does. The command writes only those two files and refuses, writing nothing, when a product file is missing or blank or no decision file is found. It takes no `--feature` or `--handoff`. If the page cannot be written after `overview.md` was written, the run refuses naming only the page, and `overview.md` stays new until the next run, which brings both files current.

For the diagram rules and the documentarist's round of questions that go with the readable brief, see [Read architecture diagrams and the readable brief](readable-brief-and-diagrams.md).

## Wave-end explanation: `documentation.expansion_prompt`

`documentation.expansion_prompt` controls optional explanation in chat after
a completed wave. The installed assistant reads this preference from the
global `~/.nwave/config.json` at wave entry. If you set `NWAVE_AGENTS_HOME`,
use its `.nwave/config.json` instead. Project-level settings do not override
this global preference. No expansion offer follows a single operation, a
refused or indeterminate wave, or a stopped wave. There is no interactive CLI
menu or `--expand` flag.

### Choose the wave-end response

Add only the preference you want to change; no configuration file is needed
for the default:

```json
{
  "documentation": { "expansion_prompt": "ask-intelligent" }
}
```

| Value | After a completed wave |
|---|---|
| `ask` | Offer optional explanation. |
| `always-skip` | Do not offer explanation. |
| `always-expand` | Explain pertinent detail without asking first. |
| `smart` | Offer detail only for a concrete optional alternative, trade-off, risk, constraint, or deferred consequence in the result. |
| `ask-intelligent` | Use the `smart` condition and name at most two relevant topics; this is the default. |

An explicit `documentation.expansion_prompt` takes precedence over the
`rigor.profile` fallback. `rigor.profile` labels (`lean`, `exhaustive`) are not
guarantees of quality or coverage. `nw-rigor` configures provider/model pairs
through `model_runtime`; it does not set that profile, and a density or profile
never picks a model. You can ask directly for more detail at any time,
including with `always-skip`. A direct request does not change accepted
documents or run another delivery operation. The explanation offer and the HTML view are
separate: accepting or ignoring one does not affect the other.

`nwave-ai status` shows the resolved wave-end mode and its source without
writing files. An invalid explicit expansion value is refused before an
installation or a wave begins; correct the global value to one from the table.

See the [global configuration reference](../reference/global-config.md) for
the configuration cascade, and the
[feature format reference](../reference/feature-format.md) for document
sections.
