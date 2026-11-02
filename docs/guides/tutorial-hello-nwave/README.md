# Tutorial: Hello nWave

Build and observe a deliberately small Python function: `render_banner("AB")` returns five rows of ASCII block letters. The agreed contract will support `A`, `B`, and spaces, return an empty string for empty input, and reject other characters with `ValueError`. This is an exercise in agreeing on an outcome before implementing it, not a promise to ship a full A–Z command-line program in five minutes.

## 1. Get the beta into a new project

You need Python 3.11+, [uv](https://docs.astral.sh/uv/), Git, and Claude Code or Codex CLI. In a terminal, install from a **local clone** of this repository:

```bash
git clone https://github.com/nWave-ai/nWave.git
cd nWave
uv sync
NWAVE_REPO="$(pwd -P)"
uv run python -m nwave_ai.cli install --platform claude-code
uv run python -m nwave_ai.cli doctor
```

For Codex, use `uv run python -m nwave_ai.cli install --platform codex` instead and check the installer's Codex-specific final validation; `doctor` checks Claude Code, not a Codex-only install. The beta has no published `nwave-ai` package, and `uv tool install .` does not currently carry every required framework asset. The checkout's CLI lives at `"$NWAVE_REPO/.venv/bin/nwave-ai"`; keep `NWAVE_REPO` in the same terminal when changing directories. Restart the chosen host after installing. Move to a permanent workspace **outside the nWave clone**:

```bash
cd /path/to/your/workspace
mkdir hello-nwave
cd hello-nwave
git init
printf '.venv/\n' > .gitignore
uv venv .venv
uv pip install --python .venv/bin/python pytest
"$NWAVE_REPO/.venv/bin/nwave-ai" project enable
"$NWAVE_REPO/.venv/bin/nwave-ai" status
```

On Windows, run this shell workflow in WSL2. Make sure status says `This project is active.` The marker is `.nwave/config.json` (`enabled: true`); `project enable` also repairs `.gitignore` so that marker can be tracked. Review these files before you commit. If you want optional project-level `CLAUDE.md`/`AGENTS.md` beta guidance, `project enable --yes` adds the managed sections; it is not required to activate the project.

## 2. Agree on the behavior

Launch `claude` from `hello-nwave` and enter this **inside Claude Code**, not the shell:

```text
/nw-discuss "Build a tiny Python banner function in banner.py: render_banner(text) returns five-row block letters for A, B, and spaces; empty input returns an empty string; unsupported characters raise ValueError. Help me choose the exact appearance of A, B, and spacing before implementation."
```

If using Codex, launch `codex` and invoke `$nw-discuss` with the same request. **Every** subsequent `/nw-...` command shown below is a Claude Code command; in Codex substitute the corresponding `$nw-...` skill. Read the reported DISCUSS brief and agree on a concrete `A`, `B`, and space example. Its location depends on scope and project configuration; a feature-scoped default is `docs/feature/<feature-id>/brief.md`, not the older `docs/feature/<feature-id>/discuss/user-stories.md`.

## 3. Resolve the small design

```text
/nw-design "For the agreed banner behavior, use one public render_banner(text) function in banner.py. Specify how each five-row glyph and inter-character spacing compose; reuse the project's Python and pytest setup."
```

Review the decision and actual path the command reports. For such a small function, avoid introducing a framework or claiming a system design is needed. If adequate architecture already exists in your own project, reuse it instead; DESIGN is about closing a real contract, not collecting documents.

## 4. Define the observation before code

```text
/nw-distill "Make the agreed A/B/space, empty-input, and invalid-character behaviors executable through the public banner function, using this project's pytest environment."
```

Inspect the resulting acceptance brief and test locator. Run the **reported** verification command with `.venv/bin/python` if necessary. Before delivery, expect RED for the specified behavior—not collection errors or a missing dependency. If the preimplementation run is broken instead of meaningfully RED, ask the host to repair its test infrastructure and inspect it again before proceeding.

## 5. Deliver, verify, and recover

```text
/nw-deliver "Implement the agreed render_banner behavior against the accepted public oracle in this project."
```

The host drives nwdes prompts and applies accepted role payloads; follow the actual results instead of expecting fixed minutes, commit counts or test filenames. Once it reports completion, run the acceptance verification command it reported and try the **public function** yourself:

```bash
.venv/bin/python -c 'from banner import render_banner; print(render_banner("AB"))'
```

Compare the five printed rows to the approved glyphs and spacing; also verify empty and invalid-input cases through the reported tests. If tests pass but the banner differs, correct the owning requirement, oracle or implementation and redeliver. If a command refuses or a session stops, retain the files and inspect the feature's handoff and briefs (`nwdes document`) before resuming. nwdes keeps no workflow cursor. `/nw-buddy` (Codex: `$nw-buddy`) can explain routing.

You have completed this tutorial only when the reported delivery is terminal **and** your own observation matches the agreed example. Next, [Your First Feature](../tutorial-first-feature/) applies the same sequence to an existing project.
