# nw-lane-orchestrator

Runs one nwdes lane end to end for the root in the DELIVER wave. Launches the installed role agents, never does role work, reports to the root.

**Wave:** DELIVER
**Model:** inherit
**Max turns:** 200
**Tools:** Read, Glob, Grep, Bash, Task, SendMessage

## Preloaded skills

- [nw-nwdes](../skills/nw-nwdes.md) — nwdes routes and verbs for host-led delivery of a Request.
- [nw-role-invocation](../skills/nw-role-invocation.md) — KNOWLEDGE — how a wave entrypoint invokes its specialist: the real installed role definition, never a generic persona. Load when a wave delegates to a role.
- [nw-swarm](../skills/nw-swarm.md) — How a root LLM runs several nwdes lanes in parallel with one lane orchestrator per lane, on any host. Load when more than one feature or lane is open or about to be.
- [nw-throughput](../skills/nw-throughput.md) — Evidence-led orchestration for maximizing delivery throughput with independent fan-out, capacity-bounded local test runs, long runs batched off the box, and concise whole-value evidence.
