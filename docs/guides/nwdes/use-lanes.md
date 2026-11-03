# Use feature lanes

**Audience.** The lane operations below are run by the root assistant — the session you talk to; it executes every `nwdes` verb and keeps the lane lifecycle. The person reads along, decides which work justifies a lane, and points the assistant at this guide — the sentence to paste is in [For your assistant](../README.md#for-your-assistant).

Use one lane per feature to isolate changes and integrate them without rewriting trunk. The prerequisites are Git 2.38 or newer, a committed project, and the intended trunk checked out in the main worktree.

An isolated checkout or single bugfix may run without a lane: work and commit in the current clean checkout and retain the same verification, review and examination obligations. There is no lane-free flag.

1. Set `lanes.trunk` in the project's nWave configuration to the actual trunk branch. Set `lanes.disposable` only for paths you are willing to delete. Patterns are project-defined; nwdes has no default disposable list. Do not classify notes or useful artifacts as disposable.
2. Invoke `lane open` from the main worktree's top level with the feature ID. Work in the reported `lanes/ID` worktree on branch `lane/ID`. The command excludes `lanes/` through `.git/info/exclude`.
3. Enter the lane's top level and run feature write commands there. Roots default to cwd and the repository root; lane verbs resolve the main worktree.
4. Commit authorized changes in the lane according to your project's policy. nwdes does not commit your feature for you.
5. Invoke `lane compose` from the checkout's top level with the feature ID. It merges trunk into the lane and prints EXPECTED and CANDIDATE commit IDs. Resolve conflicts in the lane. If two branches added different ADR bodies at one key, use `lane rekey` for the lane-added key, inspect and commit the result, then compose again.
6. Obtain one fresh independent final whole-candidate review of the composed candidate, before examination. The final reviewer runs the touched-file selector and selected tests once at CANDIDATE, reusing applicable unchanged observations with their original provenance. Host live RED/GREEN observations of declared commands are not repeated by the root; affected checks remain required, and a changed candidate needs new observations. Keep the exact EXPECTED and CANDIDATE IDs from that composition. If trunk moves, compose and review again; do not replace the expected value just to bypass refusal.
7. After the final review is accepted, obtain fresh public examiner verdicts on the same CANDIDATE. Resolve every unmet expectation before integrating.
8. Inspect remaining untracked and ignored lane files and preserve useful files before integration. Invoke `lane integrate` from the main worktree with the full EXPECTED and CANDIDATE IDs. It reports every admission problem before changing anything: tracked lane changes, an unmerged lane tip, undeclared files, dirty or off-branch trunk, moved trunk or a non-descendant candidate.
9. The same integrate command fast-forwards trunk, deletes only declared disposable paths, then removes the worktree and branch without force. After an effect failure rerun it with the same values; trunk already at CANDIDATE and absent lane parts are admitted. A moved trunk requires composing again.

**Done:** the final review and public examination accepted the same CANDIDATE, trunk contains it, and the integrated lane is removed without loss of undeclared files.

See [lane reference](reference/lane.md) for options and refusals.
