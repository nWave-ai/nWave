# packet

`packet` prints a readable review or examination packet.

| Option | Meaning |
|---|---|
| `--kind` | review or examine |
| `--handoff` | Input handoff file |
| `--diff` | Whole candidate change from the slice's base commit, including the approved oracle and supports; omitted means none; forbidden for examine |
| `--root-context` | Refused for examine |

Neither packet kind admits host observations. `--observation` and `--observation-file`, including `--name=value`, refuse with `SelfGatheredEvidence` before argument parsing or any named input read; abbreviations remain unknown arguments. Examine also refuses `--root-context` before workspace creation. Review packets have no Observations section, not even a None supplied line.

Reviewers record the observations they gather through `nwdes review observation add --text` or `--text-file`; those observations belong to the review run record, never the packet. See [review](review.md).

```text
nwdes packet --kind examine --handoff feature.handoff.json
```

Examination needs fixed expectations, not host observations. Its packet includes only public promises, slice observations and public oracles, the one optional Feature charter, fixed expectations and the examination workspace. It has no Observations section, source paths or private design records. The workspace section names its public document index and `nwdes examine read` and `nwdes examine probe` commands, and instructs the examiner to gather and record its own observations before citing them. The workspace contains a read-only projection of git-tracked `.md` and `.tmpl` files under `docs/guides`, `nWave/skills`, `nWave/templates` and `nWave/agents` at candidate HEAD, and initially empty scratch. It is outside the candidate checkout and the main worktree holding the git common directory; it contains no launcher or binding file. The charter appears once for the complete Feature, never per slice. Legacy per-slice charters are refused with guidance to the Feature charter producer. Review packets retain slice observations, targets, oracle/support paths, declared commands, public oracles and projected records, followed by the whole diff, with no host observations.

For candidate review, never exclude approved oracles or supports from the diff. Build the reviewer prompt with `--commit REV` naming clean lane HEAD. The final reviewer owns selection and sufficiency of the touched-file selected tests at that commit. It reuses a complete applicable native result (host, CI or the normal commit hook) whose source, test, argv and runtime inputs are unchanged, citing its original operator and run; it executes only missing or affected checks, once, and records complete native argv, exit status, stdout and stderr of each run it executes, including empty or incomplete selection and no selector found. Reuse never waives a check. Declared-command evidence is the host's live observation and is not repeated by the reviewer. Missing, unrun or failing evidence is a finding. nwdes stamps each review observation with the commit and cleanliness; it never selects or runs tests. The reviewer reads the packet, named evidence locators and installed skills and gathers evidence without candidate edits. Path aliases and repeated-fact references compact representation without changing supplied text; model internals remain in authority documents.
The path index groups equal directory prefixes, including nonconsecutive source paths; prepend a `Path prefix` to its indented suffixes, while unindented paths stand alone. Every alias keeps exactly one full path; target aliases retain their original change-kind/order. Each slice lists its governing shared D/K IDs; shared-record text stays in the named architecture document's `Shared records` section, which the reviewer reads via its file tool. Compact own-record labels stay outside prose fences; literal fences omit only the optional language hint, retaining collision-safe delimiters and original bodies.


The review packet names its nwdes-rendered acceptance document once and labels the row columns `locator/owner, covers, obligations`. Each slice cites its `### S<n>` section, then indexes every row by test ID or NotTested owner with that row's complete covers list and any obligation keys it binds. It does not copy stimulus, expected, user-result or NotTested-reason prose; the reviewer reads the cited sections with its own file tool. The CLI locates the acceptance document beside the supplied handoff; the pure review API may receive that handoff argument explicitly, otherwise it uses the canonical scoped destination.

Refusals include MissingFact, PartInvalid, HandoffInvalid, DanglingReference, InconsistentFacts, SelfGatheredEvidence, WorkspaceContaminated and InputUnreadable. Refusals emit no packet. Retired host-evidence flags and contamination exit **2**; unavailable git or workspace writes exit **1**.

See the actual examination packet in the [tutorial](../../tutorial-nwdes-first-feature/).
