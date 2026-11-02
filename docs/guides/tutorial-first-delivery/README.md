# Tutorial: Your First Delivery

Deliver a small Python image-to-ASCII converter from a prepared P3 PPM fixture. This tutorial lets you inspect existing tests as **inputs to the conversation**, then work through DISCUSS → DESIGN → DISTILL → DELIVER until you can observe a converted image yourself. This beta does not promise a 13-minute run, a fixed number of commits, or a guaranteed outcome from one agent command.

## 1. Install locally and prepare the starter

You need Python 3.11+, Git, [uv](https://docs.astral.sh/uv/), and Claude Code or Codex CLI. There is **no published nWave package** in this beta. In a terminal, install from a local clone:

```bash
git clone https://github.com/nWave-ai/nWave.git
cd nWave
uv sync
NWAVE_REPO="$(pwd -P)"
uv run python -m nwave_ai.cli install --platform claude-code
uv run python -m nwave_ai.cli doctor
```

For Codex, use `uv run python -m nwave_ai.cli install --platform codex` instead and check the installer's Codex-specific final validation; `doctor` checks Claude Code, not a Codex-only install. The beta has no published package, and `uv tool install .` does not currently carry every required framework asset. Quit and reopen the chosen host after installation. Keep `NWAVE_REPO` in this terminal to use the checkout's **local** starter script from a permanent workspace outside the nWave clone:

```bash
cd /path/to/your/workspace
python3 "$NWAVE_REPO/docs/guides/tutorial-first-delivery/setup.py"
cd tutorial-ascii-art
"$NWAVE_REPO/.venv/bin/nwave-ai" project enable
"$NWAVE_REPO/.venv/bin/nwave-ai" status
```

Read the [local setup script](./setup.py) first if you want to inspect what it writes, or follow [manual setup](./manual-setup.md) instead. The script creates `tutorial-ascii-art/`, a virtual environment, a Git starter commit, and installs `pytest` with pip (so package network access may be required). It refuses to overwrite an existing directory unless you deliberately use `--force`—do **not** use that option to recover an interrupted delivery. Windows users should run this shell workflow in WSL2.

Confirm status says `This project is active.` `project enable` writes `.nwave/config.json` with `enabled: true` and updates `.gitignore` so the config can be tracked. Review these changes before committing. The optional `project enable --yes` also adds managed beta guidance to `CLAUDE.md`/`AGENTS.md` without prompting; it is not needed for activation.

## 2. Inspect what the starter actually says

The project starts with `src/ascii_art/__init__.py` empty, three tests in `tests/test_ascii_art.py`, and a 4×4 white-diagonal-on-black P3 fixture in `tests/fixtures/diagonal.ppm`. Inspect them and run:

```bash
.venv/bin/python -m pytest tests/ -v
```

These tests describe output width, allowed density characters, and bright/dark contrast. **Do not confuse their initial failure with a ready acceptance oracle:** the function is missing, so an import error is possible, and these starter assertions alone do not settle resizing, row count, or which edges are preserved. They are evidence to bring to nWave, not a pre-certified RED gate or a claim that the feature is complete once exactly three tests pass.

## 3. Agree on the request and design

Launch `claude` from `tutorial-ascii-art`; the following commands go **inside Claude Code**, not into a terminal. For Codex, launch `codex` and use `$nw-discuss`, `$nw-design`, `$nw-distill`, and `$nw-deliver` instead of the corresponding `/nw-...` Claude commands.

```text
/nw-discuss "Add image_to_ascii(path, width) for the supplied P3 PPM fixture. The output should use the density ramp ' .:-=+*#%@': bright pixels dense, dark pixels sparse. Treat the three starter tests as input; help me agree on row count, resize behavior, and invalid-file behavior before coding."
```

Review the actual DISCUSS brief reported by the host. Ask it to clarify anything untestable. Feature-scoped briefs normally begin under `docs/feature/<feature-id>/`, but project configuration can change the location.

```text
/nw-design "Reuse this project's Python package and pytest setup for the agreed P3 PPM converter. Resolve pixel sampling and public error behavior without introducing unnecessary image dependencies."
```

Review the reported design decisions. In particular, agree on what `width=4` and `width=20` mean for this 4×4 fixture; a text-art snapshot or row count cannot be inferred from the starter tests alone.

## 4. Turn the agreement into an executable oracle

```text
/nw-distill "Create a public-port acceptance oracle for the agreed P3 converter. Reconcile the three supplied starter tests with the agreed output and make the preimplementation test run meaningfully RED, not broken at import."
```

Open the acceptance brief and test locator the host reports. Run the exact verification command it reports using this project's `.venv` interpreter. If the run still fails only because of a missing symbol, unavailable dependency, or bad fixture, ask for a minimal RED-ready scaffold or corrected test infrastructure and run it again. Do not change expectations merely to get green; review any proposed change to the starter assertions against the agreed contract.

## 5. Deliver and see the result

```text
/nw-deliver "Implement the agreed P3 PPM image_to_ascii(path, width) behavior against the accepted public oracle in this project."
```

Follow the nwdes role results and the host's observed evidence rather than assuming a roadmap filename, a specific reviewer, a mutation score, or automatic resume. A successful apply or generated document alone is not proof of delivery. After the host reports completion, rerun its reported acceptance verification command and the starter suite:

```bash
.venv/bin/python -m pytest tests/ -v
.venv/bin/python -c 'from ascii_art import image_to_ascii; print(image_to_ascii("tests/fixtures/diagonal.ppm", width=4))'
```

Compare the printed 4×4 fixture conversion with the agreed pixel-to-character behavior: a bright diagonal should be visually distinguishable from its dark background. If the public result or a test disagrees with your approved contract, correct the owning requirement, design, oracle, or implementation; do not announce success because a generated summary says “done.”

If interrupted, **keep the worktree**. Read the reported cause and have the host inspect the feature's handoff and briefs, using `nwdes document` for reading views. Resolve the specific missing input or mismatched authority, then continue from current evidence. nwdes keeps no workflow cursor. `/nw-buddy` (Codex: `$nw-buddy`) can help route recovery.

This tutorial demonstrates delivery using real starter inputs, not a promise that the inputs alone establish completion. For a new project without a starter fixture, see [Hello nWave](../tutorial-hello-nwave/).
