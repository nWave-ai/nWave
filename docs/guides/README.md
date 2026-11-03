# nWave Guides

User-facing documentation, organized by the four
[Divio documentation types](https://docs.divio.com/documentation-system/). Each
type serves a different need — pick the one that matches what you're trying
to do right now.

| Type | When to use it | Index |
|------|----------------|-------|
| **Tutorials** | You are learning nWave and want a guided, hands-on lesson | [Tutorials →](./TUTORIALS.md) |
| **How-To Guides** | You have a specific job to do and want a recipe | [How-To Guides →](./HOW-TO.md) |
| **Reference** | You need precise specs for a verb, command, skill, agent, or config key | [Reference →](./REFERENCE.md) |
| **Explanation** | You want to understand *why* nWave works the way it does | [Explanation →](./EXPLANATION.md) |

---

## For your assistant

`nwdes` is your assistant's tool, not a command you type. It gives an LLM a
deterministic delivery route: the tool itself builds each step — the handoff,
role prompts, output schemas and packets — from typed values, so a wrong state
cannot be written. It makes no model calls and enforces no gates. You talk to
your assistant, point it at the right guide, and decide scope and trade-offs.
The `nwave-ai` command line (`install`, `doctor`, `attribution`, backup and
restore) is the person's tool.

To start a delivery, paste this sentence to your assistant:

```text
Use your nw-nwdes skill if you have it, otherwise read https://github.com/nWave-ai/nWave/blob/main/docs/guides/nwdes/deliver-feature.md, then run its nwdes steps for me; ask me only for scope and trade-off decisions.
```

After `nwave-ai install`, a fresh assistant session can use nWave and nwdes on
its own on the hosts that receive nWave's skills and agents:

| Hosts | A fresh session finds nwdes by itself? |
|---|---|
| Claude Code, OpenCode, OMP | Yes — skills, agents and `/nw-*` commands are installed on the host |
| Codex | Yes — skills and agents are installed; Codex has no `/nw-*` commands |
| Devin | Partly — skills only; ask your assistant about the installed `nw-` skills |
| Cursor, Copilot | No — hooks only; point your assistant at the guide each session |

A person runs an `nwdes` command on purpose in three places: the `nwdes --help`
check after install, the [First feature with nwdes](./tutorial-nwdes-first-feature/)
lesson (typed by hand once, to learn the command flow), and the terminal
fallback on Cursor and Copilot.

---

**New to nWave?** Read [What's new in v4](./whats-new-v4/) for a short map
of how delivery works now, walk the safe
[First feature with nwdes](./tutorial-nwdes-first-feature/) lesson in a
throwaway repository, then run real work with the
[Deliver a feature](./nwdes/deliver-feature.md) how-to. Terms you meet along
the way are defined in the [glossary](./glossary.md).

**Coming from 3.x?** Follow [Migrate from nWave 3.x](./migrating-from-3x.md).
