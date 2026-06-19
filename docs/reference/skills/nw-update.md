# nw-update

Queues a deferred self-update of nwave-ai. Writes a PendingUpdateFlag that the SessionStart hook replays on the next Claude Code launch, so the current session is not interrupted. Falls back to manual instructions when the package manager cannot be detected.

**Source:** [SKILL.md on GitHub](https://github.com/nWave-ai/nWave/blob/main/nWave/skills/nw-update/SKILL.md)
