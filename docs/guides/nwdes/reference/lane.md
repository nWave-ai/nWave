# lane

Run every nwdes command from the top level of the checkout; lane actions resolve the main project worktree. All actions take `--feature` (ID naming lanes/ID and lane/ID). Git 2.38 or newer and a declared `lanes.trunk` are required.

Lanes are optional for an isolated checkout or single bugfix. Without a lane, work and commit in the current clean checkout; no lane-free flag or lane command is required.

When using a lane, run lane open from the main worktree, then enter the lane's top level and run feature new. Every product, design, slice, expectations, acceptance and examiner application writes there, never to trunk:

```sh
ROOT=$PWD
LANE="$ROOT/lanes/search"
nwdes lane open --feature search
cd "$LANE"
nwdes feature new --feature search --request 'Search' --size M --value 'Find'
```

Commit deliberately through the host's existing lifecycle, then compose before whole-candidate review. Retain compose's EXPECTED/CANDIDATE identities; review, public examination and integration refer to that same candidate. A changed candidate or trunk requires the host to reassess affected evidence, not reuse another candidate's verdict.

| Action | Additional options | Result |
|---|---|---|
| `lane open` | None | Opens a worktree at trunk or reports the existing lane |
| `lane compose` | None | Merges trunk into the lane; prints EXPECTED and CANDIDATE full commit IDs |
| `lane rekey` | `--key` ADR key added by this lane | Renumbers an ADR using a number free on both sides |
| `lane integrate` | `--expected` and `--candidate` full IDs printed by compose | Fast-forwards trunk, deletes declared disposable files and removes the lane without force |

Common refusals: MissingFact, PartInvalid, ConfigurationMalformed, LaneOutsideProject, GitUnavailable, LaneTrunkUndeclared, DanglingReference.

| Action | Additional refusals |
|---|---|
| open | LaneOccupied |
| compose | LaneUncommitted, AdrKeyTaken, MergeConflict, AdrKeyClash |
| rekey | InconsistentFacts, AdrKeyClash, AdrForeignLayout, FeatureUnknown, HandoffInvalid, DestinationInvalid, AssetMissing, AssetUnreadable |
| integrate | NotOnTrunk, TrunkDirty, TrunkMoved, NotFastForward, LaneNotMerged, LaneUncommitted, LaneFileUndeclared |

Integration reports all admission problems in one pass before effects. Trunk must equal EXPECTED or CANDIDATE, CANDIDATE must descend from EXPECTED, and every lane commit must be contained in CANDIDATE. It deletes paths classified by project-defined `lanes.disposable` patterns and removes the worktree and branch without force. There are no built-in disposable patterns.

Only for files intentionally safe to delete, merge `{"lanes": {"disposable": ["PATTERN"]}}` into `ROOT/.nwave/config.json`, where ROOT is the main worktree passed as `--repo-root`. Preserve other settings, `lanes.trunk` and existing disposable patterns. Each list entry is a deliberate matching lane-worktree-relative POSIX path pattern, not a path prefixed with `lanes/FEATURE`; use separate entries for additional patterns. An exact reported lane-relative path can be used deliberately. This is not Git-ignore syntax.

A disposable declaration authorizes deletion, not merely ignoring a file. Preserve user work outside the lane, or commit project files and compose again. If a disposable declaration changes trunk, commit it and compose again before integrating. Never declare user work disposable merely to finish. After EffectFailed, correct its cause and rerun the same integrate command with the same EXPECTED and CANDIDATE; already integrated trunk and absent lane parts are skipped. If trunk moved elsewhere, compose again.

See [Use lanes](../use-lanes.md).
