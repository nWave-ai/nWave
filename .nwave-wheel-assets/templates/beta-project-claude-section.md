## nWave (beta) — How to Work in This Project

{{DELIVERY_ROUTE_FRAGMENT}}

nWave is a spine-driven delivery framework. Wave commands (`/nw-*`) carry the
gates; skills carry on-demand knowledge; agents execute. This section is an
INDEX.

Human authority decides genuine scope/trade-offs.

| User wants... | Load / run |
|---|---|
| Validate a problem is real | `/nw-discover` |
| Compare solution directions | `/nw-diverge` |
| Clarify jobs, journeys, outcomes | `/nw-discuss` |
| Architecture, reuse, boundaries | `/nw-design` |
| Deployment / operational constraints | `/nw-devops` |
| Executable public oracle | `/nw-distill` |
| Dispatch one Request | `/nw-deliver` |
| Fix one observed defect | `/nw-bugfix` |
| Review an artifact or diff | `/nw-review` |
| Reduce a noisy test suite | `/nw-optimize-tests` |
| Explicit mutation probe | `/nw-mutation-test` |
| Resume after an interruption | Read-only: `git worktree list`, then `lanes/<feature>/docs/feature/<feature>/handoff.json` and skill `nw-nwdes` |
| Run several lanes in parallel | skill `nw-swarm` |
| Fuller S/M/L evidence, splitting a Request | skill `nw-auto` |
| Anything else — methodology, routing, "what do I do" | skill `nw-buddy` |

{{TOOL_BATCHING_FRAGMENT}}

{{QUESTION_FORMAT_FRAGMENT}}

### Communication

<!-- GENERATED:communication-rules START — source of truth: nwave_ai.platform.config.NWaveConfig.effective_config() (ADR-CFG-001 Slice 2 -- ~/.nwave/config.json + .nwave/config.json); do not hand-edit (docgen renders this region) -->
- Communication verbosity: **standard**
<!-- GENERATED:communication-rules END -->

### Privacy — Non-Negotiable

nWave stores workflow data locally and collects no telemetry. Jev, a remote question service, is on by default for supported questions and sends only permitted data classes; refuse it with `--jev unauthorized` or `"jev": "unauthorized"` in `~/.nwave/config.json`. `TYPESAFE_API_KEY` is only Jev's technical prerequisite, not its authorization ([PRIVACY.md](../../PRIVACY.md)). Feedback via GitHub Issues is welcome, never required.
