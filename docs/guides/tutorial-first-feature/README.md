# Tutorial: Your First Feature in an Existing Project

Use this walkthrough for a small change to a Python project that already has a public behavior and a working test command. The example is login with email and password **in an application that already has an identity store and a login boundary**. If your project does not, choose a similarly bounded feature of your own; do not ask nWave to invent an authentication system to make the example fit.

This beta has **no published nWave package**. Installation is from a local clone; the work may require several conversations, reviews, and paid model turns. There is no fixed completion time or guaranteed artifact list.

## 1. Install, then opt in to your project

With Python 3.11+, [uv](https://docs.astral.sh/uv/), Git, and Claude Code **or** Codex CLI available, run this in a terminal:

```bash
git clone https://github.com/nWave-ai/nWave.git
cd nWave
uv sync
NWAVE_REPO="$(pwd -P)"
uv run python -m nwave_ai.cli install --platform claude-code
uv run python -m nwave_ai.cli doctor
```

If using **Codex instead of Claude Code**, use `uv run python -m nwave_ai.cli install --platform codex` and check the installer's Codex-specific final validation; `doctor` checks Claude Code, not a Codex-only install. A package-index or `uv tool install .` route cannot currently install the complete framework assets in this beta. The checkout's CLI lives at `"$NWAVE_REPO/.venv/bin/nwave-ai"`; keep `NWAVE_REPO` in the same terminal when changing directories. Restart your chosen AI host after installation so it loads the new assets.

```bash
cd /path/to/your/existing-project
"$NWAVE_REPO/.venv/bin/nwave-ai" project enable
"$NWAVE_REPO/.venv/bin/nwave-ai" status
```

Stop if status does not say `This project is active.` Enabling writes `.nwave/config.json` with `enabled: true` and updates `.gitignore` to keep the configuration trackable. Inspect both changes before committing. Optional project guidance for `CLAUDE.md` or `AGENTS.md` is offered separately; `project enable --yes` adds the managed beta sections without a prompt if you want them.

## 2. Start a bounded feature request

Launch `claude` or `codex` **from the enabled project**. Commands in the next sections are entered in that host, not your terminal. Claude Code uses `/nw-discuss`; Codex uses the skill `$nw-discuss`. Substitute the same prefix for each subsequent wave (`/nw-design` → `$nw-design`, etc.).

For the login example, start with:

```text
/nw-discuss "Add email/password login through this project's existing login interface and identity store. Confirm the intended success result and the response to invalid credentials with me before implementation."
```

In Codex, enter `$nw-discuss` followed by that same request. Answer questions about existing behavior and what an observer should see; do not let a proposed token format or security rule become a requirement without your approval. Review the product brief reported by the command. The default feature-scoped DISCUSS path is `docs/feature/<feature-id>/brief.md`, but project configuration can change it. A printed path is not proof the content is correct.

## 3. Settle only the necessary design

For login, the existing auth boundary, credential-checking owner, and error translation are consequential. Ask for a design that **reuses** the project's real interfaces:

```text
/nw-design "For the agreed login behavior, identify the existing auth and identity boundaries to reuse, and resolve any missing public contract before tests are written."
```

Review the rendered architecture brief or ADR path the host reports. If the project already has adequate design for a smaller feature, say so and ask the host to reuse it rather than generating an unnecessary new architecture. Fix disagreements with the requirement before proceeding.

## 4. Make the expected behavior executable

```text
/nw-distill "Produce the public-port acceptance oracle for the agreed login behavior using the existing test infrastructure."
```

Read the reported acceptance brief and actual test locator. Run the verification command the host reports **in the project environment**; the intended preimplementation outcome is a meaningful RED assertion, not a missing import, dependency, or broken fixture. If it cannot create an executable oracle, resolve the specific missing contract or test infrastructure first. Paths such as `tests/acceptance/test_us001_user_login.py` are not universal.

## 5. Deliver and observe

```text
/nw-deliver "Implement the agreed login behavior against the accepted public oracle, preserving the existing auth contract."
```

`/nw-deliver` drives nwdes through the host; it does not guarantee one implementation step per scenario, commits after every test, a fixed mutation score, or an automatic pass. Review role results against actual evidence. Run the **reported project verification command** again, then exercise the login interface with valid and invalid credentials through its public entry point. Compare those observations with your approved brief; passing tests alone do not establish usefulness.

If interrupted or refused, keep the worktree and have the host read the feature handoff and briefs (`nwdes document`). Correct the owning decision or missing prerequisite, then resume from current evidence. nwdes stores no workflow cursor. `/nw-buddy` (Codex: `$nw-buddy`) can explain routing, but does not replace verification or a human decision.

For a smaller existing-project request, the host may reuse adequate requirements or design and omit a redundant wave. This tutorial makes the four decisions visible because login changes a public contract. Your final result is the behavior observed at your own app boundary, with its actual tests and reviewed decisions—not a predetermined folder tree.
