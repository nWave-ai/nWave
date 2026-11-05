## nWave (beta) — How to Work in This Project

{{DELIVERY_ROUTE_FRAGMENT}}

nWave is in **active development**.

DISCUSS/DESIGN resolve only real gaps. Human authority decides genuine scope/trade-offs.

Several lanes in parallel: skill `nw-swarm` (a host without skill loading reads its `SKILL.md` from the installed skills folder).

{{TOOL_BATCHING_FRAGMENT}}

{{QUESTION_FORMAT_FRAGMENT}}

### Privacy — Non-Negotiable

nWave stores workflow data locally and collects no telemetry. Jev, a remote question service, is on by default for supported questions and sends only permitted data classes; refuse it with `--jev unauthorized` or `"jev": "unauthorized"` in `~/.nwave/config.json`. `TYPESAFE_API_KEY` is only Jev's technical prerequisite, not its authorization. See [PRIVACY.md](../../PRIVACY.md) for the complete policy. Feedback on nWave itself is welcome via GitHub Issues on the experimental repo, at your discretion — never a required step of doing the work.
