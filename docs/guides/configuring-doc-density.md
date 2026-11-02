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
