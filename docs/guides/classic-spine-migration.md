# Updating an Existing Project

Use `nwave-ai update` to update the installed nWave package, then follow the
[3.x migration guide](migrating-from-3x.md) for the project compatibility boundary.

A delivery already in progress on v3 must finish on 3.22.2 or restart with
`nwdes feature new`. Updating the package does not convert a delivery's artifacts.
Preserve the original checkout, runtime and project files when finishing v3 work.
Completed execution logs remain historical records; do not rewrite them to make
them look like current handoffs.

For a new delivery, use the installed nwdes skill. Read its feature handoff and
rendered briefs to resume work; the builder does not maintain a workflow cursor.
