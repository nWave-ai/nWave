---
description: Runs a step-recorded delivery from init to briefs.
argument-hint: '[interactive] [request or request-file]'
---
# NW-DYNAMIC

Dynamic mode: one executor agent delivers one Request end to end, recording each
step through the `nwstep` tool. The steps are oracle, design, model, craft,
refactor, probe, selfreview, handoff and examine. The public oracle comes
before code. You are the host: you prepare the run and relay; you do not do the executor's work.

## Argument

- First word `interactive` selects interactive mode; anything else selects auto mode.
- The rest is the request text or the path of a request file.
- No request given: ask the person for it in one question, then continue.

## Procedure

1. Find the tool: `command -v nwstep`. If it is missing: WHAT, the tool is not
   installed for this machine; WHY, the nWave installation does not provide it on
   the PATH; HOW, reinstall nWave with pip, open a new shell and check again.
2. Workspace: pick a new directory under `$HOME/.cache/nwave/nwstep-runs/`. Never
   create it inside the project. A request given as text goes to a file there.
3. From the project root (git on the PATH; the pre-feature baseline is the commit
   at `HEAD`), run `nwstep init --schema dynamic-v11 --workspace <dir> --mode <mode>`.
   `dynamic-v11` is a schema name nwstep ships; it needs no path.
4. Run `nwstep prompt --workspace <dir> --root <project root> --request <file> --mode <mode>`.
   It prints the executor prompt. Keep specifics in the request file, not in the prompt.
5. Give the printed text, unchanged, to ONE executor agent: the nWave crafter
   agent, or the functional crafter when the project paradigm is functional.
   Do not edit or summarise it.
6. The executor records its steps with `nwstep`. `nwstep status --workspace <dir>`
   shows progress; `nwstep brief --kind summary --workspace <dir>` renders the summary.

## Readable output (interactive mode only)

Before step 4, read `documents.readable_brief` from the project `.nwave/config.json`,
then the global `~/.nwave/config.json`; the project value wins. When neither file declares
it, the built-in default is enabled in `en`. Skip this section in auto mode and when the
resolved `enabled` is not true. When it is true, append this to the request file, with the
language from the setting:

```text
Readable output is on, language <language>. Before you record a decision or a diagram,
read the skills nw-diagram and nw-doc-as-artifact. Write each decision as a title of
at most 8 words, a colon, then the reason. Draw each diagram under the rules R1-R12.
```

When the executor has recorded the design step, ask the nWave documentarist agent for
ONE round: it reads the request file and the workspace records and returns numbered
questions, each citing a decision id or a diagram. Relay them to the executor in one
message. The executor answers once, by recording the correction at its source and citing
the id. Run no second round. The documentarist presents decisions; it records none.

## Sizes and pauses

A delivery declares its size before its first record: `nwstep size --workspace <dir> --size S|M|L --why '<one sentence>'`. The size decides which steps are due, and `nwstep status` shows the size and the steps it skips.

| Size | Steps due |
| --- | --- |
| S | oracle, craft, selfreview, handoff |
| M | oracle, design, craft, selfreview, handoff |
| L | oracle, design, model, craft, refactor, probe, selfreview, handoff, examine |

A step the size does not make due is refused with what, why and how. Closing (handoff in S and M, examine in L) is refused while a due step is not recorded, and the refusal names the missing steps. A size can be raised at any time. Lowering needs `--owner-note` and `--author`, the owner's note and id, and the status keeps both. The selfreview step needs an independent review item (`independent_review`) in every size, so no delivery closes without one. In M and L it also needs the seventeen review answers; in S the independent review item alone is the whole self-review.

A workspace made from `dynamic-v9` or `dynamic-v10` has no sizes: every step is due, `size` is refused, and its records are unchanged.

## Interactive mode

Interactive mode asks the person at pauses only: size M after oracle and design, size L after oracle, design, craft and examine, and size S never. While the workspace waits, `nwstep status` prints `awaiting person after '<step>': <question>`, and no record of the next step is accepted until the person answers with `nwstep answer --workspace <dir> --author <id> --text '<answer>'`. The answer keeps its text and the id of the person who gave it. Relay each question to the person in one message: context, your recommendation, the options each with its consequence, and one direct question, in plain language and without step codes. Steps without a pause go on without stopping. Never answer for the person.

## Auto mode

No pauses. The executor decides, records each decision and says so.

## Review: what a verdict is worth

Before a review, run `nwstep packet --workspace <dir> --root <project root>`. It prints
the review packet: the identity of the candidate (the change as it is now), the base
commit, the stale steps, any earlier verdict, and the command that records a verdict.
Give the packet to the reviewer.

- The identity is `commit:<hash>` when everything is committed. With uncommitted
  changes, or in a project without git, it is `tree:<digest>`, a digest of the files,
  and the tool prints a warning that says so.
- The reviewer records the decision with
  `nwstep verdict --reviewer <id> --candidate <identity> --outcome <accepted|rejected>`.
- A verdict holds for that identity only. If the candidate changes afterwards, the tool
  refuses a verdict that names the old identity, and status shows the earlier verdict as
  not holding for the new candidate. Run `packet` again and ask for a new verdict.

## Rework: how a review finding is corrected

A finding does not start a new delivery. It is corrected in the same workspace, with
the same base.

1. Record the finding with the case that shows it:
   `nwstep finding --author <id> --text <what is wrong> --red <one command> --root <project root>`.
   The tool runs the command now. It must fail; a command that passes, or cannot start,
   is refused. The workspace keeps the author, the text and the failing run. If the case
   was written wrong, record the finding again with the same author, the same text and
   the corrected case: both records are kept and only the corrected case has to pass.
2. The implementation step and the steps after it are now stale. The steps before it
   (the tests of the request, the design, the model) are not.
3. Correct the code until the case passes. Commit.
4. Run `nwstep replay --workspace <dir> --root <project root>`. It records again only the
   stale steps, from their kept submissions. The record of the implementation step runs
   the case of every open finding: all pass and all findings close in that one record,
   or the record is refused and nothing closes.
5. A step marked as a verdict in the schema (in `dynamic-v10`, the examine step) is never
   recorded again by a replay: it stays stale until the examiner records it again for
   the new candidate.
6. Run `packet` again and ask the reviewer for a new verdict.

After a verdict, the corrections enter one delta: when that delta is closed, a further
finding is refused until a new verdict is recorded for the new candidate. Record every
finding of a review before the replay that closes them.

## Limits

- `nwstep` does not check who wrote an independent review, who records a verdict or who
  reports a finding: the ids are kept as given. The selfreview step has an optional field
  for an independent review. The examine step (after `handoff`) records an examiner's id
  and one line per fixed row; the tool does not check that examiner's identity, does not
  run the rows' checks, and does not enforce the examine level's repair rounds (the nwdes
  examination enforces them). When it matters, a person or another agent reviews the
  result independently.
- The tool does not check that a verdict was recorded before the handoff or the
  examination, and the examine step does not name the candidate it examined. What the
  tool enforces is narrower: a verdict is recorded only for the identity frozen last,
  while the candidate still has it.
- The tool reads the candidate when a command runs. A change made between two commands
  is seen by the next `packet` or `verdict`, not before.
- A `tree:` identity covers the files git lists (tracked and untracked, not ignored), or
  every file under the root when there is no git. It does not carry over to the commit
  made from those files: after the commit, run `packet` again.
- A finding cannot be withdrawn, and its text cannot be edited; only its case can be
  corrected, by the same author id with the same text. A finding recorded by mistake
  stays open until a case recorded for it passes.
- A change with no finding (a step simply recorded again) is not counted as a delta.
- A workspace created with `dynamic-v9` keeps working and can use `finding`, `packet`
  and `verdict`; its examine step is not marked as a verdict, so a replay records it
  again as before.
- After a delta, the refactor step may be refused by the replay when the commits it
  named are no longer the last ones: record that step again by hand.
- Not proven: two tool commands at the same moment on one workspace beyond the
  workspace lock, and a crash in the middle of a write. The protocol model is checked by
  bounded random simulation, which is not a proof.
- Recording the handoff of `dynamic-v10` runs, once each, the quick checks the project
  declares in `.nwave/prereview.json` (named commands, each a list of words started without
  a shell; optionally one remote verification command, requested once per committed
  candidate and told the commit in `NWAVE_CANDIDATE`). A check that does not exit 0 refuses
  the record; with no file the summary says `no checks declared`, which is not a pass. The
  checks run on the work tree as it is at that record: documents generated afterwards are
  not covered. A workspace initialised with an earlier schema runs none, and `nwdes` runs
  none: its reviewer runs the declared verification commands itself.
- In interactive mode the executor obeys the protocol by prose; no tool checks it.
- One workspace keeps its first mode; a later prompt with the other mode is refused.
- The tool prints the skill directories each step names: from `NWSTEP_SKILLS_ROOT` when
  set, else from `$HOME/.omp/agent/skills` when it exists, else from a built-in
  default path. Set `NWSTEP_SKILLS_ROOT` to the skills folder you work against when
  that is not the default, before running `nwstep prompt`.
- Only the host reads `documents.readable_brief`, and only in interactive mode. `nwstep`
  does not read it, so no tool checks that the executor follows the readable-output block.
- The size is kept as declared; the reason is not checked. A lowering keeps the owner's note and id as given; the tool does not check that the id is the owner's.
- Probe cases run on the pre-feature tree with the change's test files copied over it. A case whose test file is in neither tree is could-not-verify, and is shown as such, not as a difference.
- A commit that changes only documents (Markdown, or files under docs/) does not stale a refactor. A commit that changes code after the named refactor commits does, and `status` says so with the reason.
- The examine pause appears only once the examiner records the examine step; the run stops there.
- Not proven: two `size` or `answer` commands at the same moment on one workspace, and a crash inside the atomic write of the size or answer file. The formal model of the gate is checked by bounded random simulation, which is not a proof; each of its invariants has a mutant that yields a counterexample.
